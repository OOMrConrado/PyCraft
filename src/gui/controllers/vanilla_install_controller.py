"""
Vanilla Install Controller - Handles vanilla server creation UI and logic.
"""

import threading
from typing import Dict, Optional, Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QCursor

from ..widgets import NonPropagatingScrollArea, NonPropagatingTextEdit
from ..pages.base_page import BasePage


class VanillaInstallController(BasePage):
    """
    Controller for the Vanilla Server Installation page.

    Handles:
    - Version selection from Minecraft API
    - Folder selection with safety checks
    - Server download and initial setup
    """

    # Signals for thread-safe communication
    install_success = Signal(str, str)  # version, folder
    _log_signal = Signal(str, str)  # msg, level - internal signal for thread-safe logging

    def __init__(
        self,
        colors: Dict[str, str],
        api_handler,
        downloader,
        java_manager,
        navigate_callback: Optional[Callable[[str], None]] = None,
        log_signal=None,
        progress_signal=None,
        check_java_callback=None,
        parent=None
    ):
        super().__init__(colors, navigate_callback, parent)

        # Dependencies
        self.api_handler = api_handler
        self.downloader = downloader
        self.java_manager = java_manager
        self.log_signal = log_signal
        self.progress_signal = progress_signal
        self._check_and_get_java = check_java_callback

        # State
        self.versions_list = []
        self.filtered_versions = []
        self.selected_version = None
        self.server_folder = None
        self.server_manager = None  # Will be set after creation

        # Connect internal log signal with QueuedConnection for thread safety
        self._log_signal.connect(self._on_log_signal, Qt.ConnectionType.QueuedConnection)

        self._build_ui()
        self._load_versions()

    def _on_log_signal(self, msg: str, level: str):
        """Handle log signal in main thread"""
        if hasattr(self, 'console') and self.console:
            self._log(self.console, msg, level)

    def _build_ui(self):
        """Build the vanilla server creation page UI"""
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
        title = QLabel("Create New Server")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        content_layout.addWidget(title)

        # Version selection
        content_layout.addWidget(self._build_version_section())

        # Folder selection
        content_layout.addWidget(self._build_folder_section())

        # Download button
        self.download_btn = self._styled_button(
            "Download and Install",
            self.colors['accent'],
            "#000000",
            280
        )
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._download_server)
        content_layout.addWidget(self.download_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Console
        console_frame = self._section_frame("Console")
        self.console = self._console()
        console_frame.layout().addWidget(self.console)
        content_layout.addWidget(console_frame)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        content_layout.addWidget(self.status_label)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._log(self.console, "Ready to create a new server.\n", "info")

    def _build_version_section(self) -> QFrame:
        """Build the version selection section"""
        frame = self._section_frame("Minecraft Version")
        layout = frame.layout()

        # Search input
        self.ver_search = self._input("Search version...", 400)
        self.ver_search.textChanged.connect(self._filter_versions)
        self.ver_search.mousePressEvent = lambda e: self._show_version_dropdown()

        # Focus handler
        original_focus_in = self.ver_search.focusInEvent
        def on_focus_in(event):
            self._show_version_dropdown()
            original_focus_in(event)
        self.ver_search.focusInEvent = on_focus_in
        layout.addWidget(self.ver_search)

        # Version list scroll area
        self.ver_scroll = NonPropagatingScrollArea()
        self.ver_scroll.setFixedHeight(140)
        self.ver_scroll.setWidgetResizable(True)
        self.ver_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {self.colors['bg_card']};
                width: 12px;
                border-radius: 6px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: #4a4a4a;
                border-radius: 6px;
                border: none;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #5a5a5a;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                border: none;
            }}
            QScrollBar:horizontal {{
                height: 0px;
            }}
        """)

        self.ver_list = QWidget()
        self.ver_list_layout = QVBoxLayout(self.ver_list)
        self.ver_list_layout.setSpacing(4)
        self.ver_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.ver_scroll.setWidget(self.ver_list)
        layout.addWidget(self.ver_scroll)

        # Selected version label
        self.ver_selected = QLabel("No version selected")
        self.ver_selected.setStyleSheet(
            f"color: {self.colors['yellow']}; font-size: 13px; font-weight: 600; border: none;"
        )
        layout.addWidget(self.ver_selected)

        return frame

    def _build_folder_section(self) -> QFrame:
        """Build the folder selection section"""
        frame = self._section_frame("Destination Folder")
        layout = frame.layout()

        folder_btn = self._styled_button(
            "Select Folder",
            self.colors['bg_input'],
            self.colors['text'],
            180
        )
        folder_btn.clicked.connect(self._select_folder)
        layout.addWidget(folder_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        layout.addWidget(self.folder_label)

        return frame

    # ============================================================
    # Version Logic
    # ============================================================

    def _load_versions(self):
        """Load available Minecraft versions from API"""
        def load():
            versions = self.api_handler.get_version_names()
            if versions:
                self.versions_list = versions
                self.filtered_versions = versions.copy()
                QTimer.singleShot(0, lambda: self._show_versions(versions))

        threading.Thread(target=load, daemon=True).start()

    def _show_versions(self, versions: list):
        """Display version list in the dropdown"""
        # Clear existing items
        while self.ver_list_layout.count():
            child = self.ver_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for v in versions[:50]:
            btn = QPushButton(v)
            btn.setFixedHeight(34)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {self.colors['text']};
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                    padding-left: 12px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {self.colors['bg_input']};
                }}
            """)
            btn.clicked.connect(lambda _, ver=v: self._pick_version(ver))
            self.ver_list_layout.addWidget(btn)

    def _show_version_dropdown(self):
        """Show version dropdown and focus input"""
        if self.versions_list:
            self._show_versions(self.versions_list)
        self.ver_scroll.show()
        self.ver_search.setFocus()
        if self.selected_version:
            self.ver_search.setPlaceholderText("Search version...")

    def _collapse_version_dropdown(self, ver: str):
        """Collapse version dropdown after selection"""
        self.ver_search.textChanged.disconnect(self._filter_versions)
        self.ver_scroll.hide()
        self.ver_search.setText("")
        self.ver_search.setPlaceholderText(f"✓ {ver} (click to change)")
        self.ver_search.clearFocus()
        self.ver_search.textChanged.connect(self._filter_versions)

    def _filter_versions(self, text: str):
        """Filter version list based on search text"""
        if not self.ver_scroll.isVisible():
            self.ver_scroll.show()

        if not text:
            self.filtered_versions = self.versions_list.copy()
        else:
            self.filtered_versions = [
                v for v in self.versions_list
                if text.lower() in v.lower()
            ]
        self._show_versions(self.filtered_versions)

    def _pick_version(self, ver: str):
        """Handle version selection"""
        self.selected_version = ver
        self.ver_selected.setText(f"✓ Selected: {ver}")
        self.ver_selected.setStyleSheet(
            f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600; border: none;"
        )
        self._update_download_btn()
        QTimer.singleShot(50, lambda: self._collapse_version_dropdown(ver))

    # ============================================================
    # Folder Logic
    # ============================================================

    def _select_folder(self):
        """Handle folder selection with safety checks"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            if not self._warn_dangerous_folder(folder):
                return
            if not self._warn_existing_server(folder):
                return

            self.server_folder = folder
            self.folder_label.setText(f"Folder: {folder}")
            self._update_download_btn()

    def _is_dangerous_folder(self, folder_path: str) -> tuple:
        """Check if a folder is a dangerous/important system location"""
        if not folder_path:
            return False, ""

        path = Path(folder_path).resolve()
        path_str = str(path).lower()
        path_name = path.name.lower()

        # Check if it's a drive root
        if path.parent == path:
            return True, "You selected a drive root. This will create server files directly in your drive."

        # Dangerous folder names
        dangerous_names = {
            "downloads": "Downloads folder",
            "descargas": "Downloads folder",
            "desktop": "Desktop",
            "escritorio": "Desktop",
            "documents": "Documents folder",
            "documentos": "Documents folder",
            "program files": "Program Files",
            "program files (x86)": "Program Files",
            "windows": "Windows system folder",
            "system32": "Windows system folder",
            "users": "Users folder",
            "appdata": "AppData folder",
        }

        if path_name in dangerous_names:
            location = dangerous_names[path_name]
            return True, f"You selected your {location}. Creating a Minecraft server here is not recommended."

        # Check common paths
        user_profile = Path.home()
        if path == user_profile:
            return True, "You selected your user folder directly."

        return False, ""

    def _warn_dangerous_folder(self, folder_path: str) -> bool:
        """Show warning for dangerous folder locations"""
        is_dangerous, warning = self._is_dangerous_folder(folder_path)
        if not is_dangerous:
            return True

        msg = QMessageBox(self)
        msg.setWindowTitle("Warning: Folder Location")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("Are you sure you want to use this folder?")
        msg.setInformativeText(
            f"{warning}\n\nIt's recommended to create a dedicated folder for your server."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        return msg.exec() == QMessageBox.StandardButton.Yes

    def _is_existing_server(self, folder_path: str) -> bool:
        """Check if folder already contains a server"""
        import os
        server_files = ["server.jar", "server.properties", "eula.txt"]
        return any(os.path.exists(os.path.join(folder_path, f)) for f in server_files)

    def _warn_existing_server(self, folder_path: str) -> bool:
        """Warn if folder already contains server files"""
        if not self._is_existing_server(folder_path):
            return True

        msg = QMessageBox(self)
        msg.setWindowTitle("Server Already Exists")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("This folder already contains a Minecraft server.")
        msg.setInformativeText("Installing here will overwrite existing server files. Continue?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        return msg.exec() == QMessageBox.StandardButton.Yes

    # ============================================================
    # Download Logic
    # ============================================================

    def _update_download_btn(self):
        """Update download button state"""
        self.download_btn.setEnabled(bool(self.selected_version and self.server_folder))

    def _download_server(self):
        """Start server download and installation process"""
        if not self.selected_version or not self.server_folder:
            return

        # Check Java compatibility
        if self._check_and_get_java:
            java_executable = self._check_and_get_java(self.selected_version)
            if not java_executable:
                return
        else:
            java_executable = "java"

        self.download_btn.setEnabled(False)
        java_to_use = java_executable

        def process():
            nonlocal java_to_use
            try:
                self._emit_log(f"\nDownloading Minecraft {self.selected_version}...\n", "info")

                url = self.api_handler.get_server_jar_url(self.selected_version)
                if not url:
                    self._emit_log("Error: Could not get URL\n", "error")
                    return

                server_path = self.downloader.download_server(
                    url, self.server_folder, self.selected_version,
                    progress_callback=lambda p: self._emit_progress(p)
                )

                if not server_path:
                    self._emit_log("Download failed\n", "error")
                    return

                self._emit_log("Download complete\n", "success")

                # Use Java
                if java_to_use:
                    java = java_to_use
                    self._emit_log(f"Using Java: {java}\n", "info")
                else:
                    java = self.java_manager.ensure_java_installed(
                        self.selected_version,
                        log_callback=lambda m: self._emit_log(m, "normal")
                    )

                if not java:
                    self._emit_log("Java not available\n", "error")
                    return

                self._emit_log("\nConfiguring server...\n", "info")

                # Import here to avoid circular imports
                from ...managers.server import ServerManager
                self.server_manager = ServerManager(self.server_folder, java_executable=java)
                success = self.server_manager.run_server_first_time(
                    log_callback=lambda m: self._emit_log(m, "normal")
                )

                if success:
                    self._emit_log("\n" + "="*50 + "\n", "success")
                    self._emit_log("SERVER CREATED SUCCESSFULLY\n", "success")
                    self._emit_log("="*50 + "\n", "success")

                    # Emit success signal
                    self.install_success.emit(self.selected_version, self.server_folder)

            except Exception as e:
                self._emit_log(f"Error: {e}\n", "error")

            finally:
                QTimer.singleShot(0, lambda: self.download_btn.setEnabled(True))

        threading.Thread(target=process, daemon=True).start()

    def _emit_log(self, msg: str, level: str):
        """Emit log message to console (thread-safe via Qt Signal)"""
        self._log_signal.emit(msg, level)

    def _emit_progress(self, value: int):
        """Emit progress via signal"""
        if self.progress_signal:
            self.progress_signal.emit(value)

    def get_server_manager(self):
        """Return the server manager after creation"""
        return self.server_manager

    def get_selected_version(self):
        """Return the selected version"""
        return self.selected_version

    def get_server_folder(self):
        """Return the server folder"""
        return self.server_folder
