import requests
from typing import List, Dict, Optional
import json


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
