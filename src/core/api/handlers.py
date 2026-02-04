import requests
from typing import List, Dict, Optional, Tuple
import json
import os
from pathlib import Path
from urllib.parse import quote


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

    def search_modpacks(self, query: str, limit: int = 10, offset: int = 0, side_filter: str = None) -> Tuple[Optional[List[Dict]], int]:
        """
        Busca modpacks en Modrinth

        Args:
            query: Texto de búsqueda
            limit: Número máximo de resultados por página
            offset: Número de resultados a saltar (para paginación)
            side_filter: Filtro de lado - "server" para mostrar solo modpacks con server pack,
                        "client" para mostrar solo modpacks con soporte cliente,
                        None para no filtrar

        Returns:
            Tuple de (lista de modpacks, total de resultados)
        """
        try:
            url = f"{self.BASE_URL}/search"

            if side_filter:
                # When filtering, we need to request from the beginning and paginate after filtering
                # Request enough results to cover the requested page after filtering
                # Estimate ~70% pass rate, so request ~1.5x more than needed
                request_limit = min((offset + limit) * 2, 100)  # Cap at 100 to avoid huge requests
                request_offset = 0
            else:
                request_limit = limit
                request_offset = offset

            params = {
                "query": query,
                "limit": request_limit,
                "offset": request_offset,
                "facets": '[["project_type:modpack"]]'
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            hits = data.get("hits", [])
            total = data.get("total_hits", 0)

            # Filter by side if specified
            # Modrinth returns server_side and client_side fields with values:
            # "required", "optional", "unsupported", "unknown"
            if side_filter and hits:
                filtered_hits = []
                for hit in hits:
                    if side_filter == "server":
                        # For server: only show modpacks where server_side is NOT "unsupported"
                        server_side = hit.get("server_side", "unknown")
                        if server_side in ("required", "optional"):
                            filtered_hits.append(hit)
                    elif side_filter == "client":
                        # For client: only show modpacks where client_side is NOT "unsupported"
                        client_side = hit.get("client_side", "unknown")
                        if client_side in ("required", "optional"):
                            filtered_hits.append(hit)

                # Apply pagination AFTER filtering
                hits = filtered_hits[offset:offset + limit]

                # Estimate total filtered results based on ratio
                if request_limit > 0:
                    filter_ratio = len(filtered_hits) / request_limit
                    total = max(int(total * filter_ratio), len(filtered_hits))

            # Normalize Modrinth results to consistent format
            normalized = self._normalize_modrinth_modpacks(hits)
            return normalized, total

        except Exception as e:
            print(f"Error al buscar modpacks en Modrinth: {e}")
            return None, 0

    def _normalize_modrinth_modpacks(self, modpacks: list) -> List[Dict]:
        """Normalize Modrinth modpacks to consistent format"""
        normalized = []
        for mp in modpacks:
            normalized.append({
                "project_id": mp.get("project_id", mp.get("slug", "")),
                "title": mp.get("title", "Unknown"),
                "description": mp.get("description", ""),
                "icon_url": mp.get("icon_url", ""),
                "downloads": mp.get("downloads", 0),
                "categories": mp.get("categories", []),
                "versions": mp.get("versions", []),
                "slug": mp.get("slug", ""),
                "author": mp.get("author", "Unknown"),
                "source": "modrinth",
                "server_side": mp.get("server_side", "unknown"),
                "client_side": mp.get("client_side", "unknown"),
            })
        return normalized

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

    def get_projects_info(self, project_ids: List[str]) -> Optional[List[Dict]]:
        """
        Obtiene información de múltiples proyectos en una sola llamada (batch)

        Args:
            project_ids: Lista de IDs de proyectos

        Returns:
            Lista de información de proyectos
        """
        if not project_ids:
            return []

        try:
            url = f"{self.BASE_URL}/projects"
            # Modrinth expects the ids as a JSON array string
            params = {
                "ids": json.dumps(project_ids)
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Error al obtener información de proyectos: {e}")
            return None

    def extract_project_id_from_url(self, url: str) -> Optional[str]:
        """
        Extrae el project_id de una URL de descarga de Modrinth

        URLs de Modrinth tienen el formato:
        https://cdn.modrinth.com/data/{project_id}/versions/{version_id}/filename.jar

        Args:
            url: URL de descarga

        Returns:
            Project ID o None si no es una URL de Modrinth
        """
        try:
            if 'cdn.modrinth.com/data/' in url:
                # Extract project_id from URL
                parts = url.split('cdn.modrinth.com/data/')[1].split('/')
                if len(parts) >= 1:
                    return parts[0]
        except Exception:
            pass
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

            # Descargar archivo (sanitize filename to prevent path traversal)
            safe_filename = os.path.basename(filename)
            dest_path = os.path.join(dest_folder, safe_filename)
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

class CurseForgeAPI:
    """Handles requests to the CurseForge API for modpacks via proxy"""

    # Use proxy URL to keep API key secure
    PROXY_URL = "https://pycraft-curseforge-proxy.conradogomez556.workers.dev"
    MINECRAFT_GAME_ID = 432
    MODPACK_CLASS_ID = 4471

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize CurseForge API

        Args:
            api_key: Not used anymore - proxy handles the API key
        """
        # API key is no longer needed - proxy handles it
        self.headers = {
            "Accept": "application/json"
        }

    def set_api_key(self, api_key: str):
        """Legacy method - API key is handled by proxy now"""
        pass

    def is_configured(self) -> bool:
        """Always returns True since proxy handles the API key"""
        return True

    def search_modpacks(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        server_pack_filter: bool = False
    ) -> Tuple[Optional[List[Dict]], int]:
        """
        Search modpacks on CurseForge

        Args:
            query: Search text
            limit: Maximum number of results per page
            offset: Number of results to skip (for pagination)
            server_pack_filter: If True, only return modpacks that have server packs

        Returns:
            Tuple of (list of modpacks in normalized format, total results count)
        """
        try:
            url = f"{self.PROXY_URL}/v1/mods/search"

            if server_pack_filter:
                # When filtering, we need to accumulate enough filtered results
                # Fetch multiple pages if needed to get offset + limit filtered results
                return self._search_modpacks_with_server_filter(url, query, limit, offset)

            # Normal search without filter
            params = {
                "gameId": self.MINECRAFT_GAME_ID,
                "classId": self.MODPACK_CLASS_ID,
                "searchFilter": query,
                "pageSize": min(limit, 50),
                "index": offset,
                "sortField": 2,  # Popularity
                "sortOrder": "desc"
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            modpacks = data.get("data", [])
            pagination = data.get("pagination", {})
            total = pagination.get("totalCount", len(modpacks))

            normalized = self._normalize_curseforge_modpacks(modpacks)
            return normalized, total

        except Exception as e:
            print(f"Error searching modpacks on CurseForge: {e}")
            return None, 0

    def _search_modpacks_with_server_filter(
        self,
        url: str,
        query: str,
        limit: int,
        offset: int
    ) -> Tuple[Optional[List[Dict]], int]:
        """
        Search modpacks with server pack filter.
        Fetches enough results to fill the requested page.
        Returns estimated total based on filter ratio.
        """
        all_filtered = []
        api_offset = 0
        total_api_results = 0
        total_fetched = 0
        max_api_calls = 10

        for _ in range(max_api_calls):
            params = {
                "gameId": self.MINECRAFT_GAME_ID,
                "classId": self.MODPACK_CLASS_ID,
                "searchFilter": query,
                "pageSize": 50,
                "index": api_offset,
                "sortField": 2,
                "sortOrder": "desc"
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            modpacks = data.get("data", [])
            pagination = data.get("pagination", {})
            total_api_results = pagination.get("totalCount", 0)

            if not modpacks:
                break

            total_fetched += len(modpacks)

            # Filter and normalize
            for mp in modpacks:
                latest_files_full = mp.get("latestFiles", [])
                has_server_pack = any(f.get("serverPackFileId") for f in latest_files_full)
                if has_server_pack:
                    all_filtered.extend(self._normalize_curseforge_modpacks([mp]))

            # Stop if we have enough for the requested page
            if len(all_filtered) >= offset + limit:
                break

            api_offset += 50
            if api_offset >= total_api_results:
                break

        # Apply pagination
        result_page = all_filtered[offset:offset + limit]

        # Estimate total filtered results based on observed ratio
        if total_fetched > 0:
            filter_ratio = len(all_filtered) / total_fetched
            estimated_total = int(total_api_results * filter_ratio)
            # At minimum, show what we've actually found
            estimated_total = max(estimated_total, len(all_filtered))
        else:
            estimated_total = 0

        return result_page, estimated_total

    def _normalize_curseforge_modpacks(self, modpacks: list) -> List[Dict]:
        """Normalize CurseForge modpacks to Modrinth-like format"""
        LOADER_MAP = {1: "forge", 4: "fabric", 5: "quilt", 6: "neoforge"}
        normalized = []

        for mp in modpacks:
            categories = []
            for cat in mp.get("categories", []):
                cat_name = cat.get("name", "").lower() if isinstance(cat, dict) else str(cat).lower()
                categories.append(cat_name)

            versions = []
            loaders = set()
            latest_files = mp.get("latestFilesIndexes", [])
            for f in latest_files:
                gv = f.get("gameVersion", "")
                if gv and gv not in versions:
                    versions.append(gv)
                mod_loader = f.get("modLoader")
                if mod_loader and mod_loader in LOADER_MAP:
                    loaders.add(LOADER_MAP[mod_loader])

            categories.extend(list(loaders))

            normalized.append({
                "project_id": str(mp.get("id", "")),
                "title": mp.get("name", "Unknown"),
                "description": mp.get("summary", ""),
                "icon_url": mp.get("logo", {}).get("thumbnailUrl", "") if mp.get("logo") else "",
                "downloads": mp.get("downloadCount", 0),
                "categories": categories,
                "versions": sorted(versions, reverse=True) if versions else [],
                "slug": mp.get("slug", ""),
                "author": mp.get("authors", [{}])[0].get("name", "Unknown") if mp.get("authors") else "Unknown",
                "source": "curseforge",
                "_curseforge_id": mp.get("id"),
                "_curseforge_data": mp
            })

        return normalized

    def _modpack_has_server_pack(self, modpack_id: int) -> bool:
        """
        Check if a modpack has any file with a server pack available

        Args:
            modpack_id: Modpack ID

        Returns:
            True if modpack has at least one file with server pack
        """
        try:
            files = self.get_modpack_files(modpack_id)
            if files:
                for file in files:
                    # serverPackFileId indicates a server pack exists for this file
                    if file.get("serverPackFileId"):
                        return True
            return False
        except Exception:
            return False

    def get_modpack_info(self, modpack_id: int) -> Optional[Dict]:
        """
        Get modpack information

        Args:
            modpack_id: Modpack ID

        Returns:
            Modpack information
        """
        try:
            url = f"{self.PROXY_URL}/v1/mods/{modpack_id}"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            return data.get("data")

        except Exception as e:
            print(f"Error getting modpack info: {e}")
            return None

    def get_modpack_files(self, modpack_id: int) -> Optional[List[Dict]]:
        """
        Get modpack files/versions

        Args:
            modpack_id: Modpack ID

        Returns:
            List of available files
        """
        try:
            url = f"{self.PROXY_URL}/v1/mods/{modpack_id}/files"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            return data.get("data", [])

        except Exception as e:
            print(f"Error getting modpack files: {e}")
            return None

    def get_server_pack_file_id(self, modpack_id: int, file_id: int) -> Optional[int]:
        """
        Get the server pack file ID for a specific modpack file

        Args:
            modpack_id: Modpack ID
            file_id: Client modpack file ID

        Returns:
            Server pack file ID if available, None otherwise
        """
        try:
            url = f"{self.PROXY_URL}/v1/mods/{modpack_id}/files/{file_id}"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            file_data = data.get("data", {})
            return file_data.get("serverPackFileId")

        except Exception as e:
            print(f"Error getting server pack file ID: {e}")
            return None

    def download_modpack_file(self, modpack_id: int, file_id: int, dest_folder: str, log_callback=None) -> Optional[str]:
        """
        Download a modpack file

        Args:
            modpack_id: Modpack ID
            file_id: File ID
            dest_folder: Destination folder
            log_callback: Optional callback for logging progress

        Returns:
            Path to downloaded file
        """
        try:
            # Get file information
            url = f"{self.PROXY_URL}/v1/mods/{modpack_id}/files/{file_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            file_data = response.json().get("data")

            if not file_data:
                if log_callback:
                    log_callback("    Error: No file data returned from API\n")
                return None

            download_url = file_data.get("downloadUrl")
            filename = file_data.get("fileName")

            if not filename:
                if log_callback:
                    log_callback("    Error: No filename in file data\n")
                return None

            # If no direct download URL, try to construct it using CurseForge CDN pattern
            used_fallback = False
            if not download_url:
                if log_callback:
                    log_callback("    Using CDN fallback method...\n")
                used_fallback = True

                # Split file_id for CDN URL pattern
                file_id_str = str(file_id)
                if len(file_id_str) >= 4:
                    # Split as: first 4 digits / remaining digits
                    first_part = file_id_str[:4]
                    second_part = file_id_str[4:]
                    # URL encode the filename to handle special characters (spaces, etc.)
                    encoded_filename = quote(filename)
                    constructed_url = f"https://edge.forgecdn.net/files/{first_part}/{second_part}/{encoded_filename}"
                    download_url = constructed_url
                else:
                    if log_callback:
                        log_callback(f"    Error: File ID {file_id} is too short to construct CDN URL\n")
                    return None

            # Download file
            safe_filename = os.path.basename(filename)
            dest_path = os.path.join(dest_folder, safe_filename)

            if log_callback:
                log_callback(f"    Downloading {safe_filename}...\n")

            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            last_progress = 0

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):  # 64KB chunks for faster downloads
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Report progress every 10%
                        if total_size > 0 and log_callback:
                            progress = int((downloaded / total_size) * 100)
                            if progress >= last_progress + 10:
                                log_callback(f"    Progress: {progress}%\n")
                                last_progress = progress

            if log_callback:
                log_callback(f"    Download complete\n")

            return dest_path

        except Exception as e:
            if log_callback:
                log_callback(f"    Error downloading: {type(e).__name__}: {e}\n")
            return None

    def get_mod_file_info(self, mod_id: int, file_id: int) -> Optional[Dict]:
        """
        Get information about a specific mod file

        Args:
            mod_id: Mod ID
            file_id: File ID

        Returns:
            File information
        """
        try:
            url = f"{self.PROXY_URL}/v1/mods/{mod_id}/files/{file_id}"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            return data.get("data")

        except Exception as e:
            print(f"Error getting file info: {e}")
            return None

    def get_mod_info(self, mod_id: int) -> Optional[Dict]:
        """
        Get information about a mod (name, slug, links, etc.)

        Args:
            mod_id: Mod ID

        Returns:
            Mod information including slug for URL construction
        """
        try:
            url = f"{self.PROXY_URL}/v1/mods/{mod_id}"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            return data.get("data")

        except Exception as e:
            print(f"Error getting mod info: {e}")
            return None

    def get_mods_info_batch(self, mod_ids: List[int]) -> Optional[List[Dict]]:
        """
        Get information about multiple mods in a single request

        Args:
            mod_ids: List of mod IDs

        Returns:
            List of mod information
        """
        try:
            url = f"{self.PROXY_URL}/v1/mods"

            response = requests.post(
                url,
                headers={**self.headers, "Content-Type": "application/json"},
                json={"modIds": mod_ids},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            return data.get("data", [])

        except Exception as e:
            print(f"Error getting mods batch info: {e}")
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
        except Exception:
            return None

    def load_config(self) -> Dict:
        """Carga la configuración"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
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
