import requests
import subprocess
import os
from typing import Optional, Callable, List, Dict
from pathlib import Path
import json


class LoaderManager:
    """Gestiona la instalación de loaders (Forge/Fabric) para servidores"""

    # URLs de las APIs
    FORGE_MAVEN_URL = "https://maven.minecraftforge.net/net/minecraftforge/forge"
    FORGE_PROMO_URL = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
    FABRIC_META_URL = "https://meta.fabricmc.net/v2"

    def __init__(self):
        pass

    # ==================== FORGE ====================

    def get_forge_versions(self, minecraft_version: str) -> Optional[List[str]]:
        """
        Obtiene las versiones de Forge disponibles para una versión de Minecraft

        Args:
            minecraft_version: Versión de Minecraft (ej: "1.20.1")

        Returns:
            Lista de versiones de Forge disponibles
        """
        try:
            response = requests.get(self.FORGE_PROMO_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Buscar versiones para la versión de Minecraft
            promos = data.get("promos", {})
            versions = []

            # Formato de clave: "1.20.1-recommended", "1.20.1-latest"
            for key, value in promos.items():
                if key.startswith(minecraft_version):
                    versions.append(value)

            return versions if versions else None

        except Exception as e:
            print(f"Error al obtener versiones de Forge: {e}")
            return None

    def get_forge_latest(self, minecraft_version: str) -> Optional[str]:
        """
        Obtiene la última versión de Forge para una versión de Minecraft

        Args:
            minecraft_version: Versión de Minecraft

        Returns:
            Versión de Forge (ej: "47.2.0") o None
        """
        try:
            response = requests.get(self.FORGE_PROMO_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            promos = data.get("promos", {})

            # Intentar obtener la versión recomendada primero
            recommended_key = f"{minecraft_version}-recommended"
            if recommended_key in promos:
                return promos[recommended_key]

            # Si no hay recomendada, usar latest
            latest_key = f"{minecraft_version}-latest"
            if latest_key in promos:
                return promos[latest_key]

            return None

        except Exception as e:
            print(f"Error al obtener última versión de Forge: {e}")
            return None

    def install_forge(
        self,
        minecraft_version: str,
        server_folder: str,
        java_executable: str = "java",
        forge_version: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Instala Forge en el servidor

        Args:
            minecraft_version: Versión de Minecraft
            server_folder: Carpeta del servidor
            java_executable: Ejecutable de Java a usar
            forge_version: Versión específica de Forge (opcional, usa latest si no se especifica)
            log_callback: Función para reportar progreso

        Returns:
            True si la instalación fue exitosa
        """
        try:
            if log_callback:
                log_callback("\n=== Instalando Forge ===\n")

            # Obtener versión de Forge
            if not forge_version:
                forge_version = self.get_forge_latest(minecraft_version)

            if not forge_version:
                if log_callback:
                    log_callback("Error: No se pudo obtener la versión de Forge\n")
                return False

            full_version = f"{minecraft_version}-{forge_version}"

            if log_callback:
                log_callback(f"Versión de Forge: {full_version}\n")
                log_callback("Descargando instalador de Forge...\n")

            # Descargar instalador
            installer_url = f"{self.FORGE_MAVEN_URL}/{full_version}/forge-{full_version}-installer.jar"
            installer_path = os.path.join(server_folder, "forge-installer.jar")

            response = requests.get(installer_url, stream=True, timeout=30)
            response.raise_for_status()

            with open(installer_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            if log_callback:
                log_callback("Descarga completada\n")
                log_callback("\nEjecutando instalador de Forge...\n")
                log_callback("Esto puede tomar varios minutos...\n")

            # Ejecutar instalador
            result = subprocess.run(
                [java_executable, "-jar", "forge-installer.jar", "--installServer"],
                cwd=server_folder,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos timeout
            )

            # Verificar que se instaló correctamente
            # Buscar el archivo run.bat o run.sh
            run_bat = os.path.join(server_folder, "run.bat")
            run_sh = os.path.join(server_folder, "run.sh")

            if os.path.exists(run_bat) or os.path.exists(run_sh):
                if log_callback:
                    log_callback("\n✓ Forge instalado correctamente\n")

                # Limpiar instalador
                try:
                    os.remove(installer_path)
                    installer_log = os.path.join(server_folder, "forge-installer.jar.log")
                    if os.path.exists(installer_log):
                        os.remove(installer_log)
                except:
                    pass

                return True
            else:
                if log_callback:
                    log_callback("\n✗ Error: La instalación de Forge no se completó correctamente\n")
                    if result.stdout:
                        log_callback(f"Salida: {result.stdout}\n")
                    if result.stderr:
                        log_callback(f"Errores: {result.stderr}\n")
                return False

        except Exception as e:
            if log_callback:
                log_callback(f"\nError al instalar Forge: {str(e)}\n")
            return False

    # ==================== FABRIC ====================

    def get_fabric_loader_versions(self) -> Optional[List[str]]:
        """
        Obtiene las versiones disponibles del Fabric Loader

        Returns:
            Lista de versiones del loader
        """
        try:
            url = f"{self.FABRIC_META_URL}/versions/loader"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            return [item["version"] for item in data]

        except Exception as e:
            print(f"Error al obtener versiones de Fabric Loader: {e}")
            return None

    def get_fabric_latest_loader(self) -> Optional[str]:
        """
        Obtiene la última versión estable del Fabric Loader

        Returns:
            Versión del loader
        """
        try:
            url = f"{self.FABRIC_META_URL}/versions/loader"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data and len(data) > 0:
                # La primera es la más reciente
                for item in data:
                    if item.get("stable", False):
                        return item["version"]

                # Si no hay stable, usar la primera
                return data[0]["version"]

            return None

        except Exception as e:
            print(f"Error al obtener última versión de Fabric: {e}")
            return None

    def install_fabric(
        self,
        minecraft_version: str,
        server_folder: str,
        java_executable: str = "java",
        loader_version: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Instala Fabric en el servidor

        Args:
            minecraft_version: Versión de Minecraft
            server_folder: Carpeta del servidor
            java_executable: Ejecutable de Java a usar
            loader_version: Versión específica del loader (opcional)
            log_callback: Función para reportar progreso

        Returns:
            True si la instalación fue exitosa
        """
        try:
            if log_callback:
                log_callback("\n=== Instalando Fabric ===\n")

            # Obtener versión del loader
            if not loader_version:
                loader_version = self.get_fabric_latest_loader()

            if not loader_version:
                if log_callback:
                    log_callback("Error: No se pudo obtener la versión de Fabric Loader\n")
                return False

            if log_callback:
                log_callback(f"Minecraft: {minecraft_version}\n")
                log_callback(f"Fabric Loader: {loader_version}\n")
                log_callback("\nDescargando servidor de Fabric...\n")

            # Descargar Fabric Server Launcher
            launcher_url = (
                f"{self.FABRIC_META_URL}/versions/loader/"
                f"{minecraft_version}/{loader_version}/1.0.0/server/jar"
            )

            launcher_path = os.path.join(server_folder, "fabric-server-launch.jar")

            response = requests.get(launcher_url, stream=True, timeout=30)
            response.raise_for_status()

            with open(launcher_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            if log_callback:
                log_callback("Descarga completada\n")
                log_callback("\n✓ Fabric instalado correctamente\n")
                log_callback("El launcher de Fabric descargará los archivos necesarios al iniciar por primera vez\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"\nError al instalar Fabric: {str(e)}\n")
            return False

    # ==================== UTILIDADES ====================

    def detect_loader_type(self, modpack_manifest: Dict) -> Optional[str]:
        """
        Detecta el tipo de loader requerido desde un manifest de modpack

        Args:
            modpack_manifest: Manifest del modpack (manifest.json o modrinth.index.json)

        Returns:
            "forge", "fabric", o None si no se puede determinar
        """
        try:
            # Para CurseForge (manifest.json)
            if "minecraft" in modpack_manifest:
                mod_loaders = modpack_manifest["minecraft"].get("modLoaders", [])
                if mod_loaders and len(mod_loaders) > 0:
                    loader_id = mod_loaders[0].get("id", "").lower()
                    if "forge" in loader_id:
                        return "forge"
                    elif "fabric" in loader_id:
                        return "fabric"

            # Para Modrinth (modrinth.index.json)
            if "dependencies" in modpack_manifest:
                dependencies = modpack_manifest["dependencies"]
                if "forge" in dependencies:
                    return "forge"
                elif "fabric-loader" in dependencies:
                    return "fabric"

            return None

        except Exception as e:
            print(f"Error al detectar tipo de loader: {e}")
            return None

    def get_loader_version_from_manifest(self, modpack_manifest: Dict) -> Optional[str]:
        """
        Extrae la versión del loader desde el manifest

        Args:
            modpack_manifest: Manifest del modpack

        Returns:
            Versión del loader o None
        """
        try:
            # Para CurseForge
            if "minecraft" in modpack_manifest:
                mod_loaders = modpack_manifest["minecraft"].get("modLoaders", [])
                if mod_loaders and len(mod_loaders) > 0:
                    loader_id = mod_loaders[0].get("id", "")
                    # Formato: "forge-47.2.0" o "fabric-0.15.0"
                    if "-" in loader_id:
                        return loader_id.split("-", 1)[1]

            # Para Modrinth
            if "dependencies" in modpack_manifest:
                dependencies = modpack_manifest["dependencies"]
                if "forge" in dependencies:
                    return dependencies["forge"]
                elif "fabric-loader" in dependencies:
                    return dependencies["fabric-loader"]

            return None

        except Exception as e:
            print(f"Error al obtener versión del loader: {e}")
            return None

    def get_minecraft_version_from_manifest(self, modpack_manifest: Dict) -> Optional[str]:
        """
        Extrae la versión de Minecraft desde el manifest

        Args:
            modpack_manifest: Manifest del modpack

        Returns:
            Versión de Minecraft
        """
        try:
            # Para CurseForge
            if "minecraft" in modpack_manifest:
                return modpack_manifest["minecraft"].get("version")

            # Para Modrinth
            if "dependencies" in modpack_manifest:
                return modpack_manifest["dependencies"].get("minecraft")

            return None

        except Exception as e:
            print(f"Error al obtener versión de Minecraft: {e}")
            return None
