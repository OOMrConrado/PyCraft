"""
Modpack Run Controller - Handles modded server running UI and logic.
"""

import os
import glob
import threading
from typing import Dict, Optional, Callable
from collections import deque

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QCursor

from ..widgets import NonPropagatingTextEdit
from ..pages.base_page import BasePage
from ..services.version_detection import VersionDetector


class ModpackRunController(BasePage):
    """
    Controller for the Modpack Server Run page.

    Handles:
    - Server folder selection and validation
    - Server detection (Forge, Fabric, NeoForge, Quilt)
    - Missing server installation
    - Server start/stop
    - Command sending
    """

    # Signals
    server_started = Signal(bool)  # success
    server_stopped = Signal(bool)  # was_successful
    server_install_done = Signal()  # missing server installed
    server_ready = Signal()  # emitted when server shows "Done" message
    _log_signal = Signal(str, str)  # msg, level - internal signal for thread-safe logging

    def __init__(
        self,
        colors: Dict[str, str],
        java_manager,
        navigate_callback: Optional[Callable[[str], None]] = None,
        log_signal=None,
        check_java_callback=None,
        open_config_callback=None,
        server_crashed_signal=None,
        parent=None
    ):
        super().__init__(colors, navigate_callback, parent)

        # Dependencies
        self.java_manager = java_manager
        self.log_signal = log_signal
        self._check_and_get_java = check_java_callback
        self._open_config_callback = open_config_callback
        self.server_crashed_signal = server_crashed_signal

        # State
        self.server_path = None
        self.server_manager = None
        self.is_configured = False
        self.ram_mb = 4096  # Default RAM for modded servers
        self.detected_mc_version = None
        self.detected_loader = None

        # Track if server started successfully
        self._server_started_successfully = False

        # Command history
        self._command_history = []
        self._history_index = -1

        # Simple direct logging, no buffers

        self._build_ui()

    def _build_ui(self):
        """Build the modpack run page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._scroll_style())

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 25, 40, 25)
        content_layout.setSpacing(18)

        # Back button
        back = self._text_button("< Back")
        back.clicked.connect(lambda: self.navigate_to("modded"))
        content_layout.addWidget(back)

        # Title
        title = QLabel("Run Modded Server")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        content_layout.addWidget(title)

        # Folder selection
        content_layout.addWidget(self._build_folder_section())

        # Console section
        content_layout.addWidget(self._build_console_section())

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._log(self.console, "Select a server folder to begin.\n", "info")

    def _build_folder_section(self) -> QFrame:
        """Build the folder selection section"""
        frame = self._section_frame("Server Folder")
        layout = frame.layout()

        select_btn = self._styled_button(
            "Select Folder", self.colors['bg_input'], self.colors['text'], 180
        )
        select_btn.clicked.connect(self._select_folder)
        layout.addWidget(select_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        layout.addWidget(self.folder_label)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            f"color: {self.colors['text_secondary']}; font-size: 13px; font-weight: 600;"
        )
        layout.addWidget(self.status_label)

        return frame

    def _build_console_section(self) -> QFrame:
        """Build the console and controls section"""
        frame = self._section_frame("Console")
        layout = frame.layout()

        # Console output
        self.console = self._console()
        layout.addWidget(self.console)

        # Command input row
        cmd_row = QWidget()
        cmd_row.setStyleSheet("background: transparent;")
        cmd_layout = QHBoxLayout(cmd_row)
        cmd_layout.setContentsMargins(0, 10, 0, 0)

        self.cmd_input = self._input("/command", 500)
        self.cmd_input.returnPressed.connect(self._send_command)
        self.cmd_input.installEventFilter(self)  # For arrow key history
        cmd_layout.addWidget(self.cmd_input)

        self.cmd_btn = self._styled_button("Send", self.colors['accent'], "#000000", 80)
        self.cmd_btn.setEnabled(False)
        self.cmd_btn.clicked.connect(self._send_command)
        cmd_layout.addWidget(self.cmd_btn)

        layout.addWidget(cmd_row)

        # Control buttons row
        ctrl_row = QWidget()
        ctrl_row.setStyleSheet("background: transparent;")
        ctrl_layout = QHBoxLayout(ctrl_row)
        ctrl_layout.setContentsMargins(0, 10, 0, 0)
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        ctrl_layout.setSpacing(12)

        self.start_btn = self._styled_button("Start", self.colors['accent'], "#000000", 120)
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start_server)
        ctrl_layout.addWidget(self.start_btn)

        self.stop_btn = self._styled_button("Stop", self.colors['red'], "#ffffff", 120)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_server)
        ctrl_layout.addWidget(self.stop_btn)

        self.config_btn = self._styled_button("Config", self.colors['yellow'], "#000000", 120)
        self.config_btn.setEnabled(False)
        self.config_btn.clicked.connect(self._open_config)
        ctrl_layout.addWidget(self.config_btn)

        # Install Server button (for missing server)
        self.install_server_btn = self._styled_button(
            "Install Server", self.colors['blue'], "#ffffff", 140
        )
        self.install_server_btn.setEnabled(False)
        self.install_server_btn.setVisible(False)
        self.install_server_btn.clicked.connect(self._install_missing_server)
        ctrl_layout.addWidget(self.install_server_btn)

        layout.addWidget(ctrl_row)

        # Server info footer
        self.server_info = QLabel("")
        self.server_info.setStyleSheet(
            f"color: {self.colors['text_muted']}; font-size: 12px; margin-top: 8px;"
        )
        self.server_info.setVisible(False)
        layout.addWidget(self.server_info)

        return frame

    # ============================================================
    # Folder Selection
    # ============================================================

    def _select_folder(self):
        """Handle folder selection"""
        folder = QFileDialog.getExistingDirectory(self, "Select Server Folder")
        if not folder:
            return

        # Clear previous state
        self.console.clear()
        self.cmd_input.clear()
        self.cmd_btn.setEnabled(False)
        self._log(self.console, "Loading server folder...\n", "info")

        if self._has_server(folder):
            self._setup_server(folder)
        else:
            self._handle_no_server(folder)

    def _has_server(self, folder: str) -> bool:
        """Check if folder contains a Minecraft server"""
        # Check for common server jar patterns
        jar_patterns = [
            "server.jar",
            "forge-*.jar",
            "neoforge-*.jar",
            "fabric-server-*.jar",
            "quilt-server-*.jar",
            "minecraft_server*.jar"
        ]

        for p in jar_patterns:
            if glob.glob(os.path.join(folder, p)):
                return True

        # Check for run scripts
        scripts = ["run.bat", "run.sh", "start.bat", "start.sh", "startserver.bat", "startserver.sh"]
        for script in scripts:
            if os.path.exists(os.path.join(folder, script)):
                return True

        # Check for libraries folder (modern Forge/NeoForge)
        if os.path.exists(os.path.join(folder, "libraries", "net", "minecraftforge")):
            return True
        if os.path.exists(os.path.join(folder, "libraries", "net", "neoforged")):
            return True

        return False

    def _setup_server(self, folder: str):
        """Set up server manager for valid folder"""
        from ...managers.server import ServerManager

        self.server_path = folder
        self.folder_label.setText(f"Folder: {folder}")
        self.status_label.setText("Server found")
        self.status_label.setStyleSheet(
            f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600; border: none;"
        )

        self.server_manager = ServerManager(folder)
        self.is_configured = True

        self.start_btn.setEnabled(True)
        self.install_server_btn.setEnabled(False)
        self.install_server_btn.setVisible(False)

        # Create server.properties if it doesn't exist (so Config button works immediately)
        if not os.path.exists(os.path.join(folder, "server.properties")):
            self.server_manager.ensure_server_properties()
        self.config_btn.setEnabled(True)

        self.stop_btn.setEnabled(False)

        self._log(self.console, f"\nServer found: {folder}\n", "success")

        # Detect loader and MC version
        loader_info = VersionDetector.detect_loader(folder)
        mc_version = self.server_manager.detect_minecraft_version()
        if not mc_version:
            mc_version = VersionDetector.detect_mc_version(folder)

        # Store for config dialog
        self.detected_mc_version = mc_version
        self.detected_loader = loader_info

        info_parts = []
        if mc_version:
            info_parts.append(f"Minecraft {mc_version}")
        if loader_info:
            info_parts.append(loader_info)

        if info_parts:
            self.server_info.setText(" | ".join(info_parts))
            self.server_info.setVisible(True)
            self._log(self.console, f"Detected: {' | '.join(info_parts)}\n", "info")
        else:
            self.server_info.setVisible(False)

    def _handle_no_server(self, folder: str):
        """Handle folder without server - check for auto-install possibility"""
        from ...managers.server import ServerManager

        self.server_path = None
        self.folder_label.setText(f"Folder: {folder}")
        self.start_btn.setEnabled(False)
        self.config_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.cmd_btn.setEnabled(False)
        self.is_configured = False

        # Check if we can detect version/loader for auto-install
        temp_sm = ServerManager(folder)
        detected_version = temp_sm.detect_version_from_mods()
        detected_loader = temp_sm.detect_loader_from_mods()

        # Store for config dialog
        self.detected_mc_version = detected_version
        self.detected_loader = detected_loader

        if detected_version and detected_loader:
            self.status_label.setText(
                f"Server not found - Can install {detected_loader.title()} {detected_version}"
            )
            self.status_label.setStyleSheet(
                f"color: {self.colors['yellow']}; font-size: 13px; font-weight: 600; border: none;"
            )
            self.install_server_btn.setEnabled(True)
            self.install_server_btn.setVisible(True)
            self.server_manager = temp_sm
            self.server_info.setText(f"Detected: MC {detected_version} | {detected_loader.title()}")
            self.server_info.setVisible(True)
            self._log(
                self.console,
                f"Server not found, but detected: MC {detected_version} | {detected_loader.title()}\n",
                "warning"
            )
            self._log(
                self.console,
                f"Click 'Install Server' to auto-install {detected_loader.title()}\n",
                "info"
            )
        else:
            self.status_label.setText("Server not found")
            self.status_label.setStyleSheet(
                f"color: {self.colors['red']}; font-size: 13px; font-weight: 600; border: none;"
            )
            self.install_server_btn.setEnabled(False)
            self.install_server_btn.setVisible(False)
            self.server_manager = None
            self.server_info.setVisible(False)

    # ============================================================
    # Server Control
    # ============================================================

    def _start_server(self):
        """Start the modded server"""
        print("[DEBUG] _start_server: INICIO", flush=True)
        if not self.server_manager:
            print("[DEBUG] No server_manager", flush=True)
            return

        # Get Minecraft version (quick check, should be cached)
        print("[DEBUG] Detectando version MC...", flush=True)
        mc_version = None
        if self.server_path:
            mc_version = VersionDetector.detect_mc_version(self.server_path)
        print(f"[DEBUG] MC version = {mc_version}", flush=True)

        if not mc_version:
            mc_version = "1.20"
            self._log(self.console, "\nCould not detect MC version, assuming Java 17+ required\n", "warning")

        # Check Java compatibility - this may show a modal, must be in main thread
        print("[DEBUG] Verificando Java...", flush=True)
        if self._check_and_get_java:
            java_executable = self._check_and_get_java(mc_version)
            print(f"[DEBUG] Java = {java_executable}", flush=True)
            if not java_executable:
                return
        else:
            java_executable = "java"

        # Update server manager
        self.server_manager.java_executable = java_executable
        java_source = "system" if java_executable == "java" else "PyCraft"
        self._log(self.console, f"\nUsing {java_source} Java: {java_executable}\n", "info")
        print("[DEBUG] Preparando para iniciar...", flush=True)

        self._server_started_successfully = False

        # Disable start, enable stop immediately for responsiveness
        self.start_btn.setEnabled(False)
        self.config_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        def on_stopped():
            try:
                self.server_stopped.emit(self._server_started_successfully)
            except Exception:
                pass  # Prevent crash if signal emit fails

        def log_callback(line: str):
            if "Done" in line and "!" in line:
                self._server_started_successfully = True
            self._emit_log(line, "normal")

        def start():
            print("[DEBUG] THREAD: Inicio", flush=True)
            try:
                # Move file operations to thread to avoid UI freeze
                # Accept EULA if needed
                print("[DEBUG] THREAD: Verificando EULA...", flush=True)
                eula_path = os.path.join(self.server_path, "eula.txt")
                if os.path.exists(eula_path):
                    try:
                        with open(eula_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        if 'eula=false' in content:
                            self._emit_log("Accepting EULA automatically...\n", "info")
                            self.server_manager.accept_eula()
                    except Exception:
                        pass
                print("[DEBUG] THREAD: EULA OK", flush=True)

                # Configure online-mode=false
                print("[DEBUG] THREAD: set_online_mode...", flush=True)
                self.server_manager.set_online_mode(False)
                print("[DEBUG] THREAD: online_mode OK", flush=True)

                # Detect server type
                print("[DEBUG] THREAD: detect_server_type...", flush=True)
                server_type = self.server_manager.detect_server_type()
                print(f"[DEBUG] THREAD: server_type = {server_type}", flush=True)

                if server_type == "unknown":
                    self._emit_log("Could not detect server type (Forge/Fabric).\n", "error")
                    self.server_started.emit(False)
                    return

                self._emit_log("\n=== STARTING SERVER ===\n", "info")

                print(f"[DEBUG] THREAD: Iniciando {server_type}...", flush=True)
                if server_type in ("forge", "fabric", "neoforge", "quilt"):
                    success = self.server_manager.start_modded_server(
                        server_type=server_type,
                        ram_mb=self.ram_mb,
                        java_executable=java_executable,
                        log_callback=log_callback,
                        detached=True,
                        on_stopped=on_stopped
                    )
                else:
                    success = self.server_manager.start_server(
                        ram_mb=self.ram_mb,
                        log_callback=log_callback,
                        detached=True,
                        on_stopped=on_stopped
                    )
                print(f"[DEBUG] THREAD: success = {success}", flush=True)
                self.server_started.emit(success)
            except Exception as e:
                print(f"[DEBUG] THREAD: ERROR: {e}", flush=True)
                self._emit_log(f"\n[ERROR] Failed to start server: {e}\n", "error")
                self.server_started.emit(False)

        print("[DEBUG] Lanzando thread...", flush=True)
        threading.Thread(target=start, daemon=True).start()
        print("[DEBUG] Thread lanzado, FIN _start_server", flush=True)

    def on_server_started(self, success: bool):
        """Handle server started event (call from main thread)"""
        if success:
            self.cmd_btn.setEnabled(True)
        else:
            self._on_server_stopped_normal()

    def on_server_stopped(self, started_successfully: bool):
        """Handle server stopped event (call from main thread)"""
        self.start_btn.setEnabled(True)

        if self.server_path:
            has_properties = os.path.exists(os.path.join(self.server_path, "server.properties"))
            self.config_btn.setEnabled(has_properties)
        else:
            self.config_btn.setEnabled(False)

        self.stop_btn.setEnabled(False)
        self.cmd_btn.setEnabled(False)

        if started_successfully:
            self._emit_log("\n[Server stopped - Ready to restart]\n", "info")
        else:
            self._emit_log("\n[Server crashed - Ready to restart]\n", "error")
            if self.server_crashed_signal and self.server_path:
                QTimer.singleShot(100, lambda: self.server_crashed_signal.emit(self.server_path))

    def _on_server_stopped_normal(self):
        """Reset UI to normal stopped state"""
        self.start_btn.setEnabled(True)
        if self.server_path:
            has_properties = os.path.exists(os.path.join(self.server_path, "server.properties"))
            self.config_btn.setEnabled(has_properties)
        self.stop_btn.setEnabled(False)
        self.cmd_btn.setEnabled(False)

    def _stop_server(self):
        """Stop the server"""
        if not self.server_manager:
            return

        if not self.server_manager.is_server_running():
            self._log(self.console, "\nServer is not running\n", "warning")
            return

        # Disable all buttons
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.config_btn.setEnabled(False)
        self.cmd_btn.setEnabled(False)
        self._log(self.console, "\nStopping server...\n", "warning")

        def stop():
            try:
                self.server_manager.stop_server()

                def enable_buttons():
                    self._log(self.console, "Server stopped - Ready to restart\n", "success")
                    self.start_btn.setEnabled(True)
                    self.config_btn.setEnabled(True)
                    self.stop_btn.setEnabled(False)
                    self.cmd_btn.setEnabled(False)

                QTimer.singleShot(0, enable_buttons)
            except Exception as e:
                def enable_buttons_on_error():
                    self._log(self.console, f"Error stopping server: {e}\n", "error")
                    self.start_btn.setEnabled(True)
                    self.config_btn.setEnabled(True)
                    self.stop_btn.setEnabled(False)
                    self.cmd_btn.setEnabled(False)

                QTimer.singleShot(0, enable_buttons_on_error)

        threading.Thread(target=stop, daemon=True).start()

    # ============================================================
    # Commands
    # ============================================================

    def _send_command(self):
        """Send command to server"""
        cmd = self.cmd_input.text().strip()
        if cmd and self.server_manager:
            if not cmd.startswith("/"):
                self._log(self.console, "Commands must start with /\n", "warning")
                return

            server_cmd = cmd[1:]
            self._log(self.console, f"> {cmd}\n", "info")
            self.server_manager.send_command(server_cmd)

            # Add to history (avoid duplicates of last command)
            if not self._command_history or self._command_history[-1] != cmd:
                self._command_history.append(cmd)
            self._history_index = len(self._command_history)  # Reset to end

            self.cmd_input.clear()

            # Flash button for feedback
            self._flash_send_button()

    def _flash_send_button(self):
        """Flash the send button once for visual feedback"""
        self.cmd_btn.setEnabled(False)

        def restore():
            self.cmd_btn.setEnabled(
                self.server_manager is not None and
                self.server_manager.is_server_running()
            )

        QTimer.singleShot(150, restore)

    def eventFilter(self, obj, event):
        """Handle arrow keys for command history"""
        from PySide6.QtCore import QEvent

        if obj == self.cmd_input and event.type() == QEvent.Type.KeyPress:
            key = event.key()

            if key == Qt.Key.Key_Up:
                # Navigate to previous command
                if self._command_history and self._history_index > 0:
                    self._history_index -= 1
                    self.cmd_input.setText(self._command_history[self._history_index])
                elif self._command_history and self._history_index == -1:
                    self._history_index = len(self._command_history) - 1
                    self.cmd_input.setText(self._command_history[self._history_index])
                return True

            elif key == Qt.Key.Key_Down:
                # Navigate to next command
                if self._command_history and self._history_index < len(self._command_history) - 1:
                    self._history_index += 1
                    self.cmd_input.setText(self._command_history[self._history_index])
                elif self._history_index >= len(self._command_history) - 1:
                    self._history_index = len(self._command_history)
                    self.cmd_input.clear()
                return True

        return super().eventFilter(obj, event)

    # ============================================================
    # Config
    # ============================================================

    def _open_config(self):
        """Open server configuration dialog"""
        if self.server_manager and self.server_manager.is_server_running():
            QMessageBox.warning(self, "Warning", "Stop server first")
            return

        if self._open_config_callback:
            self._open_config_callback("modpack")

    # ============================================================
    # Missing Server Install
    # ============================================================

    def _install_missing_server(self):
        """Install missing server for modpack"""
        if not self.server_manager:
            return

        folder = self.server_manager.server_folder

        # Get Java executable
        mc_version = self.server_manager.detect_version_from_mods()
        java_exe = "java"
        if mc_version:
            java_check = self.java_manager.get_best_java_for_version(mc_version)
            if java_check.get("java_path"):
                java_exe = java_check["java_path"]
            elif java_check.get("needs_install"):
                required_ver = java_check.get("required_java_version", 17)
                reply = QMessageBox.question(
                    self, "Java Required",
                    f"Minecraft {mc_version} requires Java {required_ver}.\n\nDo you want to install it now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

        # Disable buttons during install
        self.install_server_btn.setEnabled(False)
        self.install_server_btn.setText("Installing...")

        def install_thread():
            def log_cb(msg):
                self._emit_log(msg, "info")

            success, message = self.server_manager.install_missing_server(
                java_executable=java_exe,
                log_callback=log_cb
            )
            self.server_install_done.emit()

        threading.Thread(target=install_thread, daemon=True).start()

    def on_server_install_done(self):
        """Handle missing server install completion (call from main thread)"""
        self.install_server_btn.setText("Install Server")

        if self.server_manager.is_server_installed():
            self._emit_log("\n[SUCCESS] Server installed successfully!\n", "success")
            self.install_server_btn.setVisible(False)
            self.start_btn.setEnabled(True)
            self.server_path = self.server_manager.server_folder
            self.is_configured = True
            self.status_label.setText("Ready")
            self.status_label.setStyleSheet(
                f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600; border: none;"
            )

            mc_ver = VersionDetector.detect_mc_version(self.server_path)
            loader = VersionDetector.detect_loader(self.server_path)
            info_parts = []
            if mc_ver:
                info_parts.append(f"MC {mc_ver}")
            if loader:
                info_parts.append(loader)
            if info_parts:
                self.server_info.setText(" | ".join(info_parts))

            props_path = os.path.join(self.server_path, "server.properties")
            self.config_btn.setEnabled(os.path.exists(props_path))
        else:
            self._emit_log("\n[ERROR] Server installation failed\n", "error")
            self.install_server_btn.setEnabled(True)

    # ============================================================
    # Helpers
    # ============================================================

    def _emit_log(self, msg: str, level: str):
        """Log directly to console"""
        if hasattr(self, 'console') and self.console:
            self._log(self.console, msg, level)
            QApplication.processEvents()

            if "Done" in msg and "For help, type" in msg:
                self.server_ready.emit()

    def set_ram(self, ram_mb: int):
        """Set RAM allocation"""
        self.ram_mb = ram_mb

    def get_server_manager(self):
        """Return the server manager"""
        return self.server_manager

    def get_server_path(self):
        """Return the server path"""
        return self.server_path
