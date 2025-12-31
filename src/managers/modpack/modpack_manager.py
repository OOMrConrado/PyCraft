import os
import json
import sys
import zipfile
import shutil
import requests
from typing import Optional, Callable, Dict, List, Tuple, Set
from pathlib import Path

from ...core.api import ModrinthAPI, CurseForgeAPI
from ..loader import LoaderManager
from ..java import JavaManager


class ModpackManager:
    """Manages the download and installation of complete modpacks"""

    def __init__(self):
        self.modrinth_api = ModrinthAPI()
        self.curseforge_api = None  # Initialized if API key is available
        self.loader_manager = LoaderManager()
        self.java_manager = JavaManager()
        self._known_issues_cache = None

    def set_curseforge_api_key(self, api_key: str):
        """Configures the CurseForge API key"""
        self.curseforge_api = CurseForgeAPI(api_key)

    def _load_known_issues(self) -> Dict:
        """
        Load the global known_issues.json database.
        This contains known client-only mods and crash patterns.

        Returns:
            Dict with known issues data, or empty dict if not found
        """
        if self._known_issues_cache is not None:
            return self._known_issues_cache

        try:
            # Try PyInstaller bundled location first
            if hasattr(sys, '_MEIPASS'):
                path = os.path.join(sys._MEIPASS, 'data', 'known_issues.json')
            else:
                # Development path - try multiple locations
                possible_paths = [
                    os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'known_issues.json'),
                    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'data', 'known_issues.json'),
                ]
                path = None
                for p in possible_paths:
                    if os.path.exists(p):
                        path = p
                        break

            if path and os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self._known_issues_cache = json.load(f)
                    return self._known_issues_cache
        except Exception:
            pass

        self._known_issues_cache = {"loaders": {}, "universal_patterns": []}
        return self._known_issues_cache

    def _get_known_client_mods(self, loader: str = None) -> Set[str]:
        """
        Get the set of known client-only mod patterns from known_issues.json.

        Args:
            loader: Optional loader type ('fabric', 'forge', 'neoforge', 'quilt')
                   If None, returns mods from all loaders.

        Returns:
            Set of mod pattern strings (lowercase)
        """
        known_issues = self._load_known_issues()
        patterns = set()

        loaders_data = known_issues.get("loaders", {})

        if loader:
            # Get patterns for specific loader
            loader_data = loaders_data.get(loader.lower(), {})
            for mod in loader_data.get("client_only_mods", []):
                for pattern in mod.get("patterns", []):
                    patterns.add(pattern.lower())
        else:
            # Get patterns from all loaders
            for loader_name, loader_data in loaders_data.items():
                for mod in loader_data.get("client_only_mods", []):
                    for pattern in mod.get("patterns", []):
                        patterns.add(pattern.lower())

        return patterns

    # ==================== MOD METADATA ====================

    def _save_mod_metadata(self, server_folder: str, metadata: Dict) -> bool:
        """
        Save mod environment metadata to a JSON file in the server folder.
        This data comes from the mrpack manifest 'env' field.

        Args:
            server_folder: Path to the server folder
            metadata: Dict mapping filename -> {client: str, server: str}

        Returns:
            True if saved successfully
        """
        try:
            metadata_file = Path(server_folder) / "pycraft_mod_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "version": 1,
                    "description": "Mod environment metadata from Modrinth mrpack. DO NOT EDIT.",
                    "mods": metadata
                }, f, indent=2)
            return True
        except Exception:
            return False

    def _load_mod_metadata(self, server_folder: str) -> Dict:
        """
        Load mod environment metadata from the server folder.

        Args:
            server_folder: Path to the server folder

        Returns:
            Dict mapping filename -> {client: str, server: str}, empty if not found
        """
        try:
            metadata_file = Path(server_folder) / "pycraft_mod_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("mods", {})
        except Exception:
            pass
        return {}

    # ==================== MODRINTH ====================

    def install_modrinth_modpack(
        self,
        project_id: str,
        version_id: str,
        server_folder: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Installs a modpack from Modrinth

        Args:
            project_id: Project ID on Modrinth
            version_id: Version ID to install
            server_folder: Folder where to install the server
            log_callback: Function to report progress

        Returns:
            True if installation was successful
        """
        try:
            if log_callback:
                log_callback("\n╔════════════════════════════════════════════════╗\n")
                log_callback("║   MODRINTH MODPACK INSTALLATION                ║\n")
                log_callback("╚════════════════════════════════════════════════╝\n\n")

            # Create folder if it doesn't exist
            os.makedirs(server_folder, exist_ok=True)

            # Download modpack
            if log_callback:
                log_callback("Step 1/6: Downloading modpack...\n")

            temp_dir = Path(server_folder) / ".temp_modpack"
            temp_dir.mkdir(exist_ok=True)

            modpack_file = self.modrinth_api.download_version_file(version_id, str(temp_dir))

            if not modpack_file:
                if log_callback:
                    log_callback("✗ Error downloading modpack\n")
                return False

            if log_callback:
                log_callback(f"[OK] Modpack downloaded: {os.path.basename(modpack_file)}\n\n")

            # Extract modpack
            if log_callback:
                log_callback("Step 2/6: Extracting modpack files...\n")

            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(modpack_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            if log_callback:
                log_callback("[OK] Files extracted successfully\n\n")

            # Read manifest (modrinth.index.json)
            manifest_path = extract_dir / "modrinth.index.json"
            if not manifest_path.exists():
                if log_callback:
                    log_callback("✗ Error: modrinth.index.json not found\n")
                return False

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Detect modpack information
            minecraft_version = self.loader_manager.get_minecraft_version_from_manifest(manifest)
            loader_type = self.loader_manager.detect_loader_type(manifest)
            loader_version = self.loader_manager.get_loader_version_from_manifest(manifest)

            if log_callback:
                log_callback("Step 3/6: Modpack information detected\n")
                log_callback(f"  -Minecraft: {minecraft_version}\n")
                log_callback(f"  -Loader: {loader_type}\n")
                log_callback(f"  -Loader version: {loader_version or 'latest'}\n\n")

            # Verify/install Java
            if log_callback:
                log_callback("Step 4/6: Verifying Java...\n")

            java_exe = self.java_manager.ensure_java_installed(minecraft_version, log_callback)

            if not java_exe:
                if log_callback:
                    log_callback("✗ Error: Could not install Java\n")
                return False

            # Download mods and extract environment metadata
            if log_callback:
                log_callback("\nStep 5/6: Downloading modpack mods...\n")

            mods_folder = Path(server_folder) / "mods"
            mods_folder.mkdir(exist_ok=True)

            files = manifest.get("files", [])
            total_files = len(files)

            if log_callback:
                log_callback(f"Downloading {total_files} mods...\n")

            for i, file_info in enumerate(files, 1):
                downloads = file_info.get("downloads", [])
                file_path = file_info.get("path", "")

                if downloads and file_path:
                    download_url = downloads[0]
                    filename = os.path.basename(file_path)

                    # Only download mods (not configs or resources)
                    if file_path.startswith("mods/"):
                        try:
                            dest_file = mods_folder / filename

                            if log_callback:
                                log_callback(f"  [{i}/{total_files}] {filename}...")

                            # Use streaming to avoid loading entire file into memory
                            response = requests.get(download_url, timeout=30, stream=True)
                            response.raise_for_status()

                            # Write in chunks to reduce memory usage
                            with open(dest_file, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)

                            if log_callback:
                                log_callback(" [OK]\n")

                        except Exception as e:
                            if log_callback:
                                log_callback(f" [ERROR: {str(e)}]\n")

            if log_callback:
                log_callback("\n[OK] Mods downloaded\n\n")

            # Copy overrides (Modrinth supports layered overrides for server)
            # 1. First copy general overrides
            overrides_dir = extract_dir / "overrides"
            if overrides_dir.exists():
                if log_callback:
                    log_callback("Copying configuration files...\n")

                self._copy_overrides(overrides_dir, Path(server_folder), log_callback)

                if log_callback:
                    log_callback("[OK] Configurations copied\n")

            # 2. Then copy server-overrides (overwrites general overrides for server-specific configs)
            server_overrides_dir = extract_dir / "server-overrides"
            if server_overrides_dir.exists():
                if log_callback:
                    log_callback("Applying server-specific configurations...\n")

                self._copy_overrides(server_overrides_dir, Path(server_folder), log_callback)

                if log_callback:
                    log_callback("[OK] Server configurations applied\n")

            if log_callback:
                log_callback("\n")

            # Install loader
            if log_callback:
                log_callback("Step 6/6: Installing mod loader...\n")

            if loader_type in ("forge", "neoforge"):
                # NeoForge is a Forge fork - attempt Forge installation
                if loader_type == "neoforge" and log_callback:
                    log_callback("⚠ NeoForge detected - attempting Forge-compatible installation\n")
                success = self.loader_manager.install_forge(
                    minecraft_version,
                    server_folder,
                    java_exe,
                    loader_version,
                    log_callback
                )
            elif loader_type in ("fabric", "quilt"):
                # Quilt is compatible with Fabric loader for most cases
                success = self.loader_manager.install_fabric(
                    minecraft_version,
                    server_folder,
                    java_exe,
                    loader_version,
                    log_callback
                )
                if loader_type == "quilt" and log_callback:
                    log_callback("⚠ Nota: Installed Fabric (compatible with most Quilt mods)\n")
            else:
                if log_callback:
                    log_callback(f"✗ Error: Loader '{loader_type}' no soportado\n")
                    log_callback("  Loaders soportados: forge, neoforge, fabric, quilt\n")
                success = False

            # Save manifest to server folder for version detection later
            if success:
                try:
                    dest_manifest = Path(server_folder) / "modrinth.index.json"
                    shutil.copy2(manifest_path, dest_manifest)
                    if log_callback:
                        log_callback("\n[OK] Manifest saved for future reference\n")
                except Exception as e:
                    if log_callback:
                        log_callback(f"⚠ Warning: Could not save manifest: {e}\n")

                # Pre-create EULA so server can start and generate files in a single run
                if log_callback:
                    log_callback("\nConfiguring EULA...\n")
                self._create_eula_file(server_folder, log_callback)

            # Clean up temporary files
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

            if success and log_callback:
                log_callback("\n╔════════════════════════════════════════════════╗\n")
                log_callback("║   [OK] MODPACK INSTALLED SUCCESSFULLY            ║\n")
                log_callback("╚════════════════════════════════════════════════╝\n\n")

            return success

        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error during installation: {str(e)}\n")
            return False

    # ==================== CURSEFORGE ====================

    def install_curseforge_modpack(
        self,
        modpack_id: int,
        file_id: int,
        server_folder: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Installs a modpack from CurseForge.

        CurseForge modpacks can have a separate SERVER PACK file that contains
        everything ready to run (mods, configs, start scripts, etc).
        This method will:
        1. Check if a server pack exists for the selected file
        2. If yes: download and extract the server pack directly (preferred)
        3. If no: fall back to downloading the client modpack and mods individually

        Args:
            modpack_id: Modpack ID
            file_id: File/version ID (client modpack file)
            server_folder: Folder where to install the server
            log_callback: Function to report progress

        Returns:
            True if installation was successful
        """
        if not self.curseforge_api or not self.curseforge_api.is_configured():
            if log_callback:
                log_callback("✗ Error: CurseForge API key not configured\n")
            return False

        try:
            if log_callback:
                log_callback("\n╔════════════════════════════════════════════════╗\n")
                log_callback("║   CURSEFORGE MODPACK INSTALLATION              ║\n")
                log_callback("╚════════════════════════════════════════════════╝\n\n")

            # Create folder if it doesn't exist
            os.makedirs(server_folder, exist_ok=True)

            # Step 1: Check if a server pack exists for this file
            if log_callback:
                log_callback("Step 1/4: Checking for server pack...\n")

            server_pack_file_id = self.curseforge_api.get_server_pack_file_id(modpack_id, file_id)

            if server_pack_file_id:
                if log_callback:
                    log_callback(f"[OK] Server pack found (ID: {server_pack_file_id})\n")
                    log_callback("    Using official server pack - this includes all files ready to run!\n\n")

                # Use the server pack installation method
                return self._install_curseforge_server_pack(
                    modpack_id, server_pack_file_id, server_folder, log_callback
                )
            else:
                if log_callback:
                    log_callback("⚠ No server pack available for this version\n")
                    log_callback("    Falling back to manual installation (downloading mods individually)...\n\n")

                # Fall back to the old method
                return self._install_curseforge_modpack_fallback(
                    modpack_id, file_id, server_folder, log_callback
                )

        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error during installation: {str(e)}\n")
            return False

    def _install_curseforge_server_pack(
        self,
        modpack_id: int,
        server_pack_file_id: int,
        server_folder: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Install a CurseForge server pack directly.
        Server packs are pre-built ZIP files that contain everything needed:
        - All mods already downloaded
        - Configuration files
        - Start scripts (LaunchServer.bat, LaunchServer.sh)
        - server.properties
        - etc.

        Args:
            modpack_id: Modpack ID
            server_pack_file_id: Server pack file ID
            server_folder: Folder where to install the server
            log_callback: Function to report progress

        Returns:
            True if installation was successful
        """
        try:
            # Download server pack
            if log_callback:
                log_callback("Step 2/4: Downloading server pack...\n")

            temp_dir = Path(server_folder) / ".temp_modpack"
            temp_dir.mkdir(exist_ok=True)

            server_pack_file = self.curseforge_api.download_modpack_file(
                modpack_id, server_pack_file_id, str(temp_dir)
            )

            if not server_pack_file:
                if log_callback:
                    log_callback("✗ Error downloading server pack\n")
                return False

            if log_callback:
                log_callback(f"[OK] Server pack downloaded: {os.path.basename(server_pack_file)}\n\n")

            # Extract server pack to server folder
            if log_callback:
                log_callback("Step 3/4: Extracting server pack...\n")

            # First extract to temp folder to check structure
            extract_temp = temp_dir / "extracted"
            extract_temp.mkdir(exist_ok=True)

            with zipfile.ZipFile(server_pack_file, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                total_files = len(file_list)

                if log_callback:
                    log_callback(f"    Extracting {total_files} files...\n")

                zip_ref.extractall(extract_temp)

            # Check if everything is inside a single root folder
            # (common pattern: ZIP contains "RAD2-Serverpack-1.16/" with all files inside)
            extracted_items = list(extract_temp.iterdir())

            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                # Everything is inside a single folder - move contents up
                root_folder = extracted_items[0]
                if log_callback:
                    log_callback(f"    Detected root folder: {root_folder.name}\n")
                    log_callback(f"    Moving contents to server folder...\n")

                # Move all contents from root folder to server folder
                for item in root_folder.iterdir():
                    dest = Path(server_folder) / item.name
                    if dest.exists():
                        if dest.is_dir():
                            shutil.rmtree(dest)
                        else:
                            dest.unlink()
                    shutil.move(str(item), str(dest))
            else:
                # No root folder - move everything directly
                if log_callback:
                    log_callback(f"    Moving files to server folder...\n")

                for item in extracted_items:
                    dest = Path(server_folder) / item.name
                    if dest.exists():
                        if dest.is_dir():
                            shutil.rmtree(dest)
                        else:
                            dest.unlink()
                    shutil.move(str(item), str(dest))

            if log_callback:
                log_callback("[OK] Server pack extracted successfully\n\n")

            # Verify/install Java and detect version info
            if log_callback:
                log_callback("Step 4/4: Verifying Java and configuration...\n")

            # Try to detect Minecraft version from extracted files
            minecraft_version = None
            loader_type = None
            loader_version = None
            import re
            import glob

            # Method 1: Check for version.json or manifest.json files
            version_indicators = [
                Path(server_folder) / "version.json",
                Path(server_folder) / "manifest.json",
            ]

            for indicator in version_indicators:
                if indicator.exists():
                    try:
                        with open(indicator, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if "minecraft" in data:
                                mc_info = data.get("minecraft", {})
                                minecraft_version = mc_info.get("version")
                            elif "dependencies" in data:
                                deps = data.get("dependencies", {})
                                minecraft_version = deps.get("minecraft")
                    except:
                        pass

            # Method 2: Check libraries folder for Forge (has MC version in folder name)
            if not minecraft_version:
                forge_libs = Path(server_folder) / "libraries" / "net" / "minecraftforge" / "forge"
                if forge_libs.exists():
                    try:
                        versions = list(forge_libs.iterdir())
                        if versions:
                            # Folder name is like "1.20.1-47.2.0"
                            version_folder = versions[0].name
                            if '-' in version_folder:
                                minecraft_version = version_folder.split('-')[0]
                                loader_type = "forge"
                                loader_version = version_folder.split('-')[1] if len(version_folder.split('-')) > 1 else None
                    except Exception:
                        pass

            # Method 3: Check for NeoForge libraries
            if not minecraft_version:
                neoforge_libs = Path(server_folder) / "libraries" / "net" / "neoforged" / "neoforge"
                if neoforge_libs.exists():
                    try:
                        versions = list(neoforge_libs.iterdir())
                        if versions:
                            # NeoForge version format: MAJOR.MINOR.PATCH maps to MC 1.MAJOR.MINOR
                            version = versions[0].name
                            match = re.match(r'(\d+)\.(\d+)\.', version)
                            if match:
                                major, minor = match.groups()
                                minecraft_version = f"1.{major}.{minor}" if minor != "0" else f"1.{major}"
                                loader_type = "neoforge"
                                loader_version = version
                    except Exception:
                        pass

            # Method 4: Check for forge/fabric jar filenames
            if not minecraft_version:
                for f in os.listdir(server_folder):
                    f_lower = f.lower()
                    if "forge" in f_lower and f.endswith(".jar"):
                        # Try to extract version from forge jar name
                        # Format: forge-1.16.5-36.2.39.jar
                        match = re.search(r'forge-([\d.]+)-([\d.]+)', f)
                        if match:
                            minecraft_version = match.group(1)
                            loader_type = "forge"
                            loader_version = match.group(2)
                            break
                        # Fallback: just get any version number
                        match = re.search(r'(\d+\.\d+(?:\.\d+)?)', f)
                        if match:
                            minecraft_version = match.group(1)
                            loader_type = "forge"
                            break
                    elif "fabric" in f_lower and f.endswith(".jar"):
                        match = re.search(r'(\d+\.\d+(?:\.\d+)?)', f)
                        if match:
                            minecraft_version = match.group(1)
                            loader_type = "fabric"
                            break

            # Method 5: Check run.bat/run.sh for version info
            if not minecraft_version:
                for script in ["run.bat", "run.sh", "start.bat", "start.sh", "LaunchServer.bat", "LaunchServer.sh"]:
                    script_path = Path(server_folder) / script
                    if script_path.exists():
                        try:
                            with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                # Look for MC version pattern in Forge paths
                                match = re.search(r'forge[/-]([\d.]+)-([\d.]+)', content, re.IGNORECASE)
                                if match:
                                    minecraft_version = match.group(1)
                                    loader_type = "forge"
                                    loader_version = match.group(2)
                                    break
                                # Look for minecraft_server version
                                match = re.search(r'minecraft[_-]?server[_-]?([\d.]+)', content, re.IGNORECASE)
                                if match:
                                    minecraft_version = match.group(1)
                                    break
                        except Exception:
                            pass

            # Method 6: Check variables.txt (ServerPackCreator format by Griefed)
            if not minecraft_version:
                variables_path = Path(server_folder) / "variables.txt"
                if variables_path.exists():
                    try:
                        with open(variables_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Parse MINECRAFT_VERSION=1.20.1
                            mc_match = re.search(r'^MINECRAFT_VERSION=(.+)$', content, re.MULTILINE)
                            if mc_match:
                                minecraft_version = mc_match.group(1).strip()
                            # Parse MODLOADER=Forge
                            loader_match = re.search(r'^MODLOADER=(.+)$', content, re.MULTILINE)
                            if loader_match:
                                loader_type = loader_match.group(1).strip().lower()
                            # Parse MODLOADER_VERSION=47.4.10
                            loader_ver_match = re.search(r'^MODLOADER_VERSION=(.+)$', content, re.MULTILINE)
                            if loader_ver_match:
                                loader_version = loader_ver_match.group(1).strip()
                    except Exception:
                        pass

            # Method 7: Check user_jvm_args.txt or other config files
            if not minecraft_version:
                for config_file in ["user_jvm_args.txt", "server.properties"]:
                    config_path = Path(server_folder) / config_file
                    if config_path.exists():
                        try:
                            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                # Some modpacks put version info in comments
                                match = re.search(r'minecraft[:\s]*([\d.]+)', content, re.IGNORECASE)
                                if match:
                                    minecraft_version = match.group(1)
                                    break
                        except Exception:
                            pass

            # Default to unknown with warning if we can't detect
            if not minecraft_version:
                minecraft_version = None
                if log_callback:
                    log_callback("⚠ Could not detect Minecraft version from server pack\n")
                    log_callback("    Will attempt to detect when loading the server\n")

            # Ensure Java is available
            java_exe = self.java_manager.ensure_java_installed(minecraft_version, log_callback)

            if not java_exe:
                if log_callback:
                    log_callback("⚠ Warning: Could not verify Java installation\n")
                    log_callback("    Make sure you have Java installed to run the server\n")

            # Accept EULA
            self._create_eula_file(server_folder, log_callback)

            # Save modpack info for later detection
            try:
                modpack_info = self.curseforge_api.get_modpack_info(modpack_id)
                modpack_name = modpack_info.get("name", "Unknown") if modpack_info else "Unknown"
                modpack_slug = modpack_info.get("slug", "") if modpack_info else ""

                info_file = Path(server_folder) / "modpack_info.json"
                info_data = {
                    "name": modpack_name,
                    "slug": modpack_slug,
                    "source": "curseforge",
                    "minecraft_version": minecraft_version,
                    "loader": loader_type,
                    "loader_version": loader_version,
                    "curseforge_url": f"https://www.curseforge.com/minecraft/modpacks/{modpack_slug}" if modpack_slug else "",
                    "curseforge_id": modpack_id,
                    "install_type": "server_pack"
                }

                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump(info_data, f, indent=2)

                if minecraft_version and log_callback:
                    log_callback(f"[OK] Detected Minecraft {minecraft_version}")
                    if loader_type:
                        log_callback(f" with {loader_type.capitalize()}")
                        if loader_version:
                            log_callback(f" {loader_version}")
                    log_callback("\n")
            except Exception as e:
                # Non-critical error, continue anyway
                pass

            # Clean up temporary files
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

            if log_callback:
                log_callback("\n╔════════════════════════════════════════════════╗\n")
                log_callback("║   [OK] SERVER PACK INSTALLED SUCCESSFULLY      ║\n")
                log_callback("╚════════════════════════════════════════════════╝\n\n")
                log_callback("TIP: Use LaunchServer.bat (Windows) or LaunchServer.sh (Linux)\n")
                log_callback("     to start the server, or use PyCraft's Start Server button.\n\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error during server pack installation: {str(e)}\n")
            return False

    def _install_curseforge_modpack_fallback(
        self,
        modpack_id: int,
        file_id: int,
        server_folder: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Fallback installation method for CurseForge modpacks that don't have a server pack.
        Downloads the client modpack and then downloads each mod individually.

        Args:
            modpack_id: Modpack ID
            file_id: File/version ID
            server_folder: Folder where to install the server
            log_callback: Function to report progress

        Returns:
            True if installation was successful
        """
        try:
            # Download modpack
            if log_callback:
                log_callback("Step 2/6: Downloading client modpack...\n")

            temp_dir = Path(server_folder) / ".temp_modpack"
            temp_dir.mkdir(exist_ok=True)

            modpack_file = self.curseforge_api.download_modpack_file(modpack_id, file_id, str(temp_dir))

            if not modpack_file:
                if log_callback:
                    log_callback("✗ Error downloading modpack\n")
                return False

            if log_callback:
                log_callback(f"[OK] Modpack downloaded: {os.path.basename(modpack_file)}\n\n")

            # Extract modpack
            if log_callback:
                log_callback("Step 3/6: Extracting modpack files...\n")

            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(modpack_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            if log_callback:
                log_callback("[OK] Files extracted successfully\n\n")

            # Read manifest (manifest.json)
            manifest_path = extract_dir / "manifest.json"
            if not manifest_path.exists():
                if log_callback:
                    log_callback("✗ Error: manifest.json not found\n")
                return False

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Detect modpack information
            minecraft_version = self.loader_manager.get_minecraft_version_from_manifest(manifest)
            loader_type = self.loader_manager.detect_loader_type(manifest)
            loader_version = self.loader_manager.get_loader_version_from_manifest(manifest)

            if log_callback:
                log_callback("Step 4/6: Modpack information detected\n")
                log_callback(f"  - Minecraft: {minecraft_version}\n")
                log_callback(f"  - Loader: {loader_type}\n")
                log_callback(f"  - Loader version: {loader_version or 'latest'}\n\n")

            # Verify/install Java
            if log_callback:
                log_callback("    Verifying Java...\n")

            java_exe = self.java_manager.ensure_java_installed(minecraft_version, log_callback)

            if not java_exe:
                if log_callback:
                    log_callback("✗ Error: Could not install Java\n")
                return False

            # Download mods
            if log_callback:
                log_callback("\nStep 5/6: Downloading modpack mods...\n")

            mods_folder = Path(server_folder) / "mods"
            mods_folder.mkdir(exist_ok=True)

            files = manifest.get("files", [])
            total_files = len(files)

            if log_callback:
                log_callback(f"Downloading {total_files} mods from CurseForge...\n")

            def build_cdn_url(file_id: int, filename: str) -> str:
                """Build alternative CDN URL when downloadUrl is null"""
                file_id_str = str(file_id)
                if len(file_id_str) > 4:
                    first_part = file_id_str[:4]
                    second_part = file_id_str[4:].lstrip('0') or '0'
                else:
                    first_part = file_id_str
                    second_part = "0"
                return f"https://edge.forgecdn.net/files/{first_part}/{second_part}/{filename}"

            for i, file_info in enumerate(files, 1):
                project_id = file_info.get("projectID")
                file_id_mod = file_info.get("fileID")

                if project_id and file_id_mod:
                    try:
                        # Get file information
                        file_data = self.curseforge_api.get_mod_file_info(project_id, file_id_mod)

                        if file_data:
                            filename = file_data.get("fileName", f"mod_{project_id}.jar")
                            download_url = file_data.get("downloadUrl")

                            # If no download URL, use the CDN fallback
                            if not download_url:
                                download_url = build_cdn_url(file_id_mod, filename)

                            if log_callback:
                                log_callback(f"  [{i}/{total_files}] {filename}...")

                            dest_file = mods_folder / filename

                            # Use streaming with redirects support
                            response = requests.get(
                                download_url,
                                timeout=60,
                                stream=True,
                                allow_redirects=True,
                                headers={"User-Agent": "PyCraft/1.0"}
                            )
                            response.raise_for_status()

                            # Write in chunks to reduce memory usage
                            with open(dest_file, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)

                            if log_callback:
                                log_callback(" [OK]\n")

                    except Exception as e:
                        if log_callback:
                            log_callback(f" ✗ Error: {str(e)}\n")

            if log_callback:
                log_callback("\n[OK] Mods downloaded\n\n")

            # Copy overrides
            overrides_dir = extract_dir / manifest.get("overrides", "overrides")
            if overrides_dir.exists():
                if log_callback:
                    log_callback("Copying configuration files...\n")

                self._copy_overrides(overrides_dir, Path(server_folder), log_callback)

                if log_callback:
                    log_callback("[OK] Configurations copied\n\n")

            # Install loader
            if log_callback:
                log_callback("Step 6/6: Installing mod loader...\n")

            if loader_type in ("forge", "neoforge"):
                # NeoForge is a Forge fork - attempt Forge installation
                # Note: Some NeoForge-specific modpacks may require manual setup
                if loader_type == "neoforge" and log_callback:
                    log_callback("⚠ NeoForge detected - attempting Forge-compatible installation\n")
                success = self.loader_manager.install_forge(
                    minecraft_version,
                    server_folder,
                    java_exe,
                    loader_version,
                    log_callback
                )
            elif loader_type in ("fabric", "quilt"):
                # Quilt is compatible with Fabric loader for most cases
                success = self.loader_manager.install_fabric(
                    minecraft_version,
                    server_folder,
                    java_exe,
                    loader_version,
                    log_callback
                )
                if loader_type == "quilt" and log_callback:
                    log_callback("⚠ Note: Installed Fabric (compatible with most Quilt mods)\n")
            else:
                if log_callback:
                    log_callback(f"✗ Error: Loader '{loader_type}' not supported\n")
                    log_callback("  Supported loaders: forge, neoforge, fabric, quilt\n")
                success = False

            # Save manifest to server folder for version detection later
            if success:
                try:
                    dest_manifest = Path(server_folder) / "manifest.json"
                    shutil.copy2(manifest_path, dest_manifest)
                    if log_callback:
                        log_callback("\n[OK] Manifest saved for future reference\n")
                except Exception as e:
                    if log_callback:
                        log_callback(f"⚠ Warning: Could not save manifest: {e}\n")

                # Pre-create EULA so server can start and generate files in a single run
                if log_callback:
                    log_callback("\nConfiguring EULA...\n")
                self._create_eula_file(server_folder, log_callback)

            # Clean up temporary files
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

            if success and log_callback:
                log_callback("\n╔════════════════════════════════════════════════╗\n")
                log_callback("║   [OK] MODPACK INSTALLED SUCCESSFULLY          ║\n")
                log_callback("╚════════════════════════════════════════════════╝\n\n")

            return success

        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error during installation: {str(e)}\n")
            return False

    # ==================== UTILITIES ====================

    def _create_eula_file(self, server_folder: str, log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Creates eula.txt with eula=true in the server folder.
        This is called during modpack installation so the server can start
        without needing to be restarted after EULA generation.

        Args:
            server_folder: Path to the server folder
            log_callback: Function to report progress

        Returns:
            True if successful
        """
        try:
            eula_path = Path(server_folder) / "eula.txt"

            # Check if EULA already exists and is accepted
            if eula_path.exists():
                content = eula_path.read_text(encoding='utf-8')
                if 'eula=true' in content.lower():
                    if log_callback:
                        log_callback("[OK] EULA ya estaba aceptado\n")
                    return True
                # EULA exists but not accepted - overwrite it
                if log_callback:
                    log_callback("Actualizando EULA a aceptado...\n")

            # Create/overwrite EULA file
            eula_content = (
                "#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).\n"
                "#Auto-accepted by PyCraft during modpack installation\n"
                "eula=true\n"
            )
            eula_path.write_text(eula_content, encoding='utf-8')

            if log_callback:
                log_callback("[OK] EULA accepted automatically\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"⚠ Warning: Could not create eula.txt: {e}\n")
            return False

    def _create_server_properties(self, server_folder: str, log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Creates a default server.properties file in the server folder.
        This is called during modpack installation so the server doesn't need
        to run twice (once to generate files, once to actually start).

        Args:
            server_folder: Path to the server folder
            log_callback: Function to report progress

        Returns:
            True if successful
        """
        try:
            properties_path = Path(server_folder) / "server.properties"

            # Don't overwrite if it already exists
            if properties_path.exists():
                return True

            if log_callback:
                log_callback("Creando server.properties por defecto...\n")

            # Default server.properties content (Minecraft 1.19.2+ compatible)
            default_properties = """#Minecraft server properties
#Auto-generated by PyCraft
enable-jmx-monitoring=false
rcon.port=25575
level-seed=
gamemode=survival
enable-command-block=false
enable-query=false
generator-settings={}
enforce-secure-profile=false
level-name=world
motd=A Minecraft Server
query.port=25565
pvp=true
generate-structures=true
max-chained-neighbor-updates=1000000
difficulty=normal
network-compression-threshold=256
max-tick-time=60000
require-resource-pack=false
use-native-transport=true
max-players=20
online-mode=false
enable-status=true
allow-flight=false
initial-disabled-packs=
broadcast-rcon-to-ops=true
view-distance=10
server-ip=
resource-pack-prompt=
allow-nether=true
server-port=25565
enable-rcon=false
sync-chunk-writes=true
op-permission-level=4
prevent-proxy-connections=false
hide-online-players=false
resource-pack=
entity-broadcast-range-percentage=100
simulation-distance=10
rcon.password=
player-idle-timeout=0
force-gamemode=false
rate-limit=0
hardcore=false
white-list=false
broadcast-console-to-ops=true
spawn-npcs=true
spawn-animals=true
function-permission-level=2
initial-enabled-packs=vanilla
level-type=minecraft\\:normal
text-filtering-config=
spawn-monsters=true
enforce-whitelist=false
spawn-protection=16
resource-pack-sha1=
max-world-size=29999984
"""
            properties_path.write_text(default_properties, encoding='utf-8')

            if log_callback:
                log_callback("[OK] server.properties creado\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"⚠ Warning: Could not create server.properties: {e}\n")
            return False

    def _copy_overrides(self, source_dir: Path, dest_dir: Path, log_callback: Optional[Callable[[str], None]] = None):
        """
        Copies override files to the server

        Args:
            source_dir: Source directory (overrides)
            dest_dir: Destination directory (server folder)
            log_callback: Function to report progress
        """
        try:
            for item in source_dir.rglob("*"):
                if item.is_file():
                    # Calculate relative path
                    relative_path = item.relative_to(source_dir)
                    dest_file = dest_dir / relative_path

                    # Create directories if they don't exist
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    shutil.copy2(item, dest_file)

        except Exception as e:
            if log_callback:
                log_callback(f"Warning copying overrides: {str(e)}\n")

    def search_modpacks(
        self,
        query: str,
        platform: str = "modrinth",
        limit: int = 10,
        offset: int = 0,
        side_filter: str = None
    ) -> Tuple[Optional[List[Dict]], int]:
        """
        Searches for modpacks on the specified platform

        Args:
            query: Search text
            platform: "modrinth" or "curseforge"
            limit: Maximum number of results per page
            offset: Number of results to skip (for pagination)
            side_filter: Filter by side - "server" for server-compatible modpacks,
                        "client" for client-compatible modpacks, None for no filter

        Returns:
            Tuple of (list of modpacks, total results count)
        """
        if platform == "modrinth":
            return self.modrinth_api.search_modpacks(query, limit, offset, side_filter)
        elif platform == "curseforge":
            # CurseForge API is always configured (uses proxy)
            if self.curseforge_api is None:
                self.curseforge_api = CurseForgeAPI()
            # For server filter, use server_pack_filter
            server_pack_filter = side_filter == "server"
            return self.curseforge_api.search_modpacks(query, limit, offset, server_pack_filter)
        return None, 0

    def get_recommended_ram(self, modpack_manifest: Dict) -> int:
        """
        Gets the recommended RAM for a modpack based on the number of mods

        Args:
            modpack_manifest: Modpack manifest

        Returns:
            Recommended RAM in MB
        """
        try:
            files = modpack_manifest.get("files", [])
            num_mods = len(files)

            # Basic heuristic
            if num_mods < 50:
                return 4096  # 4 GB para modpacks pequeños
            elif num_mods < 100:
                return 6144  # 6 GB para modpacks medianos (default)
            elif num_mods < 150:
                return 8192  # 8 GB para modpacks grandes
            else:
                return 10240  # 10 GB para modpacks muy grandes

        except:
            return 6144  # Default 6 GB

    def install_client_modpack(
        self,
        project_id: str,
        version_id: str = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict:
        """
        Installs a modpack for client use in ~/.pycraft/modpacks/

        Args:
            project_id: Project ID on Modrinth
            version_id: Version ID to install (if None, uses latest)
            log_callback: Function to report progress

        Returns:
            Dict with:
            - success: bool
            - install_path: str
            - minecraft_version: str
            - loader_type: str
            - loader_version: str
        """
        try:
            if log_callback:
                log_callback("\n" + "="*50 + "\n")
                log_callback("   CLIENT MODPACK INSTALLATION\n")
                log_callback("="*50 + "\n\n")

            # Get project info
            if log_callback:
                log_callback("Step 1/5: Getting modpack info...\n")

            project_info = self.modrinth_api.get_project_info(project_id)
            if not project_info:
                if log_callback:
                    log_callback("Error: Could not get project info\n")
                return {"success": False}

            modpack_name = project_info.get("title", "unknown_modpack")
            modpack_slug = project_info.get("slug", modpack_name)
            # Clean name for folder
            safe_name = "".join(c for c in modpack_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')

            if log_callback:
                log_callback(f"Modpack: {modpack_name}\n\n")

            # Get version info
            if not version_id:
                if log_callback:
                    log_callback("Step 2/5: Getting latest version...\n")
                versions = self.modrinth_api.get_modpack_versions(project_id)
                if not versions:
                    if log_callback:
                        log_callback("Error: No versions found\n")
                    return {"success": False}
                # Get latest version
                version_data = versions[0]
                version_id = version_data.get("id")
            else:
                # Get specific version info
                versions = self.modrinth_api.get_modpack_versions(project_id)
                version_data = next((v for v in versions if v.get("id") == version_id), None)
                if not version_data:
                    if log_callback:
                        log_callback("Error: Version not found\n")
                    return {"success": False}

            game_versions = version_data.get("game_versions", [])
            loaders = version_data.get("loaders", [])
            minecraft_version = game_versions[0] if game_versions else "unknown"
            loader_type = loaders[0] if loaders else "unknown"

            if log_callback:
                log_callback(f"Version: {version_data.get('name', version_id)}\n")
                log_callback(f"Minecraft: {minecraft_version}\n")
                log_callback(f"Loader: {loader_type}\n\n")

            # Create install directory
            install_base = Path.home() / ".pycraft" / "modpacks"
            install_base.mkdir(parents=True, exist_ok=True)
            install_path = install_base / safe_name

            if install_path.exists():
                if log_callback:
                    log_callback(f"Warning: Folder exists, will be updated\n")
                # Don't delete, just overwrite
            else:
                install_path.mkdir(parents=True, exist_ok=True)

            if log_callback:
                log_callback(f"Install path: {install_path}\n\n")

            # Download modpack
            if log_callback:
                log_callback("Step 3/5: Downloading modpack...\n")

            temp_dir = install_path / ".temp_download"
            temp_dir.mkdir(exist_ok=True)

            modpack_file = self.modrinth_api.download_version_file(version_id, str(temp_dir))
            if not modpack_file:
                if log_callback:
                    log_callback("Error: Failed to download modpack\n")
                return {"success": False}

            if log_callback:
                log_callback(f"Downloaded: {os.path.basename(modpack_file)}\n\n")

            # Extract modpack
            if log_callback:
                log_callback("Step 4/5: Extracting files...\n")

            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(modpack_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Read manifest
            manifest_path = extract_dir / "modrinth.index.json"
            if not manifest_path.exists():
                if log_callback:
                    log_callback("Error: modrinth.index.json not found\n")
                return {"success": False}

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Get loader version from manifest
            dependencies = manifest.get("dependencies", {})
            loader_version = ""
            if loader_type == "forge":
                loader_version = dependencies.get("forge", "")
            elif loader_type == "fabric":
                loader_version = dependencies.get("fabric-loader", "")
            elif loader_type == "neoforge":
                loader_version = dependencies.get("neoforge", "")
            elif loader_type == "quilt":
                loader_version = dependencies.get("quilt-loader", "")

            # Create necessary directories
            mods_folder = install_path / "mods"
            mods_folder.mkdir(exist_ok=True)

            # Download mods
            files = manifest.get("files", [])
            total_files = len([f for f in files if f.get("path", "").startswith("mods/")])

            if log_callback:
                log_callback(f"Downloading {total_files} mods...\n")

            downloaded = 0
            for file_info in files:
                downloads = file_info.get("downloads", [])
                file_path = file_info.get("path", "")

                if downloads and file_path:
                    download_url = downloads[0]

                    # Determine destination
                    dest_file = install_path / file_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    try:
                        response = requests.get(download_url, timeout=30, stream=True)
                        response.raise_for_status()

                        with open(dest_file, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)

                        if file_path.startswith("mods/"):
                            downloaded += 1
                            if log_callback and downloaded % 10 == 0:
                                log_callback(f"  Progress: {downloaded}/{total_files}\n")

                    except Exception as e:
                        if log_callback:
                            log_callback(f"  Warning: Failed to download {os.path.basename(file_path)}\n")

            if log_callback:
                log_callback(f"Downloaded {downloaded}/{total_files} mods\n\n")

            # Copy overrides
            if log_callback:
                log_callback("Step 5/5: Copying configurations...\n")

            overrides_dir = extract_dir / "overrides"
            if overrides_dir.exists():
                self._copy_overrides(overrides_dir, install_path, log_callback)
                if log_callback:
                    log_callback("Configurations copied\n\n")

            # Save modpack info
            info_file = install_path / "modpack_info.json"
            info_data = {
                "name": modpack_name,
                "slug": modpack_slug,
                "source": "modrinth",
                "minecraft_version": minecraft_version,
                "loader": loader_type,
                "loader_version": loader_version,
                "modrinth_url": f"https://modrinth.com/modpack/{modpack_slug}",
                "modrinth_id": project_id,
                "version_name": version_data.get("name", ""),
                "installed_date": str(Path(install_path).stat().st_mtime) if install_path.exists() else ""
            }

            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(info_data, f, indent=2)

            # Cleanup temp
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

            return {
                "success": True,
                "install_path": str(install_path),
                "minecraft_version": minecraft_version,
                "loader_type": loader_type,
                "loader_version": loader_version
            }

        except Exception as e:
            if log_callback:
                log_callback(f"\nError during installation: {str(e)}\n")
            return {"success": False, "error": str(e)}

    def install_client_curseforge_modpack(
        self,
        modpack_id: int,
        file_id: int,
        modpack_name: str = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict:
        """
        Installs a CurseForge modpack for client use in ~/.pycraft/modpacks/

        Args:
            modpack_id: CurseForge modpack ID
            file_id: CurseForge file ID to install
            modpack_name: Name of the modpack (optional, will be fetched if not provided)
            log_callback: Function to report progress

        Returns:
            Dict with:
            - success: bool
            - install_path: str
            - minecraft_version: str
            - loader_type: str
            - loader_version: str
        """
        if not self.curseforge_api:
            from ...core.api import CurseForgeAPI
            self.curseforge_api = CurseForgeAPI()

        try:
            if log_callback:
                log_callback("\n" + "="*50 + "\n")
                log_callback("   CLIENT MODPACK INSTALLATION (CurseForge)\n")
                log_callback("="*50 + "\n\n")

            # Get modpack info if name not provided
            if log_callback:
                log_callback("Step 1/5: Getting modpack info...\n")

            modpack_info = self.curseforge_api.get_modpack_info(modpack_id)
            if not modpack_info:
                if log_callback:
                    log_callback("Error: Could not get modpack info\n")
                return {"success": False}

            modpack_name = modpack_info.get("name", modpack_name or "unknown_modpack")
            modpack_slug = modpack_info.get("slug", modpack_name)

            # Clean name for folder
            safe_name = "".join(c for c in modpack_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')

            if log_callback:
                log_callback(f"Modpack: {modpack_name}\n\n")

            # Get file info
            if log_callback:
                log_callback("Step 2/5: Getting version info...\n")

            file_info = self.curseforge_api.get_mod_file_info(modpack_id, file_id)
            if not file_info:
                if log_callback:
                    log_callback("Error: Could not get file info\n")
                return {"success": False}

            game_versions = file_info.get("gameVersions", [])
            # Filter out loader names from game versions to get MC version
            mc_versions = [v for v in game_versions if v[0].isdigit()]
            minecraft_version = mc_versions[0] if mc_versions else "unknown"

            # Detect loader from file name or game versions
            file_name = file_info.get("fileName", "").lower()
            loader_type = "unknown"
            loader_version = ""

            if "forge" in file_name or "Forge" in game_versions:
                loader_type = "forge"
            elif "neoforge" in file_name or "NeoForge" in game_versions:
                loader_type = "neoforge"
            elif "fabric" in file_name or "Fabric" in game_versions:
                loader_type = "fabric"
            elif "quilt" in file_name or "Quilt" in game_versions:
                loader_type = "quilt"

            version_name = file_info.get("displayName", file_info.get("fileName", ""))

            if log_callback:
                log_callback(f"Version: {version_name}\n")
                log_callback(f"Minecraft: {minecraft_version}\n")
                log_callback(f"Loader: {loader_type}\n\n")

            # Create install directory
            install_base = Path.home() / ".pycraft" / "modpacks"
            install_base.mkdir(parents=True, exist_ok=True)
            install_path = install_base / safe_name

            if install_path.exists():
                if log_callback:
                    log_callback(f"Warning: Folder exists, will be updated\n")
            else:
                install_path.mkdir(parents=True, exist_ok=True)

            if log_callback:
                log_callback(f"Install path: {install_path}\n\n")

            # Download modpack
            if log_callback:
                log_callback("Step 3/5: Downloading modpack...\n")

            temp_dir = install_path / ".temp_download"
            temp_dir.mkdir(exist_ok=True)

            modpack_file = self.curseforge_api.download_modpack_file(modpack_id, file_id, str(temp_dir))
            if not modpack_file:
                if log_callback:
                    log_callback("Error: Failed to download modpack\n")
                return {"success": False}

            if log_callback:
                log_callback(f"Downloaded: {os.path.basename(modpack_file)}\n\n")

            # Extract modpack
            if log_callback:
                log_callback("Step 4/5: Extracting and downloading mods...\n")

            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(modpack_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Read manifest
            manifest_path = extract_dir / "manifest.json"
            if not manifest_path.exists():
                if log_callback:
                    log_callback("Error: manifest.json not found\n")
                return {"success": False}

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Get loader version from manifest
            minecraft_info = manifest.get("minecraft", {})
            mod_loaders = minecraft_info.get("modLoaders", [])
            if mod_loaders:
                primary_loader = mod_loaders[0].get("id", "")
                if "-" in primary_loader:
                    loader_type, loader_version = primary_loader.split("-", 1)

            # Update minecraft version from manifest if available
            manifest_mc_version = minecraft_info.get("version", "")
            if manifest_mc_version:
                minecraft_version = manifest_mc_version

            # Create necessary directories
            mods_folder = install_path / "mods"
            mods_folder.mkdir(exist_ok=True)

            # Download mods using parallel downloads for speed
            files = manifest.get("files", [])
            total_files = len(files)

            if log_callback:
                log_callback(f"Downloading {total_files} mods (parallel)...\n")

            # Get all project IDs to fetch mod info in batch (for slugs)
            project_ids = [f.get("projectID") for f in files if f.get("projectID")]

            # Fetch mod info in batch for proper URLs
            mods_info_map = {}
            if project_ids:
                try:
                    mods_batch = self.curseforge_api.get_mods_info_batch(project_ids)
                    if mods_batch:
                        for mod in mods_batch:
                            mods_info_map[mod.get("id")] = mod
                except Exception:
                    pass  # Will fall back to individual lookups

            # Counters for progress (thread-safe)
            import threading
            from concurrent.futures import ThreadPoolExecutor, as_completed

            downloaded_count = [0]
            failed_mods = []
            lock = threading.Lock()

            def build_cdn_url(file_id: int, filename: str) -> str:
                """Build alternative CDN URL when downloadUrl is null"""
                # CurseForge CDN pattern: https://edge.forgecdn.net/files/{first4}/{rest}/{filename}
                file_id_str = str(file_id)
                if len(file_id_str) > 4:
                    first_part = file_id_str[:4]
                    second_part = file_id_str[4:]
                else:
                    first_part = file_id_str
                    second_part = ""
                # Remove leading zeros from second part
                second_part = second_part.lstrip('0') or '0'
                return f"https://edge.forgecdn.net/files/{first_part}/{second_part}/{filename}"

            def download_mod(mod_file):
                """Download a single mod - runs in thread pool"""
                project_id = mod_file.get("projectID")
                mod_file_id = mod_file.get("fileID")

                if not project_id or not mod_file_id:
                    return None

                try:
                    # Get file info
                    file_info = self.curseforge_api.get_mod_file_info(project_id, mod_file_id)
                    if not file_info:
                        return {"error": True, "project_id": project_id, "reason": "no_file_info"}

                    filename = file_info.get("fileName", f"mod_{project_id}.jar")
                    download_url = file_info.get("downloadUrl")

                    # If no download URL, use the CDN fallback
                    if not download_url:
                        download_url = build_cdn_url(mod_file_id, filename)

                    # Download the mod
                    dest_file = mods_folder / filename
                    response = requests.get(
                        download_url,
                        timeout=60,
                        stream=True,
                        allow_redirects=True,
                        headers={"User-Agent": "PyCraft/1.0"}
                    )
                    response.raise_for_status()

                    with open(dest_file, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    with lock:
                        downloaded_count[0] += 1
                        if log_callback and downloaded_count[0] % 20 == 0:
                            log_callback(f"  Progress: {downloaded_count[0]}/{total_files}\n")

                    return {"success": True, "filename": filename}

                except requests.exceptions.HTTPError as e:
                    # If CDN also fails, provide manual download link
                    mod_info = mods_info_map.get(project_id)
                    if not mod_info:
                        try:
                            mod_info = self.curseforge_api.get_mod_info(project_id)
                        except:
                            mod_info = None

                    if mod_info:
                        slug = mod_info.get("slug", "")
                        mod_name = mod_info.get("name", filename if 'filename' in dir() else f"mod_{project_id}")
                        page_url = f"https://www.curseforge.com/minecraft/mc-mods/{slug}/files/{mod_file_id}"
                    else:
                        mod_name = f"mod_{project_id}"
                        page_url = f"https://www.curseforge.com/minecraft/mc-mods/project/{project_id}/files/{mod_file_id}"

                    return {
                        "error": True,
                        "project_id": project_id,
                        "reason": "download_failed",
                        "mod_name": mod_name,
                        "filename": filename if 'filename' in dir() else f"mod_{project_id}.jar",
                        "manual_url": page_url
                    }

                except Exception as e:
                    return {"error": True, "project_id": project_id, "reason": str(e)}

            # Use ThreadPoolExecutor for parallel downloads (8 concurrent)
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(download_mod, mod_file): mod_file for mod_file in files}

                for future in as_completed(futures):
                    result = future.result()
                    if result and result.get("error"):
                        failed_mods.append(result)

            # Report results
            downloaded = downloaded_count[0]
            failed = len(failed_mods)

            if log_callback:
                log_callback(f"Downloaded {downloaded}/{total_files} mods")
                if failed > 0:
                    log_callback(f" ({failed} require manual download)")
                log_callback("\n")

                # Show manual download links for failed mods
                manual_downloads = [m for m in failed_mods if m.get("reason") == "no_download_url"]
                if manual_downloads:
                    log_callback("\n⚠ Some mods require manual download:\n")
                    for mod in manual_downloads:
                        mod_name = mod.get("mod_name", mod.get("filename", "Unknown"))
                        url = mod.get("manual_url", "")
                        log_callback(f"  • {mod_name}\n")
                        log_callback(f"    → {url}\n")
                    log_callback("\nDownload these and place in the 'mods' folder.\n")

                log_callback("\n")

            # Copy overrides
            if log_callback:
                log_callback("Step 5/5: Copying configurations...\n")

            overrides_name = manifest.get("overrides", "overrides")
            overrides_dir = extract_dir / overrides_name
            if overrides_dir.exists():
                self._copy_overrides(overrides_dir, install_path, log_callback)
                if log_callback:
                    log_callback("Configurations copied\n\n")

            # Save modpack info
            info_file = install_path / "modpack_info.json"
            info_data = {
                "name": modpack_name,
                "slug": modpack_slug,
                "source": "curseforge",
                "minecraft_version": minecraft_version,
                "loader": loader_type,
                "loader_version": loader_version,
                "curseforge_url": f"https://www.curseforge.com/minecraft/modpacks/{modpack_slug}",
                "curseforge_id": modpack_id,
                "version_name": version_name,
                "installed_date": str(Path(install_path).stat().st_mtime) if install_path.exists() else ""
            }

            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(info_data, f, indent=2)

            # Cleanup temp
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

            return {
                "success": True,
                "install_path": str(install_path),
                "minecraft_version": minecraft_version,
                "loader_type": loader_type,
                "loader_version": loader_version
            }

        except Exception as e:
            if log_callback:
                log_callback(f"\nError during installation: {str(e)}\n")
            return {"success": False, "error": str(e)}

    def get_installed_client_modpacks(self) -> List[Dict]:
        """
        Get list of installed client modpacks from ~/.pycraft/modpacks/

        Returns:
            List of dicts with modpack info (name, minecraft_version, loader, loader_version, path)
        """
        modpacks = []
        modpacks_dir = Path.home() / ".pycraft" / "modpacks"

        if not modpacks_dir.exists():
            return modpacks

        for folder in modpacks_dir.iterdir():
            if folder.is_dir():
                info_file = folder / "modpack_info.json"
                if info_file.exists():
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                        info["path"] = str(folder)
                        info["folder_name"] = folder.name
                        modpacks.append(info)
                    except:
                        # If info file is corrupted, still list it with basic info
                        modpacks.append({
                            "name": folder.name,
                            "folder_name": folder.name,
                            "path": str(folder),
                            "minecraft_version": "Unknown",
                            "loader": "Unknown",
                            "loader_version": ""
                        })

        return modpacks

    def uninstall_client_modpack(self, folder_name: str) -> bool:
        """
        Uninstall a client modpack by deleting its folder

        Args:
            folder_name: Name of the modpack folder to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            modpack_path = Path.home() / ".pycraft" / "modpacks" / folder_name
            if modpack_path.exists() and modpack_path.is_dir():
                shutil.rmtree(modpack_path)
                return True
            return False
        except Exception:
            return False

    def detect_client_only_mods(self, mods_folder: str, server_folder: str = None) -> List[Dict]:
        """
        Detect client-only mods using a multi-source approach (most reliable first):

        1. PRIORITY 1: Check saved Modrinth metadata (pycraft_mod_metadata.json)
           - This is the most reliable source as it comes directly from the modpack author
        2. PRIORITY 2: Analyze JAR metadata (fabric.mod.json environment, mods.toml)
           - Explicit declarations are trustworthy
        3. PRIORITY 3: Known issues database (known_issues.json)
           - Mods known to crash servers, loaded from external file

        Args:
            mods_folder: Path to the mods folder
            server_folder: Optional path to server folder (parent of mods_folder)
                          If not provided, will try to derive from mods_folder

        Returns:
            List of dicts with mod info: {name, file, reason, confidence}
        """
        client_mods = []

        if not os.path.exists(mods_folder):
            return client_mods

        # Derive server_folder if not provided
        if not server_folder:
            server_folder = str(Path(mods_folder).parent)

        # Load saved metadata from Modrinth (most reliable source)
        saved_metadata = self._load_mod_metadata(server_folder)

        # Load known client-only mods from known_issues.json
        # This is maintained externally and updated with program releases
        critical_client_mods = self._get_known_client_mods()

        # Step 1: Scan all mods to collect dependencies
        required_by_others = set()
        for filename in os.listdir(mods_folder):
            if not filename.endswith('.jar'):
                continue
            jar_path = os.path.join(mods_folder, filename)
            _, dependencies = self._extract_mod_info(jar_path)
            for dep in dependencies:
                required_by_others.add(dep.lower())

        # Step 2: Analyze each mod using multi-source detection
        for filename in os.listdir(mods_folder):
            if not filename.endswith('.jar'):
                continue

            jar_path = os.path.join(mods_folder, filename)
            mod_info = None

            # PRIORITY 1: Check saved Modrinth metadata (MOST RELIABLE)
            if filename in saved_metadata:
                meta = saved_metadata[filename]
                server_support = meta.get("server", "required")
                # "unsupported" means the mod doesn't work on server
                if server_support == "unsupported":
                    mod_name = filename.replace('.jar', '')
                    mod_info = {
                        'name': mod_name,
                        'file': filename,
                        'reason': 'Modrinth metadata: server=unsupported',
                        'confidence': 'HIGH'
                    }

            # PRIORITY 2: Check JAR metadata (fabric.mod.json, mods.toml)
            if not mod_info:
                mod_info = self._analyze_mod_jar_environment(jar_path, required_by_others)

            # PRIORITY 3: Check critical mods list (ONLY for crash-prone mods)
            if not mod_info:
                mod_id, _ = self._extract_mod_info(jar_path)
                filename_lower = filename.lower()

                for critical_mod in critical_client_mods:
                    if critical_mod in filename_lower or (mod_id and critical_mod == mod_id.lower()):
                        # Verify it's not required by other mods
                        if mod_id and mod_id.lower() in required_by_others:
                            continue
                        mod_name = filename.replace('.jar', '')
                        mod_info = {
                            'name': mod_name,
                            'file': filename,
                            'reason': f'Critical client mod: {critical_mod}',
                            'confidence': 'MEDIUM'
                        }
                        break

            if mod_info:
                mod_info['file'] = filename
                client_mods.append(mod_info)

        return client_mods

    def _analyze_mod_jar_environment(self, jar_path: str, required_by_others: set = None) -> Optional[Dict]:
        """
        Analyze JAR metadata for EXPLICIT client-only declarations.
        Only returns a result if the mod explicitly declares itself as client-only.

        Checks:
        - fabric.mod.json: "environment": "client"
        - mods.toml: side="CLIENT" or displayTest="IGNORE_ALL_VERSION"

        Args:
            jar_path: Path to the JAR file
            required_by_others: Set of mod IDs that other mods depend on

        Returns:
            Dict with {name, reason, confidence} if client-only, None otherwise
        """
        if required_by_others is None:
            required_by_others = set()

        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                namelist = jar.namelist()
                mod_name = os.path.basename(jar_path).replace('.jar', '')
                mod_id = ''

                # Check Fabric mod (fabric.mod.json)
                if 'fabric.mod.json' in namelist:
                    try:
                        with jar.open('fabric.mod.json') as f:
                            data = json.load(f)
                            mod_id = data.get('id', '')
                            mod_name = data.get('name', mod_id) or mod_name
                            environment = data.get('environment', '*')

                            # Skip if this mod is required by other mods
                            if mod_id and mod_id.lower() in required_by_others:
                                return None

                            # ONLY flag if explicitly client-only
                            if environment == 'client':
                                return {
                                    'name': mod_name,
                                    'reason': 'fabric.mod.json: environment=client',
                                    'confidence': 'HIGH'
                                }
                    except Exception:
                        pass

                # Check Forge mod (mods.toml)
                if 'META-INF/mods.toml' in namelist:
                    try:
                        with jar.open('META-INF/mods.toml') as f:
                            import re
                            content = f.read().decode('utf-8')

                            # Get mod ID and name
                            mod_id_match = re.search(r'modId\s*=\s*"([^"]+)"', content)
                            if mod_id_match:
                                mod_id = mod_id_match.group(1)

                            display_name_match = re.search(r'displayName\s*=\s*"([^"]+)"', content)
                            if display_name_match:
                                mod_name = display_name_match.group(1)

                            # Skip if required by others
                            if mod_id and mod_id.lower() in required_by_others:
                                return None

                            # Check for explicit side="CLIENT"
                            content_upper = content.upper()
                            if 'SIDE="CLIENT"' in content_upper or 'SIDE = "CLIENT"' in content_upper:
                                return {
                                    'name': mod_name,
                                    'reason': 'mods.toml: side=CLIENT',
                                    'confidence': 'HIGH'
                                }

                            # Check for displayTest indicating client-only
                            # IGNORE_ALL_VERSION means it doesn't need to be on server
                            display_test_match = re.search(r'displayTest\s*=\s*"([^"]+)"', content)
                            if display_test_match:
                                test_value = display_test_match.group(1).upper()
                                if test_value == 'IGNORE_ALL_VERSION':
                                    return {
                                        'name': mod_name,
                                        'reason': 'mods.toml: displayTest=IGNORE_ALL_VERSION',
                                        'confidence': 'HIGH'
                                    }
                    except Exception:
                        pass

        except Exception:
            pass

        return None

    def _extract_mod_info(self, jar_path: str) -> Tuple[str, List[str]]:
        """
        Extract mod ID and dependencies from a JAR file.

        Returns:
            Tuple of (mod_id, list of dependency mod_ids)
        """
        mod_id = ""
        dependencies = []

        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                namelist = jar.namelist()

                # Check Fabric mod
                if 'fabric.mod.json' in namelist:
                    try:
                        with jar.open('fabric.mod.json') as f:
                            data = json.load(f)
                            mod_id = data.get('id', '')

                            # Extract dependencies
                            depends = data.get('depends', {})
                            if isinstance(depends, dict):
                                dependencies.extend(depends.keys())
                            elif isinstance(depends, list):
                                dependencies.extend(depends)
                    except:
                        pass

                # Check Forge mod
                if 'META-INF/mods.toml' in namelist:
                    try:
                        with jar.open('META-INF/mods.toml') as f:
                            content = f.read().decode('utf-8')

                            import re
                            # Get mod ID
                            mod_id_match = re.search(r'modId\s*=\s*"([^"]+)"', content)
                            if mod_id_match:
                                mod_id = mod_id_match.group(1)

                            # Get dependencies
                            dep_matches = re.findall(r'\[\[dependencies\.[^\]]+\]\]\s*modId\s*=\s*"([^"]+)"', content)
                            dependencies.extend(dep_matches)

                            # Also check for inline dependencies
                            inline_deps = re.findall(r'modId\s*=\s*"([^"]+)"', content)
                            for dep in inline_deps:
                                if dep not in dependencies and dep != mod_id:
                                    # Only add if it looks like a dependency section
                                    pass  # Avoid false positives
                    except:
                        pass

        except:
            pass

        # Filter out minecraft and forge from dependencies
        filtered_deps = [d for d in dependencies if d.lower() not in {'minecraft', 'forge', 'fabricloader', 'fabric-api', 'fabric', 'java', 'neoforge'}]

        return mod_id, filtered_deps

    def _analyze_mod_jar(self, jar_path: str, known_client_mods: set, required_by_others: set = None) -> Optional[Dict]:
        """
        Analyze a mod JAR file to determine if it's client-only.
        Uses multiple detection strategies for maximum accuracy.

        Args:
            jar_path: Path to the JAR file
            known_client_mods: Set of known client-only mod IDs
            required_by_others: Set of mod IDs that other mods depend on (these are protected)

        Returns:
            Dict with {name, reason} if client-only, None otherwise
        """
        if required_by_others is None:
            required_by_others = set()

        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                namelist = jar.namelist()
                mod_id = ''
                mod_name = os.path.basename(jar_path)

                # Helper function to check if mod is safe to flag
                def is_safe_to_flag(mid: str) -> bool:
                    """Check if mod is NOT required by other mods"""
                    if not mid:
                        return True
                    return mid.lower() not in required_by_others

                # ========== PRIORITY 1: Check by filename FIRST (fastest, most reliable) ==========
                filename_lower = os.path.basename(jar_path).lower()
                # Remove version numbers and common suffixes for better matching
                filename_clean = filename_lower.replace('.jar', '').replace('-', '').replace('_', '').replace('+', '').replace('.', '')

                for known_mod in known_client_mods:
                    normalized_known = known_mod.replace('_', '').replace('-', '').replace('.', '')
                    if normalized_known in filename_clean:
                        # Extract mod name from filename for better display
                        display_name = os.path.basename(jar_path).replace('.jar', '')
                        return {'name': display_name, 'reason': f'Known client-only mod (pattern: {known_mod})'}

                # ========== PRIORITY 2: Check Fabric mod (fabric.mod.json) ==========
                if 'fabric.mod.json' in namelist:
                    try:
                        with jar.open('fabric.mod.json') as f:
                            data = json.load(f)
                            mod_id = data.get('id', '')
                            mod_name = data.get('name', mod_id) or mod_name
                            environment = data.get('environment', '*')

                            # Skip if this mod is required by others
                            if not is_safe_to_flag(mod_id):
                                return None

                            # Check if explicitly client-only
                            if environment == 'client':
                                return {'name': mod_name, 'reason': 'Fabric environment: client'}

                            # Check known list by mod ID
                            if mod_id.lower() in known_client_mods:
                                return {'name': mod_name, 'reason': f'Known client-only mod (id: {mod_id})'}

                            # Check mixins for client-only targets
                            mixins = data.get('mixins', [])
                            for mixin_entry in mixins:
                                if isinstance(mixin_entry, dict):
                                    if mixin_entry.get('environment') == 'client':
                                        has_non_client = any(
                                            isinstance(m, dict) and m.get('environment') != 'client'
                                            for m in mixins
                                        )
                                        if not has_non_client and len(mixins) == 1:
                                            return {'name': mod_name, 'reason': 'Only client mixins'}
                    except:
                        pass

                # ========== PRIORITY 3: Check Forge mod (META-INF/mods.toml) ==========
                if 'META-INF/mods.toml' in namelist:
                    try:
                        with jar.open('META-INF/mods.toml') as f:
                            content = f.read().decode('utf-8')

                            import re
                            mod_id_match = re.search(r'modId\s*=\s*"([^"]+)"', content)
                            if mod_id_match:
                                mod_id = mod_id_match.group(1)

                            display_name_match = re.search(r'displayName\s*=\s*"([^"]+)"', content)
                            if display_name_match:
                                mod_name = display_name_match.group(1)
                            elif mod_id:
                                mod_name = mod_id

                            # Skip if this mod is required by others
                            if not is_safe_to_flag(mod_id):
                                return None

                            # Check for side="CLIENT" in mods.toml (case insensitive)
                            content_upper = content.upper()
                            if 'SIDE="CLIENT"' in content_upper or 'SIDE = "CLIENT"' in content_upper:
                                return {'name': mod_name, 'reason': 'Forge side: CLIENT'}

                            # Check for clientSideOnly marker
                            if 'clientsideonly' in content.lower() and 'true' in content.lower():
                                return {'name': mod_name, 'reason': 'Forge clientSideOnly: true'}

                            # Check known list by mod ID
                            if mod_id.lower() in known_client_mods:
                                return {'name': mod_name, 'reason': f'Known client-only mod (id: {mod_id})'}

                            # Check displayTest - client mods often have IGNORE_SERVER_VERSION
                            if 'displayTest' in content:
                                display_test_match = re.search(r'displayTest\s*=\s*"([^"]+)"', content)
                                if display_test_match:
                                    test_value = display_test_match.group(1).upper()
                                    if test_value in ['IGNORE_SERVER_VERSION', 'IGNORE_ALL_VERSION', 'NONE']:
                                        # This mod explicitly says it doesn't need to match server
                                        # Check if it's in known list or has client-only indicators
                                        if mod_id.lower() in known_client_mods:
                                            return {'name': mod_name, 'reason': f'Client mod with displayTest={test_value}'}
                    except:
                        pass

                # ========== PRIORITY 4: Check mixin configs ==========
                mixin_configs = [f for f in namelist if f.endswith('.mixins.json') or f.endswith('-mixins.json') or f == 'mixins.json']
                for mixin_config in mixin_configs:
                    try:
                        with jar.open(mixin_config) as f:
                            mixin_data = json.load(f)

                            client_mixins = mixin_data.get('client', [])
                            common_mixins = mixin_data.get('mixins', [])
                            server_mixins = mixin_data.get('server', [])

                            # If ONLY client mixins and no common/server, it's client-only
                            if client_mixins and not common_mixins and not server_mixins:
                                return {'name': mod_name, 'reason': 'Only client mixins defined'}

                            # Check package name for client indicators
                            package = mixin_data.get('package', '')
                            if '.client.' in package or package.endswith('.client'):
                                if not server_mixins and not common_mixins:
                                    return {'name': mod_name, 'reason': 'Client mixin package'}
                    except:
                        pass

                # ========== PRIORITY 5: Deep class structure analysis ==========
                # Count classes in client vs common/server packages
                client_class_count = 0
                server_class_count = 0
                total_class_count = 0

                # Patterns that indicate client-only code
                client_only_patterns = [
                    'net/minecraft/client/',
                    'com/mojang/blaze3d/',
                    '/client/gui/',
                    '/client/renderer/',
                    '/client/render/',
                    '/client/screen/',
                    '/client/model/',
                    '/client/particle/',
                    '/client/shader/',
                    '/client/keybind/',
                    '/mixin/client/',
                    '/cleint/',  # Common typo (like in Barista mod)
                ]

                # Patterns that indicate server-compatible code
                server_patterns = [
                    '/server/',
                    '/common/',
                    '/shared/',
                    '/api/',
                    '/core/',
                    '/data/',
                    '/world/',
                    '/entity/',
                    '/block/',
                    '/item/',
                    '/network/',
                    '/command/',
                ]

                for f in namelist:
                    if f.endswith('.class'):
                        total_class_count += 1
                        f_lower = f.lower()

                        is_client = False
                        for pattern in client_only_patterns:
                            if pattern in f_lower:
                                client_class_count += 1
                                is_client = True
                                break

                        if not is_client:
                            for pattern in server_patterns:
                                if pattern in f_lower:
                                    server_class_count += 1
                                    break

                # If mod has ONLY client classes (>80% client, no server classes)
                # and it's in our suspicious list, flag it
                if total_class_count > 0:
                    client_ratio = client_class_count / total_class_count
                    if client_ratio > 0.8 and server_class_count == 0:
                        # Double check it's in known list before flagging based on structure
                        if mod_id and mod_id.lower() in known_client_mods:
                            return {'name': mod_name, 'reason': f'Client-only structure ({int(client_ratio*100)}% client classes)'}

                # ========== PRIORITY 6: Check for @OnlyIn(Dist.CLIENT) patterns in class files ==========
                # This is expensive so we only do it for suspicious mods
                if mod_id and mod_id.lower() in known_client_mods:
                    # Already checked above, but verify through class inspection
                    for f in namelist[:50]:  # Only check first 50 files for performance
                        if f.endswith('.class'):
                            try:
                                with jar.open(f) as class_file:
                                    # Read first 2KB of class file for quick pattern check
                                    class_data = class_file.read(2048)
                                    # Look for OnlyIn annotation signature
                                    if b'OnlyIn' in class_data and b'CLIENT' in class_data:
                                        return {'name': mod_name, 'reason': 'Contains @OnlyIn(Dist.CLIENT) annotations'}
                            except:
                                pass

        except Exception as e:
            # Log error for debugging but don't crash
            pass

        return None

    def remove_client_mods(self, mods_folder: str, mod_files: List[str]) -> Tuple[int, int, str]:
        """
        Move specified mod files to a backup folder instead of deleting.

        Args:
            mods_folder: Path to the mods folder
            mod_files: List of mod filenames to remove

        Returns:
            Tuple of (successfully_moved, failed_to_move, backup_folder_path)
        """
        removed = 0
        failed = 0

        # Create backup folder in the server directory (parent of mods folder)
        server_folder = os.path.dirname(mods_folder)
        backup_folder = os.path.join(server_folder, "client_mods_deleted")
        os.makedirs(backup_folder, exist_ok=True)

        for filename in mod_files:
            try:
                src_path = os.path.join(mods_folder, filename)
                dst_path = os.path.join(backup_folder, filename)

                if os.path.exists(src_path):
                    # If file already exists in backup, add a number
                    if os.path.exists(dst_path):
                        base, ext = os.path.splitext(filename)
                        counter = 1
                        while os.path.exists(dst_path):
                            dst_path = os.path.join(backup_folder, f"{base}_{counter}{ext}")
                            counter += 1

                    shutil.move(src_path, dst_path)
                    removed += 1
            except Exception:
                failed += 1

        return removed, failed, backup_folder
