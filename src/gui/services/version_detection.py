"""
Version Detection Service.
Detects Minecraft version and mod loader from server folders.
"""

import os
import re
import glob
import json
from typing import Optional


class VersionDetector:
    """Detects Minecraft version and loader type from modpack folders"""

    @staticmethod
    def detect_mc_version(folder: str) -> str:
        """
        Detect Minecraft version from modded server folder.

        Checks multiple sources:
        - modpack_info.json (PyCraft created)
        - Forge/NeoForge libraries folder
        - Jar file names
        - variables.txt (ServerPackCreator format)
        - Run scripts

        Args:
            folder: Path to server folder

        Returns:
            Minecraft version string (e.g., "1.20.1") or empty string if not detected
        """
        # First check modpack_info.json (created by PyCraft during install)
        info_file = os.path.join(folder, "modpack_info.json")
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                mc_ver = info.get("minecraft_version")
                if mc_ver:
                    return mc_ver
            except Exception:
                pass

        # Check libraries folder for forge (has MC version in folder name)
        forge_libs = os.path.join(folder, "libraries", "net", "minecraftforge", "forge")
        if os.path.exists(forge_libs):
            try:
                versions = os.listdir(forge_libs)
                if versions:
                    # Folder name is like "1.20.1-47.2.0"
                    version_folder = versions[0]
                    if '-' in version_folder:
                        mc_ver = version_folder.split('-')[0]
                        return mc_ver
            except Exception:
                pass

        # Check for forge jar name
        forge_jars = glob.glob(os.path.join(folder, "forge-*.jar"))
        if forge_jars:
            jar_name = os.path.basename(forge_jars[0])
            match = re.search(r'forge-([\d.]+)-', jar_name)
            if match:
                return match.group(1)

        # Check for neoforge libs
        neoforge_libs = os.path.join(folder, "libraries", "net", "neoforged", "neoforge")
        if os.path.exists(neoforge_libs):
            try:
                # NeoForge version starts with MC version (e.g., 21.1.77 for MC 1.21.1)
                versions = os.listdir(neoforge_libs)
                if versions:
                    # Parse NeoForge version to get MC version
                    # Format: MAJOR.MINOR.PATCH where MAJOR.MINOR maps to MC 1.MAJOR.MINOR
                    version = versions[0]
                    match = re.match(r'(\d+)\.(\d+)\.', version)
                    if match:
                        major, minor = match.groups()
                        return f"1.{major}.{minor}" if minor != "0" else f"1.{major}"
            except Exception:
                pass

        # Check variables.txt (ServerPackCreator format by Griefed)
        variables_path = os.path.join(folder, "variables.txt")
        if os.path.exists(variables_path):
            try:
                with open(variables_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Parse MINECRAFT_VERSION=1.20.1
                    match = re.search(r'^MINECRAFT_VERSION=(.+)$', content, re.MULTILINE)
                    if match:
                        return match.group(1).strip()
            except Exception:
                pass

        # Check run.bat/run.sh and startserver.bat/sh for version info
        for script in ["run.bat", "run.sh", "startserver.bat", "startserver.sh"]:
            script_path = os.path.join(folder, script)
            if os.path.exists(script_path):
                try:
                    with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
                        script_content = f.read()
                        # Look for NEOFORGE_VERSION (ATM modpacks format)
                        neoforge_match = re.search(r'NEOFORGE_VERSION[=\s]+(\d+)\.(\d+)\.(\d+)', script_content)
                        if neoforge_match:
                            major, minor, patch = neoforge_match.groups()
                            if minor == "0":
                                return f"1.{major}"
                            else:
                                return f"1.{major}.{minor}"
                        # Look for MC version pattern
                        match = re.search(r'minecraft[_-]?server[_-]?([\d.]+)', script_content, re.IGNORECASE)
                        if match:
                            return match.group(1)
                        match = re.search(r'forge[/-]([\d.]+)-[\d.]+', script_content, re.IGNORECASE)
                        if match:
                            return match.group(1)
                except Exception:
                    pass

        return ""

    @staticmethod
    def detect_loader(folder: str) -> str:
        """
        Detect modpack loader type and version from server folder.

        Detects:
        - Forge (legacy and modern)
        - NeoForge
        - Fabric
        - Quilt

        Args:
            folder: Path to server folder

        Returns:
            Loader string (e.g., "Forge 47.2.0") or empty string if not detected
        """
        # Check variables.txt (ServerPackCreator format by Griefed)
        variables_path = os.path.join(folder, "variables.txt")
        if os.path.exists(variables_path):
            try:
                with open(variables_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    loader_match = re.search(r'^MODLOADER=(.+)$', content, re.MULTILINE)
                    version_match = re.search(r'^MODLOADER_VERSION=(.+)$', content, re.MULTILINE)
                    if loader_match:
                        loader = loader_match.group(1).strip()
                        version = version_match.group(1).strip() if version_match else ""
                        if version:
                            return f"{loader} {version}"
                        return loader
            except Exception:
                pass

        # Check for Forge
        forge_jars = glob.glob(os.path.join(folder, "forge-*.jar"))
        if forge_jars:
            jar_name = os.path.basename(forge_jars[0])
            # Extract version from forge-1.20.1-47.2.0.jar
            match = re.search(r'forge-[\d.]+-(\d+\.\d+\.\d+)', jar_name)
            if match:
                return f"Forge {match.group(1)}"
            return "Forge"

        # Check for NeoForge jars
        neoforge_jars = glob.glob(os.path.join(folder, "neoforge-*.jar"))
        if neoforge_jars:
            jar_name = os.path.basename(neoforge_jars[0])
            match = re.search(r'neoforge-([\d.]+)', jar_name)
            if match:
                return f"NeoForge {match.group(1)}"
            return "NeoForge"

        # Check for NeoForge from startserver.bat/sh (ATM modpacks)
        for script in ["startserver.bat", "startserver.sh"]:
            script_path = os.path.join(folder, script)
            if os.path.exists(script_path):
                try:
                    with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
                        script_content = f.read()
                        if 'neoforge' in script_content.lower():
                            neoforge_match = re.search(r'NEOFORGE_VERSION[=\s]+(\d+\.\d+\.\d+)', script_content)
                            if neoforge_match:
                                return f"NeoForge {neoforge_match.group(1)}"
                            return "NeoForge"
                except Exception:
                    pass

        # Check for Fabric - multiple detection methods
        fabric_launcher_jar = os.path.join(folder, "fabric-server-launcher.jar")
        fabric_launch_jar = os.path.join(folder, "fabric-server-launch.jar")
        fabric_jars = glob.glob(os.path.join(folder, "fabric-server-*.jar"))

        if os.path.exists(fabric_launcher_jar) or os.path.exists(fabric_launch_jar) or fabric_jars:
            # Method 1: Check .fabric/server/version.json (created by Fabric installer)
            fabric_version_file = os.path.join(folder, ".fabric", "server", "version.json")
            if os.path.exists(fabric_version_file):
                try:
                    with open(fabric_version_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        loader_version = data.get("loader", {}).get("version")
                        if loader_version:
                            return f"Fabric Loader {loader_version}"
                except:
                    pass

            # Method 2: Try to get version from libraries folder
            fabric_loader_libs = os.path.join(folder, "libraries", "net", "fabricmc", "fabric-loader")
            if os.path.exists(fabric_loader_libs):
                try:
                    versions = os.listdir(fabric_loader_libs)
                    if versions:
                        return f"Fabric Loader {versions[0]}"
                except:
                    pass

            # Method 3: Try to get version from server log
            logs_path = os.path.join(folder, "logs", "latest.log")
            if os.path.exists(logs_path):
                try:
                    with open(logs_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f):
                            if i > 50:
                                break
                            # Look for "Fabric Loader 0.16.14"
                            if 'fabric loader' in line.lower():
                                match = re.search(r'fabric\s+loader\s+([\d.]+)', line, re.IGNORECASE)
                                if match:
                                    return f"Fabric Loader {match.group(1)}"
                except:
                    pass

            # Method 4: Fallback - try old naming pattern from jar name
            if fabric_jars:
                jar_name = os.path.basename(fabric_jars[0])
                match = re.search(r'fabric-server-mc\.[\d.]+-(\d+\.\d+\.\d+)', jar_name)
                if match:
                    return f"Fabric Loader {match.group(1)}"

            return "Fabric"

        # Check for Quilt
        quilt_jars = glob.glob(os.path.join(folder, "quilt-server-*.jar"))
        if quilt_jars:
            jar_name = os.path.basename(quilt_jars[0])
            match = re.search(r'quilt-server-[\d.]+-([\d.]+)', jar_name)
            if match:
                return f"Quilt {match.group(1)}"
            return "Quilt"

        # Check libraries folder structure (modern Forge/NeoForge)
        forge_libs = os.path.join(folder, "libraries", "net", "minecraftforge", "forge")
        if os.path.exists(forge_libs):
            try:
                versions = os.listdir(forge_libs)
                if versions:
                    # Get first version folder (e.g., "1.20.1-47.2.0")
                    version_folder = versions[0]
                    # Extract just the forge version part
                    if '-' in version_folder:
                        forge_ver = version_folder.split('-')[-1]
                        return f"Forge {forge_ver}"
                    return f"Forge {version_folder}"
            except Exception:
                pass

        neoforge_libs = os.path.join(folder, "libraries", "net", "neoforged", "neoforge")
        if os.path.exists(neoforge_libs):
            try:
                versions = os.listdir(neoforge_libs)
                if versions:
                    return f"NeoForge {versions[0]}"
            except Exception:
                pass

        # Check for run scripts that might indicate loader (fallback)
        if os.path.exists(os.path.join(folder, "run.bat")) or os.path.exists(os.path.join(folder, "run.sh")):
            # Try to detect from run script content
            for script in ["run.bat", "run.sh"]:
                script_path = os.path.join(folder, script)
                if os.path.exists(script_path):
                    try:
                        with open(script_path, 'r') as f:
                            content = f.read()
                            # Look for forge version in script
                            match = re.search(r'forge[/-]([\d.]+)-([\d.]+)', content, re.IGNORECASE)
                            if match:
                                return f"Forge {match.group(2)}"
                            match = re.search(r'neoforge[/-]([\d.]+)', content, re.IGNORECASE)
                            if match:
                                return f"NeoForge {match.group(1)}"
                            # Generic detection
                            content_lower = content.lower()
                            if 'neoforge' in content_lower:
                                return "NeoForge"
                            elif 'forge' in content_lower:
                                return "Forge"
                            elif 'fabric' in content_lower:
                                return "Fabric"
                            elif 'quilt' in content_lower:
                                return "Quilt"
                    except Exception:
                        pass

        return ""
