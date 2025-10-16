import requests
from typing import List, Dict, Optional, Tuple
import json
import os
from pathlib import Path


class MinecraftAPIHandler:
    """Maneja las peticiones a la API de Mojang para obtener versiones de Minecraft"""

    VERSION_MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"

    def __init__(self):
        self.versions_cache = None

    def get_all_versions(self) -> Optional[Dict]:
        """Obtiene todas las versiones disponibles de Minecraft"""
        try:
            response = requests.get(self.VERSION_MANIFEST_URL, timeout=10)
            response.raise_for_status()
            self.versions_cache = response.json()
            return self.versions_cache
        except Exception as e:
            print(f"Error al obtener versiones: {e}")
            return None

    def get_release_versions(self) -> List[Dict]:
        """Obtiene solo las versiones estables (releases)"""
        if not self.versions_cache:
            self.get_all_versions()

        if not self.versions_cache:
            return []

        # Filtrar solo las versiones tipo "release"
        releases = [
            version for version in self.versions_cache.get("versions", [])
            if version.get("type") == "release"
        ]
        return releases

    def get_version_names(self) -> List[str]:
        """Obtiene la lista de nombres de versiones release"""
        releases = self.get_release_versions()
        return [version.get("id") for version in releases]

    def get_server_jar_url(self, version_id: str) -> Optional[str]:
        """
        Obtiene la URL del server.jar para una versión específica

        Args:
            version_id: ID de la versión (ejemplo: "1.20.1")

        Returns:
            URL del server.jar o None si no se encuentra
        """
        try:
            # Buscar la versión en el cache
            releases = self.get_release_versions()
            version_data = None

            for version in releases:
                if version.get("id") == version_id:
                    version_data = version
                    break

            if not version_data:
                print(f"Versión {version_id} no encontrada")
                return None

            # Obtener la URL del manifiesto de la versión
            version_url = version_data.get("url")
            if not version_url:
                return None

            # Obtener los detalles de la versión
            response = requests.get(version_url, timeout=10)
            response.raise_for_status()
            version_details = response.json()

            # Extraer la URL del server.jar
            downloads = version_details.get("downloads", {})
            server_info = downloads.get("server")

            if server_info:
                return server_info.get("url")
            else:
                print(f"No se encontró server.jar para la versión {version_id}")
                return None

        except Exception as e:
            print(f"Error al obtener URL del server: {e}")
            return None


class ModrinthAPI:
    """Maneja las peticiones a la API de Modrinth para modpacks"""

    BASE_URL = "https://api.modrinth.com/v2"
    USER_AGENT = "PyCraft/1.0.0 (github.com/OOMrConrado/PyCraft; conradogomez556@gmail.com)"

    def __init__(self):
        self.headers = {
            "User-Agent": self.USER_AGENT
        }

    def search_modpacks(self, query: str, limit: int = 20) -> Optional[List[Dict]]:
        """
        Busca modpacks en Modrinth

        Args:
            query: Texto de búsqueda
            limit: Número máximo de resultados

        Returns:
            Lista de modpacks encontrados
        """
        try:
            url = f"{self.BASE_URL}/search"
            params = {
                "query": query,
                "limit": limit,
                "facets": '[["project_type:modpack"]]'
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return data.get("hits", [])

        except Exception as e:
            print(f"Error al buscar modpacks en Modrinth: {e}")
            return None

    def get_modpack_versions(self, project_id: str) -> Optional[List[Dict]]:
        """
        Obtiene las versiones disponibles de un modpack

        Args:
            project_id: ID del proyecto en Modrinth

        Returns:
            Lista de versiones disponibles
        """
        try:
            url = f"{self.BASE_URL}/project/{project_id}/version"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Error al obtener versiones del modpack: {e}")
            return None

    def get_project_info(self, project_id: str) -> Optional[Dict]:
        """
        Obtiene información detallada de un proyecto

        Args:
            project_id: ID del proyecto

        Returns:
            Información del proyecto
        """
        try:
            url = f"{self.BASE_URL}/project/{project_id}"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Error al obtener información del proyecto: {e}")
            return None

    def download_version_file(self, version_id: str, dest_folder: str) -> Optional[str]:
        """
        Descarga el archivo de una versión de modpack

        Args:
            version_id: ID de la versión
            dest_folder: Carpeta destino

        Returns:
            Ruta al archivo descargado
        """
        try:
            # Obtener información de la versión
            url = f"{self.BASE_URL}/version/{version_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            version_data = response.json()

            # Obtener el archivo principal (mrpack)
            files = version_data.get("files", [])
            if not files:
                return None

            # Buscar el archivo .mrpack
            mrpack_file = None
            for file in files:
                if file.get("filename", "").endswith(".mrpack"):
                    mrpack_file = file
                    break

            if not mrpack_file:
                # Si no hay .mrpack, usar el primer archivo
                mrpack_file = files[0]

            download_url = mrpack_file.get("url")
            filename = mrpack_file.get("filename")

            if not download_url or not filename:
                return None

            # Descargar archivo
            dest_path = os.path.join(dest_folder, filename)
            response = requests.get(download_url, headers=self.headers, stream=True, timeout=30)
            response.raise_for_status()

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return dest_path

        except Exception as e:
            print(f"Error al descargar archivo: {e}")
            return None

# Reservado para implementación futura
# API completamente funcional pero no integrada en la GUI
# Se mantiene el código para futura expansión del proyecto
class CurseForgeAPI:
    """Maneja las peticiones a la API de CurseForge para modpacks"""

    BASE_URL = "https://api.curseforge.com/v1"
    MINECRAFT_GAME_ID = 432

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa la API de CurseForge

        Args:
            api_key: API key de CurseForge (opcional - se puede configurar después)
        """
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers["x-api-key"] = api_key

    def set_api_key(self, api_key: str):
        """Establece la API key de CurseForge"""
        self.api_key = api_key
        self.headers["x-api-key"] = api_key

    def is_configured(self) -> bool:
        """Verifica si la API está configurada con una key"""
        return self.api_key is not None and len(self.api_key) > 0

    def search_modpacks(self, query: str, limit: int = 20) -> Optional[List[Dict]]:
        """
        Busca modpacks en CurseForge

        Args:
            query: Texto de búsqueda
            limit: Número máximo de resultados

        Returns:
            Lista de modpacks encontrados
        """
        if not self.is_configured():
            print("Error: CurseForge API key no configurada")
            return None

        try:
            url = f"{self.BASE_URL}/mods/search"
            params = {
                "gameId": self.MINECRAFT_GAME_ID,
                "classId": 4471,  # Modpack class ID
                "searchFilter": query,
                "pageSize": limit
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return data.get("data", [])

        except Exception as e:
            print(f"Error al buscar modpacks en CurseForge: {e}")
            return None

    def get_modpack_info(self, modpack_id: int) -> Optional[Dict]:
        """
        Obtiene información de un modpack

        Args:
            modpack_id: ID del modpack

        Returns:
            Información del modpack
        """
        if not self.is_configured():
            return None

        try:
            url = f"{self.BASE_URL}/mods/{modpack_id}"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            return data.get("data")

        except Exception as e:
            print(f"Error al obtener información del modpack: {e}")
            return None

    def get_modpack_files(self, modpack_id: int) -> Optional[List[Dict]]:
        """
        Obtiene los archivos/versiones de un modpack

        Args:
            modpack_id: ID del modpack

        Returns:
            Lista de archivos disponibles
        """
        if not self.is_configured():
            return None

        try:
            url = f"{self.BASE_URL}/mods/{modpack_id}/files"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            return data.get("data", [])

        except Exception as e:
            print(f"Error al obtener archivos del modpack: {e}")
            return None

    def download_modpack_file(self, modpack_id: int, file_id: int, dest_folder: str) -> Optional[str]:
        """
        Descarga un archivo de modpack

        Args:
            modpack_id: ID del modpack
            file_id: ID del archivo
            dest_folder: Carpeta destino

        Returns:
            Ruta al archivo descargado
        """
        if not self.is_configured():
            return None

        try:
            # Obtener información del archivo
            url = f"{self.BASE_URL}/mods/{modpack_id}/files/{file_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            file_data = response.json().get("data")

            if not file_data:
                return None

            download_url = file_data.get("downloadUrl")
            filename = file_data.get("fileName")

            if not download_url or not filename:
                return None

            # Descargar archivo
            dest_path = os.path.join(dest_folder, filename)
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return dest_path

        except Exception as e:
            print(f"Error al descargar archivo: {e}")
            return None

    def get_mod_file_info(self, mod_id: int, file_id: int) -> Optional[Dict]:
        """
        Obtiene información de un archivo específico de un mod

        Args:
            mod_id: ID del mod
            file_id: ID del archivo

        Returns:
            Información del archivo
        """
        if not self.is_configured():
            return None

        try:
            url = f"{self.BASE_URL}/mods/{mod_id}/files/{file_id}"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            return data.get("data")

        except Exception as e:
            print(f"Error al obtener información del archivo: {e}")
            return None


# Clase auxiliar para gestionar configuración de API keys
class APIConfig:
    """Gestiona la configuración de API keys"""

    def __init__(self):
        self.config_dir = Path.home() / ".pycraft"
        self.config_file = self.config_dir / "api_config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def save_curseforge_key(self, api_key: str):
        """Guarda la API key de CurseForge"""
        try:
            config = self.load_config()
            config["curseforge_api_key"] = api_key

            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

            return True
        except Exception as e:
            print(f"Error al guardar API key: {e}")
            return False

    def get_curseforge_key(self) -> Optional[str]:
        """Obtiene la API key de CurseForge guardada"""
        try:
            config = self.load_config()
            return config.get("curseforge_api_key")
        except:
            return None

    def load_config(self) -> Dict:
        """Carga la configuración"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def clear_config(self):
        """Limpia la configuración"""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            return True
        except Exception as e:
            print(f"Error al limpiar configuración: {e}")
            return False
