"""
Sidebar navigation button widget.
"""

from PySide6.QtWidgets import QPushButton, QLabel
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QCursor
import qtawesome as qta


class SidebarButton(QPushButton):
    """Navigation button for sidebar"""

    def __init__(self, text: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.setText(f"  {text}")
        self.icon_name = icon_name
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(48)
        self.setIcon(qta.icon(icon_name, color="#8b949e"))
        self.setIconSize(QSize(20, 20))
        self._apply_style(False)

        # Notification dot (hidden by default)
        self._notification_dot = QLabel(self)
        self._notification_dot.setFixedSize(8, 8)
        self._notification_dot.setStyleSheet("background-color: #fbbf24; border-radius: 4px;")
        self._notification_dot.hide()

        # Blink timer for notification
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._toggle_dot_visibility)
        self._dot_visible = True

    def _toggle_dot_visibility(self):
        """Toggle dot visibility for blinking effect"""
        self._dot_visible = not self._dot_visible
        self._notification_dot.setVisible(self._dot_visible)

    def show_notification(self, show: bool = True):
        """Show or hide the notification dot"""
        if show:
            self._notification_dot.show()
        else:
            self._notification_dot.hide()

    def resizeEvent(self, event):
        """Position the notification dot when button is resized"""
        super().resizeEvent(event)
        # Position dot at the right side of the button
        self._notification_dot.move(self.width() - 20, (self.height() - 8) // 2)

    def _apply_style(self, selected: bool):
        if selected:
            self.setIcon(qta.icon(self.icon_name, color="#4ade80"))
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(74, 222, 128, 0.1);
                    color: #ffffff;
                    border: none;
                    border-left: 3px solid #4ade80;
                    border-radius: 0px;
                    text-align: left;
                    padding-left: 15px;
                    font-size: 14px;
                    font-weight: 500;
                }
            """)
        else:
            self.setIcon(qta.icon(self.icon_name, color="#8b949e"))
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #8b949e;
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                    text-align: left;
                    padding-left: 15px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                    color: #ffffff;
                }
            """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._apply_style(checked)
