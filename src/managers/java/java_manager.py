import subprocess
import os
import platform
import requests
import zipfile
import shutil
from typing import Optional, Tuple, Callable, List
from pathlib import Path

# Windows-specific imports for PATH management
if platform.system() == "Windows":
    try:
        import winreg
        WINREG_AVAILABLE = True
    except ImportError:
        WINREG_AVAILABLE = False
else:
    WINREG_AVAILABLE = False


class JavaManager:
    """Manages Java detection, download, and installation"""

    # Adoptium API URLs
    ADOPTIUM_API_BASE = "https://api.adoptium.net/v3"

    # Java versions required by Minecraft
    # Format: "base_version": (min_version, max_version or None for no limit)
    # Note: Forge for MC < 1.17 is NOT compatible with Java 17+ due to module system changes
    JAVA_REQUIREMENTS = {
        # Minecraft < 1.17 requires Java 8-16 (Forge breaks with Java 17+)
        "1.7": (8, 16),
        "1.8": (8, 16),
        "1.9": (8, 16),
        "1.10": (8, 16),
        "1.11": (8, 16),
        "1.12": (8, 16),
        "1.13": (8, 16),
        "1.14": (8, 16),
        "1.15": (8, 16),
        "1.16": (8, 16),
        # Minecraft 1.17 requires Java 16+
        "1.17": (16, None),
        # Minecraft >= 1.18 requires Java 17+
        "1.18": (17, None),
        "1.19": (17, None),
        "1.20": (17, None),
        # Minecraft >= 1.21 requires Java 21+
        "1.21": (21, None),
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
            # Refresh environment variables from registry to detect newly installed Java
            # This is needed because os.environ doesn't auto-update when system vars change
            if self.system == "Windows" and WINREG_AVAILABLE:
                self._refresh_process_environment()

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
        Gets the minimum required Java version for a Minecraft version

        Args:
            minecraft_version: Minecraft version (e.g., "1.20.1")

        Returns:
            Required Java major version (minimum)
        """
        min_ver, _ = self.get_java_version_range(minecraft_version)
        return min_ver

    def get_java_version_range(self, minecraft_version: str) -> tuple:
        """
        Gets the required Java version range for a Minecraft version

        Args:
            minecraft_version: Minecraft version (e.g., "1.20.1")

        Returns:
            Tuple of (min_version, max_version) where max_version can be None for no limit
        """
        # Get base version (1.20, 1.19, etc)
        try:
            parts = minecraft_version.split('.')
            base_version = f"{parts[0]}.{parts[1]}"

            # Search in dictionary
            if base_version in self.JAVA_REQUIREMENTS:
                return self.JAVA_REQUIREMENTS[base_version]

            # If >= 1.21, use Java 21+
            if float(base_version) >= 1.21:
                return (21, None)

            # If >= 1.18, use Java 17+
            if float(base_version) >= 1.18:
                return (17, None)

            # If >= 1.17, use Java 16+
            if float(base_version) >= 1.17:
                return (16, None)

            # Older versions use Java 8-16 (Forge compatibility)
            return (8, 16)

        except Exception:
            # Default to Java 17+ (modern standard version)
            return (17, None)

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
        min_version, max_version = self.get_java_version_range(minecraft_version)

        # Check minimum version
        if installed_major < min_version:
            return False

        # Check maximum version (for old MC versions that don't work with new Java)
        if max_version is not None and installed_major > max_version:
            return False

        return True

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
                    log_callback(f"Downloading file ({total_size // (1024*1024)} MB)...\n")

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
                log_callback(f"Downloading Java {java_version} desde Adoptium...\n")

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
                    log_callback("\n✗ Could not complete Java download\n")
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
                    log_callback(f"✓ Java {java_version} descargado correctamente\n")
                    log_callback(f"  Directorio: {extract_dir}\n")
                    log_callback(f"  Ejecutable: {java_bin_path}\n")

                # Add Java to PATH automatically
                if log_callback:
                    log_callback("\nConfigurando PATH del sistema...\n")

                java_bin_dir = java_bin_path.parent
                if self.add_java_to_path(java_bin_dir, log_callback):
                    if log_callback:
                        log_callback("✓ Java configurado en el PATH del sistema\n")
                        log_callback("  Ahora puedes usar 'java' desde cualquier terminal\n")
                    return str(extract_dir)
                else:
                    # PATH configuration failed - clean up downloaded files
                    if log_callback:
                        log_callback("\n🗑️ Limpiando archivos descargados...\n")
                    try:
                        shutil.rmtree(extract_dir)
                        if log_callback:
                            log_callback("✓ Archivos eliminados\n")
                    except Exception as e:
                        if log_callback:
                            log_callback(f"⚠ No se pudieron eliminar los archivos: {e}\n")
                    return None
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
                min_version, max_version = self.get_java_version_range(minecraft_version)

                if log_callback:
                    log_callback(f"Java detected: {version_str} (Java {major_version})\n")

                # Check if compatible
                if self.is_java_compatible(minecraft_version):
                    if log_callback:
                        log_callback(f"✓ Java {major_version} is compatible with Minecraft {minecraft_version}\n")
                    return "java"
                elif major_version < min_version:
                    if log_callback:
                        log_callback(f"⚠ Java {major_version} is too old. Requires Java {min_version}+\n")
                elif max_version is not None and major_version > max_version:
                    if log_callback:
                        log_callback(f"⚠ Java {major_version} is too new for Minecraft {minecraft_version}\n")
                        log_callback(f"  Forge/modded servers for MC < 1.17 require Java 8-{max_version}\n")
                        log_callback(f"  Java 17+ breaks due to module system changes\n")
            else:
                if log_callback:
                    log_callback("⚠ Java is not installed on the system\n")

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
                log_callback(f"\nDownloading Java {required_version} automatically...\n")
                log_callback("Esto puede tomar varios minutos dependiendo de tu conexión.\n")
                log_callback(f"Directorio de instalación: {self.java_installs_dir}\n")

            install_path = self.download_java(required_version, log_callback)

            if install_path:
                java_exe = self._find_java_executable(Path(install_path))
                if java_exe:
                    if log_callback:
                        log_callback(f"\n✓ Java {required_version} installed successfully\n")
                    return str(java_exe)

            if log_callback:
                log_callback("\n✗ Could not install Java automatically\n")
                log_callback(f"Por favor, instala Java {required_version} manualmente desde:\n")
                log_callback("  https://adoptium.net/temurin/releases/\n")

            return None

        except Exception as e:
            if log_callback:
                log_callback(f"\nError managing Java: {str(e)}\n")
            return None

    # ==================== PATH MANAGEMENT ====================

    def _refresh_process_environment(self, log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Refreshes the current process's environment variables by reading from the Windows Registry.
        This allows the process to detect newly installed Java without restarting.

        Args:
            log_callback: Optional logging callback

        Returns:
            True if environment was refreshed successfully
        """
        if not WINREG_AVAILABLE or self.system != "Windows":
            return False

        try:
            # Read SYSTEM PATH
            system_path = self._get_path_from_registry(use_system=True) or ""

            # Read USER PATH
            user_path = self._get_path_from_registry(use_system=False) or ""

            # Combine paths (system + user, as Windows does)
            combined_path = system_path
            if user_path:
                if combined_path and not combined_path.endswith(';'):
                    combined_path += ';'
                combined_path += user_path

            # Update process PATH
            if combined_path:
                os.environ['PATH'] = combined_path

            # Read and update JAVA_HOME from SYSTEM
            try:
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                    0,
                    winreg.KEY_READ
                ) as key:
                    java_home, _ = winreg.QueryValueEx(key, "JAVA_HOME")
                    if java_home:
                        os.environ['JAVA_HOME'] = java_home
            except (FileNotFoundError, PermissionError):
                # Try USER JAVA_HOME
                try:
                    with winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Environment",
                        0,
                        winreg.KEY_READ
                    ) as key:
                        java_home, _ = winreg.QueryValueEx(key, "JAVA_HOME")
                        if java_home:
                            os.environ['JAVA_HOME'] = java_home
                except (FileNotFoundError, PermissionError):
                    pass

            if log_callback:
                log_callback("✓ Variables de entorno del proceso actualizadas\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"⚠ No se pudieron refrescar las variables: {str(e)}\n")
            return False

    def _get_path_from_registry(self, use_system: bool = False) -> Optional[str]:
        """
        Gets the current PATH from Windows Registry

        Args:
            use_system: If True, reads from SYSTEM variables, else from USER

        Returns:
            Current PATH string or None if failed
        """
        if not WINREG_AVAILABLE or self.system != "Windows":
            return None

        try:
            if use_system:
                # System variables (requires admin)
                key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
                root_key = winreg.HKEY_LOCAL_MACHINE
            else:
                # User variables
                key_path = r"Environment"
                root_key = winreg.HKEY_CURRENT_USER

            with winreg.OpenKey(root_key, key_path, 0, winreg.KEY_READ) as key:
                path_value, _ = winreg.QueryValueEx(key, "Path")
                return path_value
        except FileNotFoundError:
            # Path doesn't exist yet
            return ""
        except PermissionError:
            # No admin rights for system variables
            return None
        except Exception as e:
            print(f"Error reading PATH from registry: {e}")
            return None

    def _get_user_path_from_registry(self) -> Optional[str]:
        """
        Gets the current User PATH from Windows Registry (backward compatibility)

        Returns:
            Current PATH string or None if failed
        """
        return self._get_path_from_registry(use_system=False)

    def _set_path_to_registry(self, new_path: str, use_system: bool = False) -> bool:
        """
        Sets the PATH in Windows Registry

        Args:
            new_path: New PATH string
            use_system: If True, sets SYSTEM variables (requires admin), else USER

        Returns:
            True if successful
        """
        if not WINREG_AVAILABLE or self.system != "Windows":
            return False

        try:
            if use_system:
                # System variables (requires admin)
                key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
                root_key = winreg.HKEY_LOCAL_MACHINE
            else:
                # User variables
                key_path = r"Environment"
                root_key = winreg.HKEY_CURRENT_USER

            with winreg.OpenKey(root_key, key_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)

            # Broadcast WM_SETTINGCHANGE to notify applications
            import ctypes
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            result = ctypes.c_long()
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                "Environment",
                SMTO_ABORTIFHUNG,
                5000,
                ctypes.byref(result)
            )

            return True
        except PermissionError:
            # No admin rights for system variables
            return False
        except Exception as e:
            print(f"Error writing PATH to registry: {e}")
            return False

    def _set_user_path_to_registry(self, new_path: str) -> bool:
        """
        Sets the User PATH in Windows Registry (backward compatibility)

        Args:
            new_path: New PATH string

        Returns:
            True if successful
        """
        return self._set_path_to_registry(new_path, use_system=False)

    def _set_java_home(self, java_home_path: str, use_system: bool = False) -> bool:
        """
        Sets the JAVA_HOME environment variable in Windows Registry

        Args:
            java_home_path: Path to Java installation root (not bin/)
            use_system: If True, sets SYSTEM variable (requires admin), else USER

        Returns:
            True if successful
        """
        if not WINREG_AVAILABLE or self.system != "Windows":
            return False

        try:
            if use_system:
                # System variables (requires admin)
                key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
                root_key = winreg.HKEY_LOCAL_MACHINE
            else:
                # User variables
                key_path = r"Environment"
                root_key = winreg.HKEY_CURRENT_USER

            with winreg.OpenKey(root_key, key_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "JAVA_HOME", 0, winreg.REG_EXPAND_SZ, java_home_path)

            # Broadcast WM_SETTINGCHANGE to notify applications
            import ctypes
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            result = ctypes.c_long()
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                "Environment",
                SMTO_ABORTIFHUNG,
                5000,
                ctypes.byref(result)
            )

            return True
        except PermissionError:
            # No admin rights for system variables
            return False
        except Exception as e:
            print(f"Error setting JAVA_HOME: {e}")
            return False

    def _remove_java_home(self, use_system: bool = False) -> bool:
        """
        Removes the JAVA_HOME environment variable from Windows Registry

        Args:
            use_system: If True, removes from SYSTEM variables (requires admin), else USER

        Returns:
            True if successful
        """
        if not WINREG_AVAILABLE or self.system != "Windows":
            return False

        try:
            if use_system:
                # System variables (requires admin)
                key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
                root_key = winreg.HKEY_LOCAL_MACHINE
            else:
                # User variables
                key_path = r"Environment"
                root_key = winreg.HKEY_CURRENT_USER

            with winreg.OpenKey(root_key, key_path, 0, winreg.KEY_WRITE) as key:
                try:
                    winreg.DeleteValue(key, "JAVA_HOME")
                except FileNotFoundError:
                    # JAVA_HOME doesn't exist, that's fine
                    pass

            # Broadcast WM_SETTINGCHANGE to notify applications
            import ctypes
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            result = ctypes.c_long()
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                "Environment",
                SMTO_ABORTIFHUNG,
                5000,
                ctypes.byref(result)
            )

            return True
        except PermissionError:
            # No admin rights for system variables
            return False
        except Exception as e:
            print(f"Error removing JAVA_HOME: {e}")
            return False

    def add_java_to_path(
        self,
        java_bin_path: Path,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Adds Java bin directory to PATH and sets JAVA_HOME
        Tries SYSTEM variables first (requires admin), falls back to USER variables

        Args:
            java_bin_path: Path to the Java bin directory (containing java.exe)
            log_callback: Function to report progress

        Returns:
            True if at least USER configuration succeeded
        """
        if not WINREG_AVAILABLE or self.system != "Windows":
            if log_callback:
                log_callback("⚠ PATH management is only supported on Windows\n")
            return False

        try:
            java_bin_str = str(java_bin_path.absolute())
            java_home_str = str(java_bin_path.parent.absolute())  # Parent of bin/ is JAVA_HOME

            # Track what was configured
            path_configured_as = None
            java_home_configured_as = None

            if log_callback:
                log_callback("\n┌─ Configurando Java en el sistema ─┐\n")
                log_callback("│                                    │\n")

            # ===== STRATEGY 1: Try SYSTEM variables first (requires admin) =====
            if log_callback:
                log_callback("│ → Intentando configurar variables  │\n")
                log_callback("│   de SISTEMA (nivel global)...     │\n")
                log_callback("│                                    │\n")

            system_success = self._configure_java_environment(
                java_bin_str,
                java_home_str,
                use_system=True,
                log_callback=None  # Don't show errors yet
            )

            if system_success:
                if log_callback:
                    log_callback("│ ✓ Variables de SISTEMA configuradas│\n")
            else:
                # SYSTEM failed (no admin), try UAC elevation
                if log_callback:
                    log_callback("│ ⚠ Sin permisos de administrador    │\n")
                    log_callback("│ → Solicitando elevación UAC...     │\n")

                # Try to get admin rights via UAC popup
                elevation_success = self._configure_java_with_elevation(
                    java_bin_str,
                    java_home_str,
                    log_callback=log_callback
                )

                if not elevation_success:
                    # UAC was cancelled or failed - cannot continue
                    if log_callback:
                        log_callback("└────────────────────────────────────┘\n")
                        log_callback("\n⚠ Permisos de administrador requeridos\n")
                        log_callback("✗ Instalación cancelada\n")
                        log_callback("\nDebes aceptar los permisos de administrador\n")
                        log_callback("de Windows para instalar Java.\n\n")
                        log_callback("Intenta de nuevo y acepta la ventana\n")
                        log_callback("de permisos cuando aparezca.\n")
                    return False

            # ===== SUCCESS =====
            if log_callback:
                log_callback("│                                    │\n")
                log_callback("└────────────────────────────────────┘\n")
                log_callback("\n✅ Java configurado correctamente\n")
                log_callback(f"   • Ubicación: {java_bin_str}\n")
                log_callback(f"   • JAVA_HOME: {java_home_str}\n\n")
                log_callback("   Java está disponible para todas las aplicaciones.\n")

            # Refresh current process environment so Java is detected immediately
            self._refresh_process_environment(log_callback)

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error inesperado: {str(e)}\n")
            return False

    def _configure_java_environment(
        self,
        java_bin_path: str,
        java_home_path: str,
        use_system: bool,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Internal helper to configure both PATH and JAVA_HOME

        Args:
            java_bin_path: Path to Java bin directory
            java_home_path: Path to Java home directory
            use_system: Whether to use SYSTEM or USER variables
            log_callback: Optional logging callback

        Returns:
            True if both PATH and JAVA_HOME were configured successfully
        """
        try:
            # Get current PATH
            current_path = self._get_path_from_registry(use_system)
            if current_path is None:
                return False

            # Check if already in PATH
            path_entries = [p.strip() for p in current_path.split(';') if p.strip()]

            # Check if Java is already in PATH (case-insensitive)
            java_already_in_path = False
            for entry in path_entries:
                if entry.lower() == java_bin_path.lower():
                    java_already_in_path = True
                    break

            # Add to PATH if not already there
            if not java_already_in_path:
                if current_path and not current_path.endswith(';'):
                    new_path = current_path + ';' + java_bin_path
                else:
                    new_path = current_path + java_bin_path

                # Set new PATH
                if not self._set_path_to_registry(new_path, use_system):
                    return False

            # Set JAVA_HOME
            if not self._set_java_home(java_home_path, use_system):
                return False

            return True

        except Exception:
            return False

    def _configure_java_with_elevation(
        self,
        java_bin_path: str,
        java_home_path: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Attempts to configure Java PATH and JAVA_HOME using UAC elevation.
        This will trigger the Windows UAC prompt asking for administrator permissions.

        Uses ShellExecuteW with 'runas' verb which is the most reliable way
        to trigger UAC elevation on Windows.

        Args:
            java_bin_path: Path to Java bin directory
            java_home_path: Path to Java home directory
            log_callback: Optional logging callback

        Returns:
            True if configuration succeeded with elevation
        """
        if self.system != "Windows":
            return False

        try:
            import tempfile
            import ctypes
            import time

            if log_callback:
                log_callback("│                                    │\n")
                log_callback("│ ⚡ Se abrirá ventana de permisos   │\n")
                log_callback("│    Acepta para configurar Java     │\n")
                log_callback("│                                    │\n")

            # Create a batch script that uses setx /M (requires admin)
            # setx /M is the standard Windows way to set system environment variables
            batch_script = f'''@echo off
setlocal EnableDelayedExpansion

REM Set JAVA_HOME system variable
setx /M JAVA_HOME "{java_home_path}"
if errorlevel 1 (
    exit /b 1
)

REM Get current system PATH and add Java bin if not present
for /f "tokens=2*" %%a in ('reg query "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v Path 2^>nul') do set "CURRENT_PATH=%%b"

echo !CURRENT_PATH! | findstr /I /C:"{java_bin_path}" >nul
if errorlevel 1 (
    setx /M PATH "!CURRENT_PATH!;{java_bin_path}"
    if errorlevel 1 (
        exit /b 1
    )
)

exit /b 0
'''
            # Write batch script to temp file
            script_path = Path(tempfile.gettempdir()) / "pycraft_java_config.bat"
            script_path.write_text(batch_script, encoding='utf-8')

            try:
                # Use ShellExecuteW with 'runas' verb to trigger UAC
                # This is the most reliable way to get UAC prompt on Windows
                SEE_MASK_NOCLOSEPROCESS = 0x00000040
                SW_SHOWNORMAL = 1

                class SHELLEXECUTEINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", ctypes.c_ulong),
                        ("fMask", ctypes.c_ulong),
                        ("hwnd", ctypes.c_void_p),
                        ("lpVerb", ctypes.c_wchar_p),
                        ("lpFile", ctypes.c_wchar_p),
                        ("lpParameters", ctypes.c_wchar_p),
                        ("lpDirectory", ctypes.c_wchar_p),
                        ("nShow", ctypes.c_int),
                        ("hInstApp", ctypes.c_void_p),
                        ("lpIDList", ctypes.c_void_p),
                        ("lpClass", ctypes.c_wchar_p),
                        ("hkeyClass", ctypes.c_void_p),
                        ("dwHotKey", ctypes.c_ulong),
                        ("hIcon", ctypes.c_void_p),
                        ("hProcess", ctypes.c_void_p),
                    ]

                sei = SHELLEXECUTEINFO()
                sei.cbSize = ctypes.sizeof(sei)
                sei.fMask = SEE_MASK_NOCLOSEPROCESS
                sei.hwnd = None
                sei.lpVerb = "runas"  # This triggers UAC
                sei.lpFile = "cmd.exe"
                sei.lpParameters = f'/c "{script_path}"'
                sei.lpDirectory = None
                sei.nShow = SW_SHOWNORMAL
                sei.hInstApp = None
                sei.hProcess = None

                # Execute with elevation
                shell32 = ctypes.windll.shell32
                if not shell32.ShellExecuteExW(ctypes.byref(sei)):
                    error_code = ctypes.GetLastError()
                    if error_code == 1223:  # ERROR_CANCELLED - User cancelled UAC
                        if log_callback:
                            log_callback("│ ⚠ Usuario canceló permisos        │\n")
                        return False
                    else:
                        if log_callback:
                            log_callback(f"│ ✗ Error ShellExecute: {error_code}       │\n")
                        return False

                # Wait for the process to complete
                if sei.hProcess:
                    kernel32 = ctypes.windll.kernel32
                    kernel32.WaitForSingleObject(sei.hProcess, 30000)  # Wait up to 30 seconds

                    # Get exit code
                    exit_code = ctypes.c_ulong()
                    kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(exit_code))
                    kernel32.CloseHandle(sei.hProcess)

                    if exit_code.value != 0:
                        if log_callback:
                            log_callback("│ ✗ Error en script de config       │\n")
                        return False

                # Give Windows a moment to update the registry
                time.sleep(1)

                # Broadcast WM_SETTINGCHANGE to notify applications
                HWND_BROADCAST = 0xFFFF
                WM_SETTINGCHANGE = 0x001A
                SMTO_ABORTIFHUNG = 0x0002
                result = ctypes.c_long()
                ctypes.windll.user32.SendMessageTimeoutW(
                    HWND_BROADCAST,
                    WM_SETTINGCHANGE,
                    0,
                    "Environment",
                    SMTO_ABORTIFHUNG,
                    5000,
                    ctypes.byref(result)
                )

                # Verify by checking if Java is now in system PATH
                system_path = self._get_path_from_registry(use_system=True)
                if system_path and java_bin_path.lower() in system_path.lower():
                    if log_callback:
                        log_callback("│ ✓ Variables de SISTEMA configuradas│\n")
                    return True
                else:
                    # Check if JAVA_HOME was set at least
                    try:
                        with winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                            0,
                            winreg.KEY_READ
                        ) as key:
                            java_home, _ = winreg.QueryValueEx(key, "JAVA_HOME")
                            if java_home and java_home_path.lower() in java_home.lower():
                                if log_callback:
                                    log_callback("│ ✓ Variables de SISTEMA configuradas│\n")
                                return True
                    except:
                        pass

                    if log_callback:
                        log_callback("│ ⚠ Could not verify config     │\n")
                    return False

            finally:
                # Clean up temp file
                try:
                    time.sleep(0.5)
                    script_path.unlink()
                except:
                    pass

        except Exception as e:
            if log_callback:
                log_callback(f"│ ✗ Error: {str(e)[:28]}  │\n")
            return False

    def _remove_java_with_elevation(
        self,
        java_bin_path: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Removes Java PATH and JAVA_HOME from SYSTEM variables using UAC elevation.
        This will trigger the Windows UAC prompt asking for administrator permissions.

        Args:
            java_bin_path: Specific path to remove, or None to remove all PyCraft Java paths
            log_callback: Optional logging callback

        Returns:
            True if removal succeeded with elevation
        """
        if self.system != "Windows":
            return False

        try:
            import tempfile
            import ctypes
            import time

            if log_callback:
                log_callback("│                                     │\n")
                log_callback("│ ⚡ Se abrirá ventana de permisos    │\n")
                log_callback("│    Acepta para eliminar config      │\n")
                log_callback("│                                     │\n")

            # Determine what path pattern to remove
            pycraft_java_base = str((Path.home() / ".pycraft" / "java").absolute())
            path_to_remove = java_bin_path if java_bin_path else pycraft_java_base

            # Create a batch script that removes Java from PATH and JAVA_HOME
            batch_script = f'''@echo off
setlocal EnableDelayedExpansion

REM Remove JAVA_HOME system variable
reg delete "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v JAVA_HOME /f 2>nul

REM Get current system PATH
for /f "tokens=2*" %%a in ('reg query "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v Path 2^>nul') do set "CURRENT_PATH=%%b"

REM Remove PyCraft Java paths from PATH
set "NEW_PATH="
set "REMOVED=0"
for %%p in ("!CURRENT_PATH:;=" "!") do (
    set "ENTRY=%%~p"
    echo !ENTRY! | findstr /I /C:"{path_to_remove.replace(chr(92), chr(92)+chr(92))}" >nul
    if errorlevel 1 (
        if defined NEW_PATH (
            set "NEW_PATH=!NEW_PATH!;!ENTRY!"
        ) else (
            set "NEW_PATH=!ENTRY!"
        )
    ) else (
        set "REMOVED=1"
    )
)

REM Update PATH if we removed something
if "!REMOVED!"=="1" (
    reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v Path /t REG_EXPAND_SZ /d "!NEW_PATH!" /f
)

exit /b 0
'''
            # Write batch script to temp file
            script_path = Path(tempfile.gettempdir()) / "pycraft_java_remove.bat"
            script_path.write_text(batch_script, encoding='utf-8')

            try:
                # Use ShellExecuteW with 'runas' verb to trigger UAC
                SEE_MASK_NOCLOSEPROCESS = 0x00000040
                SW_SHOWNORMAL = 1

                class SHELLEXECUTEINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", ctypes.c_ulong),
                        ("fMask", ctypes.c_ulong),
                        ("hwnd", ctypes.c_void_p),
                        ("lpVerb", ctypes.c_wchar_p),
                        ("lpFile", ctypes.c_wchar_p),
                        ("lpParameters", ctypes.c_wchar_p),
                        ("lpDirectory", ctypes.c_wchar_p),
                        ("nShow", ctypes.c_int),
                        ("hInstApp", ctypes.c_void_p),
                        ("lpIDList", ctypes.c_void_p),
                        ("lpClass", ctypes.c_wchar_p),
                        ("hkeyClass", ctypes.c_void_p),
                        ("dwHotKey", ctypes.c_ulong),
                        ("hIcon", ctypes.c_void_p),
                        ("hProcess", ctypes.c_void_p),
                    ]

                sei = SHELLEXECUTEINFO()
                sei.cbSize = ctypes.sizeof(sei)
                sei.fMask = SEE_MASK_NOCLOSEPROCESS
                sei.hwnd = None
                sei.lpVerb = "runas"  # This triggers UAC
                sei.lpFile = "cmd.exe"
                sei.lpParameters = f'/c "{script_path}"'
                sei.lpDirectory = None
                sei.nShow = SW_SHOWNORMAL
                sei.hInstApp = None
                sei.hProcess = None

                # Execute with elevation
                shell32 = ctypes.windll.shell32
                if not shell32.ShellExecuteExW(ctypes.byref(sei)):
                    error_code = ctypes.GetLastError()
                    if error_code == 1223:  # ERROR_CANCELLED - User cancelled UAC
                        if log_callback:
                            log_callback("│ ⚠ Usuario canceló permisos         │\n")
                        return False
                    else:
                        if log_callback:
                            log_callback(f"│ ✗ Error ShellExecute: {error_code}        │\n")
                        return False

                # Wait for the process to complete
                if sei.hProcess:
                    kernel32 = ctypes.windll.kernel32
                    kernel32.WaitForSingleObject(sei.hProcess, 30000)
                    kernel32.CloseHandle(sei.hProcess)

                # Give Windows a moment to update the registry
                time.sleep(1)

                # Broadcast WM_SETTINGCHANGE to notify applications
                HWND_BROADCAST = 0xFFFF
                WM_SETTINGCHANGE = 0x001A
                SMTO_ABORTIFHUNG = 0x0002
                result = ctypes.c_long()
                ctypes.windll.user32.SendMessageTimeoutW(
                    HWND_BROADCAST,
                    WM_SETTINGCHANGE,
                    0,
                    "Environment",
                    SMTO_ABORTIFHUNG,
                    5000,
                    ctypes.byref(result)
                )

                # Verify JAVA_HOME was removed
                try:
                    with winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                        0,
                        winreg.KEY_READ
                    ) as key:
                        winreg.QueryValueEx(key, "JAVA_HOME")
                        # If we get here, JAVA_HOME still exists
                        if log_callback:
                            log_callback("│ ⚠ JAVA_HOME aún existe             │\n")
                except FileNotFoundError:
                    # JAVA_HOME was removed successfully
                    if log_callback:
                        log_callback("│ ✓ Variables de SISTEMA eliminadas  │\n")
                    return True

                return True

            finally:
                # Clean up temp file
                try:
                    time.sleep(0.5)
                    script_path.unlink()
                except:
                    pass

        except Exception as e:
            if log_callback:
                log_callback(f"│ ✗ Error: {str(e)[:28]}   │\n")
            return False

    def remove_java_from_path(
        self,
        java_bin_path: Optional[Path] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Removes Java bin directory from PATH and JAVA_HOME from both SYSTEM and USER variables

        Args:
            java_bin_path: Specific path to remove, or None to remove all PyCraft Java paths
            log_callback: Function to report progress

        Returns:
            True if at least one removal succeeded
        """
        if not WINREG_AVAILABLE or self.system != "Windows":
            if log_callback:
                log_callback("⚠ PATH management is only supported on Windows\n")
            return False

        try:
            pycraft_java_base = str((Path.home() / ".pycraft" / "java").absolute())
            overall_success = False

            if log_callback:
                log_callback("\n┌─ Eliminando configuración de Java ─┐\n")
                log_callback("│                                     │\n")

            # ===== TRY SYSTEM VARIABLES FIRST =====
            # Check if Java is in system PATH first
            system_path = self._get_path_from_registry(use_system=True)
            java_in_system = False
            if system_path:
                check_path = str(java_bin_path.absolute()).lower() if java_bin_path else pycraft_java_base.lower()
                java_in_system = check_path in system_path.lower()

            if java_in_system:
                if log_callback:
                    log_callback("│ → Eliminando de variables SISTEMA...│\n")

                system_path_removed = self._remove_from_path_registry(
                    java_bin_path, pycraft_java_base, use_system=True
                )

                if system_path_removed:
                    if log_callback:
                        log_callback("│   ✓ PATH de SISTEMA limpiado       │\n")
                    overall_success = True

                    # Remove JAVA_HOME from system
                    if self._remove_java_home(use_system=True):
                        if log_callback:
                            log_callback("│   ✓ JAVA_HOME de SISTEMA eliminado │\n")
                else:
                    # Direct removal failed (no admin), try UAC elevation
                    if log_callback:
                        log_callback("│   ⚠ Sin permisos de administrador  │\n")
                        log_callback("│   → Solicitando elevación UAC...   │\n")

                    java_bin_str = str(java_bin_path.absolute()) if java_bin_path else None
                    if self._remove_java_with_elevation(java_bin_str, log_callback):
                        overall_success = True
                    else:
                        # SYSTEM removal failed - cannot continue
                        if log_callback:
                            log_callback("│                                     │\n")
                            log_callback("│ ✗ ELIMINACIÓN CANCELADA             │\n")
                            log_callback("│                                     │\n")
                            log_callback("└─────────────────────────────────────┘\n")
                            log_callback("\n⚠ Permisos de administrador requeridos\n")
                            log_callback("✗ No se puede eliminar Java\n")
                            log_callback("\nDebes aceptar los permisos de administrador\n")
                            log_callback("de Windows para eliminar Java del sistema.\n")
                        return False

            # ===== CLEAN USER VARIABLES (only if system succeeded or wasn't in system) =====
            if log_callback:
                log_callback("│                                     │\n")
                log_callback("│ → Limpiando variables de USUARIO... │\n")

            user_path_removed = self._remove_from_path_registry(
                java_bin_path, pycraft_java_base, use_system=False
            )

            if user_path_removed:
                if log_callback:
                    log_callback("│   ✓ PATH de USUARIO limpiado       │\n")
                overall_success = True

            # Remove JAVA_HOME from user
            if self._remove_java_home(use_system=False):
                if log_callback:
                    log_callback("│   ✓ JAVA_HOME de USUARIO eliminado │\n")
                overall_success = True

            if log_callback:
                log_callback("│                                     │\n")
                log_callback("└─────────────────────────────────────┘\n")
                log_callback("\n✅ Configuración de Java eliminada\n")

            # Refresh current process environment
            self._refresh_process_environment(log_callback)

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error eliminando configuración: {str(e)}\n")
            return False

    def _remove_from_path_registry(
        self,
        java_bin_path: Optional[Path],
        pycraft_java_base: str,
        use_system: bool
    ) -> bool:
        """
        Internal helper to remove Java from PATH in registry

        Args:
            java_bin_path: Specific path to remove, or None for all PyCraft paths
            pycraft_java_base: Base path for PyCraft Java installations
            use_system: Whether to use SYSTEM or USER variables

        Returns:
            True if something was removed
        """
        try:
            # Get current PATH
            current_path = self._get_path_from_registry(use_system)
            if current_path is None:
                return False

            path_entries = [p.strip() for p in current_path.split(';') if p.strip()]
            removed_count = 0
            new_entries = []

            for entry in path_entries:
                should_remove = False

                if java_bin_path:
                    # Remove specific path
                    if entry.lower() == str(java_bin_path.absolute()).lower():
                        should_remove = True
                else:
                    # Remove all PyCraft Java paths
                    if pycraft_java_base.lower() in entry.lower():
                        should_remove = True

                if should_remove:
                    removed_count += 1
                else:
                    new_entries.append(entry)

            if removed_count == 0:
                return False

            # Set new PATH
            new_path = ';'.join(new_entries)
            return self._set_path_to_registry(new_path, use_system)

        except Exception:
            return False

    def get_java_installations(self) -> List[Tuple[int, Path, bool]]:
        """
        Lists all Java installations managed by PyCraft

        Returns:
            List of tuples: (version, path, is_in_path)
        """
        installations = []

        if not self.java_installs_dir.exists():
            return installations

        try:
            # Get current PATH for checking
            current_path = ""
            if WINREG_AVAILABLE and self.system == "Windows":
                current_path = self._get_user_path_from_registry() or ""
                current_path = current_path.lower()

            for item in self.java_installs_dir.iterdir():
                if item.is_dir() and item.name.startswith("java-"):
                    try:
                        # Extract version from folder name (e.g., "java-21" -> 21)
                        version_str = item.name.split('-')[1]
                        version = int(version_str)

                        # Find Java executable
                        java_exe = self._find_java_executable(item)

                        if java_exe:
                            # Check if in PATH
                            java_bin_dir = java_exe.parent
                            is_in_path = str(java_bin_dir.absolute()).lower() in current_path

                            installations.append((version, item, is_in_path))
                    except (ValueError, IndexError):
                        # Skip folders that don't match expected format
                        continue

            # Sort by version
            installations.sort(key=lambda x: x[0], reverse=True)
            return installations

        except Exception as e:
            print(f"Error listing Java installations: {e}")
            return installations

    def delete_java_installation(
        self,
        java_version: int,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Deletes a Java installation managed by PyCraft

        Args:
            java_version: Java major version to delete
            log_callback: Function to report progress

        Returns:
            True if successful
        """
        try:
            install_dir = self.java_installs_dir / f"java-{java_version}"

            if not install_dir.exists():
                if log_callback:
                    log_callback(f"✗ Java {java_version} installation not found\n")
                return False

            # Check if Java is in SYSTEM PATH (requires admin to remove)
            java_exe = self._find_java_executable(install_dir)
            if java_exe:
                java_bin_dir = java_exe.parent
                java_bin_str = str(java_bin_dir.absolute()).lower()

                # Check if in SYSTEM variables
                system_path = self._get_path_from_registry(use_system=True) or ""
                is_in_system = java_bin_str in system_path.lower()

                if is_in_system:
                    # Must remove from system first - requires admin
                    path_removed = self.remove_java_from_path(java_bin_dir, log_callback)

                    if not path_removed:
                        # User cancelled UAC - don't delete files
                        if log_callback:
                            log_callback("\n⚠ No se puede eliminar Java\n")
                            log_callback("Debes aceptar los permisos de administrador.\n")
                        return False
                else:
                    # Not in system, just try to clean up user variables
                    self.remove_java_from_path(java_bin_dir, log_callback)

            # Delete the directory
            if log_callback:
                log_callback(f"\n🗑️ Eliminando archivos de Java {java_version}...\n")

            shutil.rmtree(install_dir)

            if log_callback:
                log_callback(f"✓ Java {java_version} eliminado correctamente\n")

            return True

        except PermissionError as e:
            if log_callback:
                log_callback(f"✗ Permission error: {str(e)}\n")
                log_callback("  Make sure no Java processes are running\n")
            return False
        except Exception as e:
            if log_callback:
                log_callback(f"✗ Error deleting Java: {str(e)}\n")
            return False
