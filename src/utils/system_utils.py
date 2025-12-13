"""
System utilities for validation and verification
"""
import os
import time
import socket
from typing import Optional, Callable, Tuple

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️ psutil no está instalado. Algunas verificaciones estarán deshabilitadas.")


def validate_eula_file(eula_path: str) -> bool:
    """
    Validates that the EULA file has valid content

    Args:
        eula_path: Path to the eula.txt file

    Returns:
        True if the file is valid
    """
    try:
        if not os.path.exists(eula_path):
            return False

        # Check minimum size (must be at least 50 bytes)
        file_size = os.path.getsize(eula_path)
        if file_size < 50:
            print(f"⚠️ EULA demasiado pequeño: {file_size} bytes")
            return False

        # Read and verify content
        with open(eula_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Must contain "eula="
        if "eula=" not in content:
            print("⚠️ EULA no contiene 'eula='")
            return False

        return True

    except Exception as e:
        print(f"Error validando EULA: {e}")
        return False


def validate_properties_file(properties_path: str) -> bool:
    """
    Validates that server.properties has valid content

    Args:
        properties_path: Path to the server.properties file

    Returns:
        True if the file is valid
    """
    try:
        if not os.path.exists(properties_path):
            return False

        # Check minimum size (must be at least 500 bytes)
        file_size = os.path.getsize(properties_path)
        if file_size < 500:
            print(f"⚠️ server.properties demasiado pequeño: {file_size} bytes")
            return False

        # Read and verify content
        with open(properties_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Must contain key properties
        required_props = ['server-port=', 'difficulty=', 'gamemode=']
        for prop in required_props:
            if prop not in content:
                print(f"⚠️ server.properties no contiene '{prop}'")
                return False

        return True

    except Exception as e:
        print(f"Error validando server.properties: {e}")
        return False


def check_write_permissions(folder_path: str) -> Tuple[bool, str]:
    """
    Checks if we have write permissions in a folder

    Args:
        folder_path: Path to the folder

    Returns:
        (has_permissions, error_message)
    """
    try:
        # Try to create a temporary file
        test_file = os.path.join(folder_path, ".pycraft_test_write")

        with open(test_file, 'w') as f:
            f.write("test")

        os.remove(test_file)
        return (True, "")

    except PermissionError:
        return (False,
                f"No tienes permisos de escritura en:\n  {folder_path}\n\n"
                f"Sugerencia: Usa una carpeta en Documentos o Escritorio")
    except Exception as e:
        return (False, f"Error verificando permisos: {e}")


def check_available_ram() -> int:
    """
    Returns available RAM in MB

    Returns:
        Available RAM in MB, or -1 if it cannot be determined
    """
    if not PSUTIL_AVAILABLE:
        return -1

    try:
        return psutil.virtual_memory().available // (1024 * 1024)
    except Exception:
        return -1


def can_allocate_ram(required_mb: int) -> Tuple[bool, str]:
    """
    Checks if there is enough RAM for the server

    Args:
        required_mb: Required RAM in MB

    Returns:
        (can_allocate, message) - Always returns True but with warning if low RAM
    """
    available = check_available_ram()

    if available == -1:
        return (True, "")

    # Use a smaller safety margin (512MB) - just a recommendation
    safety_margin = 512
    recommended = required_mb + safety_margin

    if available < required_mb:
        # Critical: not even enough for the server
        return (True,
                f"⚠️ RAM muy baja! Disponible: {available} MB, Requerido: {required_mb} MB\n"
                f"   El servidor podría no iniciar. Cierra otros programas.\n")
    elif available < recommended:
        # Warning: enough but tight
        return (True,
                f"⚠️ RAM ajustada: {available} MB disponibles.\n"
                f"   Recomendado: {recommended} MB. El servidor debería funcionar.\n")

    return (True, f"✓ RAM OK ({available} MB disponibles)\n")


def is_port_in_use(port: int) -> bool:
    """
    Checks if a port is in use

    Args:
        port: Port number

    Returns:
        True if the port is in use
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    except Exception:
        return False


def check_minecraft_port(log_callback: Optional[Callable[[str], None]] = None) -> None:
    """
    Checks if port 25565 is occupied and warns

    Args:
        log_callback: Callback function to report messages
    """
    if is_port_in_use(25565):
        msg = ("\n⚠️ ADVERTENCIA: El puerto 25565 ya está en uso!\n"
               "  Posibles causas:\n"
               "  • Otro servidor de Minecraft está corriendo\n"
               "  • Otro programa está usando el puerto\n"
               "  Solución: Cierra el otro programa o cambia el puerto en server.properties\n")
        if log_callback:
            log_callback(msg)
        else:
            print(msg)


def show_firewall_antivirus_warning(log_callback: Optional[Callable[[str], None]] = None) -> None:
    """
    Shows a brief message directing users to the help panel

    Args:
        log_callback: Callback function to report messages
    """
    # Simplified message to avoid console spam
    msg = ("\n⚠️ IMPORTANTE: Para jugar con amigos, ve a 'Información y Ayuda' → 'Jugar con Amigos'\n")

    if log_callback:
        log_callback(msg)
    else:
        print(msg)


def cleanup_zombie_processes(log_callback: Optional[Callable[[str], None]] = None) -> None:
    """
    Cleans up zombie Java processes related to Minecraft

    Args:
        log_callback: Callback function to report messages
    """
    if not PSUTIL_AVAILABLE:
        return

    try:
        cleaned = 0
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                # Look for Java processes that are from Minecraft
                proc_info = proc.info
                if proc_info['name'] and 'java' in proc_info['name'].lower():
                    cmdline = proc_info.get('cmdline', [])
                    if cmdline and any('minecraft' in str(arg).lower() or
                                     'server.jar' in str(arg).lower() or
                                     'forge' in str(arg).lower() or
                                     'fabric' in str(arg).lower()
                                     for arg in cmdline):
                        msg = f"⚠️ Proceso zombie encontrado (PID {proc.pid}), limpiando..."
                        if log_callback:
                            log_callback(msg + "\n")
                        else:
                            print(msg)

                        proc.terminate()
                        proc.wait(timeout=5)
                        cleaned += 1

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass

        if cleaned > 0:
            msg = f"✓ {cleaned} proceso(s) zombie limpiado(s)"
            if log_callback:
                log_callback(msg + "\n")
            else:
                print(msg)

    except Exception as e:
        if log_callback:
            log_callback(f"Error limpiando procesos: {e}\n")
        else:
            print(f"Error limpiando procesos: {e}")
