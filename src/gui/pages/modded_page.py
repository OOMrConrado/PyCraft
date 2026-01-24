"""
Modded Server Selection Page.
Shows options for modpack server operations.
"""

from typing import Dict, Callable, Optional

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt

from .base_page import BasePage
from ..widgets import OptionCard


class ModdedPage(BasePage):
    """Modded server selection page"""

    def __init__(
        self,
        colors: Dict[str, str],
        navigate_callback: Optional[Callable[[str], None]] = None,
        parent=None
    ):
        super().__init__(colors, navigate_callback, parent)
        self._setup_ui()

    def _setup_ui(self):
        """Build the modded selection page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 20)

        title = QLabel("Modded Server")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 26px; font-weight: bold;")
        layout.addWidget(title)

        sub = QLabel("What would you like to do?")
        sub.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px;")
        layout.addWidget(sub)

        layout.addSpacing(30)

        cards = QWidget()
        cards.setStyleSheet("background: transparent;")
        cards_layout = QVBoxLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(15)

        # First row: Install Server and Run Server
        row1 = QWidget()
        row1.setStyleSheet("background: transparent;")
        row1_layout = QHBoxLayout(row1)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(20)
        row1_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        install_card = OptionCard("Install Server", "Download modpack server from Modrinth", "fa5s.server")
        install_card.clicked.connect(lambda: self.navigate_to("modpack_install"))
        row1_layout.addWidget(install_card)

        run_card = OptionCard("Run Server", "Manage an existing modded server", "fa5s.play-circle")
        run_card.clicked.connect(lambda: self.navigate_to("modpack_run"))
        row1_layout.addWidget(run_card)

        cards_layout.addWidget(row1)

        layout.addWidget(cards)
        layout.addStretch()
