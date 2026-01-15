"""
Footer link widget for navigation links.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
import qtawesome as qta


class FooterLink(QFrame):
    """Footer link button"""

    clicked = Signal()

    def __init__(self, title: str, subtitle: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(56)
        self._hovered = False
        self._setup_ui(title, subtitle, icon_name)
        self._apply_style()

    def _setup_ui(self, title: str, subtitle: str, icon_name: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        # Icon
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color="#8b949e").pixmap(24, 24))
        icon_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_label)

        # Text
        text_widget = QWidget()
        text_widget.setStyleSheet("background: transparent; border: none;")
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff; background: transparent; border: none;")
        text_layout.addWidget(title_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("font-size: 11px; color: #6e7681; background: transparent; border: none;")
        text_layout.addWidget(subtitle_label)

        layout.addWidget(text_widget)
        layout.addStretch()

        # Arrow
        arrow = QLabel()
        arrow.setPixmap(qta.icon("fa5s.chevron-right", color="#6e7681").pixmap(12, 12))
        arrow.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(arrow)

    def _apply_style(self):
        border = "#404040" if self._hovered else "#2d2d2d"
        bg = "#252525" if self._hovered else "#1c1c1c"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """)

    def enterEvent(self, event):
        self._hovered = True
        self._apply_style()

    def leaveEvent(self, event):
        self._hovered = False
        self._apply_style()

    def mousePressEvent(self, event):
        self.clicked.emit()
