"""
Auto-Healer for Modded Minecraft Servers v2.0

This module provides automatic crash detection, analysis, and resolution
for modded Minecraft servers. It can:
- Pre-scan mods and remove known client-only mods
- Detect crashes and identify the cause
- Install missing dependencies from Modrinth
- Remove problematic mods automatically
- Generate detailed healing reports
"""

import json
import os
import re
import shutil
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import sys


class HealingAction(Enum):
    """Actions that can be taken to heal a crash"""
    REMOVE_MOD = "remove_mod"
    INSTALL_DEPENDENCY = "install_dependency"
    NONE = "none"


@dataclass
class HealingStep:
    """Record of a single healing action"""
    attempt: int
    action: HealingAction
    target: str
    reason: str
    success: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HealingReport:
    """Complete report of the healing session"""
    server_path: str
    loader: str
    minecraft_version: str
    start_time: str
    end_time: Optional[str] = None
    result: str = "in_progress"  # "success", "failed", "in_progress"
    total_attempts: int = 0
    mods_removed: List[Dict] = field(default_factory=list)
    mods_installed: List[Dict] = field(default_factory=list)
    steps: List[HealingStep] = field(default_factory=list)
    final_error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "server_path": self.server_path,
            "loader": self.loader,
            "minecraft_version": self.minecraft_version,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "result": self.result,
            "total_attempts": self.total_attempts,
            "mods_removed": self.mods_removed,
            "mods_installed": self.mods_installed,
            "steps": [
                {
                    "attempt": s.attempt,
                    "action": s.action.value,
                    "target": s.target,
                    "reason": s.reason,
                    "success": s.success,
                    "timestamp": s.timestamp
                } for s in self.steps
            ],
            "final_error": self.final_error
        }


class AutoHealer:
    """
    Auto-healing system for modded Minecraft servers.

    Flow:
    1. Pre-scan: Check mods against database, remove known client-only mods
    2. Start server
    3. If crash: Analyze log, apply fix, restart (up to MAX_ATTEMPTS)
    4. Generate report
    """

    MAX_ATTEMPTS = 6
    REMOVED_MODS_FOLDER = "mod_removed_by_pycraft"
    MODRINTH_API = "https://api.modrinth.com/v2"
    USER_AGENT = "PyCraft-AutoHealer/2.0.0 (github.com/OOMrConrado/PyCraft)"

    def __init__(
        self,
        server_path: str,
        loader: str,
        minecraft_version: str = None,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the AutoHealer.

        Args:
            server_path: Path to the server folder
            loader: Loader type ('fabric', 'forge', 'neoforge', 'quilt')
            minecraft_version: Minecraft version (e.g., "1.19.2")
            log_callback: Optional callback for logging messages to UI
        """
        self.server_path = server_path
        self.loader = loader.lower()
        self.minecraft_version = minecraft_version or self._detect_minecraft_version()
        self.log_callback = log_callback

        self.mods_folder = os.path.join(server_path, "mods")
        self.removed_folder = os.path.join(server_path, self.REMOVED_MODS_FOLDER)
        self.logs_folder = os.path.join(server_path, "logs")

        # Load database
        self.database = self._load_database()

        # Session tracking
        self.current_attempt = 0
        self.report = HealingReport(
            server_path=server_path,
            loader=loader,
            minecraft_version=self.minecraft_version,
            start_time=datetime.now().isoformat()
        )

        # Track what we've already tried to avoid loops
        self._removed_mods: List[str] = []
        self._installed_mods: List[str] = []
        self._failed_installs: List[str] = []

    def _log(self, message: str):
        """Log message to callback if available"""
        if self.log_callback:
            self.log_callback(message)

    def _detect_minecraft_version(self) -> str:
        """Try to detect Minecraft version from server files"""
        try:
            # Check latest.log for version
            log_path = os.path.join(self.server_path, "logs", "latest.log")
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(5000)  # Read first 5KB
                    match = re.search(r'minecraft server version (\d+\.\d+\.?\d*)', content, re.IGNORECASE)
                    if match:
                        return match.group(1)
                    match = re.search(r'Loading Minecraft (\d+\.\d+\.?\d*)', content, re.IGNORECASE)
                    if match:
                        return match.group(1)

            # Check for version.json
            version_file = os.path.join(self.server_path, "version.json")
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    data = json.load(f)
                    if "id" in data:
                        return data["id"]
        except Exception:
            pass

        return "1.20.1"  # Default fallback

    def _load_database(self) -> Dict:
        """Load the mod database"""
        try:
            # Try PyInstaller bundled location
            if hasattr(sys, '_MEIPASS'):
                path = os.path.join(sys._MEIPASS, 'data', 'mod_database.json')
            else:
                # Development paths
                possible_paths = [
                    os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'mod_database.json'),
                    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'data', 'mod_database.json'),
                ]
                path = None
                for p in possible_paths:
                    if os.path.exists(p):
                        path = os.path.abspath(p)
                        break

            if path and os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self._log(f"[AutoHealer] Warning: Could not load mod_database.json: {e}\n")

        return {"known_client_mods": {"mods": []}, "error_patterns": {"patterns": []}, "fatal_errors": {"patterns": []}}

    # ==================== PRE-SCAN PHASE ====================

    def run_prescan(self) -> List[Dict]:
        """
        Pre-scan mods folder and remove known client-only mods.
        Only uses local database for speed (no API calls).

        Returns:
            List of removed mods with filename and reason
        """
        removed = []

        if not os.path.exists(self.mods_folder):
            self._log("[AutoHealer] No mods folder found, skipping pre-scan\n")
            return removed

        self._log("[AutoHealer] Running pre-scan...\n")

        # Get list of known client-only mods from local database
        known_client_mods = self.database.get("known_client_mods", {}).get("mods", [])

        # Scan each mod in folder
        for filename in os.listdir(self.mods_folder):
            if not filename.endswith('.jar'):
                continue

            filename_lower = filename.lower()

            # Check against known client mods (local database only - fast)
            for mod_info in known_client_mods:
                matched = False
                for pattern in mod_info.get("patterns", []):
                    if pattern.lower() in filename_lower:
                        matched = True
                        break

                if matched:
                    reason = mod_info.get("reason", "Known client-only mod")
                    if self._remove_mod(filename, reason):
                        removed.append({
                            "filename": filename,
                            "reason": reason,
                            "phase": "prescan"
                        })
                    break

        if removed:
            self._log(f"[AutoHealer] Pre-scan removed {len(removed)} client-only mod(s)\n")
            for mod in removed:
                self._log(f"  - {mod['filename']}\n")
                self.report.mods_removed.append(mod)
        else:
            self._log("[AutoHealer] Pre-scan: No known client-only mods found\n")

        return removed

    def _check_modrinth_mod_type(self, filename: str) -> Optional[Dict]:
        """
        Check Modrinth API for mod type (client/server).

        Args:
            filename: Mod jar filename

        Returns:
            Dict with mod info or None
        """
        # Extract mod slug from filename (remove version numbers)
        slug = re.sub(r'[-_][\d\.]+.*\.jar$', '', filename, flags=re.IGNORECASE)
        slug = re.sub(r'\.jar$', '', slug)
        slug = slug.lower().replace('_', '-')

        try:
            headers = {"User-Agent": self.USER_AGENT}

            # Search for the mod
            response = requests.get(
                f"{self.MODRINTH_API}/search",
                headers=headers,
                params={
                    "query": slug,
                    "limit": 5,
                    "facets": '[["project_type:mod"]]'
                },
                timeout=10
            )
            response.raise_for_status()

            hits = response.json().get("hits", [])
            if not hits:
                return None

            # Find best match
            for hit in hits:
                if hit.get("slug", "").lower() == slug or slug in hit.get("slug", "").lower():
                    return {
                        "slug": hit.get("slug"),
                        "title": hit.get("title"),
                        "client_side": hit.get("client_side"),
                        "server_side": hit.get("server_side")
                    }

            return None

        except Exception:
            return None

    # ==================== CRASH HANDLING ====================

    def handle_crash(self, log_content: str) -> Tuple[bool, Optional[str]]:
        """
        Analyze crash log and attempt to fix.

        Args:
            log_content: Server log content

        Returns:
            Tuple of (should_retry, error_message_if_fatal)
        """
        self.current_attempt += 1
        self.report.total_attempts = self.current_attempt

        self._log(f"\n[AutoHealer] ========================================\n")
        self._log(f"[AutoHealer] Analyzing crash (attempt {self.current_attempt}/{self.MAX_ATTEMPTS})...\n")
        self._log(f"[AutoHealer] Log size: {len(log_content)} chars\n")

        # Check if max attempts reached
        if self.current_attempt >= self.MAX_ATTEMPTS:
            self._log("[AutoHealer] Max attempts reached. Giving up.\n")
            self.report.result = "failed"
            self.report.final_error = "Maximum healing attempts reached"
            return False, "The server could not start after 6 attempts. Check the healing report for details."

        # Check for fatal errors first
        fatal_error = self._check_fatal_errors(log_content)
        if fatal_error:
            self._log(f"[AutoHealer] Fatal error detected: {fatal_error}\n")
            self.report.result = "failed"
            self.report.final_error = fatal_error
            return False, fatal_error

        # Try to identify and fix the problem
        fix_applied = self._try_fix_crash(log_content)

        if fix_applied:
            return True, None  # Retry server
        else:
            # Could not identify fix
            self._log("[AutoHealer] Could not identify a fix for this crash\n")
            self.report.result = "failed"
            self.report.final_error = "Could not identify the cause of the crash"
            return False, "The auto-healer could not identify what's causing the crash. Check the logs for more details."

    def _check_fatal_errors(self, log_content: str) -> Optional[str]:
        """Check for fatal errors that can't be auto-fixed"""
        fatal_patterns = self.database.get("fatal_errors", {}).get("patterns", [])

        for pattern_info in fatal_patterns:
            regex = pattern_info.get("regex", "")
            if regex and re.search(regex, log_content, re.IGNORECASE):
                return pattern_info.get("user_message", pattern_info.get("description"))

        return None

    def _try_fix_crash(self, log_content: str) -> bool:
        """
        Try to fix the crash based on log analysis.

        Returns:
            True if a fix was applied, False otherwise
        """
        self._log("[AutoHealer] Searching for fixable issues...\n")

        # Priority 1: Check for missing dependencies
        missing_dep = self._extract_missing_dependency(log_content)
        self._log(f"[AutoHealer] Missing dependency found: {missing_dep}\n")
        if missing_dep:
            dep_name = missing_dep.get("dependency")
            requiring_mod = missing_dep.get("requiring_mod")

            self._log(f"[AutoHealer] Missing dependency: {dep_name} (required by {requiring_mod})\n")

            # Try to install the dependency
            if dep_name not in self._failed_installs:
                self._log(f"[AutoHealer] Attempting to install dependency: {dep_name}\n")
                if self._install_dependency(dep_name):
                    self.report.steps.append(HealingStep(
                        attempt=self.current_attempt,
                        action=HealingAction.INSTALL_DEPENDENCY,
                        target=dep_name,
                        reason=f"Required by {requiring_mod}",
                        success=True
                    ))
                    return True
                else:
                    self._log(f"[AutoHealer] Failed to install {dep_name}, adding to failed list\n")
                    self._failed_installs.append(dep_name)
            else:
                self._log(f"[AutoHealer] Dependency {dep_name} already in failed installs list\n")

            # If install failed, try to remove the mod that requires it
            if requiring_mod:
                self._log(f"[AutoHealer] Trying to remove mod that requires {dep_name}: {requiring_mod}\n")
                mod_file = self._find_mod_file(requiring_mod)
                self._log(f"[AutoHealer] Found mod file: {mod_file}\n")
                if mod_file and mod_file not in self._removed_mods:
                    reason = f"Requires {dep_name} which could not be installed"
                    if self._remove_mod(mod_file, reason):
                        self.report.steps.append(HealingStep(
                            attempt=self.current_attempt,
                            action=HealingAction.REMOVE_MOD,
                            target=mod_file,
                            reason=reason,
                            success=True
                        ))
                        return True
                    else:
                        self._log(f"[AutoHealer] Failed to remove {mod_file}\n")
                elif mod_file in self._removed_mods:
                    self._log(f"[AutoHealer] Mod {mod_file} already removed\n")

        # Priority 2: Check for client-only mod errors
        client_mod = self._extract_client_mod_from_error(log_content)
        if client_mod and client_mod not in self._removed_mods:
            mod_file = self._find_mod_file(client_mod)
            if mod_file:
                reason = "Client-only mod causing server crash"
                if self._remove_mod(mod_file, reason):
                    self.report.steps.append(HealingStep(
                        attempt=self.current_attempt,
                        action=HealingAction.REMOVE_MOD,
                        target=mod_file,
                        reason=reason,
                        success=True
                    ))
                    return True

        # Priority 3: Check error patterns from database
        error_patterns = self.database.get("error_patterns", {}).get("patterns", [])
        for pattern_info in error_patterns:
            regex = pattern_info.get("regex", "")
            if regex and re.search(regex, log_content, re.IGNORECASE):
                action = pattern_info.get("action")

                if action == "identify_and_remove":
                    mod_id = self._extract_mod_from_error(log_content, pattern_info)
                    if mod_id and mod_id not in self._removed_mods:
                        mod_file = self._find_mod_file(mod_id)
                        if mod_file:
                            reason = pattern_info.get("description", "Matched error pattern")
                            if self._remove_mod(mod_file, reason):
                                self.report.steps.append(HealingStep(
                                    attempt=self.current_attempt,
                                    action=HealingAction.REMOVE_MOD,
                                    target=mod_file,
                                    reason=reason,
                                    success=True
                                ))
                                return True

        return False

    def _extract_missing_dependency(self, log_content: str) -> Optional[Dict]:
        """Extract missing dependency information from log"""
        # Dependencies to skip (loaders, minecraft, java)
        skip_deps = {'minecraft', 'java', 'forge', 'neoforge', 'fabric', 'fabricloader', 'quilt', 'fabric-api'}

        patterns = [
            # Forge/NeoForge pattern: "Mod curiouslanterns requires radiantgear 2.0.0+1.19.2"
            # With optional color codes (§e, §r, §6, etc.)
            r'Mod\s+§?[a-z0-9]?([a-zA-Z0-9_]+)§?[a-z0-9]?\s+requires\s+§?[a-z0-9]?([a-zA-Z0-9_]+)',
            # Simple Forge pattern without color codes
            r'Mod\s+([a-zA-Z0-9_]+)\s+requires\s+([a-zA-Z0-9_]+)',
            # Generic pattern with quotes
            r'mod\s+["\']?([a-zA-Z0-9_-]+)["\']?\s+requires\s+["\']?([a-zA-Z0-9_-]+)',
            # Fabric pattern: "Mod 'X' requires Y"
            r"Mod\s+'([^']+)'\s+requires\s+'?([a-zA-Z0-9_-]+)",
        ]

        # Use findall to get ALL matches, then filter
        for pattern in patterns:
            matches = re.findall(pattern, log_content, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2:
                    requiring_mod = match[0]
                    dependency = match[1]
                    # Skip loader/system dependencies
                    if dependency.lower() in skip_deps:
                        continue
                    # Skip if we already tried to install this dependency and failed
                    if dependency in self._failed_installs:
                        continue
                    # Skip if we already installed this dependency
                    if dependency in self._installed_mods:
                        continue
                    return {
                        "requiring_mod": requiring_mod,
                        "dependency": dependency
                    }

        # Single-group patterns (Fabric style: "requires mod X")
        single_patterns = [
            r'requires\s+mod\s+["\']?([a-zA-Z0-9_-]+)',
            r'requires\s+\{([a-zA-Z0-9_-]+)\}',
        ]

        for pattern in single_patterns:
            matches = re.findall(pattern, log_content, re.IGNORECASE)
            for match in matches:
                dependency = match if isinstance(match, str) else match[0]
                if dependency.lower() in skip_deps:
                    continue
                if dependency in self._failed_installs:
                    continue
                if dependency in self._installed_mods:
                    continue
                return {
                    "requiring_mod": None,
                    "dependency": dependency
                }

        return None

    def _extract_client_mod_from_error(self, log_content: str) -> Optional[str]:
        """Extract client-only mod ID from mixin/class errors"""
        # Pattern: "citresewn.mixins.json:citenchantment.ItemRendererMixin"
        mixin_pattern = r'([a-zA-Z0-9_-]+)\.mixins\.json'
        matches = re.findall(mixin_pattern, log_content)

        if matches:
            # Return the most common one (likely the culprit)
            from collections import Counter
            counter = Counter(matches)
            return counter.most_common(1)[0][0]

        return None

    def _extract_mod_from_error(self, log_content: str, pattern_info: Dict) -> Optional[str]:
        """Extract mod ID based on extraction method specified in pattern"""
        extract_from = pattern_info.get("extract_mod_from", "error_message")

        if extract_from == "mixin_config":
            return self._extract_client_mod_from_error(log_content)

        elif extract_from == "mod_id":
            # Look for mod ID in error
            match = re.search(r'from mod[:\s]+([a-zA-Z0-9_-]+)', log_content, re.IGNORECASE)
            if match:
                return match.group(1)

        elif extract_from == "stacktrace":
            # Look for mod package in stacktrace
            package_pattern = r'at\s+([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*)\.\w+'
            packages = re.findall(package_pattern, log_content)

            # Filter to potential mod packages (not minecraft/java/forge)
            for pkg in packages:
                if not any(skip in pkg for skip in ['java.', 'sun.', 'minecraft.', 'mojang.', 'forge.', 'neoforge.', 'fabric.', 'cpw.mods']):
                    # Extract first part as mod id
                    parts = pkg.split('.')
                    if len(parts) >= 2:
                        return parts[0]

        return None

    def _find_mod_file(self, mod_id: str) -> Optional[str]:
        """Find the jar file for a mod ID"""
        if not os.path.exists(self.mods_folder):
            return None

        mod_id_lower = mod_id.lower().replace('-', '').replace('_', '')

        for filename in os.listdir(self.mods_folder):
            if not filename.endswith('.jar'):
                continue

            filename_lower = filename.lower().replace('-', '').replace('_', '')

            if mod_id_lower in filename_lower:
                return filename

        return None

    # ==================== MOD OPERATIONS ====================

    def _remove_mod(self, filename: str, reason: str) -> bool:
        """Move a mod to the removed folder"""
        if filename in self._removed_mods:
            return False

        src = os.path.join(self.mods_folder, filename)
        if not os.path.exists(src):
            return False

        # Create removed folder if needed
        os.makedirs(self.removed_folder, exist_ok=True)

        dst = os.path.join(self.removed_folder, filename)

        # Handle duplicates
        if os.path.exists(dst):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dst):
                dst = os.path.join(self.removed_folder, f"{base}_{counter}{ext}")
                counter += 1

        try:
            shutil.move(src, dst)
            self._removed_mods.append(filename)
            self._log(f"[AutoHealer] Removed: {filename}\n")
            self._log(f"  Reason: {reason}\n")

            self.report.mods_removed.append({
                "filename": filename,
                "reason": reason,
                "phase": "healing"
            })

            return True
        except Exception as e:
            self._log(f"[AutoHealer] Failed to remove {filename}: {e}\n")
            return False

    def _install_dependency(self, mod_slug: str) -> bool:
        """Install a dependency from Modrinth"""
        if mod_slug in self._installed_mods:
            return False

        # Normalize slug (underscores to hyphens, common name mappings)
        slug_mappings = {
            'cloth_config': 'cloth-config',
            'clothconfig': 'cloth-config',
            'fabricloader': 'fabric-api',
            'fabric_api': 'fabric-api',
        }

        normalized_slug = slug_mappings.get(mod_slug.lower(), mod_slug.lower().replace('_', '-'))

        self._log(f"[AutoHealer] Searching for '{normalized_slug}' on Modrinth...\n")

        try:
            headers = {"User-Agent": self.USER_AGENT}

            # Try multiple search variations
            search_queries = [normalized_slug]
            if normalized_slug != mod_slug.lower():
                search_queries.append(mod_slug.lower())

            hits = []
            for query in search_queries:
                # Search for the mod
                response = requests.get(
                    f"{self.MODRINTH_API}/search",
                    headers=headers,
                    params={
                        "query": query,
                        "limit": 10,
                        "facets": f'[["project_type:mod"],["categories:{self.loader}"]]'
                    },
                    timeout=15
                )
                response.raise_for_status()
                hits = response.json().get("hits", [])
                if hits:
                    break

            if not hits:
                self._log(f"[AutoHealer] Mod '{mod_slug}' not found on Modrinth\n")
                return False

            # Find best match - check both original and normalized slug
            best_match = None
            for hit in hits:
                hit_slug = hit.get("slug", "").lower()
                if hit_slug == mod_slug.lower() or hit_slug == normalized_slug:
                    best_match = hit
                    break

            if not best_match:
                # Take first result if no exact match
                best_match = hits[0]
                self._log(f"[AutoHealer] No exact match, using first result: {best_match.get('slug')}\n")

            project_id = best_match.get("project_id") or best_match.get("slug")
            project_title = best_match.get("title", mod_slug)

            self._log(f"[AutoHealer] Found: {project_title}\n")

            # Get versions
            response = requests.get(
                f"{self.MODRINTH_API}/project/{project_id}/version",
                headers=headers,
                params={
                    "loaders": f'["{self.loader}"]',
                    "game_versions": f'["{self.minecraft_version}"]'
                },
                timeout=15
            )
            response.raise_for_status()
            versions = response.json()

            if not versions:
                # Try without version filter
                response = requests.get(
                    f"{self.MODRINTH_API}/project/{project_id}/version",
                    headers=headers,
                    params={"loaders": f'["{self.loader}"]'},
                    timeout=15
                )
                response.raise_for_status()
                versions = response.json()

            if not versions:
                self._log(f"[AutoHealer] No compatible version found for {self.loader}\n")
                return False

            # Get first (most recent) version
            version = versions[0]
            files = version.get("files", [])

            # Find jar file
            jar_file = None
            for f in files:
                if f.get("filename", "").endswith(".jar"):
                    if f.get("primary", False):
                        jar_file = f
                        break
                    elif not jar_file:
                        jar_file = f

            if not jar_file:
                self._log(f"[AutoHealer] No jar file found in version\n")
                return False

            # Download
            download_url = jar_file.get("url")
            filename = jar_file.get("filename")

            self._log(f"[AutoHealer] Downloading {filename}...\n")

            response = requests.get(download_url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()

            os.makedirs(self.mods_folder, exist_ok=True)
            dest_path = os.path.join(self.mods_folder, filename)

            if os.path.exists(dest_path):
                self._log(f"[AutoHealer] {filename} already exists\n")
                self._installed_mods.append(mod_slug)
                return True

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            self._log(f"[AutoHealer] Installed: {filename}\n")
            self._installed_mods.append(mod_slug)

            self.report.mods_installed.append({
                "slug": mod_slug,
                "filename": filename,
                "title": project_title
            })

            return True

        except Exception as e:
            self._log(f"[AutoHealer] Failed to install {mod_slug}: {e}\n")
            return False

    # ==================== REPORT GENERATION ====================

    def mark_success(self):
        """Mark the healing session as successful"""
        self.report.result = "success"
        self.report.end_time = datetime.now().isoformat()

    def mark_failed(self, error: str):
        """Mark the healing session as failed"""
        self.report.result = "failed"
        self.report.end_time = datetime.now().isoformat()
        self.report.final_error = error

    def generate_report_file(self) -> str:
        """
        Generate the healing report file.

        Returns:
            Path to the report file
        """
        self.report.end_time = datetime.now().isoformat()
        os.makedirs(self.logs_folder, exist_ok=True)

        report_path = os.path.join(self.logs_folder, "pycraft_healing_report.txt")

        lines = [
            "=" * 60,
            "PyCraft Auto-Healer Report",
            "=" * 60,
            "",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Server: {self.server_path}",
            f"Loader: {self.loader.capitalize()} {self.minecraft_version}",
            f"Result: {self.report.result.upper()}",
            f"Total Attempts: {self.report.total_attempts}",
            "",
        ]

        # Pre-scan section
        prescan_mods = [m for m in self.report.mods_removed if m.get("phase") == "prescan"]
        if prescan_mods:
            lines.append("=" * 60)
            lines.append("PRE-SCAN PHASE")
            lines.append("=" * 60)
            lines.append(f"Removed {len(prescan_mods)} client-only mod(s):")
            for mod in prescan_mods:
                lines.append(f"  - {mod['filename']}")
                lines.append(f"    Reason: {mod['reason']}")
            lines.append("")

        # Healing steps
        if self.report.steps:
            lines.append("=" * 60)
            lines.append("HEALING ATTEMPTS")
            lines.append("=" * 60)

            current_attempt = 0
            for step in self.report.steps:
                if step.attempt != current_attempt:
                    current_attempt = step.attempt
                    lines.append(f"\n--- Attempt {current_attempt} ---")

                action_str = "Removed" if step.action == HealingAction.REMOVE_MOD else "Installed"
                status = "OK" if step.success else "FAILED"
                lines.append(f"  [{status}] {action_str}: {step.target}")
                lines.append(f"       Reason: {step.reason}")
            lines.append("")

        # Installed mods
        if self.report.mods_installed:
            lines.append("=" * 60)
            lines.append("DEPENDENCIES INSTALLED")
            lines.append("=" * 60)
            for mod in self.report.mods_installed:
                lines.append(f"  + {mod['filename']}")
                lines.append(f"    ({mod['title']})")
            lines.append("")

        # All removed mods
        healing_mods = [m for m in self.report.mods_removed if m.get("phase") == "healing"]
        if healing_mods:
            lines.append("=" * 60)
            lines.append("MODS REMOVED DURING HEALING")
            lines.append("=" * 60)
            for mod in healing_mods:
                lines.append(f"  - {mod['filename']}")
                lines.append(f"    Reason: {mod['reason']}")
            lines.append("")

        # Final error if failed
        if self.report.result == "failed" and self.report.final_error:
            lines.append("=" * 60)
            lines.append("FINAL ERROR")
            lines.append("=" * 60)
            lines.append(self.report.final_error)
            lines.append("")

        # Summary
        lines.append("=" * 60)
        lines.append("SUMMARY")
        lines.append("=" * 60)
        lines.append(f"Mods removed: {len(self.report.mods_removed)}")
        lines.append(f"Mods installed: {len(self.report.mods_installed)}")
        lines.append(f"Location of removed mods: {self.REMOVED_MODS_FOLDER}/")
        lines.append("")

        # Write file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return report_path

    def get_summary(self) -> Dict:
        """Get summary for UI display"""
        return {
            "result": self.report.result,
            "attempts": self.report.total_attempts,
            "mods_removed": self.report.mods_removed,
            "mods_installed": self.report.mods_installed,
            "final_error": self.report.final_error,
            "report_path": os.path.join(self.logs_folder, "pycraft_healing_report.txt")
        }

    def reset(self):
        """Reset the healer for a new session"""
        self.current_attempt = 0
        self.report = HealingReport(
            server_path=self.server_path,
            loader=self.loader,
            minecraft_version=self.minecraft_version,
            start_time=datetime.now().isoformat()
        )
        self._removed_mods = []
        self._installed_mods = []
        self._failed_installs = []


def detect_crash_in_log(log_content: str) -> bool:
    """
    Detect if log indicates a crash vs normal shutdown.

    Args:
        log_content: Server log content

    Returns:
        True if crash detected, False otherwise
    """
    # Success indicators - server started properly
    if re.search(r'Done \(\d+\.?\d*s\)!', log_content):
        return False

    # Crash indicators
    crash_patterns = [
        r"---- Minecraft Crash Report ----",
        r"Exception in thread",
        r"\[.*FATAL.*\]",
        r"Error during.*initialization",
        r"A mod crashed on startup",
        r"Mixin apply.*failed",
        r"ModLoadingException",
        r"LoadingFailedException",
        r"Failed to start the minecraft server",
        # Missing dependency patterns
        r"Missing or unsatisfied dependencies",
        r"Unsatisfied dependency",
        r"mod\s+\w+\s+requires\s+\w+",  # "Mod X requires Y" pattern
        r"requires.*is not installed",
        r"requires.*not found",
        # Forge/NeoForge specific
        r"net\.minecraftforge\.fml\.common\.MissingModsException",
        r"Mod.*requires.*version",
        # General errors that indicate crash
        r"Caused by:.*Exception",
        r"java\.lang\.\w*Exception",
        r"java\.lang\.\w*Error",
    ]

    for pattern in crash_patterns:
        if re.search(pattern, log_content, re.IGNORECASE):
            return True

    return False
