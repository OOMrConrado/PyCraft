"""
Option card widget for selection pages.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
import qtawesome as qta


class OptionCard(QFrame):
    """Clickable card for selecting options"""

    clicked = Signal()

    def __init__(self, title: str, description: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(260, 160)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._hovered = False
        self._setup_ui(title, description, icon_name)
        self._apply_style()

    def _setup_ui(self, title: str, description: str, icon_name: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Icon
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color="#4ade80").pixmap(40, 40))
        icon_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_label)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 12px;
            color: #8b949e;
            background: transparent;
            border: none;
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch()

    def _apply_style(self):
        if self._hovered:
            self.setStyleSheet("""
                QFrame {
                    background-color: #2a2a2a;
                    border: 2px solid #4ade80;
                    border-radius: 16px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #222222;
                    border: 1px solid #333333;
                    border-radius: 16px;
                }
            """)

    def enterEvent(self, event):
        self._hovered = True
        self._apply_style()

    def leaveEvent(self, event):
        self._hovered = False
        self._apply_style()

    def mousePressEvent(self, event):
        self.clicked.emit()
