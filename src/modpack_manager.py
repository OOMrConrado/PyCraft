import os
import json
import zipfile
import shutil
import requests
from typing import Optional, Callable, Dict, List, Tuple
from pathlib import Path

from src.api_handler import ModrinthAPI, CurseForgeAPI
from src.loader_manager import LoaderManager
from src.java_manager import JavaManager


class ModpackManager:
    """Gestiona la descarga e instalación de modpacks completos"""

    def __init__(self):
        self.modrinth_api = ModrinthAPI()
        self.curseforge_api = None  # Se inicializa si hay API key
        self.loader_manager = LoaderManager()
        self.java_manager = JavaManager()

    def set_curseforge_api_key(self, api_key: str):
        """Configura la API key de CurseForge"""
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
        Instala un modpack de Modrinth

        Args:
            project_id: ID del proyecto en Modrinth
            version_id: ID de la versión a instalar
            server_folder: Carpeta donde instalar el servidor
            log_callback: Función para reportar progreso

        Returns:
            True si la instalación fue exitosa
        """
        try:
            if log_callback:
                log_callback("\n╔════════════════════════════════════════════════╗\n")
                log_callback("║   INSTALACIÓN DE MODPACK DESDE MODRINTH       ║\n")
                log_callback("╚════════════════════════════════════════════════╝\n\n")

            # Crear carpeta si no existe
            os.makedirs(server_folder, exist_ok=True)

            # Descargar modpack
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

            # Extraer modpack
            if log_callback:
                log_callback("Paso 2/6: Extrayendo archivos del modpack...\n")

            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(modpack_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            if log_callback:
                log_callback("✓ Archivos extraídos correctamente\n\n")

            # Leer manifest (modrinth.index.json)
            manifest_path = extract_dir / "modrinth.index.json"
            if not manifest_path.exists():
                if log_callback:
                    log_callback("✗ Error: No se encontró modrinth.index.json\n")
                return False

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Detectar información del modpack
            minecraft_version = self.loader_manager.get_minecraft_version_from_manifest(manifest)
            loader_type = self.loader_manager.detect_loader_type(manifest)
            loader_version = self.loader_manager.get_loader_version_from_manifest(manifest)

            if log_callback:
                log_callback("Paso 3/6: Información del modpack detectada\n")
                log_callback(f"  • Minecraft: {minecraft_version}\n")
                log_callback(f"  • Loader: {loader_type}\n")
                log_callback(f"  • Versión del loader: {loader_version or 'última'}\n\n")

            # Verificar/instalar Java
            if log_callback:
                log_callback("Paso 4/6: Verificando Java...\n")

            java_exe = self.java_manager.ensure_java_installed(minecraft_version, log_callback)

            if not java_exe:
                if log_callback:
                    log_callback("✗ Error: No se pudo instalar Java\n")
                return False

            # Descargar mods
            if log_callback:
                log_callback("\nPaso 5/6: Descargando mods del modpack...\n")

            mods_folder = Path(server_folder) / "mods"
            mods_folder.mkdir(exist_ok=True)

            files = manifest.get("files", [])
            total_files = len(files)

            if log_callback:
                log_callback(f"Se descargarán {total_files} mods...\n")

            for i, file_info in enumerate(files, 1):
                # Modrinth files tienen "downloads" y "path"
                downloads = file_info.get("downloads", [])
                file_path = file_info.get("path", "")

                if downloads and file_path:
                    download_url = downloads[0]
                    filename = os.path.basename(file_path)

                    # Solo descargar mods (no configs ni recursos)
                    if file_path.startswith("mods/"):
                        try:
                            dest_file = mods_folder / filename

                            if log_callback:
                                log_callback(f"  [{i}/{total_files}] {filename}...")

                            response = requests.get(download_url, timeout=30)
                            response.raise_for_status()

                            with open(dest_file, 'wb') as f:
                                f.write(response.content)

                            if log_callback:
                                log_callback(" ✓\n")

                        except Exception as e:
                            if log_callback:
                                log_callback(f" ✗ Error: {str(e)}\n")

            if log_callback:
                log_callback("\n✓ Mods descargados\n\n")

            # Copiar overrides
            overrides_dir = extract_dir / "overrides"
            if overrides_dir.exists():
                if log_callback:
                    log_callback("Copiando archivos de configuración...\n")

                self._copy_overrides(overrides_dir, Path(server_folder), log_callback)

                if log_callback:
                    log_callback("✓ Configuraciones copiadas\n\n")

            # Instalar loader
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

            # Limpiar archivos temporales
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
        Instala un modpack de CurseForge

        Args:
            modpack_id: ID del modpack
            file_id: ID del archivo/versión
            server_folder: Carpeta donde instalar el servidor
            log_callback: Función para reportar progreso

        Returns:
            True si la instalación fue exitosa
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

            # Crear carpeta si no existe
            os.makedirs(server_folder, exist_ok=True)

            # Descargar modpack
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

            # Extraer modpack
            if log_callback:
                log_callback("Paso 2/6: Extrayendo archivos del modpack...\n")

            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(modpack_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            if log_callback:
                log_callback("✓ Archivos extraídos correctamente\n\n")

            # Leer manifest (manifest.json)
            manifest_path = extract_dir / "manifest.json"
            if not manifest_path.exists():
                if log_callback:
                    log_callback("✗ Error: No se encontró manifest.json\n")
                return False

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Detectar información del modpack
            minecraft_version = self.loader_manager.get_minecraft_version_from_manifest(manifest)
            loader_type = self.loader_manager.detect_loader_type(manifest)
            loader_version = self.loader_manager.get_loader_version_from_manifest(manifest)

            if log_callback:
                log_callback("Paso 3/6: Información del modpack detectada\n")
                log_callback(f"  • Minecraft: {minecraft_version}\n")
                log_callback(f"  • Loader: {loader_type}\n")
                log_callback(f"  • Versión del loader: {loader_version or 'última'}\n\n")

            # Verificar/instalar Java
            if log_callback:
                log_callback("Paso 4/6: Verificando Java...\n")

            java_exe = self.java_manager.ensure_java_installed(minecraft_version, log_callback)

            if not java_exe:
                if log_callback:
                    log_callback("✗ Error: No se pudo instalar Java\n")
                return False

            # Descargar mods
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
                        # Obtener información del archivo
                        file_data = self.curseforge_api.get_mod_file_info(project_id, file_id_mod)

                        if file_data:
                            filename = file_data.get("fileName")
                            download_url = file_data.get("downloadUrl")

                            if log_callback:
                                log_callback(f"  [{i}/{total_files}] {filename}...")

                            if download_url:
                                dest_file = mods_folder / filename

                                response = requests.get(download_url, timeout=30)
                                response.raise_for_status()

                                with open(dest_file, 'wb') as f:
                                    f.write(response.content)

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

            # Copiar overrides
            overrides_dir = extract_dir / manifest.get("overrides", "overrides")
            if overrides_dir.exists():
                if log_callback:
                    log_callback("Copiando archivos de configuración...\n")

                self._copy_overrides(overrides_dir, Path(server_folder), log_callback)

                if log_callback:
                    log_callback("✓ Configuraciones copiadas\n\n")

            # Instalar loader
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

            # Limpiar archivos temporales
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

    # ==================== UTILIDADES ====================

    def _copy_overrides(self, source_dir: Path, dest_dir: Path, log_callback: Optional[Callable[[str], None]] = None):
        """
        Copia los archivos de overrides al servidor

        Args:
            source_dir: Directorio fuente (overrides)
            dest_dir: Directorio destino (carpeta del servidor)
            log_callback: Función para reportar progreso
        """
        try:
            for item in source_dir.rglob("*"):
                if item.is_file():
                    # Calcular ruta relativa
                    relative_path = item.relative_to(source_dir)
                    dest_file = dest_dir / relative_path

                    # Crear directorios si no existen
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    # Copiar archivo
                    shutil.copy2(item, dest_file)

        except Exception as e:
            if log_callback:
                log_callback(f"Advertencia al copiar overrides: {str(e)}\n")

    def search_modpacks(
        self,
        query: str,
        platform: str = "modrinth",
        limit: int = 20
    ) -> Optional[List[Dict]]:
        """
        Busca modpacks en la plataforma especificada

        Args:
            query: Texto de búsqueda
            platform: "modrinth" o "curseforge"
            limit: Número máximo de resultados

        Returns:
            Lista de modpacks encontrados
        """
        if platform == "modrinth":
            return self.modrinth_api.search_modpacks(query, limit)
        elif platform == "curseforge":
            if self.curseforge_api and self.curseforge_api.is_configured():
                return self.curseforge_api.search_modpacks(query, limit)
            else:
                return None
        return None

    def get_recommended_ram(self, modpack_manifest: Dict) -> int:
        """
        Obtiene la RAM recomendada para un modpack basándose en el número de mods

        Args:
            modpack_manifest: Manifest del modpack

        Returns:
            RAM recomendada en MB
        """
        try:
            files = modpack_manifest.get("files", [])
            num_mods = len(files)

            # Heurística básica
            if num_mods < 25:
                return 3072  # 3 GB
            elif num_mods < 50:
                return 4096  # 4 GB
            elif num_mods < 100:
                return 6144  # 6 GB
            elif num_mods < 150:
                return 8192  # 8 GB
            else:
                return 10240  # 10 GB

        except:
            return 4096  # Default 4 GB
