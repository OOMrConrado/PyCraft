import subprocess
import os
import platform
import requests
import zipfile
import shutil
from typing import Optional, Tuple, Callable
from pathlib import Path


class JavaManager:
    """Manages Java detection, download, and installation"""

    # Adoptium API URLs
    ADOPTIUM_API_BASE = "https://api.adoptium.net/v3"

    # Java versions required by Minecraft
    JAVA_REQUIREMENTS = {
        # Minecraft < 1.17 requires Java 8 or higher
        # Minecraft 1.17 - 1.17.1 requires Java 16
        # Minecraft >= 1.18 requires Java 17
        "1.18": 17,
        "1.19": 17,
        "1.20": 17,
        "1.21": 21,
    }

    def __init__(self):
        self.system = platform.system()
        self.machine = platform.machine()
        self.java_installs_dir = Path.home() / ".pycraft" / "java"
        self.java_installs_dir.mkdir(parents=True, exist_ok=True)

    def detect_java_version(self) -> Optional[Tuple[str, int]]:
        """
        Detects if Java is installed and its version

        Returns:
            Tuple of (full version, major version) or None if not installed
        """
        try:
            # Run java -version
            # Configure flags for Windows
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=creation_flags
            )

            # Output is in stderr
            output = result.stderr

            # Parse version (example: "17.0.9" or "1.8.0_392")
            for line in output.split('\n'):
                if 'version' in line.lower():
                    # Extract version between quotes
                    import re
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        version_str = match.group(1)

                        # Parse major version
                        if version_str.startswith("1."):
                            # Java 8 and earlier (1.8.0_xxx)
                            major_version = int(version_str.split('.')[1])
                        else:
                            # Java 9+ (17.0.9, 21.0.1, etc)
                            major_version = int(version_str.split('.')[0])

                        return (version_str, major_version)

            return None

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return None

    def get_required_java_version(self, minecraft_version: str) -> int:
        """
        Gets the required Java version for a Minecraft version

        Args:
            minecraft_version: Minecraft version (e.g., "1.20.1")

        Returns:
            Required Java major version
        """
        # Get base version (1.20, 1.19, etc)
        try:
            parts = minecraft_version.split('.')
            base_version = f"{parts[0]}.{parts[1]}"

            # Search in dictionary
            if base_version in self.JAVA_REQUIREMENTS:
                return self.JAVA_REQUIREMENTS[base_version]

            # If >= 1.18, use Java 17
            if float(base_version) >= 1.18:
                return 17

            # If >= 1.17, use Java 16
            if float(base_version) >= 1.17:
                return 16

            # Older versions use Java 8
            return 8

        except Exception:
            # Default to Java 17 (modern standard version)
            return 17

    def is_java_compatible(self, minecraft_version: str) -> bool:
        """
        Checks if the installed Java version is compatible with Minecraft

        Args:
            minecraft_version: Minecraft version

        Returns:
            True if compatible, False otherwise
        """
        java_info = self.detect_java_version()
        if not java_info:
            return False

        _, installed_major = java_info
        required_major = self.get_required_java_version(minecraft_version)

        # Installed Java must be >= required version
        return installed_major >= required_major

    def _download_with_retry(
        self,
        url: str,
        dest_path: Path,
        log_callback: Optional[Callable[[str], None]] = None,
        max_retries: int = 3,
        timeout: int = 60
    ) -> bool:
        """
        Downloads a file with automatic retries

        Args:
            url: URL of the file to download
            dest_path: Path where to save the file
            log_callback: Function to report progress
            max_retries: Maximum number of retries
            timeout: Timeout in seconds per attempt

        Returns:
            True if download was successful, False otherwise
        """
        import time

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    if log_callback:
                        log_callback(f"\n⚠ Reintentando descarga (intento {attempt + 1}/{max_retries})...\n")
                    time.sleep(2)  # Wait before retrying

                # Make request with timeout
                response = requests.get(url, stream=True, timeout=timeout)
                response.raise_for_status()

                # Get total size
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                last_reported_progress = -1

                if log_callback and total_size > 0:
                    log_callback(f"Descargando archivo ({total_size // (1024*1024)} MB)...\n")

                # Download in chunks
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Report progress
                            if log_callback and total_size > 0:
                                progress = int((downloaded / total_size) * 100)
                                if progress % 10 == 0 and progress != last_reported_progress:
                                    log_callback(f"  Progreso: {progress}%\n")
                                    last_reported_progress = progress

                # Validate complete download
                if total_size > 0:
                    actual_size = dest_path.stat().st_size
                    if actual_size < total_size * 0.95:  # Allow 5% margin
                        if log_callback:
                            log_callback(f"⚠ Descarga incompleta: {actual_size}/{total_size} bytes\n")
                        continue  # Retry

                if log_callback:
                    log_callback("✓ Descarga completada\n")

                return True

            except requests.Timeout:
                if log_callback:
                    log_callback(f"\n⏱️ Timeout en la descarga (intento {attempt + 1}/{max_retries})\n")
                    log_callback("  Esto puede deberse a una conexión lenta. El archivo puede ser grande (>50MB).\n")
                if attempt < max_retries - 1:
                    continue
                else:
                    if log_callback:
                        log_callback("✗ Se agotaron los reintentos por timeout\n")
                    return False

            except requests.RequestException as e:
                if log_callback:
                    log_callback(f"\n✗ Error de red: {str(e)}\n")
                    log_callback(f"  Código de estado HTTP: {getattr(e.response, 'status_code', 'N/A')}\n")
                if attempt < max_retries - 1:
                    continue
                else:
                    if log_callback:
                        log_callback("✗ Se agotaron los reintentos\n")
                    return False

            except IOError as e:
                if log_callback:
                    log_callback(f"\n✗ Error escribiendo archivo: {str(e)}\n")
                    log_callback(f"  Verifica que tienes espacio en disco y permisos de escritura.\n")
                return False

            except Exception as e:
                if log_callback:
                    log_callback(f"\n✗ Error inesperado: {str(e)}\n")
                    log_callback(f"  Tipo: {type(e).__name__}\n")
                return False

        return False

    def download_java(
        self,
        java_version: int,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """
        Downloads and installs Java from Adoptium

        Args:
            java_version: Java major version (8, 17, 21, etc)
            log_callback: Function to report progress

        Returns:
            Path to the installed Java directory, or None if failed
        """
        try:
            if log_callback:
                log_callback(f"Descargando Java {java_version} desde Adoptium...\n")

            # Determine OS and architecture for Adoptium API
            os_type = self._get_adoptium_os()
            arch_type = self._get_adoptium_arch()

            if not os_type or not arch_type:
                if log_callback:
                    log_callback("Error: Sistema operativo o arquitectura no soportados\n")
                return None

            # Build API URL
            api_url = (
                f"{self.ADOPTIUM_API_BASE}/binary/latest/{java_version}/ga/"
                f"{os_type}/{arch_type}/jre/hotspot/normal/eclipse"
            )

            if log_callback:
                log_callback(f"Obteniendo Java para {os_type} {arch_type}...\n")

            # Save file
            file_extension = ".zip" if self.system == "Windows" else ".tar.gz"
            download_path = self.java_installs_dir / f"java-{java_version}{file_extension}"

            # Download with automatic retries (longer timeout for large file)
            if not self._download_with_retry(api_url, download_path, log_callback, max_retries=3, timeout=300):
                if log_callback:
                    log_callback("\n✗ No se pudo completar la descarga de Java\n")
                    log_callback("Verifica tu conexión a internet e intenta de nuevo.\n")
                return None

            if log_callback:
                log_callback("\nExtrayendo archivos...\n")
                log_callback(f"Archivo descargado: {download_path}\n")
                log_callback(f"Tamaño: {download_path.stat().st_size // (1024*1024)} MB\n")

            # Extract file
            extract_dir = self.java_installs_dir / f"java-{java_version}"

            try:
                if self.system == "Windows":
                    with zipfile.ZipFile(download_path, 'r') as zip_ref:
                        if log_callback:
                            log_callback(f"Extrayendo {len(zip_ref.namelist())} archivos...\n")
                        zip_ref.extractall(extract_dir)
                else:
                    import tarfile
                    with tarfile.open(download_path, 'r:gz') as tar_ref:
                        tar_ref.extractall(extract_dir)

                if log_callback:
                    log_callback("✓ Extracción completada\n")
            except zipfile.BadZipFile as e:
                if log_callback:
                    log_callback(f"✗ Error: Archivo ZIP corrupto\n")
                    log_callback(f"  Detalles: {str(e)}\n")
                return None
            except Exception as e:
                if log_callback:
                    log_callback(f"✗ Error durante la extracción: {str(e)}\n")
                    log_callback(f"  Tipo: {type(e).__name__}\n")
                return None

            # Clean up downloaded file
            download_path.unlink()

            # Find the bin/java directory
            if log_callback:
                log_callback("Buscando ejecutable de Java...\n")

            java_bin_path = self._find_java_executable(extract_dir)

            if java_bin_path:
                if log_callback:
                    log_callback(f"✓ Java {java_version} instalado correctamente\n")
                    log_callback(f"  Directorio: {extract_dir}\n")
                    log_callback(f"  Ejecutable: {java_bin_path}\n")
                return str(extract_dir)
            else:
                if log_callback:
                    log_callback("✗ Error: No se encontró el ejecutable de Java después de la extracción\n")
                    log_callback(f"  Contenido del directorio:\n")
                    try:
                        for item in extract_dir.rglob("*"):
                            if item.is_dir():
                                log_callback(f"    DIR: {item.relative_to(extract_dir)}\n")
                    except:
                        pass
                return None

        except PermissionError as e:
            if log_callback:
                log_callback(f"\n✗ Error de permisos: No se puede crear la carpeta de Java.\n")
                log_callback(f"Detalles: {str(e)}\n")
            return None
        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error inesperado al descargar Java: {str(e)}\n")
                log_callback("Tipo de error: " + type(e).__name__ + "\n")
            return None

    def _get_adoptium_os(self) -> Optional[str]:
        """Gets the OS identifier for Adoptium API"""
        system_map = {
            "Windows": "windows",
            "Linux": "linux",
            "Darwin": "mac"
        }
        return system_map.get(self.system)

    def _get_adoptium_arch(self) -> Optional[str]:
        """Gets the architecture identifier for Adoptium API"""
        arch_map = {
            "AMD64": "x64",
            "x86_64": "x64",
            "aarch64": "aarch64",
            "arm64": "aarch64",
        }
        return arch_map.get(self.machine)

    def _find_java_executable(self, base_dir: Path) -> Optional[Path]:
        """Finds the Java executable in the extracted directory"""
        # Search in subdirectories
        for root, dirs, files in os.walk(base_dir):
            if "bin" in dirs:
                bin_dir = Path(root) / "bin"
                java_exe = bin_dir / ("java.exe" if self.system == "Windows" else "java")
                if java_exe.exists():
                    # Verify the executable works
                    try:
                        creation_flags = 0
                        if os.name == 'nt':
                            creation_flags = subprocess.CREATE_NO_WINDOW

                        result = subprocess.run(
                            [str(java_exe), "-version"],
                            capture_output=True,
                            timeout=5,
                            creationflags=creation_flags
                        )
                        # If it runs without error, return it
                        if result.returncode == 0 or result.stderr:
                            return java_exe
                    except:
                        # If verification fails, keep searching
                        continue
        return None

    def get_java_executable(self, minecraft_version: str) -> Optional[str]:
        """
        Gets the path to the Java executable, installing it if necessary

        Args:
            minecraft_version: Minecraft version

        Returns:
            Path to the Java executable, or None if failed
        """
        # First try to use system Java
        if self.is_java_compatible(minecraft_version):
            return "java"  # Use Java from PATH

        # If no compatible Java, download it
        required_version = self.get_required_java_version(minecraft_version)

        # Check if we already downloaded it before
        install_dir = self.java_installs_dir / f"java-{required_version}"
        if install_dir.exists():
            java_exe = self._find_java_executable(install_dir)
            if java_exe:
                return str(java_exe)

        # Download Java
        install_path = self.download_java(required_version)
        if install_path:
            java_exe = self._find_java_executable(Path(install_path))
            if java_exe:
                return str(java_exe)

        return None

    def ensure_java_installed(
        self,
        minecraft_version: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """
        Ensures that Java is installed and compatible

        Args:
            minecraft_version: Minecraft version
            log_callback: Function to report progress

        Returns:
            Path to Java executable or "java" if using system Java
        """
        try:
            if log_callback:
                log_callback("\n=== Verificando Java ===\n")

            # Detect installed Java
            java_info = self.detect_java_version()
            required_version = self.get_required_java_version(minecraft_version)

            if java_info:
                version_str, major_version = java_info
                if log_callback:
                    log_callback(f"Java detectado: {version_str} (Java {major_version})\n")

                if major_version >= required_version:
                    if log_callback:
                        log_callback(f"✓ Java {major_version} es compatible con Minecraft {minecraft_version}\n")
                    return "java"
                else:
                    if log_callback:
                        log_callback(f"⚠ Java {major_version} no es suficiente. Se requiere Java {required_version}+\n")
            else:
                if log_callback:
                    log_callback("⚠ Java no está instalado en el sistema\n")

            # Check if we already have Java downloaded
            install_dir = self.java_installs_dir / f"java-{required_version}"
            if log_callback:
                log_callback(f"Buscando Java en: {install_dir}\n")

            if install_dir.exists():
                java_exe = self._find_java_executable(install_dir)
                if java_exe:
                    if log_callback:
                        log_callback(f"✓ Usando Java {required_version} descargado previamente\n")
                        log_callback(f"  Ruta: {java_exe}\n")
                    return str(java_exe)
                else:
                    if log_callback:
                        log_callback(f"⚠ Directorio Java existe pero ejecutable no encontrado\n")
                        log_callback(f"  Eliminando directorio corrupto...\n")
                    # Remove corrupted directory
                    import shutil
                    try:
                        shutil.rmtree(install_dir)
                    except:
                        pass

            # Download Java automatically
            if log_callback:
                log_callback(f"\nDescargando Java {required_version} automáticamente...\n")
                log_callback("Esto puede tomar varios minutos dependiendo de tu conexión.\n")
                log_callback(f"Directorio de instalación: {self.java_installs_dir}\n")

            install_path = self.download_java(required_version, log_callback)

            if install_path:
                java_exe = self._find_java_executable(Path(install_path))
                if java_exe:
                    if log_callback:
                        log_callback(f"\n✓ Java {required_version} instalado correctamente\n")
                    return str(java_exe)

            if log_callback:
                log_callback("\n✗ No se pudo instalar Java automáticamente\n")
                log_callback(f"Por favor, instala Java {required_version} manualmente desde:\n")
                log_callback("  https://adoptium.net/temurin/releases/\n")

            return None

        except Exception as e:
            if log_callback:
                log_callback(f"\nError al gestionar Java: {str(e)}\n")
            return None
