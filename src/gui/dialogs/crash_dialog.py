"""
Server Crash Dialog.
Displays information when a server crashes.
"""

import os
import sys
import subprocess
from typing import Dict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

try:
    import qtawesome as qta
    HAS_QTAWESOME = True
except ImportError:
    HAS_QTAWESOME = False


class ServerCrashDialog(QDialog):
    """Dialog displayed when a server crashes"""

    def __init__(self, server_path: str, colors: Dict[str, str], parent=None):
        """
        Initialize the crash dialog.

        Args:
            server_path: Path to the server folder (for logs/crash-reports)
            colors: Color scheme dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        self.server_path = server_path
        self.colors = colors
        self._setup_ui()

    def _setup_ui(self):
        """Build the dialog UI"""
        self.setWindowTitle("Server Crashed")
        self.setFixedSize(420, 220)
        self.setStyleSheet(f"background-color: {self.colors['bg_card']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        # Icon and title row
        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        if HAS_QTAWESOME:
            try:
                icon_label = QLabel()
                icon = qta.icon("fa5s.exclamation-triangle", color=self.colors['red'])
                icon_label.setPixmap(icon.pixmap(32, 32))
                title_row.addWidget(icon_label)
            except Exception:
                pass

        title = QLabel("Server Crashed")
        title.setStyleSheet(f"color: {self.colors['red']}; font-size: 18px; font-weight: bold;")
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)

        # Message
        msg = QLabel("The server has stopped unexpectedly.\nCheck the logs or crash reports for more details.")
        msg.setStyleSheet(f"color: {self.colors['text']}; font-size: 13px;")
        msg.setWordWrap(True)
        layout.addWidget(msg)

        layout.addStretch()

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        # Open Logs button
        logs_folder = os.path.join(self.server_path, "logs") if self.server_path else None
        if logs_folder and os.path.exists(logs_folder):
            logs_btn = self._create_button("Open Logs", self.colors['bg_input'], self.colors['text'], 120)
            logs_btn.clicked.connect(lambda: self._open_folder(logs_folder))
            btn_row.addWidget(logs_btn)

        # Open Crash Reports button
        crash_folder = os.path.join(self.server_path, "crash-reports") if self.server_path else None
        if crash_folder and os.path.exists(crash_folder):
            crash_btn = self._create_button("Crash Reports", self.colors['bg_input'], self.colors['text'], 120)
            crash_btn.clicked.connect(lambda: self._open_folder(crash_folder))
            btn_row.addWidget(crash_btn)

        btn_row.addStretch()

        # OK button
        ok_btn = self._create_button("OK", self.colors['accent'], "#000000", 80)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

    def _create_button(self, text: str, bg_color: str, text_color: str, width: int) -> QPushButton:
        """Create a styled button"""
        btn = QPushButton(text)
        btn.setFixedSize(width, 36)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {self.colors.get('accent_hover', bg_color)};
            }}
        """)
        return btn

    def _open_folder(self, folder_path: str):
        """Open a folder in the system file manager"""
        try:
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', folder_path])
            else:
                subprocess.run(['xdg-open', folder_path])
        except Exception:
            pass
