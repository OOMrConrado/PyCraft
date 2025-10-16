import subprocess
import os
import time
from typing import Optional, Callable
import threading


class ServerManager:
    """Maneja la ejecución y configuración del servidor de Minecraft"""

    def __init__(self, server_folder: str):
        self.server_folder = server_folder
        self.server_jar_path = os.path.join(server_folder, "server.jar")
        self.eula_path = os.path.join(server_folder, "eula.txt")
        self.properties_path = os.path.join(server_folder, "server.properties")
        self.server_process = None

    def accept_eula(self) -> bool:
        """
        Acepta automáticamente el EULA modificando el archivo eula.txt

        Returns:
            True si se modificó correctamente, False en caso contrario
        """
        try:
            if not os.path.exists(self.eula_path):
                print("Archivo eula.txt no encontrado")
                return False

            # Leer el archivo
            with open(self.eula_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Reemplazar eula=false por eula=true
            content = content.replace('eula=false', 'eula=true')

            # Escribir el archivo modificado
            with open(self.eula_path, 'w', encoding='utf-8') as file:
                file.write(content)

            print("EULA aceptado automáticamente")
            return True

        except Exception as e:
            print(f"Error al aceptar EULA: {e}")
            return False

    def configure_server_properties(self, difficulty: str = "normal") -> bool:
        """
        Modifica server.properties para establecer online-mode=false y difficulty

        Args:
            difficulty: Dificultad del servidor (peaceful, easy, normal, hard)

        Returns:
            True si se modificó correctamente, False en caso contrario
        """
        try:
            if not os.path.exists(self.properties_path):
                print("Archivo server.properties no encontrado")
                return False

            # Leer todas las líneas del archivo
            with open(self.properties_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            # Modificar las propiedades necesarias
            online_mode_modified = False
            difficulty_modified = False

            for i, line in enumerate(lines):
                # Configurar online-mode=false
                if line.strip().startswith('online-mode='):
                    lines[i] = 'online-mode=false\n'
                    online_mode_modified = True

                # Configurar difficulty
                elif line.strip().startswith('difficulty='):
                    lines[i] = f'difficulty={difficulty}\n'
                    difficulty_modified = True

            if not online_mode_modified or not difficulty_modified:
                print(f"Propiedades no encontradas - online-mode: {online_mode_modified}, difficulty: {difficulty_modified}")
                return False

            # Escribir el archivo modificado con encoding UTF-8
            with open(self.properties_path, 'w', encoding='utf-8', newline='\n') as file:
                file.writelines(lines)

            print(f"server.properties configurado: online-mode=false, difficulty={difficulty}")
            return True

        except Exception as e:
            print(f"Error al modificar server.properties: {e}")
            return False

    def update_property(self, property_name: str, property_value: str) -> bool:
        """
        Actualiza una propiedad específica en server.properties

        Args:
            property_name: Nombre de la propiedad
            property_value: Valor de la propiedad

        Returns:
            True si se modificó correctamente, False en caso contrario
        """
        try:
            if not os.path.exists(self.properties_path):
                print("Archivo server.properties no encontrado")
                return False

            # Leer todas las líneas del archivo
            with open(self.properties_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            # Modificar la propiedad
            property_modified = False

            for i, line in enumerate(lines):
                if line.strip().startswith(f'{property_name}='):
                    lines[i] = f'{property_name}={property_value}\n'
                    property_modified = True
                    break

            if not property_modified:
                print(f"Propiedad '{property_name}' no encontrada")
                return False

            # Escribir el archivo modificado
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
        Ejecuta el servidor por primera vez y realiza toda la configuración automática

        Args:
            log_callback: Función callback para recibir logs del proceso

        Returns:
            True si todo el proceso fue exitoso, False en caso contrario
        """
        try:
            if log_callback:
                log_callback("Iniciando servidor por primera vez...\n")

            # Primera ejecución (generará eula.txt) - más rápida
            if log_callback:
                log_callback("Generando EULA...\n")

            self._run_server_and_wait(log_callback, timeout=10, check_for="eula.txt")

            # Esperar brevemente
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

            # Segunda ejecución (generará todos los archivos del servidor) - optimizada
            if log_callback:
                log_callback("Generando archivos del servidor...\n")

            self._run_server_and_wait(log_callback, timeout=30, check_for="server.properties")

            # Esperar brevemente
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
            # Comando para ejecutar el servidor
            command = ["java", "-Xmx1024M", "-Xms1024M", "-jar", "server.jar", "nogui"]

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

        except Exception as e:
            if log_callback:
                log_callback(f"Error al ejecutar servidor: {e}\n")

    def start_server(
        self,
        log_callback: Optional[Callable[[str], None]] = None,
        detached: bool = False
    ) -> bool:
        """
        Inicia el servidor de Minecraft

        Args:
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

            # Comando para ejecutar el servidor
            command = ["java", "-Xmx1024M", "-Xms1024M", "-jar", "server.jar", "nogui"]

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

        except Exception as e:
            if log_callback:
                log_callback(f"Error al iniciar servidor: {e}\n")
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
        ram_mb: int = 4096,
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
                # Primera vez - generar EULA
                if log_callback:
                    log_callback("=== CONFIGURACIÓN INICIAL ===\n")
                    log_callback("Generando EULA...\n")

                self._run_modded_server_and_wait(server_type, ram_mb, java_executable, log_callback, timeout=20, check_for="eula.txt")
                time.sleep(0.5)

                # Aceptar EULA
                if os.path.exists(self.eula_path):
                    if log_callback:
                        log_callback("Aceptando EULA automáticamente...\n")
                    self.accept_eula()
                else:
                    if log_callback:
                        log_callback("Error: EULA no se generó\n")
                    return False

                # Segunda ejecución - generar server.properties
                if log_callback:
                    log_callback("Generando archivos del servidor...\n")

                self._run_modded_server_and_wait(server_type, ram_mb, java_executable, log_callback, timeout=40, check_for="server.properties")
                time.sleep(0.5)

                # Configurar server.properties
                if os.path.exists(self.properties_path):
                    if log_callback:
                        log_callback("Configurando server.properties...\n")
                    self.configure_server_properties()

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

        except Exception as e:
            if log_callback:
                log_callback(f"Error al iniciar servidor: {e}\n")
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
        ram_mb: int = 4096,
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

            self._run_modded_server_and_wait(server_type, ram_mb, java_executable, log_callback, timeout=15, check_for="eula.txt")

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

        except Exception as e:
            if log_callback:
                log_callback(f"Error al ejecutar servidor: {e}\n")

    def get_recommended_ram_for_modpack(self, num_mods: int) -> int:
        """
        Obtiene RAM recomendada basándose en el número de mods

        Args:
            num_mods: Número de mods en el modpack

        Returns:
            RAM recomendada en MB
        """
        if num_mods < 25:
            return 3072  # 3 GB
        elif num_mods < 50:
            return 4096  # 4 GB
        elif num_mods < 100:
            return 6144  # 6 GB
        elif num_mods < 150:
            return 8192  # 8 GB
        else:
            return 10240  # 10 GB

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
