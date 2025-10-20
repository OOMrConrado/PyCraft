import subprocess
import os
import time
from typing import Optional, Callable
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

    def accept_eula(self) -> bool:
        """
        Automatically accepts the EULA by modifying the eula.txt file

        Returns:
            True if modified successfully, False otherwise
        """
        try:
            if not os.path.exists(self.eula_path):
                print("Archivo eula.txt no encontrado")
                return False

            # Read the file
            with open(self.eula_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Replace eula=false with eula=true
            content = content.replace('eula=false', 'eula=true')

            # Write the modified file
            with open(self.eula_path, 'w', encoding='utf-8') as file:
                file.write(content)

            print("EULA aceptado automáticamente")
            return True

        except Exception as e:
            print(f"Error al aceptar EULA: {e}")
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
        Updates a specific property in server.properties

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

            if not property_modified:
                print(f"Propiedad '{property_name}' no encontrada")
                return False

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
            command = [self.java_executable, "-Xmx2048M", "-Xms2048M", "-jar", "server.jar", "nogui"]

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
        detached: bool = False
    ) -> bool:
        """
        Inicia el servidor de Minecraft

        Args:
            ram_mb: RAM en megabytes a asignar (default: 2048 = 2GB)
            log_callback: Función callback para recibir logs del servidor
            detached: Si es True, el servidor se ejecuta en segundo plano

        Returns:
            True si el servidor se inició correctamente, False en caso contrario
        """
        try:
            if self.server_process and self.server_process.poll() is None:
                if log_callback:
                    log_callback("El servidor ya está en ejecución\n")
                return False

            # Verificar que existe el server.jar
            if not os.path.exists(self.server_jar_path):
                if log_callback:
                    log_callback("server.jar no encontrado\n")
                return False

            # Comando para ejecutar el servidor con RAM configurable
            command = [self.java_executable, f"-Xmx{ram_mb}M", f"-Xms{ram_mb}M", "-jar", "server.jar", "nogui"]

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
                    creationflags=creation_flags
                )

                # Leer logs en un hilo separado si hay callback
                if log_callback:
                    def read_output():
                        for line in self.server_process.stdout:
                            log_callback(line)

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
                    creationflags=creation_flags
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

    def stop_server(self) -> bool:
        """
        Detiene el servidor si está en ejecución

        Returns:
            True si se detuvo correctamente, False en caso contrario
        """
        try:
            if self.server_process and self.server_process.poll() is None:
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.server_process.kill()
                print("Servidor detenido")
                return True
            else:
                print("El servidor no está en ejecución")
                return False
        except Exception as e:
            print(f"Error al detener servidor: {e}")
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
        detached: bool = False
    ) -> bool:
        """
        Inicia un servidor con mods (Forge o Fabric)

        Args:
            server_type: "forge" o "fabric"
            ram_mb: RAM en megabytes a asignar
            java_executable: Ejecutable de Java a usar
            log_callback: Función callback para recibir logs del servidor
            detached: Si es True, el servidor se ejecuta en segundo plano

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
                    log_callback("  (Movidos a: mods_disabled_client/)\n\n")
            else:
                if log_callback:
                    log_callback("✓ No se encontraron mods solo-cliente\n\n")

            # Configuración automática como en vanilla
            if not os.path.exists(self.eula_path):
                # Primera vez - generar EULA (Forge modpacks necesitan más tiempo)
                if log_callback:
                    log_callback("=== CONFIGURACIÓN INICIAL ===\n")
                    log_callback("Generando EULA (esto puede tomar hasta 2 minutos para modpacks grandes)...\n")

                # Aumentar timeout para modpacks Forge que tardan más
                timeout_eula = 90 if server_type == "forge" else 60
                self._run_modded_server_and_wait(server_type, ram_mb, java_executable, log_callback, timeout=timeout_eula, check_for="eula.txt")
                time.sleep(1)

                # Aceptar EULA
                if os.path.exists(self.eula_path):
                    if log_callback:
                        log_callback("✓ EULA generado correctamente\n")
                        log_callback("Aceptando EULA automáticamente...\n")
                    self.accept_eula()
                else:
                    if log_callback:
                        log_callback("\n❌ Error: EULA no se generó\n")
                        log_callback("   Posibles causas:\n")
                        log_callback("   • El modpack no está correctamente instalado\n")
                        log_callback("   • Falta Java o es una versión incorrecta\n")
                        log_callback("   • Los archivos del servidor están corruptos\n")
                        log_callback("   • El servidor se cerró prematuramente\n")
                    return False

                # Segunda ejecución - generar server.properties (Forge necesita más tiempo)
                if log_callback:
                    log_callback("✓ EULA aceptado\n\n")
                    log_callback("Generando archivos del servidor (esto puede tomar hasta 2 minutos)...\n")

                timeout_props = 120 if server_type == "forge" else 60
                self._run_modded_server_and_wait(server_type, ram_mb, java_executable, log_callback, timeout=timeout_props, check_for="server.properties")
                time.sleep(1)

                # Configurar server.properties
                if os.path.exists(self.properties_path):
                    if log_callback:
                        log_callback("✓ server.properties generado correctamente\n")
                        log_callback("Configurando server.properties...\n")
                    self.configure_server_properties()
                else:
                    if log_callback:
                        log_callback("⚠ Advertencia: server.properties no se generó, pero continuando...\n")

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

                command = [java_executable, ram_min, ram_max, "-jar", fabric_jar, "nogui"]

            elif server_type == "forge":
                # Forge usa archivos de argumentos (@user_jvm_args.txt, @win_args.txt)
                # Necesitamos leerlos y ejecutar Java directamente

                # Primero, modificar user_jvm_args.txt con la RAM correcta
                user_jvm_args_path = os.path.join(self.server_folder, "user_jvm_args.txt")
                if os.path.exists(user_jvm_args_path):
                    # Leer y modificar argumentos de RAM
                    with open(user_jvm_args_path, 'r', encoding='utf-8') as f:
                        jvm_args = f.read()

                    # Reemplazar argumentos de RAM
                    import re
                    jvm_args = re.sub(r'-Xmx\d+[MGmg]', f'-Xmx{ram_mb}M', jvm_args)
                    jvm_args = re.sub(r'-Xms\d+[MGmg]', f'-Xms{ram_mb}M', jvm_args)

                    with open(user_jvm_args_path, 'w', encoding='utf-8') as f:
                        f.write(jvm_args)

                # Buscar el archivo win_args.txt o unix_args.txt
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
                    if log_callback:
                        log_callback("Error: No se encontró el archivo de argumentos de Forge\n")
                    return False

                # Construir comando usando @ para archivos de argumentos
                command = [
                    java_executable,
                    f"@{user_jvm_args_path}",
                    f"@{args_file_path}",
                    "nogui"
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
                if log_callback:
                    def read_output():
                        for line in self.server_process.stdout:
                            log_callback(line)

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

            # Primera ejecución (generará eula.txt)
            if log_callback:
                log_callback("Generando EULA...\n")

            self._run_modded_server_and_wait(server_type, ram_mb, java_executable, log_callback, timeout=60, check_for="eula.txt")

            time.sleep(0.5)

            # Aceptar EULA
            if os.path.exists(self.eula_path):
                if log_callback:
                    log_callback("Aceptando EULA automáticamente...\n")
                if not self.accept_eula():
                    if log_callback:
                        log_callback("Error al aceptar EULA\n")
                    return False
            else:
                if log_callback:
                    log_callback("Archivo EULA no encontrado\n")
                return False

            # Segunda ejecución (generará archivos del servidor)
            if log_callback:
                log_callback("Generando archivos del servidor...\n")

            self._run_modded_server_and_wait(server_type, ram_mb, java_executable, log_callback, timeout=40, check_for="server.properties")

            time.sleep(0.5)

            # Modificar server.properties
            if os.path.exists(self.properties_path):
                if log_callback:
                    log_callback("Configurando server.properties...\n")
                if not self.configure_server_properties():
                    if log_callback:
                        log_callback("Error al modificar server.properties\n")
                    return False
            else:
                if log_callback:
                    log_callback("Archivo server.properties no encontrado\n")
                return False

            if log_callback:
                log_callback("¡Configuración completada!\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"Error durante la configuración: {e}\n")
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
                command = [java_executable, ram_min, ram_max, "-jar", "fabric-server-launch.jar", "nogui"]
            elif server_type == "forge":
                # Modificar user_jvm_args.txt
                user_jvm_args_path = os.path.join(self.server_folder, "user_jvm_args.txt")
                if os.path.exists(user_jvm_args_path):
                    with open(user_jvm_args_path, 'r', encoding='utf-8') as f:
                        jvm_args = f.read()
                    import re
                    jvm_args = re.sub(r'-Xmx\d+[MGmg]', f'-Xmx{ram_mb}M', jvm_args)
                    jvm_args = re.sub(r'-Xms\d+[MGmg]', f'-Xms{ram_mb}M', jvm_args)
                    with open(user_jvm_args_path, 'w', encoding='utf-8') as f:
                        f.write(jvm_args)

                # Buscar win_args.txt o unix_args.txt
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
                    command = [java_executable, f"@{user_jvm_args_path}", f"@{args_file_path}", "nogui"]
                else:
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
                        file_found = True
                        time.sleep(1)
                        process.terminate()
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        break

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
        # Lista de patrones de mods solo-cliente comunes
        CLIENT_ONLY_MOD_PATTERNS = [
            # Rendering & Graphics
            "entity_texture_features", "entity_model_features", "etf-", "emf-",
            "embeddium", "rubidium", "oculus", "iris",
            "optifine", "sodium", "phosphor", "lithium",
            "immediatelyfast",

            # Visual Effects
            "betteranimationscollection", "notenoughanimations",
            "visuality", "falling_leaves", "fallingleaves",
            "skinlayers3d", "3dskinlayers",
            "blur", "dynamiclights", "sodiumdynamiclights",
            "lambdynamiclights", "fancy_video_player",
            "presence_footsteps", "sound_physics",

            # UI & HUD
            "betterf3", "betterthirdperson", "chat_heads",
            "fancymenu", "loadingbackgrounds", "inventoryhud",
            "xaerosminimap", "xaeroworldmap", "journeymap-client",
            "bhmenu", "catalogue", "configured",
            "defaultoptions", "roughly_enough_items_client",
            "mouse_tweaks", "controlling-client",

            # Camera & Controls
            "camera", "zoomify", "justzoom", "logical_zoom",
            "better_third_person", "shoulder_surfing",

            # Client Optimization
            "lazydfu", "starlight-client", "ferrite_core-client",
            "entityculling", "memoryleakfix-client",

            # Audio
            "sound_physics_remastered", "extreme_sound_muffler",
            "audio_player", "music_triggers",

            # Client-side Utilities
            "screenshots_viewer", "screenshot_to_clipboard",
            "borderless_window", "fullscreen_windowed",
            "replay_mod", "minihud", "tweakeroo",
            "litematica", "item_scroller",

            # Shaders & Effects
            "shader", "complementary", "bsl", "sildurs",
            "seus", "kuda", "continuum",

            # Resource Pack Related
            "cit_resewn", "chime", "cem",
            "custom_entity_models", "optifabric",

            # Performance (Client-only)
            "exordium", "ksyxis", "dashloader",
            "cull_less_leaves", "enhanced_block_entities",

            # Misc Client-only
            "light_overlay", "appleskin-client",
            "torohealth", "damage_indicator",
            "inventory_tweaks", "inventory_profiles",
            "mod_menu", "fabric_api-client"
        ]

        try:
            mods_folder = os.path.join(self.server_folder, "mods")
            if not os.path.exists(mods_folder):
                return []

            # Crear carpeta para mods deshabilitados
            disabled_folder = os.path.join(self.server_folder, "mods_disabled_client")
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
