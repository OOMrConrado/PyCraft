"""
Home Page for PyCraft GUI.
Welcome screen with main navigation options.
"""

from typing import Dict, Callable, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton
)
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QCursor, QDesktopServices

import qtawesome as qta

from .base_page import BasePage


class HomePage(BasePage):
    """Home/welcome page with main navigation"""

    def __init__(
        self,
        colors: Dict[str, str],
        navigate_callback: Optional[Callable[[str], None]] = None,
        parent=None
    ):
        super().__init__(colors, navigate_callback, parent)
        self._setup_ui()

    def _setup_ui(self):
        """Build the home page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 20)

        # Welcome card
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_card']};
                border-radius: 16px;
                border: 1px solid {self.colors['border']};
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(8)

        # Top row with welcome text and website icon
        top_row = QWidget()
        top_row.setStyleSheet("background: transparent;")
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(0)

        welcome = QLabel("Welcome to")
        welcome.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px; background: transparent;")
        top_row_layout.addWidget(welcome)

        top_row_layout.addStretch()

        # Website icon button
        website_btn = QPushButton()
        website_btn.setIcon(qta.icon("fa5s.globe", color=self.colors['text_secondary']))
        website_btn.setIconSize(QSize(24, 24))
        website_btn.setFixedSize(28, 28)
        website_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        website_btn.setToolTip("Visit PyCraft Website")
        website_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
            }}
            QPushButton:hover {{
                background-color: transparent;
            }}
        """)
        website_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://pycraft-web.vercel.app")))
        top_row_layout.addWidget(website_btn)

        card_layout.addWidget(top_row)

        title = QLabel("PyCraft")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 36px; font-weight: bold; background: transparent;")
        card_layout.addWidget(title)

        desc = QLabel("A modern tool to create and manage Minecraft servers")
        desc.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px; background: transparent;")
        card_layout.addWidget(desc)

        card_layout.addSpacing(24)

        # Buttons
        btn_container = QWidget()
        btn_container.setStyleSheet("background: transparent;")
        btn_layout = QVBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)

        vanilla_btn = self._styled_button("Create Vanilla Server", self.colors['bg_input'], self.colors['text'])
        vanilla_btn.clicked.connect(lambda: self.navigate_to("vanilla"))
        btn_layout.addWidget(vanilla_btn)

        modded_btn = self._styled_button("Install Modpack Server", self.colors['accent'], "#000000")
        modded_btn.clicked.connect(lambda: self.navigate_to("modded"))
        btn_layout.addWidget(modded_btn)

        card_layout.addWidget(btn_container)

        layout.addWidget(card)
        layout.addStretch()
