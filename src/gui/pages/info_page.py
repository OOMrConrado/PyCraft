"""
Info & Help Page.
Displays help information and system requirements.
"""

from typing import Dict, Callable, Optional

from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel, QScrollArea

from .base_page import BasePage


class InfoPage(BasePage):
    """Info and help page"""

    def __init__(
        self,
        colors: Dict[str, str],
        navigate_callback: Optional[Callable[[str], None]] = None,
        parent=None
    ):
        super().__init__(colors, navigate_callback, parent)
        self._setup_ui()

    def _setup_ui(self):
        """Build the info page UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._scroll_style())

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        title = QLabel("Info & Help")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 26px; font-weight: bold;")
        layout.addWidget(title)

        sections = [
            (
                "Playing with Friends",
                "1. Install Hamachi or ZeroTier VPN\n"
                "2. Create a network and share with friends\n"
                "3. Friends connect using your VPN IP\n"
                "4. Disable firewall or allow Minecraft\n\n"
                "PyCraft sets online-mode=false automatically."
            ),
            (
                "Common Issues",
                "Server won't start:\n"
                "- Check Java in the Management section\n"
                "- Verify enough RAM is available\n\n"
                "Friends can't connect:\n"
                "- Ensure same VPN network\n"
                "- Check firewall settings\n"
                "- Use correct IP address"
            ),
            (
                "System Requirements",
                "- Java 17+ (installable via Java Management)\n"
                "- 4GB RAM minimum (8GB for modded)\n"
                "- 2GB disk space\n"
                "- Internet connection"
            ),
        ]

        for sec_title, sec_content in sections:
            frame = self._section_frame(sec_title)
            label = QLabel(sec_content)
            label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px; background: transparent;")
            label.setWordWrap(True)
            frame.layout().addWidget(label)
            layout.addWidget(frame)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
