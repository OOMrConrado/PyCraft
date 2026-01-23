"""
Vanilla Server Selection Page.
Shows options to create or run vanilla servers.
"""

from typing import Dict, Callable, Optional

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt

from .base_page import BasePage
from ..widgets import OptionCard


class VanillaPage(BasePage):
    """Vanilla server selection page"""

    def __init__(
        self,
        colors: Dict[str, str],
        navigate_callback: Optional[Callable[[str], None]] = None,
        parent=None
    ):
        super().__init__(colors, navigate_callback, parent)
        self._setup_ui()

    def _setup_ui(self):
        """Build the vanilla selection page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 20)

        title = QLabel("Vanilla Server")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 26px; font-weight: bold;")
        layout.addWidget(title)

        sub = QLabel("What would you like to do?")
        sub.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px;")
        layout.addWidget(sub)

        layout.addSpacing(30)

        cards = QWidget()
        cards.setStyleSheet("background: transparent;")
        cards_layout = QHBoxLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(20)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        create_card = OptionCard("Create Server", "Download and setup a new Minecraft server", "fa5s.plus-circle")
        create_card.clicked.connect(lambda: self.navigate_to("vanilla_create"))
        cards_layout.addWidget(create_card)

        run_card = OptionCard("Run Server", "Open and manage an existing server", "fa5s.play-circle")
        run_card.clicked.connect(lambda: self.navigate_to("vanilla_run"))
        cards_layout.addWidget(run_card)

        layout.addWidget(cards)
        layout.addStretch()
