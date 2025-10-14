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

    def configure_server_properties(self) -> bool:
        """
        Modifica server.properties para establecer online-mode=false y difficulty=normal

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

                # Configurar difficulty=normal
                elif line.strip().startswith('difficulty='):
                    lines[i] = 'difficulty=normal\n'
                    difficulty_modified = True

            if not online_mode_modified or not difficulty_modified:
                print(f"Propiedades no encontradas - online-mode: {online_mode_modified}, difficulty: {difficulty_modified}")
                return False

            # Escribir el archivo modificado con encoding UTF-8
            with open(self.properties_path, 'w', encoding='utf-8', newline='\n') as file:
                file.writelines(lines)

            print("server.properties configurado: online-mode=false, difficulty=normal")
            return True

        except Exception as e:
            print(f"Error al modificar server.properties: {e}")
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
            process = subprocess.Popen(
                command,
                cwd=self.server_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
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

                self.server_process = subprocess.Popen(
                    command,
                    cwd=self.server_folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1
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

                self.server_process = subprocess.Popen(
                    command,
                    cwd=self.server_folder
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
