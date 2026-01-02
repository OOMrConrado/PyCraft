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

    def _patch_serverpack_script(
        self,
        script_path: str,
        java_executable: str = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Patches ServerPackCreator's start.ps1 script to fix CMD /C compatibility issues
        and inject the correct Java path.

        The original script uses 'CMD /C' to execute Java commands, which fails on some
        Windows configurations. This method replaces the problematic RunJavaCommand
        function with a direct PowerShell execution.

        Additionally, if java_executable is provided, it will override the script's
        Java detection to use the correct version (e.g., Java 17 for MC 1.20+).

        Args:
            script_path: Path to the start.ps1 script
            java_executable: Path to the Java executable to use (if None, uses script's default)
            log_callback: Optional callback for logging

        Returns:
            True if patched successfully (or no patch needed), False on error
        """
        if not os.path.exists(script_path):
            return False

        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()

            modified = False
            new_content = content

            # === JAVA PATH INJECTION ===
            # This is critical: the script's own Java detection may find the wrong version
            # (e.g., Java 8 in PATH when MC 1.20+ needs Java 17+)
            # We inject the correct Java path at the start of the script
            if java_executable and java_executable != "java":
                # Check if we already injected the Java path
                if '# PyCraft Java Override' not in content:
                    # Normalize path for PowerShell (use forward slashes or escaped backslashes)
                    java_path = java_executable.replace('\\', '/')

                    # Inject at the very beginning of the script, after any initial comments
                    # This ensures $Java is set before SetJavaBinary runs
                    java_override = f'''# PyCraft Java Override - Using correct Java version for this Minecraft version
$global:Java = "{java_path}"
$env:JAVA_HOME = Split-Path -Parent (Split-Path -Parent $global:Java)

'''
                    # Find a good insertion point (after initial comments/param blocks)
                    import re
                    # Insert after any initial param() block or at the start
                    param_match = re.search(r'^param\s*\([^)]*\)\s*\n', new_content, re.MULTILINE | re.IGNORECASE)
                    if param_match:
                        insert_pos = param_match.end()
                        new_content = new_content[:insert_pos] + java_override + new_content[insert_pos:]
                    else:
                        # Insert at start, but after any shebang or initial comments
                        lines = new_content.split('\n')
                        insert_line = 0
                        for i, line in enumerate(lines):
                            stripped = line.strip()
                            if stripped and not stripped.startswith('#'):
                                insert_line = i
                                break
                        lines.insert(insert_line, java_override.rstrip())
                        new_content = '\n'.join(lines)

                    modified = True
                    if log_callback:
                        log_callback(f"Injecting Java path: {java_executable}\n")

            # === CMD /C FIX ===
            # Check if the script has the problematic CMD /C pattern in RunJavaCommand
            if 'Function global:RunJavaCommand' in new_content and 'CMD /C' in new_content:
                # Check if already patched with our CMD /C fix
                if '$ArgsArray = $CommandToRun -split' not in new_content:
                    if log_callback:
                        log_callback("Patching start.ps1 for CMD compatibility...\n")

                    # Replace the problematic CMD /C line in RunJavaCommand with direct Java execution
                    # The issue is that CMD /C doesn't work reliably inside PowerShell on some systems
                    pattern = r'(Function global:RunJavaCommand\s*\{\s*param\s*\(\$CommandToRun\))\s*CMD /C ["`]+\$\{Java\}["`]+ \$\{CommandToRun\}["`]*'

                    replacement = r'''\1
    # Patched by PyCraft: Execute Java directly instead of via CMD /C
    $ArgsArray = $CommandToRun -split ' '
    & $Java @ArgsArray'''

                    new_content, count = re.subn(pattern, replacement, new_content, flags=re.IGNORECASE)

                    if count > 0:
                        modified = True
                        # Also fix the GetJavaVersion function that uses CMD /C
                        new_content = new_content.replace(
                            'CMD /C "`"${Java}`" -fullversion 2>&1"',
                            '(& $Java -fullversion 2>&1) -join ""'
                        )

                        # Fix the 32-bit check
                        new_content = new_content.replace(
                            'CMD /C "`"${Java}`" -version 2>&1"',
                            '(& $Java -version 2>&1) -join ""'
                        )
                    else:
                        # Try simpler string replacement as fallback
                        if 'CMD /C "`"${Java}`" ${CommandToRun}"' in new_content:
                            new_content = new_content.replace(
                                'CMD /C "`"${Java}`" ${CommandToRun}"',
                                '''# Patched by PyCraft
    $ArgsArray = $CommandToRun -split ' '
    & $Java @ArgsArray'''
                            )
                            # Also fix other CMD /C usages
                            new_content = new_content.replace(
                                'CMD /C "`"${Java}`" -fullversion 2>&1"',
                                '(& $Java -fullversion 2>&1) -join ""'
                            )
                            new_content = new_content.replace(
                                'CMD /C "`"${Java}`" -version 2>&1"',
                                '(& $Java -version 2>&1) -join ""'
                            )
                            modified = True

            # Write changes if modified
            if modified:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                if log_callback:
                    log_callback("Script patched successfully\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"Warning: Could not patch script: {e}\n")
            return True  # Continue anyway

    def _patch_serverpack_bat(
        self,
        script_path: str,
        java_executable: str = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Patches ServerPackCreator's start.bat script to use the correct Java path.

        The original script may find the wrong Java version in PATH.
        This method injects the correct Java path at the start of the script.

        Args:
            script_path: Path to the start.bat script
            java_executable: Path to the Java executable to use (if None, uses script's default)
            log_callback: Optional callback for logging

        Returns:
            True if patched successfully (or no patch needed), False on error
        """
        if not os.path.exists(script_path):
            return False

        # Only patch if we have a specific Java path to use
        if not java_executable or java_executable == "java":
            return True

        try:
            with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Check if already patched
            if 'REM PyCraft Java Override' in content:
                return True

            # Normalize path for batch (use backslashes)
            java_path = java_executable.replace('/', '\\')
            java_home = os.path.dirname(os.path.dirname(java_path))

            # Create the override block
            java_override = f'''@echo off
REM PyCraft Java Override - Using correct Java version for this Minecraft version
set "JAVA_HOME={java_home}"
set "JAVA={java_path}"
set "PATH=%JAVA_HOME%\\bin;%PATH%"

'''
            # If script starts with @echo off, replace it
            if content.strip().lower().startswith('@echo off'):
                # Find where @echo off ends
                lines = content.split('\n')
                first_line = lines[0]
                rest = '\n'.join(lines[1:])
                new_content = java_override + rest
            else:
                new_content = java_override + content

            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            if log_callback:
                log_callback(f"Injecting Java path into start.bat: {java_executable}\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"Warning: Could not patch batch script: {e}\n")
            return True  # Continue anyway

    def _find_start_script(self) -> Optional[Tuple[str, str]]:
        """
        Finds any start script in the server folder.

        Returns:
            Tuple of (script_path, script_type) where script_type is 'bat', 'ps1', or 'sh'
            or None if no script found
        """
        # Common script names used by modpacks (in order of preference)
        script_names = [
            "run",           # Modern Forge/NeoForge
            "start",         # ServerPackCreator
            "startserver",   # ATM and similar modpacks
            "launch",        # Some modpacks
            "server",        # Generic
        ]

        if os.name == 'nt':  # Windows
            # Check .bat and .ps1 files
            for name in script_names:
                for ext in [".bat", ".ps1"]:
                    script_path = os.path.join(self.server_folder, f"{name}{ext}")
                    if os.path.exists(script_path):
                        return (script_path, ext[1:])  # Remove the dot from extension
        else:  # Linux/Mac
            for name in script_names:
                script_path = os.path.join(self.server_folder, f"{name}.sh")
                if os.path.exists(script_path):
                    return (script_path, "sh")

        return None

    def detect_minecraft_version(self) -> Optional[str]:
        """
        Detects the Minecraft version from various sources.

        Checks multiple locations:
        1. modpack_info.json (created by PyCraft during install)
        2. modrinth.index.json (modpack manifest)
        3. Fabric's .fabric directory
        4. server.jar version.json
        5. Server logs

        Returns:
            Minecraft version string (e.g., "1.20.4") or None if not detected
        """
        import re

        # Return cached version if available
        if self._detected_version:
            return self._detected_version

        # Helper function to convert NeoForge version to MC version
        def neoforge_to_mc_version(neoforge_ver: str) -> Optional[str]:
            """Convert NeoForge version (e.g., 21.1.215) to MC version (e.g., 1.21.1)"""
            match = re.match(r'^(\d+)\.(\d+)\.', neoforge_ver)
            if match:
                major, minor = match.groups()
                if minor == "0":
                    return f"1.{major}"
                return f"1.{major}.{minor}"
            return None

        # Helper to validate MC version format
        def is_valid_mc_version(ver: str) -> bool:
            return bool(re.match(r'^1\.\d+(\.\d+)?$', ver))

        # Method 0: Check NeoForge installer/jar for version (most reliable for NeoForge packs)
        for file in os.listdir(self.server_folder):
            if "neoforge" in file.lower() and file.endswith(".jar"):
                # Extract version from filename like neoforge-21.1.215-installer.jar
                match = re.search(r'neoforge[_-]?(\d+\.\d+\.\d+)', file.lower())
                if match:
                    mc_ver = neoforge_to_mc_version(match.group(1))
                    if mc_ver:
                        self._detected_version = mc_ver
                        return self._detected_version

        # Method 0b: Check startserver.bat/sh for NEOFORGE_VERSION
        for script_name in ["startserver.bat", "startserver.sh"]:
            script_path = os.path.join(self.server_folder, script_name)
            if os.path.exists(script_path):
                try:
                    with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Look for NEOFORGE_VERSION=21.1.215
                        match = re.search(r'NEOFORGE_VERSION[=\s]+(\d+\.\d+\.\d+)', content)
                        if match:
                            mc_ver = neoforge_to_mc_version(match.group(1))
                            if mc_ver:
                                self._detected_version = mc_ver
                                return self._detected_version
                except Exception:
                    pass

        # Method 1: Check modpack_info.json (created by PyCraft during install)
        info_file = os.path.join(self.server_folder, "modpack_info.json")
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                mc_ver = info.get("minecraft_version")
                # Validate it's a real MC version (starts with "1.")
                if mc_ver and is_valid_mc_version(mc_ver):
                    self._detected_version = mc_ver
                    return self._detected_version
            except Exception:
                pass

        # Method 2: Check variables.txt (ServerPackCreator format by Griefed)
        variables_file = os.path.join(self.server_folder, "variables.txt")
        if os.path.exists(variables_file):
            try:
                with open(variables_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Parse MINECRAFT_VERSION=1.20.1
                    match = re.search(r'^MINECRAFT_VERSION=(.+)$', content, re.MULTILINE)
                    if match:
                        self._detected_version = match.group(1).strip()
                        return self._detected_version
            except Exception:
                pass

        # Method 3: Check modrinth.index.json (modpack manifest)
        modrinth_manifest = os.path.join(self.server_folder, "modrinth.index.json")
        if os.path.exists(modrinth_manifest):
            try:
                with open(modrinth_manifest, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                    deps = manifest.get("dependencies", {})
                    if "minecraft" in deps:
                        self._detected_version = deps["minecraft"]
                        return self._detected_version
            except Exception:
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
            except Exception:
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
            except Exception:
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
            except Exception:
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
            except Exception:
                pass

        # Method 6: Check versions directory created by Fabric
        versions_dir = os.path.join(self.server_folder, "versions")
        if os.path.exists(versions_dir):
            try:
                for folder in os.listdir(versions_dir):
                    if re.match(r'^\d+\.\d+(?:\.\d+)?$', folder):
                        self._detected_version = folder
                        return self._detected_version
            except Exception:
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
                log_callback(f"[WARN] Could not create server.properties: {e}\n")
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
                log_callback(f"[ERROR] Error verifying/accepting EULA: {e}\n")
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
                success_msg = f"[OK] Configuración actualizada:\n  -Dificultad cambiada de '{old_difficulty}' a '{difficulty}'"
            else:
                success_msg = f"[OK] Configuración aplicada:\n  -Dificultad: {difficulty}"

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
            error_msg = f"Error modifying server.properties: {e}"
            print(error_msg)
            if log_callback:
                log_callback(error_msg + "\n")
            return False

    def set_online_mode(self, online_mode: bool = False, log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Sets online-mode in server.properties.

        Args:
            online_mode: True for online mode (requires Mojang auth), False for offline mode
            log_callback: Callback function to report status

        Returns:
            True if modified successfully, False otherwise
        """
        try:
            if not os.path.exists(self.properties_path):
                # server.properties doesn't exist yet, will be created on first server run
                return True

            with open(self.properties_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            mode_value = 'true' if online_mode else 'false'
            modified = False

            for i, line in enumerate(lines):
                if line.strip().startswith('online-mode='):
                    current_value = line.strip().split('=')[1]
                    if current_value != mode_value:
                        lines[i] = f'online-mode={mode_value}\n'
                        modified = True
                    break
            else:
                # Property not found, add it
                lines.append(f'online-mode={mode_value}\n')
                modified = True

            if modified:
                with open(self.properties_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.writelines(lines)
                if log_callback:
                    log_callback(f"[OK] online-mode set to {mode_value}\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"Warning: Could not set online-mode: {e}\n")
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
            print(f"Error reading property: {e}")
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
            print(f"Error updating property: {e}")
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
                    log_callback(f"\n[ERROR] {perm_msg}\n")
                return False

            if log_callback:
                log_callback("[OK] Permisos de escritura confirmados\n\n")

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
                    log_callback("\n[ERROR] EULA no se generó correctamente o está corrupto\n")
                    log_callback("   Posibles causas:\n")
                    log_callback("   -Java no se ejecutó correctamente\n")
                    log_callback("   -El proceso se interrumpió\n")
                    log_callback("   -Problemas de permisos\n")
                return False

            # 6. Accept EULA
            if os.path.exists(self.eula_path):
                if log_callback:
                    log_callback("[OK] EULA generado correctamente\n")
                    log_callback("Aceptando EULA automáticamente...\n")
                if not self.accept_eula():
                    if log_callback:
                        log_callback("[ERROR] Error accepting EULA\n")
                    return False
            else:
                if log_callback:
                    log_callback("[ERROR] Archivo EULA no encontrado\n")
                return False

            # 7. Second execution (will generate all server files) - Increased timeout to 40s
            if log_callback:
                log_callback("[OK] EULA aceptado\n\n")
                log_callback("Generando archivos del servidor (esto puede tomar hasta 40 segundos)...\n")

            self._run_server_and_wait(log_callback, timeout=40, check_for="server.properties")

            # Wait briefly
            time.sleep(0.5)

            # 8. Validate server.properties file
            if not system_utils.validate_properties_file(self.properties_path):
                if log_callback:
                    log_callback("\n[ERROR] server.properties no se generó correctamente o está corrupto\n")
                    log_callback("   Posibles causas:\n")
                    log_callback("   -El servidor no tuvo tiempo suficiente para inicializar\n")
                    log_callback("   -Versión de Minecraft incompatible\n")
                    log_callback("   -Problemas de permisos\n")
                return False

            # 9. Modify server.properties
            if os.path.exists(self.properties_path):
                if log_callback:
                    log_callback("[OK] server.properties generado correctamente\n")
                    log_callback("Configurando server.properties...\n")
                if not self.configure_server_properties(log_callback=log_callback):
                    if log_callback:
                        log_callback("[ERROR] Error modifying server.properties\n")
                    return False
            else:
                if log_callback:
                    log_callback("[ERROR] Archivo server.properties no encontrado\n")
                return False

            # 10. Configuration complete
            if log_callback:
                log_callback("\n[OK] ¡Configuración completada exitosamente!\n\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"\n[ERROR] Error durante la configuración: {e}\n")
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
                log_callback("Make sure Java is installed correctly.\n")
        except PermissionError as e:
            if log_callback:
                log_callback(f"\n✗ Error de permisos al ejecutar el servidor: {e}\n")
        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error running server: {e}\n")
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

            # NOTE: Client-only mods detection/removal is now handled by main_window.py
            # with user choice (Continue/Remove). Don't auto-remove here.

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
                    # Patch the batch script to use correct Java
                    self._patch_serverpack_bat(run_bat, self.java_executable, log_callback)
                    command = [run_bat]
                    use_shell = True
                    if log_callback:
                        log_callback("Using run.bat to start server...\n")
                elif os.path.exists(start_bat):
                    # Patch the batch script to use correct Java
                    self._patch_serverpack_bat(start_bat, self.java_executable, log_callback)
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
                    except Exception:
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
                log_callback("Make sure Java is installed correctly.\n")
            return False
        except PermissionError as e:
            if log_callback:
                log_callback(f"\n✗ Error de permisos al iniciar el servidor: {e}\n")
            return False
        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error starting server: {e}\n")
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
                pid = self.server_process.pid

                # First, send "stop" command for graceful Minecraft shutdown
                if self.server_process.stdin:
                    try:
                        self.server_process.stdin.write("stop\n")
                        self.server_process.stdin.flush()
                    except (OSError, BrokenPipeError):
                        pass

                # Give Minecraft a moment to save and shutdown gracefully
                import time
                time.sleep(2)

                # Now kill the ENTIRE process tree to prevent restart scripts
                # This is necessary because some modpacks use scripts with auto-restart loops
                try:
                    import psutil
                    try:
                        parent = psutil.Process(pid)
                        # Get all children BEFORE killing anything
                        children = parent.children(recursive=True)

                        # Kill children first (Java process)
                        for child in children:
                            try:
                                child.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass

                        # Then kill parent (script/cmd)
                        try:
                            parent.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                        # Wait for all to terminate
                        psutil.wait_procs(children + [parent], timeout=5)

                    except psutil.NoSuchProcess:
                        # Process already dead
                        pass

                except ImportError:
                    # psutil not available, use basic approach
                    self.server_process.terminate()
                    try:
                        self.server_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.server_process.kill()
                        try:
                            self.server_process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            # On Windows, try taskkill for the whole tree
                            if os.name == 'nt':
                                try:
                                    subprocess.run(
                                        ['taskkill', '/F', '/T', '/PID', str(pid)],
                                        capture_output=True,
                                        timeout=10
                                    )
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
            print(f"Error stopping server: {e}")
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
            print(f"Error sending command: {e}")
            return False

    # ==================== SOPORTE PARA MODPACKS ====================

    def detect_server_type(self) -> str:
        """
        Detecta el tipo de servidor (vanilla, forge, fabric, neoforge, quilt)

        Returns:
            "vanilla", "forge", "fabric", "neoforge", "quilt", o "unknown"
        """
        # First do a quick check for NeoForge files (takes precedence over modpack_info.json
        # because some modpacks incorrectly report "forge" when they're actually NeoForge)
        for file in os.listdir(self.server_folder):
            if "neoforge" in file.lower() and file.endswith(".jar"):
                return "neoforge"

        # Also check startserver.bat/sh for NeoForge references
        for script_name in ["startserver.bat", "startserver.sh"]:
            script_path = os.path.join(self.server_folder, script_name)
            if os.path.exists(script_path):
                try:
                    with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        if 'neoforge' in content:
                            return "neoforge"
                except Exception:
                    pass

        # Check modpack_info.json (created by PyCraft during install)
        info_file = os.path.join(self.server_folder, "modpack_info.json")
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                loader = info.get("loader")
                if loader:
                    loader_lower = loader.lower()
                    if loader_lower in ["forge", "fabric", "neoforge", "quilt"]:
                        return loader_lower
            except Exception:
                pass

        # Check variables.txt (ServerPackCreator format by Griefed)
        variables_file = os.path.join(self.server_folder, "variables.txt")
        if os.path.exists(variables_file):
            try:
                with open(variables_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Parse MODLOADER=Forge
                    import re
                    match = re.search(r'^MODLOADER=(.+)$', content, re.MULTILINE)
                    if match:
                        loader = match.group(1).strip().lower()
                        if loader in ["forge", "fabric", "neoforge", "quilt"]:
                            return loader
            except Exception:
                pass

        # Verificar si es Quilt
        for file in os.listdir(self.server_folder):
            if file.startswith("quilt-server") and file.endswith(".jar"):
                return "quilt"

        # Verificar si es Fabric (check both naming conventions)
        for fabric_name in ["fabric-server-launcher.jar", "fabric-server-launch.jar"]:
            fabric_launcher = os.path.join(self.server_folder, fabric_name)
            if os.path.exists(fabric_launcher):
                return "fabric"

        # Verificar NeoForge (check libraries folder for neoforge)
        neoforge_libs = os.path.join(self.server_folder, "libraries", "net", "neoforged")
        if os.path.exists(neoforge_libs):
            return "neoforge"

        # Buscar archivos neoforge-*.jar
        for file in os.listdir(self.server_folder):
            if "neoforge" in file.lower() and file.endswith(".jar"):
                return "neoforge"

        # Check Forge libraries folder (used by modern Forge server packs)
        forge_libs = os.path.join(self.server_folder, "libraries", "net", "minecraftforge", "forge")
        if os.path.exists(forge_libs):
            return "forge"

        # Verificar si es Forge (buscar archivos run.bat/run.sh o forge jar)
        run_bat = os.path.join(self.server_folder, "run.bat")
        run_sh = os.path.join(self.server_folder, "run.sh")

        if os.path.exists(run_bat) or os.path.exists(run_sh):
            # Check if it's actually NeoForge by reading the file
            try:
                run_file = run_bat if os.path.exists(run_bat) else run_sh
                with open(run_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if 'neoforge' in content:
                        return "neoforge"
            except Exception:
                pass
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
        Inicia un servidor con mods (Forge, Fabric, NeoForge o Quilt)

        Args:
            server_type: "forge", "fabric", "neoforge", o "quilt"
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

            # NOTE: Client-only mods detection/removal is now handled by main_window.py
            # with user choice (Continue/Remove). Don't auto-remove here.

            # === PRE-EMPTIVE EULA ACCEPTANCE ===
            # Accept EULA BEFORE starting the server - this allows the server to
            # start and generate server.properties in a SINGLE run (no restart needed)
            if log_callback:
                log_callback("=== CONFIGURACIÓN INICIAL ===\n")

            if not self.ensure_eula_accepted(log_callback):
                if log_callback:
                    log_callback("\n[ERROR] Error: Could not accept the EULA\n")
                return False

            if log_callback:
                log_callback("[OK] Configuración completada\n\n")

            ram_min = f"-Xms{ram_mb}M"
            ram_max = f"-Xmx{ram_mb}M"

            if server_type == "fabric":
                # Fabric uses fabric-server-launcher.jar (or fabric-server-launch.jar in older versions)
                fabric_jar = None
                fabric_jar_path = None

                # Check for common Fabric jar names
                for jar_name in ["fabric-server-launcher.jar", "fabric-server-launch.jar"]:
                    jar_path = os.path.join(self.server_folder, jar_name)
                    if os.path.exists(jar_path):
                        fabric_jar = jar_name
                        fabric_jar_path = jar_path
                        break

                if fabric_jar_path:
                    # Found Fabric jar - use it directly
                    command = [java_executable, ram_min, ram_max, "-Djava.awt.headless=true", "-jar", fabric_jar, "nogui"]
                else:
                    # No Fabric jar found - try to install it automatically
                    # This avoids using problematic .bat/.ps1 scripts from ServerPackCreator
                    if log_callback:
                        log_callback("Fabric server jar not found. Installing Fabric...\n")

                    # Try to get MC version and Fabric version from variables.txt first
                    mc_version = None
                    fabric_version = None
                    variables_file = os.path.join(self.server_folder, "variables.txt")

                    if os.path.exists(variables_file):
                        try:
                            with open(variables_file, 'r', encoding='utf-8') as f:
                                for line in f:
                                    line = line.strip()
                                    if line.startswith('MINECRAFT_VERSION='):
                                        mc_version = line.split('=', 1)[1].strip().strip('"')
                                    elif line.startswith('MODLOADER_VERSION='):
                                        fabric_version = line.split('=', 1)[1].strip().strip('"')
                            if mc_version and log_callback:
                                log_callback(f"Detected from variables.txt: MC {mc_version}, Fabric {fabric_version}\n")
                        except Exception as e:
                            if log_callback:
                                log_callback(f"Warning: Could not read variables.txt: {e}\n")

                    # Fallback to other detection methods
                    if not mc_version:
                        mc_version = self.detect_minecraft_version()

                    if mc_version:
                        try:
                            from ..loader.loader_manager import LoaderManager
                            loader_mgr = LoaderManager()

                            # Install Fabric with specific version if we have it
                            if loader_mgr.install_fabric(mc_version, self.server_folder, java_executable,
                                                        loader_version=fabric_version, log_callback=log_callback):
                                # Check which jar was created
                                for jar_name in ["fabric-server-launcher.jar", "fabric-server-launch.jar"]:
                                    if os.path.exists(os.path.join(self.server_folder, jar_name)):
                                        fabric_jar = jar_name
                                        break
                                else:
                                    fabric_jar = "fabric-server-launcher.jar"

                                command = [java_executable, ram_min, ram_max, "-Djava.awt.headless=true", "-jar", fabric_jar, "nogui"]
                                if log_callback:
                                    log_callback(f"Fabric installed successfully. Using {fabric_jar}\n")
                            else:
                                if log_callback:
                                    log_callback("Error: Could not install Fabric automatically\n")
                                return False
                        except Exception as e:
                            if log_callback:
                                log_callback(f"Error installing Fabric: {e}\n")
                            return False
                    else:
                        if log_callback:
                            log_callback("Error: Could not detect Minecraft version for Fabric installation\n")
                        return False

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
                    # Fallback 1: Try to find forge jar directly
                    if log_callback:
                        log_callback("Warning: Forge args file not found, trying fallback...\n")
                    import glob
                    forge_jars = glob.glob(os.path.join(self.server_folder, "forge-*.jar"))
                    if forge_jars:
                        forge_jar = os.path.basename(forge_jars[0])
                        command = [java_executable, f"-Xms{ram_mb}M", f"-Xmx{ram_mb}M", "-Djava.awt.headless=true", "-jar", forge_jar, "nogui"]
                    else:
                        # Fallback 2: Check for ServerPackCreator format or other modpack formats
                        # Instead of running their buggy scripts, we run Java directly
                        variables_file = os.path.join(self.server_folder, "variables.txt")
                        server_jar = os.path.join(self.server_folder, "server.jar")
                        run_jar = os.path.join(self.server_folder, "run.jar")

                        # Try to find a runnable jar
                        jar_to_run = None
                        if os.path.exists(server_jar):
                            jar_to_run = "server.jar"
                        elif os.path.exists(run_jar):
                            jar_to_run = "run.jar"

                        if jar_to_run:
                            if log_callback:
                                log_callback(f"Using {jar_to_run} directly...\n")

                            # Read variables.txt to get modloader info if available
                            modloader_version = None
                            mc_version = None
                            if os.path.exists(variables_file):
                                try:
                                    with open(variables_file, 'r', encoding='utf-8') as f:
                                        for line in f:
                                            if line.startswith('MODLOADER_VERSION='):
                                                modloader_version = line.split('=', 1)[1].strip().strip('"')
                                            elif line.startswith('MINECRAFT_VERSION='):
                                                mc_version = line.split('=', 1)[1].strip().strip('"')
                                except Exception:
                                    pass

                            # Build command - server.jar from NeoForge/Forge handles everything
                            command = [
                                java_executable,
                                f"-Xms{ram_mb}M",
                                f"-Xmx{ram_mb}M",
                                "-Djava.awt.headless=true",
                            ]

                            # Add user_jvm_args.txt if it exists
                            user_jvm_args = os.path.join(self.server_folder, "user_jvm_args.txt")
                            if os.path.exists(user_jvm_args):
                                command.append(f"@user_jvm_args.txt")

                            command.extend(["-jar", jar_to_run])

                            # Add installer args if needed for first run
                            if modloader_version and mc_version:
                                installer_url = f"https://files.minecraftforge.net/maven/net/minecraftforge/forge/{mc_version}-{modloader_version}/forge-{mc_version}-{modloader_version}-installer.jar"
                                command.extend(["--installer-force", "--installer", installer_url])

                            command.append("nogui")

                            if log_callback:
                                log_callback(f"Java: {java_executable}\n")

                        else:
                            # No jar found, check for start scripts as last resort
                            start_bat = os.path.join(self.server_folder, "start.bat")
                            start_ps1 = os.path.join(self.server_folder, "start.ps1")
                            start_sh = os.path.join(self.server_folder, "start.sh")

                            if os.name == 'nt':
                                # Run PowerShell script directly with full path (avoids PATH issues)
                                if os.path.exists(start_ps1):
                                    powershell_path = os.path.join(
                                        os.environ.get('SystemRoot', 'C:\\Windows'),
                                        'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe'
                                    )
                                    if os.path.exists(powershell_path):
                                        # Patch the script to fix CMD /C compatibility issues AND inject correct Java path
                                        self._patch_serverpack_script(start_ps1, java_executable, log_callback)
                                        if log_callback:
                                            log_callback("Using start.ps1 with PowerShell...\n")
                                        command = [powershell_path, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", start_ps1]
                                    elif os.path.exists(start_bat):
                                        # Patch the batch script to use correct Java
                                        self._patch_serverpack_bat(start_bat, java_executable, log_callback)
                                        if log_callback:
                                            log_callback("Using start.bat...\n")
                                        command = ["cmd", "/c", start_bat]
                                    else:
                                        if log_callback:
                                            log_callback("Error: PowerShell not found\n")
                                        return False
                                elif os.path.exists(start_bat):
                                    # Patch the batch script to use correct Java
                                    self._patch_serverpack_bat(start_bat, java_executable, log_callback)
                                    if log_callback:
                                        log_callback("Using start.bat...\n")
                                    command = ["cmd", "/c", start_bat]
                                else:
                                    if log_callback:
                                        log_callback("Error: No server files found. Try running the modpack installer first.\n")
                                    return False
                            elif os.path.exists(start_sh):
                                if log_callback:
                                    log_callback("Using start.sh...\n")
                                command = ["bash", start_sh]
                            else:
                                if log_callback:
                                    log_callback("Error: No server files found. Try running the modpack installer first.\n")
                                return False
                else:
                    # Add nogui to the args file if not present
                    try:
                        with open(args_file_path, 'r', encoding='utf-8') as f:
                            args_content = f.read()
                        if 'nogui' not in args_content.lower():
                            with open(args_file_path, 'a', encoding='utf-8') as f:
                                f.write('\nnogui\n')
                    except Exception:
                        pass

                    # Build command using @ for argument files
                    command = [
                        java_executable,
                        f"@{user_jvm_args_path}",
                        f"@{args_file_path}"
                    ]

            elif server_type == "neoforge":
                # NeoForge uses similar structure to modern Forge
                # Check for libraries/net/neoforged/neoforge/ folder

                user_jvm_args_path = os.path.join(self.server_folder, "user_jvm_args.txt")

                # Create or update user_jvm_args.txt
                if not os.path.exists(user_jvm_args_path):
                    with open(user_jvm_args_path, 'w', encoding='utf-8') as f:
                        f.write(f"-Djava.awt.headless=true\n-Xms{ram_mb}M\n-Xmx{ram_mb}M\n")
                else:
                    with open(user_jvm_args_path, 'r', encoding='utf-8') as f:
                        jvm_args = f.read()

                    import re
                    jvm_args = re.sub(r'-Xmx\d+[MGmg]', f'-Xmx{ram_mb}M', jvm_args)
                    jvm_args = re.sub(r'-Xms\d+[MGmg]', f'-Xms{ram_mb}M', jvm_args)

                    if '-Djava.awt.headless=true' not in jvm_args:
                        jvm_args = '-Djava.awt.headless=true\n' + jvm_args

                    with open(user_jvm_args_path, 'w', encoding='utf-8') as f:
                        f.write(jvm_args)

                # Find NeoForge args file
                neoforge_path = os.path.join(self.server_folder, "libraries", "net", "neoforged", "neoforge")
                args_file_path = None

                if os.path.exists(neoforge_path):
                    for version_folder in os.listdir(neoforge_path):
                        version_path = os.path.join(neoforge_path, version_folder)
                        if os.path.isdir(version_path):
                            args_file = "win_args.txt" if os.name == 'nt' else "unix_args.txt"
                            potential_path = os.path.join(version_path, args_file)
                            if os.path.exists(potential_path):
                                args_file_path = potential_path
                                break

                if args_file_path:
                    # Add nogui if not present
                    try:
                        with open(args_file_path, 'r', encoding='utf-8') as f:
                            args_content = f.read()
                        if 'nogui' not in args_content.lower():
                            with open(args_file_path, 'a', encoding='utf-8') as f:
                                f.write('\nnogui\n')
                    except Exception:
                        pass

                    command = [
                        java_executable,
                        f"@{user_jvm_args_path}",
                        f"@{args_file_path}"
                    ]
                else:
                    # Fallback: Check for run.bat/run.sh, start.bat/start.sh, or startserver.bat/startserver.sh
                    run_bat = os.path.join(self.server_folder, "run.bat")
                    run_sh = os.path.join(self.server_folder, "run.sh")
                    start_bat = os.path.join(self.server_folder, "start.bat")
                    start_sh = os.path.join(self.server_folder, "start.sh")
                    startserver_bat = os.path.join(self.server_folder, "startserver.bat")
                    startserver_sh = os.path.join(self.server_folder, "startserver.sh")

                    if os.name == 'nt':
                        if os.path.exists(run_bat):
                            # Patch the batch script to use correct Java
                            self._patch_serverpack_bat(run_bat, java_executable, log_callback)
                            if log_callback:
                                log_callback("Using run.bat for NeoForge...\n")
                            command = ["cmd", "/c", run_bat]
                        elif os.path.exists(start_bat):
                            # Patch the batch script to use correct Java
                            self._patch_serverpack_bat(start_bat, java_executable, log_callback)
                            if log_callback:
                                log_callback("Using start.bat for NeoForge...\n")
                            command = ["cmd", "/c", start_bat]
                        elif os.path.exists(startserver_bat):
                            # ATM and similar modpacks use startserver.bat
                            self._patch_serverpack_bat(startserver_bat, java_executable, log_callback)
                            if log_callback:
                                log_callback("Using startserver.bat for NeoForge...\n")
                            command = ["cmd", "/c", startserver_bat]
                        else:
                            if log_callback:
                                log_callback("Error: No NeoForge server files found\n")
                            return False
                    else:
                        if os.path.exists(run_sh):
                            if log_callback:
                                log_callback("Using run.sh for NeoForge...\n")
                            command = ["bash", run_sh]
                        elif os.path.exists(start_sh):
                            if log_callback:
                                log_callback("Using start.sh for NeoForge...\n")
                            command = ["bash", start_sh]
                        elif os.path.exists(startserver_sh):
                            if log_callback:
                                log_callback("Using startserver.sh for NeoForge...\n")
                            command = ["bash", startserver_sh]
                        else:
                            if log_callback:
                                log_callback("Error: No NeoForge server files found\n")
                            return False

            elif server_type == "quilt":
                # Quilt uses quilt-server-launch.jar (similar to Fabric)
                quilt_jar = "quilt-server-launch.jar"
                quilt_jar_path = os.path.join(self.server_folder, quilt_jar)

                if os.path.exists(quilt_jar_path):
                    command = [java_executable, ram_min, ram_max, "-Djava.awt.headless=true", "-jar", quilt_jar, "nogui"]
                else:
                    # Fallback: Check for start scripts or other quilt jars
                    start_bat = os.path.join(self.server_folder, "start.bat")
                    start_sh = os.path.join(self.server_folder, "start.sh")

                    # Also check for quilt-server-*.jar pattern
                    import glob
                    quilt_jars = glob.glob(os.path.join(self.server_folder, "quilt-server-*.jar"))

                    if quilt_jars:
                        quilt_jar = os.path.basename(quilt_jars[0])
                        if log_callback:
                            log_callback(f"Using {quilt_jar}...\n")
                        command = [java_executable, ram_min, ram_max, "-Djava.awt.headless=true", "-jar", quilt_jar, "nogui"]
                    elif os.name == 'nt' and os.path.exists(start_bat):
                        # Patch the batch script to use correct Java
                        self._patch_serverpack_bat(start_bat, java_executable, log_callback)
                        if log_callback:
                            log_callback("Using start.bat for Quilt...\n")
                        command = ["cmd", "/c", start_bat]
                    elif os.path.exists(start_sh):
                        if log_callback:
                            log_callback("Using start.sh for Quilt...\n")
                        command = ["bash", start_sh]
                    else:
                        if log_callback:
                            log_callback(f"Error: {quilt_jar} not found\n")
                        return False

            else:
                if log_callback:
                    log_callback(f"Error: Server type '{server_type}' not supported\n")
                return False

            if detached:
                if log_callback:
                    log_callback(f"Iniciando servidor {server_type} en segundo plano...\n")
                    log_callback(f"RAM asignada: {ram_mb} MB\n")

                # Configurar flags para Windows (evitar ventana CMD extra)
                creation_flags = 0
                env = os.environ.copy()
                if os.name == 'nt':  # Windows
                    creation_flags = subprocess.CREATE_NO_WINDOW
                    # Ensure System32 is in PATH for PowerShell scripts that call CMD
                    system32 = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32')
                    if system32 not in env.get('PATH', ''):
                        env['PATH'] = system32 + ';' + env.get('PATH', '')

                # Set JAVA_HOME and prepend Java to PATH to ensure correct version is used
                # This is critical when scripts (start.ps1, start.bat) search for Java
                if java_executable and java_executable != "java":
                    java_bin_dir = os.path.dirname(java_executable)
                    java_home = os.path.dirname(java_bin_dir)
                    env['JAVA_HOME'] = java_home
                    env['JAVA'] = java_executable
                    # Prepend Java bin to PATH so it's found first
                    env['PATH'] = java_bin_dir + os.pathsep + env.get('PATH', '')

                self.server_process = subprocess.Popen(
                    command,
                    cwd=self.server_folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    creationflags=creation_flags,
                    env=env
                )

                # Leer logs en un hilo separado
                def read_output():
                    try:
                        if log_callback and self.server_process and self.server_process.stdout:
                            for line in self.server_process.stdout:
                                log_callback(line)
                    except Exception:
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
                env = os.environ.copy()
                if os.name == 'nt':
                    creation_flags = subprocess.CREATE_NO_WINDOW
                    # Ensure System32 is in PATH for PowerShell scripts that call CMD
                    system32 = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32')
                    if system32 not in env.get('PATH', ''):
                        env['PATH'] = system32 + ';' + env.get('PATH', '')

                # Set JAVA_HOME and prepend Java to PATH to ensure correct version is used
                if java_executable and java_executable != "java":
                    java_bin_dir = os.path.dirname(java_executable)
                    java_home = os.path.dirname(java_bin_dir)
                    env['JAVA_HOME'] = java_home
                    env['JAVA'] = java_executable
                    env['PATH'] = java_bin_dir + os.pathsep + env.get('PATH', '')

                self.server_process = subprocess.Popen(
                    command,
                    cwd=self.server_folder,
                    creationflags=creation_flags,
                    env=env
                )
                self.server_process.wait()
                return True

        except FileNotFoundError as e:
            if log_callback:
                log_callback(f"\n✗ Error: Executable not found.\n")
                log_callback(f"Details: {e}\n")
                if java_executable and java_executable != "java":
                    log_callback(f"Java path: {java_executable}\n")
                log_callback("Make sure Java and required tools are installed correctly.\n")
            return False
        except PermissionError as e:
            if log_callback:
                log_callback(f"\n✗ Error de permisos al iniciar el servidor: {e}\n")
            return False
        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error starting server: {e}\n")
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
            print(f"Error modifying script: {e}")

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
                    log_callback("[ERROR] Error accepting EULA\n")
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
                    log_callback("[OK] server.properties generado\n")
                    log_callback("Configurando server.properties...\n")
                if not self.configure_server_properties():
                    if log_callback:
                        log_callback("⚠ Error modifying server.properties (continuando)\n")
            else:
                if log_callback:
                    log_callback("⚠ server.properties no encontrado (se generará al iniciar)\n")

            if log_callback:
                log_callback("[OK] ¡Configuración completada!\n")

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"[ERROR] Error durante la configuración: {e}\n")
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
            server_type: "forge", "fabric", "neoforge", or "quilt"
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
                # Check for common Fabric jar names
                fabric_jar = None
                fabric_jar_path = None
                for jar_name in ["fabric-server-launcher.jar", "fabric-server-launch.jar"]:
                    jar_path = os.path.join(self.server_folder, jar_name)
                    if os.path.exists(jar_path):
                        fabric_jar = jar_name
                        fabric_jar_path = jar_path
                        break

                if fabric_jar_path:
                    command = [java_executable, ram_min, ram_max, "-Djava.awt.headless=true", "-jar", fabric_jar, "nogui"]
                else:
                    # No Fabric jar found - install it automatically
                    if log_callback:
                        log_callback("Fabric server jar not found. Installing Fabric...\n")

                    # Try to get MC version and Fabric version from variables.txt
                    mc_version = None
                    fabric_version = None
                    variables_file = os.path.join(self.server_folder, "variables.txt")

                    if os.path.exists(variables_file):
                        try:
                            with open(variables_file, 'r', encoding='utf-8') as f:
                                for line in f:
                                    line = line.strip()
                                    if line.startswith('MINECRAFT_VERSION='):
                                        mc_version = line.split('=', 1)[1].strip().strip('"')
                                    elif line.startswith('MODLOADER_VERSION='):
                                        fabric_version = line.split('=', 1)[1].strip().strip('"')
                            if mc_version and log_callback:
                                log_callback(f"Detected from variables.txt: MC {mc_version}, Fabric {fabric_version}\n")
                        except Exception:
                            pass

                    if not mc_version:
                        mc_version = self.detect_minecraft_version()

                    if mc_version:
                        try:
                            from ..loader.loader_manager import LoaderManager
                            loader_mgr = LoaderManager()
                            if loader_mgr.install_fabric(mc_version, self.server_folder, java_executable,
                                                        loader_version=fabric_version, log_callback=log_callback):
                                for jar_name in ["fabric-server-launcher.jar", "fabric-server-launch.jar"]:
                                    if os.path.exists(os.path.join(self.server_folder, jar_name)):
                                        fabric_jar = jar_name
                                        break
                                else:
                                    fabric_jar = "fabric-server-launcher.jar"
                                command = [java_executable, ram_min, ram_max, "-Djava.awt.headless=true", "-jar", fabric_jar, "nogui"]
                                if log_callback:
                                    log_callback(f"Fabric installed successfully. Using {fabric_jar}\n")
                            else:
                                if log_callback:
                                    log_callback("Error: Could not install Fabric\n")
                                return
                        except Exception as e:
                            if log_callback:
                                log_callback(f"Error installing Fabric: {e}\n")
                            return
                    else:
                        if log_callback:
                            log_callback("Error: Could not detect Minecraft version\n")
                        return

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
                    except Exception:
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

            elif server_type == "neoforge":
                # NeoForge - similar to Forge
                user_jvm_args_path = os.path.join(self.server_folder, "user_jvm_args.txt")

                if not os.path.exists(user_jvm_args_path):
                    with open(user_jvm_args_path, 'w', encoding='utf-8') as f:
                        f.write(f"-Djava.awt.headless=true\n-Xms{ram_mb}M\n-Xmx{ram_mb}M\n")
                else:
                    with open(user_jvm_args_path, 'r', encoding='utf-8') as f:
                        jvm_args = f.read()
                    import re
                    jvm_args = re.sub(r'-Xmx\d+[MGmg]', f'-Xmx{ram_mb}M', jvm_args)
                    jvm_args = re.sub(r'-Xms\d+[MGmg]', f'-Xms{ram_mb}M', jvm_args)
                    if '-Djava.awt.headless=true' not in jvm_args:
                        jvm_args = '-Djava.awt.headless=true\n' + jvm_args
                    with open(user_jvm_args_path, 'w', encoding='utf-8') as f:
                        f.write(jvm_args)

                neoforge_path = os.path.join(self.server_folder, "libraries", "net", "neoforged", "neoforge")
                args_file_path = None

                if os.path.exists(neoforge_path):
                    for version_folder in os.listdir(neoforge_path):
                        version_path = os.path.join(neoforge_path, version_folder)
                        if os.path.isdir(version_path):
                            args_file = "win_args.txt" if os.name == 'nt' else "unix_args.txt"
                            potential_path = os.path.join(version_path, args_file)
                            if os.path.exists(potential_path):
                                args_file_path = potential_path
                                break

                if args_file_path:
                    try:
                        with open(args_file_path, 'r', encoding='utf-8') as f:
                            args_content = f.read()
                        if 'nogui' not in args_content.lower():
                            with open(args_file_path, 'a', encoding='utf-8') as f:
                                f.write('\nnogui\n')
                    except Exception:
                        pass
                    command = [java_executable, f"@{user_jvm_args_path}", f"@{args_file_path}"]
                else:
                    # Fallback to scripts
                    run_bat = os.path.join(self.server_folder, "run.bat")
                    run_sh = os.path.join(self.server_folder, "run.sh")
                    if os.name == 'nt' and os.path.exists(run_bat):
                        # Patch the batch script to use correct Java
                        self._patch_serverpack_bat(run_bat, java_executable, log_callback)
                        command = ["cmd", "/c", run_bat]
                    elif os.path.exists(run_sh):
                        command = ["bash", run_sh]
                    else:
                        if log_callback:
                            log_callback("Error: No NeoForge server files found\n")
                        return

            elif server_type == "quilt":
                # Quilt - similar to Fabric
                quilt_jar = "quilt-server-launch.jar"
                quilt_jar_path = os.path.join(self.server_folder, quilt_jar)

                if os.path.exists(quilt_jar_path):
                    command = [java_executable, ram_min, ram_max, "-Djava.awt.headless=true", "-jar", quilt_jar, "nogui"]
                else:
                    import glob
                    quilt_jars = glob.glob(os.path.join(self.server_folder, "quilt-server-*.jar"))
                    if quilt_jars:
                        quilt_jar = os.path.basename(quilt_jars[0])
                        command = [java_executable, ram_min, ram_max, "-Djava.awt.headless=true", "-jar", quilt_jar, "nogui"]
                    else:
                        start_bat = os.path.join(self.server_folder, "start.bat")
                        start_sh = os.path.join(self.server_folder, "start.sh")
                        if os.name == 'nt' and os.path.exists(start_bat):
                            # Patch the batch script to use correct Java
                            self._patch_serverpack_bat(start_bat, java_executable, log_callback)
                            command = ["cmd", "/c", start_bat]
                        elif os.path.exists(start_sh):
                            command = ["bash", start_sh]
                        else:
                            if log_callback:
                                log_callback(f"Error: {quilt_jar} not found\n")
                            return

            else:
                return

            # Configurar flags para Windows
            creation_flags = 0
            env = os.environ.copy()
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NO_WINDOW
                # Ensure System32 is in PATH
                system32 = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32')
                if system32 not in env.get('PATH', ''):
                    env['PATH'] = system32 + ';' + env.get('PATH', '')

            # Set JAVA_HOME and prepend Java to PATH to ensure correct version is used
            if java_executable and java_executable != "java":
                java_bin_dir = os.path.dirname(java_executable)
                java_home = os.path.dirname(java_bin_dir)
                env['JAVA_HOME'] = java_home
                env['JAVA'] = java_executable
                env['PATH'] = java_bin_dir + os.pathsep + env.get('PATH', '')

            process = subprocess.Popen(
                command,
                cwd=self.server_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=creation_flags,
                env=env
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
                log_callback("Make sure Java is installed correctly.\n")
        except PermissionError as e:
            if log_callback:
                log_callback(f"\n✗ Error de permisos al ejecutar el servidor: {e}\n")
        except Exception as e:
            if log_callback:
                log_callback(f"\n✗ Error running server: {e}\n")
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
        Remove mods that are KNOWN to crash dedicated servers.
        This is a minimal list - only mods proven to cause server crashes.

        NOTE: This function is now rarely used. The main detection is done by
        modpack_manager.detect_client_only_mods() which uses Modrinth metadata.

        Args:
            log_callback: Función callback para reportar progreso

        Returns:
            Lista de mods removidos
        """
        # CRITICAL ONLY: Mods that actually CRASH dedicated servers
        # This list is intentionally minimal - better to miss some than remove needed mods
        CLIENT_ONLY_MOD_PATTERNS = [
            # Rendering mods that access client-only OpenGL/rendering classes
            "sodium", "embeddium", "rubidium", "magnesium",
            "iris", "oculus", "optifine", "optifabric",
            "indium", "nvidium",

            # Dynamic lighting mods (crash on dedicated server)
            "lambdynamiclights", "ryoamiclights", "ryoamiclight",
            "dynamiclights", "sodiumdynamiclights",

            # Client UI libraries that crash servers
            "obsidianui", "spruceui", "spruce_ui",

            # Client-only optimization mods that crash servers
            "immediatelyfast", "entityculling", "bocchium",
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
                log_callback(f"Error cleaning client-only mods: {str(e)}\n")
            return []
