import subprocess
import os
import time
import json
import zipfile
from typing import Optional, Callable, Tuple
import threading

# Import system utilities for validation
from ...utils import system_utils


class ServerManager:
    """Handles Minecraft server execution and configuration"""

    def __init__(self, server_folder: str, java_executable: str = "java"):
        self.server_folder = server_folder
        self.server_jar_path = os.path.join(server_folder, "server.jar")
        self.eula_path = os.path.join(server_folder, "eula.txt")
        self.properties_path = os.path.join(server_folder, "server.properties")
        self.server_process = None
        self.java_executable = java_executable
        self._detected_version = None  # Cache for detected version

    def detect_minecraft_version(self) -> Optional[str]:
        """
        Detects the Minecraft version from various sources.

        Checks multiple locations:
        1. modrinth.index.json (modpack manifest)
        2. Fabric's .fabric directory
        3. server.jar version.json
        4. Server logs

        Returns:
            Minecraft version string (e.g., "1.20.4") or None if not detected
        """
        import re

        # Return cached version if available
        if self._detected_version:
            return self._detected_version

        # Method 1: Check modrinth.index.json (modpack manifest)
        modrinth_manifest = os.path.join(self.server_folder, "modrinth.index.json")
        if os.path.exists(modrinth_manifest):
            try:
                with open(modrinth_manifest, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                    deps = manifest.get("dependencies", {})
                    if "minecraft" in deps:
                        self._detected_version = deps["minecraft"]
                        return self._detected_version
            except:
                pass

        # Method 2: Check Fabric's install directory
        fabric_version_file = os.path.join(self.server_folder, ".fabric", "server", "version.json")
        if os.path.exists(fabric_version_file):
            try:
                with open(fabric_version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "id" in data:
                        self._detected_version = data["id"]
                        return self._detected_version
            except:
                pass

        # Method 3: Check fabric-server-launcher.properties
        fabric_props = os.path.join(self.server_folder, "fabric-server-launcher.properties")
        if os.path.exists(fabric_props):
            try:
                with open(fabric_props, 'r', encoding='utf-8') as f:
                    for line in f:
                        if "serverJar" in line:
                            # Extract version from path like "versions/1.20.1/server-1.20.1.jar"
                            match = re.search(r'(\d+\.\d+(?:\.\d+)?)', line)
                            if match:
                                self._detected_version = match.group(1)
                                return self._detected_version
            except:
                pass

        # Method 4: Check server.jar if it exists
        if os.path.exists(self.server_jar_path):
            try:
                with zipfile.ZipFile(self.server_jar_path, 'r') as jar:
                    if 'version.json' in jar.namelist():
                        with jar.open('version.json') as f:
                            version_data = json.load(f)
                            if 'id' in version_data:
                                self._detected_version = version_data['id']
                                return self._detected_version
                            if 'name' in version_data:
                                self._detected_version = version_data['name']
                                return self._detected_version

                    if 'META-INF/MANIFEST.MF' in jar.namelist():
                        with jar.open('META-INF/MANIFEST.MF') as f:
                            manifest = f.read().decode('utf-8', errors='ignore')
                            for line in manifest.split('\n'):
                                if 'Implementation-Version' in line:
                                    version = line.split(':')[-1].strip()
                                    if version:
                                        self._detected_version = version
                                        return self._detected_version
            except:
                pass

        # Method 5: Check server logs for version info
        logs_path = os.path.join(self.server_folder, "logs", "latest.log")
        if os.path.exists(logs_path):
            try:
                with open(logs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f):
                        if i > 100:
                            break
                        # Fabric: "Loading Minecraft 1.20.1"
                        if 'loading minecraft' in line.lower():
                            match = re.search(r'minecraft\s+(\d+\.\d+(?:\.\d+)?)', line, re.IGNORECASE)
                            if match:
                                self._detected_version = match.group(1)
                                return self._detected_version
                        # Vanilla/Forge: "Starting minecraft server version 1.20.4"
                        if 'minecraft server version' in line.lower():
                            match = re.search(r'version\s+(\d+\.\d+(?:\.\d+)?)', line, re.IGNORECASE)
                            if match:
                                self._detected_version = match.group(1)
                                return self._detected_version
            except:
                pass

        # Method 6: Check versions directory created by Fabric
        versions_dir = os.path.join(self.server_folder, "versions")
        if os.path.exists(versions_dir):
            try:
                for folder in os.listdir(versions_dir):
                    if re.match(r'^\d+\.\d+(?:\.\d+)?$', folder):
                        self._detected_version = folder
                        return self._detected_version
            except:
                pass

        return None

    def get_version_info(self) -> Tuple[Optional[str], str]:
        """
        Gets version information with a human-readable status.

        Returns:
            Tuple of (version_string, status_message)
        """
        version = self.detect_minecraft_version()
        if version:
            return (version, f"Minecraft {version}")
        return (None, "Version unknown")

    def accept_eula(self) -> bool:
        """
        Automatically accepts the EULA by modifying the eula.txt file.
        If the file doesn't exist or is empty, creates it with eula=true.

        Returns:
            True if modified successfully, False otherwise
        """
        try:
            # Wait a moment for file to be fully written
            time.sleep(0.5)

            # If file doesn't exist, create it directly
            if not os.path.exists(self.eula_path):
                with open(self.eula_path, 'w', encoding='utf-8') as file:
                    file.write("#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).\n")
                    file.write("eula=true\n")
                return True

            # Read the file
            with open(self.eula_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # If file is empty or doesn't have eula setting, write it directly
            if not content.strip() or 'eula=' not in content.lower():
                with open(self.eula_path, 'w', encoding='utf-8') as file:
                    file.write("#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).\n")
                    file.write("eula=true\n")
                return True

            # Replace eula=false with eula=true (case insensitive)
            import re
            content = re.sub(r'eula\s*=\s*false', 'eula=true', content, flags=re.IGNORECASE)

            # Write the modified file
            with open(self.eula_path, 'w', encoding='utf-8') as file:
                file.write(content)

            return True

        except Exception as e:
            print(f"Error accepting EULA: {e}")
            return False

    def ensure_server_properties(self, log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Pre-emptively creates server.properties if it doesn't exist.
        This avoids having to run the server just to generate this file.

        Args:
            log_callback: Callback function to report progress

        Returns:
            True if server.properties exists or was created successfully
        """
        try:
            if os.path.exists(self.properties_path):
                return True

            if log_callback:
                log_callback("[INFO] server.properties no encontrado. Creando archivo por defecto...\n")

            # Default server.properties content (Minecraft 1.19.2+ compatible)
            default_properties = """#Minecraft server properties
#Auto-generated by PyCraft
enable-jmx-monitoring=false
rcon.port=25575
level-seed=
gamemode=survival
enable-command-block=false
enable-query=false
generator-settings={}
enforce-secure-profile=false
level-name=world
motd=A Minecraft Server
query.port=25565
pvp=true
generate-structures=true
max-chained-neighbor-updates=1000000
difficulty=normal
network-compression-threshold=256
max-tick-time=60000
require-resource-pack=false
use-native-transport=true
max-players=20
online-mode=false
enable-status=true
allow-flight=false
initial-disabled-packs=
broadcast-rcon-to-ops=true
view-distance=10
server-ip=
resource-pack-prompt=
allow-nether=true
server-port=25565
enable-rcon=false
sync-chunk-writes=true
op-permission-level=4
prevent-proxy-connections=false
hide-online-players=false
resource-pack=
entity-broadcast-range-percentage=100
simulation-distance=10
rcon.password=
player-idle-timeout=0
force-gamemode=false
rate-limit=0
hardcore=false
white-list=false
broadcast-console-to-ops=true
spawn-npcs=true
spawn-animals=true
function-permission-level=2
initial-enabled-packs=vanilla
level-type=minecraft\\:normal
text-filtering-config=
spawn-monsters=true
enforce-whitelist=false
spawn-protection=16
resource-pack-sha1=
max-world-size=29999984
"""
            with open(self.properties_path, 'w', encoding='utf-8') as f:
                f.write(default_properties)

            if log_callback:
                log_callback("[OK] server.properties creado con configuración por defecto\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"[WARN] No se pudo crear server.properties: {e}\n")
            return False

    def ensure_eula_accepted(self, log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Pre-emptively ensures EULA is accepted BEFORE starting the server.
        This creates/modifies eula.txt directly without needing to run the server first.

        This is the correct approach for modded servers that can take a long time to start,
        avoiding the need to start -> wait for eula.txt -> stop -> restart cycle.

        Args:
            log_callback: Callback function to report progress

        Returns:
            True if EULA is accepted and ready, False otherwise
        """
        try:
            if log_callback:
                log_callback("[INFO] Verificando EULA...\n")

            # Case 1: eula.txt doesn't exist - create it directly with eula=true
            if not os.path.exists(self.eula_path):
                if log_callback:
                    log_callback("[INFO] eula.txt no encontrado. Creando y aceptando EULA...\n")

                with open(self.eula_path, 'w', encoding='utf-8') as file:
                    file.write("#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).\n")
                    file.write("#Generated automatically by PyCraft\n")
                    file.write("eula=true\n")

                if log_callback:
                    log_callback("[OK] EULA aceptado automaticamente (archivo creado)\n")
                return True

            # Case 2: eula.txt exists - check if already accepted
            with open(self.eula_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Check if eula=true is already set
            if 'eula=true' in content.lower():
                if log_callback:
                    log_callback("[OK] EULA ya estaba aceptado\n")
                return True

            # Case 3: eula.txt exists but eula=false or missing - update it
            if log_callback:
                log_callback("[INFO] eula.txt encontrado pero no aceptado. Aceptando...\n")

            # If file is empty or doesn't have eula setting, write it fresh
            if not content.strip() or 'eula=' not in content.lower():
                with open(self.eula_path, 'w', encoding='utf-8') as file:
                    file.write("#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).\n")
                    file.write("#Modified automatically by PyCraft\n")
                    file.write("eula=true\n")
            else:
                # Replace eula=false with eula=true
                import re
                content = re.sub(r'eula\s*=\s*false', 'eula=true', content, flags=re.IGNORECASE)
                with open(self.eula_path, 'w', encoding='utf-8') as file:
                    file.write(content)

            if log_callback:
                log_callback("[OK] EULA aceptado automaticamente\n")
            return True

        except PermissionError as e:
            if log_callback:
                log_callback(f"[ERROR] Sin permisos para escribir eula.txt: {e}\n")
            return False
        except Exception as e:
            if log_callback:
                log_callback(f"[ERROR] Error al verificar/aceptar EULA: {e}\n")
            return False

    def configure_server_properties(self, difficulty: str = "normal", log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Modifies server.properties to set online-mode=false and difficulty

        Args:
            difficulty: Server difficulty (peaceful, easy, normal, hard)
            log_callback: Callback function to report errors

        Returns:
            True if modified successfully, False otherwise
        """
        try:
            if not os.path.exists(self.properties_path):
                error_msg = "Archivo server.properties no encontrado. Asegúrate de que el servidor se haya ejecutado al menos una vez."
                print(error_msg)
                if log_callback:
                    log_callback(error_msg + "\n")
                return False

            # Validate difficulty
            valid_difficulties = ['peaceful', 'easy', 'normal', 'hard']
            if difficulty not in valid_difficulties:
                error_msg = f"Dificultad inválida: {difficulty}. Debe ser una de: {', '.join(valid_difficulties)}"
                print(error_msg)
                if log_callback:
                    log_callback(error_msg + "\n")
                return False

            # Read all file lines
            with open(self.properties_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            # Modify necessary properties
            online_mode_modified = False
            difficulty_modified = False
            old_difficulty = None

            for i, line in enumerate(lines):
                # Configure online-mode=false
                if line.strip().startswith('online-mode='):
                    lines[i] = 'online-mode=false\n'
                    online_mode_modified = True

                # Configure difficulty (IMPORTANT: use if, not elif)
                if line.strip().startswith('difficulty='):
                    # Save previous value to report the change
                    old_difficulty = line.strip().split('=')[1]
                    lines[i] = f'difficulty={difficulty}\n'
                    difficulty_modified = True

            if not difficulty_modified:
                error_msg = f"Propiedad 'difficulty' no encontrada en server.properties. El archivo podría estar corrupto."
                print(error_msg)
                if log_callback:
                    log_callback(error_msg + "\n")
                return False

            # online-mode is optional for this function
            if not online_mode_modified:
                # Find where to add online-mode
                for i, line in enumerate(lines):
                    if line.strip().startswith('difficulty='):
                        lines.insert(i+1, 'online-mode=false\n')
                        break

            # Write modified file with UTF-8 encoding
            with open(self.properties_path, 'w', encoding='utf-8', newline='\n') as file:
                file.writelines(lines)

            # Verify that the change was applied correctly
            with open(self.properties_path, 'r', encoding='utf-8') as file:
                content = file.read()
                if f'difficulty={difficulty}' not in content:
                    error_msg = "Error: El cambio no se guardó correctamente en server.properties"
                    print(error_msg)
                    if log_callback:
                        log_callback(error_msg + "\n")
                    return False

            # Report success with details
            if old_difficulty and old_difficulty != difficulty:
                success_msg = f"✓ Configuración actualizada:\n  • Dificultad cambiada de '{old_difficulty}' a '{difficulty}'"
            else:
                success_msg = f"✓ Configuración aplicada:\n  • Dificultad: {difficulty}"

            print(success_msg)
            if log_callback:
                log_callback(success_msg + "\n")

            return True

        except PermissionError as e:
            error_msg = f"Error de permisos al modificar server.properties. Asegúrate de que el servidor no esté corriendo: {e}"
            print(error_msg)
            if log_callback:
                log_callback(error_msg + "\n")
            return False
        except Exception as e:
            error_msg = f"Error al modificar server.properties: {e}"
            print(error_msg)
            if log_callback:
                log_callback(error_msg + "\n")
            return False

    def get_property(self, property_name: str) -> Optional[str]:
        """
        Gets a specific property value from server.properties

        Args:
            property_name: Property name

        Returns:
            Property value or None if not found
        """
        try:
            if not os.path.exists(self.properties_path):
                return None

            with open(self.properties_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith(f'{property_name}='):
                        return line.split('=', 1)[1]

            return None

        except Exception as e:
            print(f"Error al leer propiedad: {e}")
            return None

    def update_property(self, property_name: str, property_value: str) -> bool:
        """
        Updates a specific property in server.properties.
        If the property doesn't exist, it will be added.

        Args:
            property_name: Property name
            property_value: Property value

        Returns:
            True if modified successfully, False otherwise
        """
        try:
            if not os.path.exists(self.properties_path):
                print("Archivo server.properties no encontrado")
                return False

            # Read all file lines
            with open(self.properties_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            # Modify the property
            property_modified = False

            for i, line in enumerate(lines):
                if line.strip().startswith(f'{property_name}='):
                    lines[i] = f'{property_name}={property_value}\n'
                    property_modified = True
                    break

            # If property doesn't exist, add it at the end
            if not property_modified:
                # Ensure there's a newline at the end before adding
                if lines and not lines[-1].endswith('\n'):
                    lines[-1] += '\n'
                lines.append(f'{property_name}={property_value}\n')
                print(f"Propiedad '{property_name}' agregada a server.properties")

            # Write modified file
            with open(self.properties_path, 'w', encoding='utf-8', newline='\n') as file:
                file.writelines(lines)

            print(f"server.properties actualizado: {property_name}={property_value}")
            return True

        except Exception as e:
            print(f"Error al actualizar propiedad: {e}")
            return False

    def run_server_first_time(
        self,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Runs the server for the first time and performs all automatic configuration

        Args:
            log_callback: Callback function to receive process logs

        Returns:
            True if the entire process was successful, False otherwise
        """
        try:
            if log_callback:
                log_callback("Iniciando servidor por primera vez...\n")
                log_callback("\n" + "="*70 + "\n")
                log_callback("VERIFICACIONES PREVIAS\n")
                log_callback("="*70 + "\n\n")

            # 1. Check write permissions
            if log_callback:
                log_callback("Verificando permisos de escritura...\n")

            has_perms, perm_msg = system_utils.check_write_permissions(self.server_folder)
            if not has_perms:
                if log_callback:
                    log_callback(f"\n❌ {perm_msg}\n")
                return False

            if log_callback:
                log_callback("✓ Permisos de escritura confirmados\n\n")

            # 2. Check available RAM (minimum 1GB for server)
            if log_callback:
                log_callback("Verificando RAM disponible...\n")

            can_ram, ram_msg = system_utils.can_allocate_ram(1024)
            if log_callback:
                log_callback(f"{ram_msg}\n\n")
            if not can_ram:
                return False

            # 3. Check if port 25565 is in use
            if log_callback:
                log_callback("Verificando puerto 25565...\n")

            system_utils.check_minecraft_port(log_callback)

            if log_callback:
                log_callback("\n" + "="*70 + "\n")
                log_callback("GENERACIÓN DE ARCHIVOS\n")
                log_callback("="*70 + "\n\n")

            # 4. First execution (will generate eula.txt) - Increased timeout to 20s
            if log_callback:
                log_callback("Generando EULA (esto puede tomar hasta 20 segundos)...\n")

            self._run_server_and_wait(log_callback, timeout=20, check_for="eula.txt")

            # Wait briefly
            time.sleep(0.5)

            # 5. Validate EULA file
            if not system_utils.validate_eula_file(self.eula_path):
                if log_callback:
                    log_callback("\n❌ EULA no se generó correctamente o está corrupto\n")
                    log_callback("   Posibles causas:\n")
                    log_callback("   • Java no se ejecutó correctamente\n")
                    log_callback("   • El proceso se interrumpió\n")
                    log_callback("   • Problemas de permisos\n")
                return False

            # 6. Accept EULA
            if os.path.exists(self.eula_path):
                if log_callback:
                    log_callback("✓ EULA generado correctamente\n")
                    log_callback("Aceptando EULA automáticamente...\n")
                if not self.accept_eula():
                    if log_callback:
                        log_callback("❌ Error al aceptar EULA\n")
                    return False
            else:
                if log_callback:
                    log_callback("❌ Archivo EULA no encontrado\n")
                return False

            # 7. Second execution (will generate all server files) - Increased timeout to 40s
            if log_callback:
                log_callback("✓ EULA aceptado\n\n")
                log_callback("Generando archivos del servidor (esto puede tomar hasta 40 segundos)...\n")

            self._run_server_and_wait(log_callback, timeout=40, check_for="server.properties")

            # Wait briefly
            time.sleep(0.5)

            # 8. Validate server.properties file
            if not system_utils.validate_properties_file(self.properties_path):
                if log_callback:
                    log_callback("\n❌ server.properties no se generó correctamente o está corrupto\n")
                    log_callback("   Posibles causas:\n")
                    log_callback("   • El servidor no tuvo tiempo suficiente para inicializar\n")
                    log_callback("   • Versión de Minecraft incompatible\n")
                    log_callback("   • Problemas de permisos\n")
                return False

            # 9. Modify server.properties
            if os.path.exists(self.properties_path):
                if log_callback:
                    log_callback("✓ server.properties generado correctamente\n")
                    log_callback("Configurando server.properties...\n")
                if not self.configure_server_properties(log_callback=log_callback):
                    if log_callback:
                        log_callback("❌ Error al modificar server.properties\n")
                    return False
            else:
                if log_callback:
                    log_callback("❌ Archivo server.properties no encontrado\n")
                return False

            # 10. Configuration complete
            if log_callback:
                log_callback("\n✅ ¡Configuración completada exitosamente!\n\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"\n❌ Error durante la configuración: {e}\n")
                log_callback(f"   Tipo de error: {type(e).__name__}\n")
            return False
        finally:
            # Clean up zombie processes
            system_utils.cleanup_zombie_processes(log_callback)

    def _run_server_and_wait(
        self,
        log_callback: Optional[Callable[[str], None]] = None,
        timeout: int = 30,
        check_for: Optional[str] = None
    ):
        """
        Ejecuta el servidor y espera a que termine o alcance el timeout

        Args:
            log_callback: Función callback para recibir logs
            timeout: Tiempo máximo de espera en segundos
            check_for: Archivo a buscar para terminar antes (optimización)
        """
        try:
            # Comando para ejecutar el servidor (2GB RAM por defecto para vanilla)
            command = [self.java_executable, "-Xmx2048M", "-Xms2048M", "-Djava.awt.headless=true", "-jar", "server.jar", "nogui"]

            # Ejecutar el proceso
            # Configurar flags para Windows
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(
                command,
                cwd=self.server_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=creation_flags
            )

            # Esperar el timeout o que termine el proceso
            start_time = time.time()
            file_found = False

            while True:
                # Si el proceso terminó
                if process.poll() is not None:
                    break

                # Si encontramos el archivo que buscamos, terminamos
                if check_for and not file_found:
                    check_path = os.path.join(self.server_folder, check_for)
                    if os.path.exists(check_path):
                        file_found = True
                        # Dar un poco más de tiempo para que termine de escribir
                        time.sleep(1)
                        process.terminate()
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        break

                # Timeout
                if time.time() - start_time > timeout:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break

                # Leer salida si hay
                if process.stdout:
                    line = process.stdout.readline()
                    if line and log_callback:
                        log_callback(line)

                time.sleep(0.1)

        except FileNotFoundError as e:
            if log_callback:
                log_callback(f"\n✗ Error: No se encontró el ejecutable de Java.\n")
                log_callback(f"Ruta buscada: {self.java_executable}\n")
                log_callback("Asegúrate de que Java esté instalado correctamente.\n")
        except PermissionError as e:
            if log_callback:
                log_callback(f"\n✗ Error de permisos al ejecutar el servidor: {e}\n")
        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error al ejecutar servidor: {e}\n")
                log_callback(f"Tipo de error: {type(e).__name__}\n")

    def start_server(
        self,
        ram_mb: int = 2048,
        log_callback: Optional[Callable[[str], None]] = None,
        detached: bool = False,
        on_stopped: Optional[Callable[[], None]] = None
    ) -> bool:
        """
        Inicia el servidor de Minecraft

        Args:
            ram_mb: RAM en megabytes a asignar (default: 2048 = 2GB)
            log_callback: Función callback para recibir logs del servidor
            detached: Si es True, el servidor se ejecuta en segundo plano
            on_stopped: Callback que se llama cuando el servidor se detiene (solo en modo detached)

        Returns:
            True si el servidor se inició correctamente, False en caso contrario
        """
        try:
            if self.server_process and self.server_process.poll() is None:
                if log_callback:
                    log_callback("El servidor ya está en ejecución\n")
                return False

            # Always clean client-only mods before starting (safety measure)
            mods_folder = os.path.join(self.server_folder, "mods")
            if os.path.exists(mods_folder):
                if log_callback:
                    log_callback("\n=== LIMPIANDO MODS SOLO-CLIENTE ===\n")
                removed = self.clean_client_only_mods(log_callback)
                if removed:
                    if log_callback:
                        log_callback(f"\n✓ {len(removed)} mods solo-cliente removidos\n\n")
                else:
                    if log_callback:
                        log_callback("✓ No se encontraron mods solo-cliente\n\n")

            # Ensure EULA is accepted before starting
            self.ensure_eula_accepted(log_callback)

            # Determine how to start the server
            command = None
            use_shell = False

            # Check for run scripts (modern Forge/NeoForge)
            run_bat = os.path.join(self.server_folder, "run.bat")
            run_sh = os.path.join(self.server_folder, "run.sh")
            start_bat = os.path.join(self.server_folder, "start.bat")
            start_sh = os.path.join(self.server_folder, "start.sh")

            if os.name == 'nt':  # Windows
                if os.path.exists(run_bat):
                    command = [run_bat]
                    use_shell = True
                    if log_callback:
                        log_callback("Using run.bat to start server...\n")
                elif os.path.exists(start_bat):
                    command = [start_bat]
                    use_shell = True
                    if log_callback:
                        log_callback("Using start.bat to start server...\n")
            else:  # Linux/Mac
                if os.path.exists(run_sh):
                    command = ["bash", run_sh]
                    if log_callback:
                        log_callback("Using run.sh to start server...\n")
                elif os.path.exists(start_sh):
                    command = ["bash", start_sh]
                    if log_callback:
                        log_callback("Using start.sh to start server...\n")

            # If no script found, try to find a server jar
            if command is None:
                import glob

                # Check for server.jar first
                if os.path.exists(self.server_jar_path):
                    command = [self.java_executable, f"-Xmx{ram_mb}M", f"-Xms{ram_mb}M", "-Djava.awt.headless=true", "-jar", "server.jar", "nogui"]
                else:
                    # Look for other server jars
                    jar_patterns = ["forge-*.jar", "neoforge-*.jar", "fabric-server-*.jar", "quilt-server-*.jar"]
                    server_jar = None

                    for pattern in jar_patterns:
                        matches = glob.glob(os.path.join(self.server_folder, pattern))
                        if matches:
                            server_jar = os.path.basename(matches[0])
                            break

                    if server_jar:
                        command = [self.java_executable, f"-Xmx{ram_mb}M", f"-Xms{ram_mb}M", "-Djava.awt.headless=true", "-jar", server_jar, "nogui"]
                        if log_callback:
                            log_callback(f"Using {server_jar}...\n")
                    else:
                        if log_callback:
                            log_callback("No server jar or start script found\n")
                        return False

            if log_callback:
                log_callback(f"Iniciando servidor con {ram_mb} MB ({ram_mb/1024:.1f} GB) de RAM...\n")

            if detached:
                # Ejecutar en segundo plano con stdin para comandos
                if log_callback:
                    log_callback("Iniciando servidor en segundo plano...\n")

                # Configurar flags para Windows
                creation_flags = 0
                if os.name == 'nt':
                    creation_flags = subprocess.CREATE_NO_WINDOW

                self.server_process = subprocess.Popen(
                    command,
                    cwd=self.server_folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    creationflags=creation_flags,
                    shell=use_shell
                )

                # Leer logs en un hilo separado
                def read_output():
                    try:
                        if log_callback and self.server_process and self.server_process.stdout:
                            for line in self.server_process.stdout:
                                log_callback(line)
                    except:
                        pass
                    finally:
                        # Server process has ended - call the on_stopped callback
                        if on_stopped:
                            on_stopped()

                thread = threading.Thread(target=read_output, daemon=True)
                thread.start()

                if log_callback:
                    log_callback("Servidor iniciado!\n")
                return True
            else:
                # Ejecutar en primer plano (bloqueante)
                if log_callback:
                    log_callback("Iniciando servidor...\n")

                # Configurar flags para Windows
                creation_flags = 0
                if os.name == 'nt':
                    creation_flags = subprocess.CREATE_NO_WINDOW

                self.server_process = subprocess.Popen(
                    command,
                    cwd=self.server_folder,
                    creationflags=creation_flags,
                    shell=use_shell
                )
                self.server_process.wait()
                return True

        except FileNotFoundError as e:
            if log_callback:
                log_callback(f"\n✗ Error: No se encontró el ejecutable de Java.\n")
                log_callback(f"Ruta buscada: {self.java_executable}\n")
                log_callback("Asegúrate de que Java esté instalado correctamente.\n")
            return False
        except PermissionError as e:
            if log_callback:
                log_callback(f"\n✗ Error de permisos al iniciar el servidor: {e}\n")
            return False
        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error al iniciar servidor: {e}\n")
                log_callback(f"Tipo de error: {type(e).__name__}\n")
            return False

    def stop_server(self, log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Detiene el servidor si está en ejecución

        Args:
            log_callback: Función callback para recibir logs

        Returns:
            True si se detuvo correctamente, False en caso contrario
        """
        try:
            if self.server_process and self.server_process.poll() is None:
                # First try graceful shutdown with "stop" command
                if self.server_process.stdin:
                    try:
                        self.server_process.stdin.write("stop\n")
                        self.server_process.stdin.flush()
                        # Wait for graceful shutdown
                        self.server_process.wait(timeout=15)
                        print("Servidor detenido (graceful)")
                        self.server_process = None
                        return True
                    except (subprocess.TimeoutExpired, OSError, BrokenPipeError):
                        # Graceful shutdown failed, proceed to terminate
                        pass

                # Forceful termination
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Kill if terminate didn't work
                    self.server_process.kill()
                    try:
                        self.server_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # Last resort: use psutil to force kill
                        try:
                            import psutil
                            parent = psutil.Process(self.server_process.pid)
                            for child in parent.children(recursive=True):
                                child.kill()
                            parent.kill()
                        except Exception:
                            pass

                print("Servidor detenido")
                self.server_process = None
                return True
            else:
                print("El servidor no está en ejecución")
                self.server_process = None  # Clean up reference anyway
                return False
        except Exception as e:
            print(f"Error al detener servidor: {e}")
            self.server_process = None  # Clean up on error too
            return False

    def is_server_running(self) -> bool:
        """Verifica si el servidor está en ejecución"""
        return self.server_process is not None and self.server_process.poll() is None

    def send_command(self, command: str) -> bool:
        """
        Envía un comando al servidor en ejecución

        Args:
            command: Comando a enviar (ej: "stop", "list", "op player")

        Returns:
            True si el comando se envió correctamente, False en caso contrario
        """
        try:
            if not self.is_server_running():
                print("El servidor no está en ejecución")
                return False

            if self.server_process and self.server_process.stdin:
                self.server_process.stdin.write(f"{command}\n")
                self.server_process.stdin.flush()
                return True
            else:
                print("No se puede enviar comando: stdin no disponible")
                return False

        except Exception as e:
            print(f"Error al enviar comando: {e}")
            return False

    # ==================== SOPORTE PARA MODPACKS ====================

    def detect_server_type(self) -> str:
        """
        Detecta el tipo de servidor (vanilla, forge, fabric)

        Returns:
            "vanilla", "forge", "fabric", o "unknown"
        """
        # Verificar si es Fabric
        fabric_launcher = os.path.join(self.server_folder, "fabric-server-launch.jar")
        if os.path.exists(fabric_launcher):
            return "fabric"

        # Verificar si es Forge (buscar archivos run.bat/run.sh o forge jar)
        run_bat = os.path.join(self.server_folder, "run.bat")
        run_sh = os.path.join(self.server_folder, "run.sh")

        if os.path.exists(run_bat) or os.path.exists(run_sh):
            return "forge"

        # Buscar archivos forge-*.jar
        for file in os.listdir(self.server_folder):
            if file.startswith("forge-") and file.endswith(".jar"):
                return "forge"

        # Si existe server.jar, es vanilla
        if os.path.exists(self.server_jar_path):
            return "vanilla"

        return "unknown"

    def start_modded_server(
        self,
        server_type: str,
        ram_mb: int = 6144,
        java_executable: str = "java",
        log_callback: Optional[Callable[[str], None]] = None,
        detached: bool = False,
        on_stopped: Optional[Callable[[], None]] = None
    ) -> bool:
        """
        Inicia un servidor con mods (Forge o Fabric)

        Args:
            server_type: "forge" o "fabric"
            ram_mb: RAM en megabytes a asignar
            java_executable: Ejecutable de Java a usar
            log_callback: Función callback para recibir logs del servidor
            detached: Si es True, el servidor se ejecuta en segundo plano
            on_stopped: Callback que se llama cuando el servidor se detiene (solo en modo detached)

        Returns:
            True si el servidor se inició correctamente
        """
        try:
            if self.server_process and self.server_process.poll() is None:
                if log_callback:
                    log_callback("El servidor ya está en ejecución\n")
                return False

            # Limpiar mods solo-cliente automáticamente
            if log_callback:
                log_callback("\n=== LIMPIANDO MODS SOLO-CLIENTE ===\n")

            removed_mods = self.clean_client_only_mods(log_callback)

            if removed_mods:
                if log_callback:
                    log_callback(f"\n✓ {len(removed_mods)} mods solo-cliente removidos automáticamente\n")
                    log_callback("  (Moved to: client_mods_deleted/)\n\n")
            else:
                if log_callback:
                    log_callback("✓ No se encontraron mods solo-cliente\n\n")

            # === PRE-EMPTIVE EULA ACCEPTANCE ===
            # Accept EULA BEFORE starting the server - this allows the server to
            # start and generate server.properties in a SINGLE run (no restart needed)
            if log_callback:
                log_callback("=== CONFIGURACIÓN INICIAL ===\n")

            if not self.ensure_eula_accepted(log_callback):
                if log_callback:
                    log_callback("\n❌ Error: No se pudo aceptar el EULA\n")
                return False

            if log_callback:
                log_callback("✓ Configuración completada\n\n")

            ram_min = f"-Xms{ram_mb}M"
            ram_max = f"-Xmx{ram_mb}M"

            if server_type == "fabric":
                # Fabric usa fabric-server-launch.jar
                fabric_jar = "fabric-server-launch.jar"
                if not os.path.exists(os.path.join(self.server_folder, fabric_jar)):
                    if log_callback:
                        log_callback(f"Error: {fabric_jar} no encontrado\n")
                    return False

                command = [java_executable, ram_min, ram_max, "-Djava.awt.headless=true", "-jar", fabric_jar, "nogui"]

            elif server_type == "forge":
                # Forge uses argument files (@user_jvm_args.txt, @win_args.txt)

                # First, modify or create user_jvm_args.txt with RAM settings
                user_jvm_args_path = os.path.join(self.server_folder, "user_jvm_args.txt")

                # Create default user_jvm_args.txt if it doesn't exist
                if not os.path.exists(user_jvm_args_path):
                    with open(user_jvm_args_path, 'w', encoding='utf-8') as f:
                        f.write(f"-Djava.awt.headless=true\n-Xms{ram_mb}M\n-Xmx{ram_mb}M\n")
                else:
                    # Read and modify JVM arguments
                    with open(user_jvm_args_path, 'r', encoding='utf-8') as f:
                        jvm_args = f.read()

                    # Replace RAM arguments
                    import re
                    jvm_args = re.sub(r'-Xmx\d+[MGmg]', f'-Xmx{ram_mb}M', jvm_args)
                    jvm_args = re.sub(r'-Xms\d+[MGmg]', f'-Xms{ram_mb}M', jvm_args)

                    # Add headless mode to prevent server GUI window from opening
                    if '-Djava.awt.headless=true' not in jvm_args:
                        jvm_args = '-Djava.awt.headless=true\n' + jvm_args

                    with open(user_jvm_args_path, 'w', encoding='utf-8') as f:
                        f.write(jvm_args)

                # Find win_args.txt or unix_args.txt
                forge_path = os.path.join(self.server_folder, "libraries", "net", "minecraftforge", "forge")
                args_file_path = None

                if os.path.exists(forge_path):
                    for version_folder in os.listdir(forge_path):
                        version_path = os.path.join(forge_path, version_folder)
                        if os.path.isdir(version_path):
                            args_file = "win_args.txt" if os.name == 'nt' else "unix_args.txt"
                            potential_path = os.path.join(version_path, args_file)
                            if os.path.exists(potential_path):
                                args_file_path = potential_path
                                break

                if not args_file_path:
                    # Fallback: try to find forge jar directly
                    if log_callback:
                        log_callback("Warning: Forge args file not found, trying fallback...\n")
                    import glob
                    forge_jars = glob.glob(os.path.join(self.server_folder, "forge-*.jar"))
                    if forge_jars:
                        forge_jar = os.path.basename(forge_jars[0])
                        command = [java_executable, f"-Xms{ram_mb}M", f"-Xmx{ram_mb}M", "-Djava.awt.headless=true", "-jar", forge_jar, "nogui"]
                    else:
                        if log_callback:
                            log_callback("Error: No Forge server files found\n")
                        return False
                else:
                    # Add nogui to the args file if not present
                    try:
                        with open(args_file_path, 'r', encoding='utf-8') as f:
                            args_content = f.read()
                        if 'nogui' not in args_content.lower():
                            with open(args_file_path, 'a', encoding='utf-8') as f:
                                f.write('\nnogui\n')
                    except:
                        pass

                    # Build command using @ for argument files
                    command = [
                        java_executable,
                        f"@{user_jvm_args_path}",
                        f"@{args_file_path}"
                    ]

            else:
                if log_callback:
                    log_callback(f"Error: Tipo de servidor '{server_type}' no soportado\n")
                return False

            if detached:
                if log_callback:
                    log_callback(f"Iniciando servidor {server_type} en segundo plano...\n")
                    log_callback(f"RAM asignada: {ram_mb} MB\n")

                # Configurar flags para Windows (evitar ventana CMD extra)
                creation_flags = 0
                if os.name == 'nt':  # Windows
                    creation_flags = subprocess.CREATE_NO_WINDOW

                self.server_process = subprocess.Popen(
                    command,
                    cwd=self.server_folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    creationflags=creation_flags
                )

                # Leer logs en un hilo separado
                def read_output():
                    try:
                        if log_callback and self.server_process and self.server_process.stdout:
                            for line in self.server_process.stdout:
                                log_callback(line)
                    except:
                        pass
                    finally:
                        # Server process has ended - call the on_stopped callback
                        if on_stopped:
                            on_stopped()

                thread = threading.Thread(target=read_output, daemon=True)
                thread.start()

                if log_callback:
                    log_callback("Servidor iniciado!\n")
                return True
            else:
                if log_callback:
                    log_callback(f"Iniciando servidor {server_type}...\n")

                # Configurar flags para Windows
                creation_flags = 0
                if os.name == 'nt':
                    creation_flags = subprocess.CREATE_NO_WINDOW

                self.server_process = subprocess.Popen(
                    command,
                    cwd=self.server_folder,
                    creationflags=creation_flags
                )
                self.server_process.wait()
                return True

        except FileNotFoundError as e:
            if log_callback:
                log_callback(f"\n✗ Error: No se encontró el ejecutable de Java.\n")
                log_callback(f"Ruta buscada: {java_executable}\n")
                log_callback("Asegúrate de que Java esté instalado correctamente.\n")
            return False
        except PermissionError as e:
            if log_callback:
                log_callback(f"\n✗ Error de permisos al iniciar el servidor: {e}\n")
            return False
        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error al iniciar servidor: {e}\n")
                log_callback(f"Tipo de error: {type(e).__name__}\n")
            return False

    def _modify_forge_run_script(self, script_path: str, ram_mb: int):
        """
        Modifica el script run.bat o run.sh de Forge para usar la RAM especificada

        Args:
            script_path: Ruta al script
            ram_mb: RAM en megabytes
        """
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Reemplazar valores de RAM
            # Buscar patrones como -Xmx4G, -Xms1G, etc.
            import re
            content = re.sub(r'-Xmx\d+[GM]', f'-Xmx{ram_mb}M', content)
            content = re.sub(r'-Xms\d+[GM]', f'-Xms{ram_mb}M', content)

            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(content)

        except Exception as e:
            print(f"Error al modificar script: {e}")

    def run_modded_server_first_time(
        self,
        server_type: str,
        ram_mb: int = 6144,
        java_executable: str = "java",
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Ejecuta un servidor con mods por primera vez y realiza la configuración

        Args:
            server_type: "forge" o "fabric"
            ram_mb: RAM en megabytes
            java_executable: Ejecutable de Java
            log_callback: Función callback para logs

        Returns:
            True si fue exitoso
        """
        try:
            if log_callback:
                log_callback("Iniciando servidor por primera vez...\n")

            # Pre-create EULA BEFORE running the server (no need for start -> stop -> start cycle)
            if not self.ensure_eula_accepted(log_callback):
                if log_callback:
                    log_callback("❌ Error al aceptar EULA\n")
                return False

            # Single execution to generate server files (EULA already accepted)
            if log_callback:
                log_callback("\nGenerando archivos del servidor...\n")

            timeout_props = 120 if server_type == "forge" else 60
            self._run_modded_server_and_wait(server_type, ram_mb, java_executable, log_callback, timeout=timeout_props, check_for="server.properties")

            time.sleep(0.5)

            # Modificar server.properties
            if os.path.exists(self.properties_path):
                if log_callback:
                    log_callback("✓ server.properties generado\n")
                    log_callback("Configurando server.properties...\n")
                if not self.configure_server_properties():
                    if log_callback:
                        log_callback("⚠ Error al modificar server.properties (continuando)\n")
            else:
                if log_callback:
                    log_callback("⚠ server.properties no encontrado (se generará al iniciar)\n")

            if log_callback:
                log_callback("✓ ¡Configuración completada!\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"❌ Error durante la configuración: {e}\n")
            return False

    def _run_modded_server_and_wait(
        self,
        server_type: str,
        ram_mb: int,
        java_executable: str,
        log_callback: Optional[Callable[[str], None]] = None,
        timeout: int = 30,
        check_for: Optional[str] = None
    ):
        """
        Ejecuta servidor con mods y espera

        Args:
            server_type: "forge" o "fabric"
            ram_mb: RAM en MB
            java_executable: Ejecutable de Java
            log_callback: Callback para logs
            timeout: Timeout en segundos
            check_for: Archivo a buscar para terminar antes
        """
        try:
            ram_min = f"-Xms{ram_mb}M"
            ram_max = f"-Xmx{ram_mb}M"

            if server_type == "fabric":
                command = [java_executable, ram_min, ram_max, "-Djava.awt.headless=true", "-jar", "fabric-server-launch.jar", "nogui"]
            elif server_type == "forge":
                # Modify or create user_jvm_args.txt
                user_jvm_args_path = os.path.join(self.server_folder, "user_jvm_args.txt")

                # Create default user_jvm_args.txt if it doesn't exist
                if not os.path.exists(user_jvm_args_path):
                    with open(user_jvm_args_path, 'w', encoding='utf-8') as f:
                        f.write(f"-Djava.awt.headless=true\n-Xms{ram_mb}M\n-Xmx{ram_mb}M\n")
                else:
                    with open(user_jvm_args_path, 'r', encoding='utf-8') as f:
                        jvm_args = f.read()
                    import re
                    jvm_args = re.sub(r'-Xmx\d+[MGmg]', f'-Xmx{ram_mb}M', jvm_args)
                    jvm_args = re.sub(r'-Xms\d+[MGmg]', f'-Xms{ram_mb}M', jvm_args)

                    # Add headless mode to prevent server GUI window from opening
                    if '-Djava.awt.headless=true' not in jvm_args:
                        jvm_args = '-Djava.awt.headless=true\n' + jvm_args

                    with open(user_jvm_args_path, 'w', encoding='utf-8') as f:
                        f.write(jvm_args)

                # Find win_args.txt or unix_args.txt
                forge_path = os.path.join(self.server_folder, "libraries", "net", "minecraftforge", "forge")
                args_file_path = None

                if os.path.exists(forge_path):
                    for version_folder in os.listdir(forge_path):
                        version_path = os.path.join(forge_path, version_folder)
                        if os.path.isdir(version_path):
                            args_file = "win_args.txt" if os.name == 'nt' else "unix_args.txt"
                            potential_path = os.path.join(version_path, args_file)
                            if os.path.exists(potential_path):
                                args_file_path = potential_path
                                break

                if args_file_path:
                    # Add nogui to the args file if not present
                    try:
                        with open(args_file_path, 'r', encoding='utf-8') as f:
                            args_content = f.read()
                        if 'nogui' not in args_content.lower():
                            with open(args_file_path, 'a', encoding='utf-8') as f:
                                f.write('\nnogui\n')
                    except:
                        pass

                    command = [java_executable, f"@{user_jvm_args_path}", f"@{args_file_path}"]
                else:
                    # Fallback: try to run with direct jar
                    if log_callback:
                        log_callback("Warning: Forge args file not found, trying fallback...\n")
                    import glob
                    forge_jars = glob.glob(os.path.join(self.server_folder, "forge-*.jar"))
                    if forge_jars:
                        forge_jar = os.path.basename(forge_jars[0])
                        command = [java_executable, ram_min, ram_max, "-Djava.awt.headless=true", "-jar", forge_jar, "nogui"]
                    else:
                        if log_callback:
                            log_callback("Error: No Forge server files found\n")
                        return
            else:
                return

            # Configurar flags para Windows
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(
                command,
                cwd=self.server_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=creation_flags
            )

            start_time = time.time()
            file_found = False

            while True:
                if process.poll() is not None:
                    break

                if check_for and not file_found:
                    check_path = os.path.join(self.server_folder, check_for)
                    if os.path.exists(check_path):
                        # Wait for file to have content (not just exist)
                        try:
                            file_size = os.path.getsize(check_path)
                            if file_size > 10:  # At least 10 bytes to ensure it's written
                                file_found = True
                                # Wait longer for the file to be completely written
                                # and for server to finish its shutdown sequence
                                time.sleep(3)
                                # Check if process already exited naturally
                                if process.poll() is None:
                                    process.terminate()
                                    try:
                                        process.wait(timeout=10)
                                    except subprocess.TimeoutExpired:
                                        process.kill()
                                break
                        except OSError:
                            pass  # File might be locked, retry next iteration

                if time.time() - start_time > timeout:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break

                if process.stdout:
                    line = process.stdout.readline()
                    if line and log_callback:
                        log_callback(line)

                time.sleep(0.1)

        except FileNotFoundError as e:
            if log_callback:
                log_callback(f"\n✗ Error: No se encontró el ejecutable de Java.\n")
                log_callback(f"Ruta buscada: {java_executable}\n")
                log_callback("Asegúrate de que Java esté instalado correctamente.\n")
        except PermissionError as e:
            if log_callback:
                log_callback(f"\n✗ Error de permisos al ejecutar el servidor: {e}\n")
        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error al ejecutar servidor: {e}\n")
                log_callback(f"Tipo de error: {type(e).__name__}\n")

    def get_recommended_ram_for_modpack(self, num_mods: int) -> int:
        """
        Obtiene RAM recomendada basándose en el número de mods

        Args:
            num_mods: Número de mods en el modpack

        Returns:
            RAM recomendada en MB
        """
        if num_mods < 50:
            return 4096  # 4 GB para modpacks pequeños
        elif num_mods < 100:
            return 6144  # 6 GB para modpacks medianos (default)
        elif num_mods < 150:
            return 8192  # 8 GB para modpacks grandes
        else:
            return 10240  # 10 GB para modpacks muy grandes

    def clean_client_only_mods(
        self,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> list:
        """
        Detecta y remueve automáticamente mods solo-cliente que causan crashes en servidores

        Args:
            log_callback: Función callback para reportar progreso

        Returns:
            Lista de mods removidos
        """
        # EXHAUSTIVE list of client-only mod patterns
        # IMPORTANT: These patterns are searched in the filename (case-insensitive)
        CLIENT_ONLY_MOD_PATTERNS = [
            # ===== CRITICAL: Mods that ALWAYS crash dedicated servers =====
            "ryoamiclights", "ryoamiclight", "ryoamic",  # Dynamic lighting - CRASHES SERVERS
            "barista", "barsita",  # Client keybindings - CRASHES SERVERS
            "obsidianui", "obsidian_ui",  # Client UI library - CRASHES SERVERS

            # ===== Rendering & Graphics =====
            "entity_texture_features", "entity_model_features", "etf-", "emf-",
            "embeddium", "rubidium", "oculus", "iris", "magnesium", "reforgium",
            "optifine", "optifabric", "sodium", "sodiumextra", "reeses_sodium",
            "phosphor", "starlight", "indium",
            "immediatelyfast", "nvidium", "badoptimizations",
            "continuity", "enhancedblockentities", "enhanced_block_entities",

            # ===== Visual Effects =====
            "betteranimationscollection", "betteranimationsmod", "notenoughanimations",
            "not_enough_animations", "playeranimator", "player_animator",
            "visuality", "falling_leaves", "fallingleaves", "particle_rain",
            "skinlayers3d", "3dskinlayers", "skin_layers",
            "blur", "cleanview", "betterskybox", "clear_skies",
            "dynamiclights", "sodiumdynamiclights", "lambdynamiclights",
            "dynamiclightsreforged", "fancy_video_player",
            "presence_footsteps", "presencefootsteps",
            "wakes", "bedrockwaters", "particle_blocker",

            # ===== UI & HUD =====
            "betterf3", "better_f3", "betterthirdperson", "better_third_person",
            "chat_heads", "chatheads", "chatpatches", "chatting",
            "fancymenu", "loadingbackgrounds", "inventoryhud", "inventory_hud",
            "xaerosminimap", "xaeroworldmap", "xaeros", "journeymap",
            "voxelmap", "mapfrontiers", "worldmap", "minimaps",
            "bhmenu", "catalogue", "configured", "controlling", "searchables",
            "defaultoptions", "roughly_enough_items_client", "rei-",
            "mouse_tweaks", "mousewheelie", "controlling-client",
            "modmenu", "mod_menu", "shulkerboxtooltip",
            "forgeconfigscreens", "forge_config_screens", "forgeconfigs",
            "welcomescreen", "welcome_screen",
            "advancementinfo", "betterstats", "itemphysic", "physics_mod",
            "legendary_tooltips", "legendarytooltips", "equipmentcompare",
            "tooltipfix", "advancedtooltips", "effectdescriptions",
            "enchantmentdescriptions", "itemdescriptions",

            # ===== Camera & Controls =====
            "cameraoverhaul", "camera_overhaul", "camerautils",
            "zoomify", "justzoom", "logical_zoom", "okzoomer", "wizmiczoom",
            "shoulder_surfing", "firstperson", "firstpersonmodel",
            "freelook", "freecamera", "perspectivemod",
            "better_third_person", "bettertps", "headtilt",

            # ===== Client Optimization =====
            "lazydfu", "lazy_dfu", "dashloader", "smoothboot", "smooth_boot",
            "starlight-client", "ferrite_core-client", "ferritecore-client",
            "entityculling", "cullleaves", "cull_leaves", "cull_less_leaves",
            "memoryleakfix", "memory_leak_fix", "memoryusagescreen",
            "dynamicfps", "dynamic_fps", "fpsdisplay", "exordium", "ksyxis",
            "moreculling", "more_culling", "viewdistancefix",

            # ===== Audio =====
            "soundphysics", "sound_physics", "sound_physics_remastered",
            "extreme_sound_muffler", "audio_player", "music_triggers",
            "dynamic_sound_filters", "ambientsounds", "ambient_sounds",
            "extrasounds", "auditory", "soundreloader", "drippysoundengine",

            # ===== Client-side Utilities =====
            "screenshots_viewer", "screenshot_to_clipboard", "screenshottoclipboard",
            "fabrishot", "borderless_window", "borderlessmining", "windowedmode",
            "fullscreen_windowed", "custom_window_title",
            "replay_mod", "replaymod", "bobby",
            "minihud", "tweakeroo", "litematica", "item_scroller", "itemscroller",
            "malilib", "inventoryprofiles", "inventoryprofilesnext", "invprofiles",
            "itemswapper", "reacharound", "advancedchat",

            # ===== Shaders & Resource Packs =====
            "shader", "complementary", "bsl", "sildurs",
            "seus", "kuda", "continuum",
            "cit_resewn", "citresewn", "citreforged", "chime", "cem",
            "custom_entity_models", "fusion",  # CIT mod

            # ===== Recipe Viewers (Client-only) =====
            "emi-", "emi_loot", "emi_trades", "emienchants",
            "jeiintegration", "jerintegration",

            # ===== Cosmetics =====
            "capes", "cosmetica", "ears", "customskinloader",
            "showmeyourskin", "armorstandhud",

            # ===== Screen/Loading =====
            "better_loading_screen", "loadingscreen", "customloadingscreen",
            "seamless_loading_screen", "splashscreen", "mainmenucredits",
            "bettermodbutton", "darkmode", "darkmodeeverywhere", "darkgui",

            # ===== Misc Client-only =====
            "light_overlay", "lightoverlay", "spawnmarkers",
            "appleskin-client", "torohealth", "damage_indicator",
            "inventory_tweaks", "inventory_profiles", "trashslot",
            "mod_menu", "fabric_api-client",
            "notenoughcrashes", "not_enough_crashes", "crashassistant", "yosbr",
            "betterbiomeblend", "better_biome_blend", "noisium",
            "textureloader", "lambdabettergrass", "colinoclient",
            "modelfix", "model_fix", "no_fog", "fogcontrol",
            "resolutioncontrol", "resizablechat",
            "boostedbrightness", "fullbright", "gamma_utils", "nightvisionflash",
            "eating_animation", "eatinganimation", "bettercombatrenders",
            "cubesideanywhere", "findme", "highlight", "radon",
            "distant_horizons", "distanthorizons",
            "worldedit_cui",

            # ===== Problematic mods specific to 1.19.2 =====
            "euphoriapatcher", "euphoria_patcher",
            "neko", "nekoenchanted",
            "yungsmenutweaks", "yungs_menu",
            "spruceui", "spruce_ui",
            "bocchium",
            "jeresources", "jer-", "justplayer",
        ]

        try:
            mods_folder = os.path.join(self.server_folder, "mods")
            if not os.path.exists(mods_folder):
                return []

            # Crear carpeta para mods deshabilitados
            disabled_folder = os.path.join(self.server_folder, "client_mods_deleted")
            os.makedirs(disabled_folder, exist_ok=True)

            removed_mods = []

            # Listar todos los archivos en la carpeta mods
            for filename in os.listdir(mods_folder):
                if not filename.endswith(".jar"):
                    continue

                # Verificar si coincide con algún patrón
                filename_lower = filename.lower()
                is_client_only = False

                for pattern in CLIENT_ONLY_MOD_PATTERNS:
                    if pattern.lower() in filename_lower:
                        is_client_only = True
                        break

                if is_client_only:
                    source = os.path.join(mods_folder, filename)
                    destination = os.path.join(disabled_folder, filename)

                    # Mover el mod
                    import shutil
                    shutil.move(source, destination)
                    removed_mods.append(filename)

                    if log_callback:
                        log_callback(f"  ⚠ Removido: {filename}\n")

            return removed_mods

        except Exception as e:
            if log_callback:
                log_callback(f"Error al limpiar mods solo-cliente: {str(e)}\n")
            return []
