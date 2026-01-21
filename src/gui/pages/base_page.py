"""
Base Page for PyCraft GUI.
Provides common functionality for all page components.
"""

from typing import Dict, Callable, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QLineEdit, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QTextCharFormat, QColor, QTextCursor

from ..widgets import NonPropagatingTextEdit, NonPropagatingScrollArea


class BasePage(QWidget):
    """
    Base class for all application pages.

    Provides:
    - Access to color scheme
    - Navigation callback
    - Common UI helper methods
    - Style generators
    """

    # Signal emitted when navigation is requested
    navigation_requested = Signal(str)

    def __init__(
        self,
        colors: Dict[str, str],
        navigate_callback: Optional[Callable[[str], None]] = None,
        parent=None
    ):
        """
        Initialize the base page.

        Args:
            colors: Color scheme dictionary
            navigate_callback: Callback for navigation (page_id) -> None
            parent: Parent widget
        """
        super().__init__(parent)
        self.colors = colors
        self._navigate_callback = navigate_callback
        self.setStyleSheet(f"background-color: {colors['bg_content']}; border: none;")

    def navigate_to(self, page_id: str):
        """Navigate to another page"""
        if self._navigate_callback:
            self._navigate_callback(page_id)
        self.navigation_requested.emit(page_id)

    # ============================================================
    # UI Helper Methods (extracted from main_window.py)
    # ============================================================

    def _section_frame(self, title: str) -> QFrame:
        """Create a styled section frame with title"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_card']};
                border: 1px solid {self.colors['border']};
                border-radius: 12px;
            }}
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(20, 16, 20, 16)
        frame_layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {self.colors['text']};
            font-size: 15px;
            font-weight: 600;
            background: transparent;
        """)
        frame_layout.addWidget(title_label)

        return frame

    def _styled_button(
        self,
        text: str,
        bg_color: str,
        text_color: str,
        width: int = 200,
        height: int = 42
    ) -> QPushButton:
        """Create a themed button with custom colors"""
        btn = QPushButton(text)
        btn.setFixedSize(width, height)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {self.colors.get('accent_hover', bg_color)};
            }}
            QPushButton:disabled {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text_muted']};
            }}
        """)
        return btn

    def _text_button(self, text: str) -> QPushButton:
        """Create a transparent text button for navigation (back buttons)"""
        btn = QPushButton(text)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colors['accent']};
                border: none;
                font-size: 13px;
                font-weight: 500;
                text-align: left;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {self.colors['accent_hover']};
            }}
        """)
        return btn

    def _input(self, placeholder: str = "", width: int = 400, height: int = 42) -> QLineEdit:
        """Create a themed text input field"""
        entry = QLineEdit()
        entry.setPlaceholderText(placeholder)
        entry.setFixedSize(width, height)
        entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 10px;
                padding: 0 14px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colors['accent']};
            }}
            QLineEdit::placeholder {{
                color: {self.colors['text_muted']};
            }}
        """)
        return entry

    def _console(self, height: int = 250) -> NonPropagatingTextEdit:
        """Create a styled read-only console output widget"""
        console = NonPropagatingTextEdit()
        console.setReadOnly(True)
        console.setFixedHeight(height)
        console.setStyleSheet(f"""
            QTextEdit {{
                background-color: #0d1117;
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 10px;
                padding: 12px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }}
        """)
        return console

    def _log(self, console, msg: str, level: str = "normal", max_lines: int = 500):
        """
        Log a message to a console widget with color.

        Args:
            console: QTextEdit widget to log to
            msg: Message to log
            level: Log level (normal, info, success, warning, error)
            max_lines: Maximum lines to keep in console
        """
        level_colors = {
            "normal": "#ffffff",
            "info": "#60a5fa",
            "success": "#4ade80",
            "warning": "#fbbf24",
            "error": "#f87171"
        }
        color = level_colors.get(level, "#ffffff")

        cursor = console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))

        cursor.insertText(msg, fmt)
        console.setTextCursor(cursor)
        console.ensureCursorVisible()

        # Limit lines to prevent memory issues
        doc = console.document()
        if doc.blockCount() > max_lines:
            cursor = console.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(doc.blockCount() - max_lines):
                cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def _scroll_style(self) -> str:
        """Generate stylesheet for scroll areas"""
        return f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {self.colors['bg_card']};
                width: 10px;
                border-radius: 5px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: #3a3a3a;
                border-radius: 5px;
                border: none;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                border: none;
            }}
            QScrollBar:horizontal {{
                height: 0px;
            }}
        """

    def _progress_style(self) -> str:
        """Generate stylesheet for progress bars"""
        return f"""
            QProgressBar {{
                background-color: {self.colors['bg_input']};
                border: none;
                border-radius: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {self.colors['accent']};
                border-radius: 6px;
            }}
        """
