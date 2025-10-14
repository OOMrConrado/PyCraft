import requests
import os
from typing import Optional, Callable


class ServerDownloader:
    """Maneja la descarga del server.jar de Minecraft"""

    def __init__(self):
        self.download_progress = 0
        # Crear sesión persistente para mejor rendimiento
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PyCraft/1.0',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })

    def download_server(
        self,
        url: str,
        destination_folder: str,
        version_id: str,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Optional[str]:
        """
        Descarga el server.jar desde la URL proporcionada (optimizado para velocidad)

        Args:
            url: URL del server.jar
            destination_folder: Carpeta donde se guardará el servidor
            version_id: ID de la versión para nombrar el archivo
            progress_callback: Función callback para actualizar el progreso (0-100)

        Returns:
            Ruta completa del archivo descargado o None si hay error
        """
        try:
            # Crear la carpeta si no existe
            os.makedirs(destination_folder, exist_ok=True)

            # Nombre del archivo
            file_name = "server.jar"
            file_path = os.path.join(destination_folder, file_name)

            # Realizar la descarga con sesión persistente
            response = self.session.get(url, stream=True, timeout=60)
            response.raise_for_status()

            # Obtener el tamaño total
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            last_progress = 0

            # Usar chunk size de 1 MB para descarga mucho más rápida
            # En lugar de 8 KB, usar 1048576 bytes (1 MB)
            chunk_size = 1024 * 1024  # 1 MB

            # Escribir el archivo en bloques grandes con buffer optimizado
            with open(file_path, 'wb', buffering=chunk_size * 2) as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)

                        # Actualizar progreso solo cuando cambie (reduce overhead)
                        if total_size > 0 and progress_callback:
                            progress = int((downloaded_size / total_size) * 100)
                            if progress != last_progress:
                                self.download_progress = progress
                                progress_callback(progress)
                                last_progress = progress

            # Asegurar que el progreso llegue a 100%
            if progress_callback:
                progress_callback(100)

            print(f"Descarga completada: {file_path}")
            return file_path

        except Exception as e:
            print(f"Error al descargar el servidor: {e}")
            return None

    def verify_file_exists(self, file_path: str) -> bool:
        """Verifica si el archivo existe"""
        return os.path.exists(file_path) and os.path.isfile(file_path)
