"""
Vanilla Run Controller - Handles vanilla server running UI and logic.
"""

import os
import threading
from typing import Dict, Optional, Callable
from collections import deque

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QCursor

from ..widgets import NonPropagatingTextEdit
from ..pages.base_page import BasePage


class VanillaRunController(BasePage):
    """
    Controller for the Vanilla Server Run page.

    Handles:
    - Server folder selection and validation
    - Server start/stop
    - Command sending
    - Server status monitoring
    """

    # Signals
    server_started = Signal(bool)  # success
    server_stopped = Signal(bool)  # was_successful
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
        self.server_folder = None
        self.server_manager = None
        self.is_server_configured = False
        self.detected_mc_version = None
        self.ram_mb = 2048  # Default RAM

        # Track if server started successfully (for crash detection)
        self._server_started_successfully = False

        # Command history
        self._command_history = []
        self._history_index = -1

        self._build_ui()

        # Connect log signal for thread-safe logging
        self._log_signal.connect(self._on_log_signal)

    def _build_ui(self):
        """Build the vanilla server run page UI"""
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
        back.clicked.connect(lambda: self.navigate_to("vanilla"))
        content_layout.addWidget(back)

        # Title
        title = QLabel("Run Existing Server")
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
            "Select Folder",
            self.colors['bg_input'],
            self.colors['text'],
            180
        )
        select_btn.clicked.connect(self._select_folder)
        layout.addWidget(select_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        layout.addWidget(self.folder_label)

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

        layout.addWidget(ctrl_row)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            f"color: {self.colors['text_secondary']}; font-size: 13px; font-weight: 600;"
        )
        layout.addWidget(self.status_label)

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

        if os.path.exists(os.path.join(folder, "server.jar")):
            self._setup_server(folder)
        else:
            self._handle_invalid_folder(folder)

    def _setup_server(self, folder: str):
        """Set up server manager for valid folder"""
        from ...managers.server import ServerManager

        self.server_folder = folder
        self.folder_label.setText(f"Folder: {folder}")

        self.server_manager = ServerManager(folder)
        self.is_server_configured = True

        # Detect Minecraft version
        mc_version = self.server_manager.detect_minecraft_version()
        self.detected_mc_version = mc_version

        if mc_version:
            self.status_label.setText(f"Minecraft {mc_version}")
            self._log(self.console, f"\nServer found: {folder}\n", "success")
            self._log(self.console, f"Detected version: Minecraft {mc_version}\n", "info")
            self.server_info.setText(f"Minecraft {mc_version}")
            self.server_info.setVisible(True)
        else:
            self.status_label.setText("Server found (version unknown)")
            self._log(self.console, f"\nServer found: {folder}\n", "success")
            self._log(self.console, "Could not detect Minecraft version\n", "warning")
            self.server_info.setVisible(False)

        self.status_label.setStyleSheet(
            f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600; border: none;"
        )
        self.start_btn.setEnabled(True)

        # Create server.properties if it doesn't exist (so Config button works immediately)
        if not os.path.exists(os.path.join(folder, "server.properties")):
            self.server_manager.ensure_server_properties()
        self.config_btn.setEnabled(True)

        self.stop_btn.setEnabled(False)

    def _handle_invalid_folder(self, folder: str):
        """Handle invalid server folder"""
        self.server_folder = None
        self.folder_label.setText(f"Folder: {folder}")
        self.status_label.setText("server.jar not found")
        self.status_label.setStyleSheet(
            f"color: {self.colors['red']}; font-size: 13px; font-weight: 600; border: none;"
        )
        self.server_info.setVisible(False)
        self.start_btn.setEnabled(False)
        self.config_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.cmd_btn.setEnabled(False)
        self.server_manager = None
        self.is_server_configured = False
        self.detected_mc_version = None

    # ============================================================
    # Server Control
    # ============================================================

    def _start_server(self):
        """Start the server"""
        if not self.server_manager:
            return

        # Get Minecraft version
        mc_version = self.detected_mc_version or self.server_manager.detect_minecraft_version()
        if not mc_version:
            mc_version = "1.20"
            self._log(self.console, "\nCould not detect version, assuming Java 17+ required\n", "warning")

        # Check Java compatibility
        if self._check_and_get_java:
            java_executable = self._check_and_get_java(mc_version)
            if not java_executable:
                return
        else:
            java_executable = "java"

        # Update server manager with the selected Java
        self.server_manager.java_executable = java_executable
        java_source = "system" if java_executable == "java" else "PyCraft"
        self._log(self.console, f"\nUsing {java_source} Java: {java_executable}\n", "info")

        # Disable buttons immediately for responsiveness
        self.start_btn.setEnabled(False)
        self.config_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # Track if server started successfully
        self._server_started_successfully = False

        def on_server_stopped():
            """Called when server process ends"""
            try:
                self.server_stopped.emit(self._server_started_successfully)
            except Exception:
                pass  # Prevent crash if signal emit fails

        def log_callback(line: str):
            """Monitor server output"""
            if "Done" in line and "!" in line:
                self._server_started_successfully = True
            self._emit_log(line, "normal")

        def start():
            try:
                # Configure online-mode=false in thread to avoid UI freeze
                self.server_manager.set_online_mode(False)

                self._emit_log("\n=== STARTING SERVER ===\n", "info")

                success = self.server_manager.start_server(
                    ram_mb=self.ram_mb,
                    log_callback=log_callback,
                    detached=True,
                    on_stopped=on_server_stopped
                )
                self.server_started.emit(success)
            except Exception as e:
                self._emit_log(f"\n[ERROR] Failed to start server: {e}\n", "error")
                self.server_started.emit(False)

        threading.Thread(target=start, daemon=True).start()

    def on_server_started(self, success: bool):
        """Handle server started event (call from main thread)"""
        if success:
            self.cmd_btn.setEnabled(True)
        else:
            self.start_btn.setEnabled(True)
            self.config_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def on_server_stopped(self, started_successfully: bool):
        """Handle server stopped event (call from main thread)"""
        self.start_btn.setEnabled(True)

        if self.server_folder:
            has_properties = os.path.exists(os.path.join(self.server_folder, "server.properties"))
            self.config_btn.setEnabled(has_properties)
        else:
            self.config_btn.setEnabled(False)

        self.stop_btn.setEnabled(False)
        self.cmd_btn.setEnabled(False)

        if started_successfully:
            self._emit_log("\n[Server stopped - Ready to restart]\n", "info")
        else:
            self._emit_log("\n[Server crashed - Ready to restart]\n", "error")
            if self.server_crashed_signal and self.server_folder:
                QTimer.singleShot(100, lambda: self.server_crashed_signal.emit(self.server_folder))

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

            server_cmd = cmd[1:]  # Remove "/" prefix
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
        from PySide6.QtGui import QKeyEvent

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
            self._open_config_callback("vanilla")

    # ============================================================
    # Helpers
    # ============================================================

    def _emit_log(self, msg: str, level: str):
        """Log using signal for thread safety"""
        self._log_signal.emit(msg, level)

    def _on_log_signal(self, msg: str, level: str):
        """Handle log signal in main thread"""
        if hasattr(self, 'console') and self.console:
            self._log(self.console, msg, level)

            # Detect when server is ready
            if "Done" in msg and "For help, type" in msg:
                self.server_ready.emit()

    def set_ram(self, ram_mb: int):
        """Set RAM allocation"""
        self.ram_mb = ram_mb

    def get_server_manager(self):
        """Return the server manager"""
        return self.server_manager

    def get_server_folder(self):
        """Return the server folder"""
        return self.server_folder
