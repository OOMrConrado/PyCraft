import subprocess
import os
import platform
import requests
import zipfile
import shutil
from typing import Optional, Tuple, Callable
from pathlib import Path


class JavaManager:
    """Gestiona la detección, descarga e instalación de Java"""

    # URLs de Adoptium API
    ADOPTIUM_API_BASE = "https://api.adoptium.net/v3"

    # Versiones de Java requeridas por Minecraft
    JAVA_REQUIREMENTS = {
        # Minecraft < 1.17 requiere Java 8 o superior
        # Minecraft 1.17 - 1.17.1 requiere Java 16
        # Minecraft >= 1.18 requiere Java 17
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
        Detecta si Java está instalado y su versión

        Returns:
            Tupla de (versión completa, versión mayor) o None si no está instalado
        """
        try:
            # Ejecutar java -version
            # Configurar flags para Windows
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

            # La salida está en stderr
            output = result.stderr

            # Parsear la versión (ejemplo: "17.0.9" o "1.8.0_392")
            for line in output.split('\n'):
                if 'version' in line.lower():
                    # Extraer versión entre comillas
                    import re
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        version_str = match.group(1)

                        # Parsear versión mayor
                        if version_str.startswith("1."):
                            # Java 8 y anteriores (1.8.0_xxx)
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
        Obtiene la versión de Java requerida para una versión de Minecraft

        Args:
            minecraft_version: Versión de Minecraft (ej: "1.20.1")

        Returns:
            Versión mayor de Java requerida
        """
        # Obtener la versión base (1.20, 1.19, etc)
        try:
            parts = minecraft_version.split('.')
            base_version = f"{parts[0]}.{parts[1]}"

            # Buscar en el diccionario
            if base_version in self.JAVA_REQUIREMENTS:
                return self.JAVA_REQUIREMENTS[base_version]

            # Si es >= 1.18, usar Java 17
            if float(base_version) >= 1.18:
                return 17

            # Si es >= 1.17, usar Java 16
            if float(base_version) >= 1.17:
                return 16

            # Versiones más antiguas usan Java 8
            return 8

        except Exception:
            # Por defecto, Java 17 (versión moderna estándar)
            return 17

    def is_java_compatible(self, minecraft_version: str) -> bool:
        """
        Verifica si la versión de Java instalada es compatible con Minecraft

        Args:
            minecraft_version: Versión de Minecraft

        Returns:
            True si es compatible, False si no
        """
        java_info = self.detect_java_version()
        if not java_info:
            return False

        _, installed_major = java_info
        required_major = self.get_required_java_version(minecraft_version)

        # Java instalado debe ser >= a la requerida
        return installed_major >= required_major

    def download_java(
        self,
        java_version: int,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """
        Descarga e instala Java desde Adoptium

        Args:
            java_version: Versión mayor de Java (8, 17, 21, etc)
            log_callback: Función para reportar progreso

        Returns:
            Ruta al directorio de Java instalado, o None si falló
        """
        try:
            if log_callback:
                log_callback(f"Descargando Java {java_version} desde Adoptium...\n")

            # Determinar OS y arquitectura para Adoptium API
            os_type = self._get_adoptium_os()
            arch_type = self._get_adoptium_arch()

            if not os_type or not arch_type:
                if log_callback:
                    log_callback("Error: Sistema operativo o arquitectura no soportados\n")
                return None

            # Construir URL de la API
            api_url = (
                f"{self.ADOPTIUM_API_BASE}/binary/latest/{java_version}/ga/"
                f"{os_type}/{arch_type}/jre/hotspot/normal/eclipse"
            )

            if log_callback:
                log_callback(f"Obteniendo Java para {os_type} {arch_type}...\n")

            # Descargar Java
            response = requests.get(api_url, stream=True, timeout=30)
            response.raise_for_status()

            # Guardar archivo
            file_extension = ".zip" if self.system == "Windows" else ".tar.gz"
            download_path = self.java_installs_dir / f"java-{java_version}{file_extension}"

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            if log_callback:
                log_callback(f"Descargando archivo ({total_size // (1024*1024)} MB)...\n")

            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if log_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if int(progress) % 10 == 0:  # Reportar cada 10%
                                log_callback(f"  Progreso: {int(progress)}%\n")

            if log_callback:
                log_callback("Descarga completada. Extrayendo archivos...\n")

            # Extraer archivo
            extract_dir = self.java_installs_dir / f"java-{java_version}"

            if self.system == "Windows":
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:
                import tarfile
                with tarfile.open(download_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)

            # Limpiar archivo descargado
            download_path.unlink()

            # Encontrar el directorio bin/java
            java_bin_path = self._find_java_executable(extract_dir)

            if java_bin_path:
                if log_callback:
                    log_callback(f"Java {java_version} instalado correctamente en:\n")
                    log_callback(f"  {extract_dir}\n")
                return str(extract_dir)
            else:
                if log_callback:
                    log_callback("Error: No se encontró el ejecutable de Java después de la extracción\n")
                return None

        except Exception as e:
            if log_callback:
                log_callback(f"Error al descargar Java: {str(e)}\n")
            return None

    def _get_adoptium_os(self) -> Optional[str]:
        """Obtiene el identificador de OS para Adoptium API"""
        system_map = {
            "Windows": "windows",
            "Linux": "linux",
            "Darwin": "mac"
        }
        return system_map.get(self.system)

    def _get_adoptium_arch(self) -> Optional[str]:
        """Obtiene el identificador de arquitectura para Adoptium API"""
        arch_map = {
            "AMD64": "x64",
            "x86_64": "x64",
            "aarch64": "aarch64",
            "arm64": "aarch64",
        }
        return arch_map.get(self.machine)

    def _find_java_executable(self, base_dir: Path) -> Optional[Path]:
        """Encuentra el ejecutable de Java en el directorio extraído"""
        # Buscar en subdirectorios
        for root, dirs, files in os.walk(base_dir):
            if "bin" in dirs:
                bin_dir = Path(root) / "bin"
                java_exe = bin_dir / ("java.exe" if self.system == "Windows" else "java")
                if java_exe.exists():
                    return java_exe
        return None

    def get_java_executable(self, minecraft_version: str) -> Optional[str]:
        """
        Obtiene la ruta al ejecutable de Java, instalándolo si es necesario

        Args:
            minecraft_version: Versión de Minecraft

        Returns:
            Ruta al ejecutable de Java, o None si falló
        """
        # Primero intentar usar Java del sistema
        if self.is_java_compatible(minecraft_version):
            return "java"  # Usar el Java del PATH

        # Si no hay Java compatible, descargar
        required_version = self.get_required_java_version(minecraft_version)

        # Ver si ya lo descargamos antes
        install_dir = self.java_installs_dir / f"java-{required_version}"
        if install_dir.exists():
            java_exe = self._find_java_executable(install_dir)
            if java_exe:
                return str(java_exe)

        # Descargar Java
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
        Asegura que Java esté instalado y sea compatible

        Args:
            minecraft_version: Versión de Minecraft
            log_callback: Función para reportar progreso

        Returns:
            Ruta al ejecutable de Java o "java" si usar el del sistema
        """
        try:
            if log_callback:
                log_callback("\n=== Verificando Java ===\n")

            # Detectar Java instalado
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

            # Verificar si ya tenemos Java descargado
            install_dir = self.java_installs_dir / f"java-{required_version}"
            if install_dir.exists():
                java_exe = self._find_java_executable(install_dir)
                if java_exe:
                    if log_callback:
                        log_callback(f"✓ Usando Java {required_version} descargado previamente\n")
                    return str(java_exe)

            # Descargar Java automáticamente
            if log_callback:
                log_callback(f"\nDescargando Java {required_version} automáticamente...\n")
                log_callback("Esto puede tomar varios minutos dependiendo de tu conexión.\n")

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
