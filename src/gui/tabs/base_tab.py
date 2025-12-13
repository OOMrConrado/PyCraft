"""
Base module with common utilities for all tabs
"""

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QTextEdit, QScrollArea, QVBoxLayout, QProgressBar
)
from PySide6.QtGui import QFont, QColor, QPalette, QTextCharFormat, QTextCursor
from PySide6.QtCore import Qt


class BaseTab:
    """Base class with common utilities for all tabs"""

    # Common color palette
    COLORS = {
        "bg_primary": "#1a1a1a",
        "bg_secondary": "#252525",
        "bg_tertiary": "#2d2d2d",
        "accent": "#4CAF50",
        "accent_light": "#81C784",
        "warning": "#FFA726",
        "error": "#EF5350",
        "info": "#42A5F5",
        "border": "#404040",
        "text_primary": "#ffffff",
        "text_secondary": "#888888",
    }

    def __init__(self, parent: QWidget):
        """
        Initialize the base tab

        Args:
            parent: The parent widget where this tab will be created
        """
        self.parent = parent

    @staticmethod
    def create_button(
        parent: QWidget,
        text: str,
        width: int = 200,
        height: int = 35,
        bg_color: str = "#2196F3",
        hover_color: str = "#1976D2",
        text_color: str = "#ffffff"
    ) -> QPushButton:
        """
        Create a styled button

        Args:
            parent: Parent widget
            text: Button text
            width: Button width
            height: Button height
            bg_color: Background color
            hover_color: Hover background color
            text_color: Text color

        Returns:
            The created button
        """
        button = QPushButton(text, parent)
        button.setFixedSize(width, height)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #555555;
                color: #888888;
            }}
        """)
        return button

    @staticmethod
    def create_label(
        parent: QWidget,
        text: str,
        font_size: int = 12,
        font_weight: str = "normal",
        text_color: str = "#ffffff"
    ) -> QLabel:
        """
        Create a styled label

        Args:
            parent: Parent widget
            text: Label text
            font_size: Font size
            font_weight: Font weight (normal, bold)
            text_color: Text color

        Returns:
            The created label
        """
        label = QLabel(text, parent)
        weight = "bold" if font_weight == "bold" else "normal"
        label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-size: {font_size}px;
                font-weight: {weight};
            }}
        """)
        return label

    @staticmethod
    def create_frame(parent: QWidget, bg_color: str = "#252525") -> QFrame:
        """
        Create a styled frame

        Args:
            parent: Parent widget
            bg_color: Background color

        Returns:
            The created frame
        """
        frame = QFrame(parent)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
            }}
        """)
        return frame

    @staticmethod
    def create_entry(
        parent: QWidget,
        placeholder: str = "",
        width: int = 400,
        height: int = 35
    ) -> QLineEdit:
        """
        Create a styled entry field

        Args:
            parent: Parent widget
            placeholder: Placeholder text
            width: Field width
            height: Field height

        Returns:
            The created entry field
        """
        entry = QLineEdit(parent)
        entry.setPlaceholderText(placeholder)
        entry.setFixedSize(width, height)
        entry.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
            QLineEdit::placeholder {
                color: #666666;
            }
        """)
        return entry

    @staticmethod
    def create_textbox(
        parent: QWidget,
        width: int = 800,
        height: int = 200,
        read_only: bool = False
    ) -> QTextEdit:
        """
        Create a styled textbox

        Args:
            parent: Parent widget
            width: Textbox width
            height: Textbox height
            read_only: Whether the textbox is read-only

        Returns:
            The created textbox
        """
        textbox = QTextEdit(parent)
        textbox.setFixedSize(width, height)
        textbox.setReadOnly(read_only)
        textbox.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
            QTextEdit:focus {
                border: 1px solid #2196F3;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        return textbox

    @staticmethod
    def create_scroll_area(parent: QWidget, width: int = 900, height: int = 600) -> QScrollArea:
        """
        Create a styled scroll area

        Args:
            parent: Parent widget
            width: Scroll area width
            height: Scroll area height

        Returns:
            The created scroll area
        """
        scroll = QScrollArea(parent)
        scroll.setFixedSize(width, height)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #2d2d2d;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #555555;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #666666;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        return scroll

    @staticmethod
    def create_progress_bar(parent: QWidget, width: int = 400, height: int = 20) -> QProgressBar:
        """
        Create a styled progress bar

        Args:
            parent: Parent widget
            width: Progress bar width
            height: Progress bar height

        Returns:
            The created progress bar
        """
        progress = QProgressBar(parent)
        progress.setFixedSize(width, height)
        progress.setValue(0)
        progress.setTextVisible(False)
        progress.setStyleSheet("""
            QProgressBar {
                background-color: #2d2d2d;
                border: none;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
        """)
        return progress

    def add_log(self, textbox: QTextEdit, message: str, log_type: str = "normal"):
        """
        Add a message to the log with the appropriate color

        Args:
            textbox: The textbox where to add the log
            message: The message to add
            log_type: Log type (normal, info, success, warning, error)
        """
        colors = {
            "normal": "#ffffff",
            "info": "#42A5F5",
            "success": "#4CAF50",
            "warning": "#FFA726",
            "error": "#EF5350"
        }

        color = colors.get(log_type, "#ffffff")

        cursor = textbox.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        format = QTextCharFormat()
        format.setForeground(QColor(color))

        cursor.insertText(message, format)
        textbox.setTextCursor(cursor)
        textbox.ensureCursorVisible()
