"""
Toast notification widget for temporary messages.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QCursor
import qtawesome as qta


class ToastNotification(QFrame):
    """Toast notification widget that appears temporarily"""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 70)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._setup_ui()
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.timeout.connect(self._fade_out)
        self._opacity = 1.0
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._do_fade)
        self._fading_out = False

    def _setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #fbbf24;
                border-radius: 10px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Icon
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon("fa5s.arrow-circle-up", color="#fbbf24").pixmap(24, 24))
        icon_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_label)

        # Text container
        text_widget = QWidget()
        text_widget.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self._title_label = QLabel("Update available")
        self._title_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #fbbf24; background: transparent; border: none;")
        text_layout.addWidget(self._title_label)

        self._subtitle_label = QLabel("Go to Settings to update")
        self._subtitle_label.setStyleSheet("font-size: 11px; color: #8b949e; background: transparent; border: none;")
        text_layout.addWidget(self._subtitle_label)

        layout.addWidget(text_widget)
        layout.addStretch()

        # Close button
        close_btn = QPushButton("x")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6e7681;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.close_immediately)
        layout.addWidget(close_btn)

    def show_update(self, version: str, duration_ms: int = 15000):
        """Show the toast with update info"""
        self._title_label.setText(f"Update available: v{version}")
        self._opacity = 1.0
        self._fading_out = False
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self._auto_hide_timer.start(duration_ms)

    def close_immediately(self):
        """Close the toast immediately without animation"""
        self._auto_hide_timer.stop()
        self._fade_timer.stop()
        self.hide()

    def _fade_out(self):
        """Start fade out animation"""
        self._auto_hide_timer.stop()
        self._fading_out = True
        self._fade_timer.start(30)  # 30ms interval for smooth fade

    def _do_fade(self):
        """Perform fade animation step"""
        self._opacity -= 0.05
        if self._opacity <= 0:
            self._fade_timer.stop()
            self.hide()
            self._opacity = 1.0
        else:
            self.setWindowOpacity(self._opacity)

    def mousePressEvent(self, event):
        if not self._fading_out:
            self.clicked.emit()
            self.close_immediately()
