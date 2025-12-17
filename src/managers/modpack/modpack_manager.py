import os
import json
import zipfile
import shutil
import requests
from typing import Optional, Callable, Dict, List, Tuple
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

    def set_curseforge_api_key(self, api_key: str):
        """Configures the CurseForge API key"""
        self.curseforge_api = CurseForgeAPI(api_key)

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
                log_callback("║   INSTALACIÓN DE MODPACK DESDE MODRINTH       ║\n")
                log_callback("╚════════════════════════════════════════════════╝\n\n")

            # Create folder if it doesn't exist
            os.makedirs(server_folder, exist_ok=True)

            # Download modpack
            if log_callback:
                log_callback("Paso 1/6: Descargando modpack...\n")

            temp_dir = Path(server_folder) / ".temp_modpack"
            temp_dir.mkdir(exist_ok=True)

            modpack_file = self.modrinth_api.download_version_file(version_id, str(temp_dir))

            if not modpack_file:
                if log_callback:
                    log_callback("✗ Error al descargar el modpack\n")
                return False

            if log_callback:
                log_callback(f"✓ Modpack descargado: {os.path.basename(modpack_file)}\n\n")

            # Extract modpack
            if log_callback:
                log_callback("Paso 2/6: Extrayendo archivos del modpack...\n")

            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(modpack_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            if log_callback:
                log_callback("✓ Archivos extraídos correctamente\n\n")

            # Read manifest (modrinth.index.json)
            manifest_path = extract_dir / "modrinth.index.json"
            if not manifest_path.exists():
                if log_callback:
                    log_callback("✗ Error: No se encontró modrinth.index.json\n")
                return False

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Detect modpack information
            minecraft_version = self.loader_manager.get_minecraft_version_from_manifest(manifest)
            loader_type = self.loader_manager.detect_loader_type(manifest)
            loader_version = self.loader_manager.get_loader_version_from_manifest(manifest)

            if log_callback:
                log_callback("Paso 3/6: Información del modpack detectada\n")
                log_callback(f"  • Minecraft: {minecraft_version}\n")
                log_callback(f"  • Loader: {loader_type}\n")
                log_callback(f"  • Versión del loader: {loader_version or 'última'}\n\n")

            # Verify/install Java
            if log_callback:
                log_callback("Paso 4/6: Verificando Java...\n")

            java_exe = self.java_manager.ensure_java_installed(minecraft_version, log_callback)

            if not java_exe:
                if log_callback:
                    log_callback("✗ Error: No se pudo instalar Java\n")
                return False

            # Download mods
            if log_callback:
                log_callback("\nPaso 5/6: Descargando mods del modpack...\n")

            mods_folder = Path(server_folder) / "mods"
            mods_folder.mkdir(exist_ok=True)

            files = manifest.get("files", [])
            total_files = len(files)

            if log_callback:
                log_callback(f"Se descargarán {total_files} mods...\n")

            for i, file_info in enumerate(files, 1):
                # Modrinth files have "downloads" and "path"
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
                                log_callback(" ✓\n")

                        except Exception as e:
                            if log_callback:
                                log_callback(f" ✗ Error: {str(e)}\n")

            if log_callback:
                log_callback("\n✓ Mods descargados\n\n")

            # Copy overrides
            overrides_dir = extract_dir / "overrides"
            if overrides_dir.exists():
                if log_callback:
                    log_callback("Copiando archivos de configuración...\n")

                self._copy_overrides(overrides_dir, Path(server_folder), log_callback)

                if log_callback:
                    log_callback("✓ Configuraciones copiadas\n\n")

            # Install loader
            if log_callback:
                log_callback("Paso 6/6: Instalando mod loader...\n")

            if loader_type == "forge":
                success = self.loader_manager.install_forge(
                    minecraft_version,
                    server_folder,
                    java_exe,
                    loader_version,
                    log_callback
                )
            elif loader_type == "fabric":
                success = self.loader_manager.install_fabric(
                    minecraft_version,
                    server_folder,
                    java_exe,
                    loader_version,
                    log_callback
                )
            else:
                if log_callback:
                    log_callback(f"✗ Error: Loader '{loader_type}' no soportado\n")
                success = False

            # Save manifest to server folder for version detection later
            if success:
                try:
                    dest_manifest = Path(server_folder) / "modrinth.index.json"
                    shutil.copy2(manifest_path, dest_manifest)
                    if log_callback:
                        log_callback("\n✓ Manifest guardado para referencia futura\n")
                except Exception as e:
                    if log_callback:
                        log_callback(f"⚠ Advertencia: No se pudo guardar el manifest: {e}\n")

            # Clean up temporary files
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

            if success and log_callback:
                log_callback("\n╔════════════════════════════════════════════════╗\n")
                log_callback("║   ✓ MODPACK INSTALADO EXITOSAMENTE            ║\n")
                log_callback("╚════════════════════════════════════════════════╝\n\n")

            return success

        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error durante la instalación: {str(e)}\n")
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
        Installs a modpack from CurseForge

        Args:
            modpack_id: Modpack ID
            file_id: File/version ID
            server_folder: Folder where to install the server
            log_callback: Function to report progress

        Returns:
            True if installation was successful
        """
        if not self.curseforge_api or not self.curseforge_api.is_configured():
            if log_callback:
                log_callback("✗ Error: CurseForge API key no configurada\n")
            return False

        try:
            if log_callback:
                log_callback("\n╔════════════════════════════════════════════════╗\n")
                log_callback("║   INSTALACIÓN DE MODPACK DESDE CURSEFORGE     ║\n")
                log_callback("╚════════════════════════════════════════════════╝\n\n")

            # Create folder if it doesn't exist
            os.makedirs(server_folder, exist_ok=True)

            # Download modpack
            if log_callback:
                log_callback("Paso 1/6: Descargando modpack...\n")

            temp_dir = Path(server_folder) / ".temp_modpack"
            temp_dir.mkdir(exist_ok=True)

            modpack_file = self.curseforge_api.download_modpack_file(modpack_id, file_id, str(temp_dir))

            if not modpack_file:
                if log_callback:
                    log_callback("✗ Error al descargar el modpack\n")
                return False

            if log_callback:
                log_callback(f"✓ Modpack descargado: {os.path.basename(modpack_file)}\n\n")

            # Extract modpack
            if log_callback:
                log_callback("Paso 2/6: Extrayendo archivos del modpack...\n")

            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(modpack_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            if log_callback:
                log_callback("✓ Archivos extraídos correctamente\n\n")

            # Read manifest (manifest.json)
            manifest_path = extract_dir / "manifest.json"
            if not manifest_path.exists():
                if log_callback:
                    log_callback("✗ Error: No se encontró manifest.json\n")
                return False

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Detect modpack information
            minecraft_version = self.loader_manager.get_minecraft_version_from_manifest(manifest)
            loader_type = self.loader_manager.detect_loader_type(manifest)
            loader_version = self.loader_manager.get_loader_version_from_manifest(manifest)

            if log_callback:
                log_callback("Paso 3/6: Información del modpack detectada\n")
                log_callback(f"  • Minecraft: {minecraft_version}\n")
                log_callback(f"  • Loader: {loader_type}\n")
                log_callback(f"  • Versión del loader: {loader_version or 'última'}\n\n")

            # Verify/install Java
            if log_callback:
                log_callback("Paso 4/6: Verificando Java...\n")

            java_exe = self.java_manager.ensure_java_installed(minecraft_version, log_callback)

            if not java_exe:
                if log_callback:
                    log_callback("✗ Error: No se pudo instalar Java\n")
                return False

            # Download mods
            if log_callback:
                log_callback("\nPaso 5/6: Descargando mods del modpack...\n")

            mods_folder = Path(server_folder) / "mods"
            mods_folder.mkdir(exist_ok=True)

            files = manifest.get("files", [])
            total_files = len(files)

            if log_callback:
                log_callback(f"Se descargarán {total_files} mods desde CurseForge...\n")

            for i, file_info in enumerate(files, 1):
                project_id = file_info.get("projectID")
                file_id_mod = file_info.get("fileID")

                if project_id and file_id_mod:
                    try:
                        # Get file information
                        file_data = self.curseforge_api.get_mod_file_info(project_id, file_id_mod)

                        if file_data:
                            filename = file_data.get("fileName")
                            download_url = file_data.get("downloadUrl")

                            if log_callback:
                                log_callback(f"  [{i}/{total_files}] {filename}...")

                            if download_url:
                                dest_file = mods_folder / filename

                                # Use streaming to avoid loading entire file into memory
                                response = requests.get(download_url, timeout=30, stream=True)
                                response.raise_for_status()

                                # Write in chunks to reduce memory usage
                                with open(dest_file, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)

                                if log_callback:
                                    log_callback(" ✓\n")
                            else:
                                if log_callback:
                                    log_callback(" ⚠ Sin URL de descarga\n")

                    except Exception as e:
                        if log_callback:
                            log_callback(f" ✗ Error: {str(e)}\n")

            if log_callback:
                log_callback("\n✓ Mods descargados\n\n")

            # Copy overrides
            overrides_dir = extract_dir / manifest.get("overrides", "overrides")
            if overrides_dir.exists():
                if log_callback:
                    log_callback("Copiando archivos de configuración...\n")

                self._copy_overrides(overrides_dir, Path(server_folder), log_callback)

                if log_callback:
                    log_callback("✓ Configuraciones copiadas\n\n")

            # Install loader
            if log_callback:
                log_callback("Paso 6/6: Instalando mod loader...\n")

            if loader_type == "forge":
                success = self.loader_manager.install_forge(
                    minecraft_version,
                    server_folder,
                    java_exe,
                    loader_version,
                    log_callback
                )
            elif loader_type == "fabric":
                success = self.loader_manager.install_fabric(
                    minecraft_version,
                    server_folder,
                    java_exe,
                    loader_version,
                    log_callback
                )
            else:
                if log_callback:
                    log_callback(f"✗ Error: Loader '{loader_type}' no soportado\n")
                success = False

            # Save manifest to server folder for version detection later
            if success:
                try:
                    dest_manifest = Path(server_folder) / "manifest.json"
                    shutil.copy2(manifest_path, dest_manifest)
                    if log_callback:
                        log_callback("\n✓ Manifest guardado para referencia futura\n")
                except Exception as e:
                    if log_callback:
                        log_callback(f"⚠ Advertencia: No se pudo guardar el manifest: {e}\n")

            # Clean up temporary files
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

            if success and log_callback:
                log_callback("\n╔════════════════════════════════════════════════╗\n")
                log_callback("║   ✓ MODPACK INSTALADO EXITOSAMENTE            ║\n")
                log_callback("╚════════════════════════════════════════════════╝\n\n")

            return success

        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error durante la instalación: {str(e)}\n")
            return False

    # ==================== UTILITIES ====================

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
                log_callback(f"Advertencia al copiar overrides: {str(e)}\n")

    def search_modpacks(
        self,
        query: str,
        platform: str = "modrinth",
        limit: int = 10,
        offset: int = 0
    ) -> Tuple[Optional[List[Dict]], int]:
        """
        Searches for modpacks on the specified platform

        Args:
            query: Search text
            platform: "modrinth" or "curseforge"
            limit: Maximum number of results per page
            offset: Number of results to skip (for pagination)

        Returns:
            Tuple of (list of modpacks, total results count)
        """
        if platform == "modrinth":
            return self.modrinth_api.search_modpacks(query, limit, offset)
        elif platform == "curseforge":
            if self.curseforge_api and self.curseforge_api.is_configured():
                results = self.curseforge_api.search_modpacks(query, limit)
                return results, len(results) if results else 0
            else:
                return None, 0
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
                "minecraft_version": minecraft_version,
                "loader": loader_type,
                "loader_version": loader_version,
                "modrinth_url": f"https://modrinth.com/modpack/{modpack_slug}",
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
