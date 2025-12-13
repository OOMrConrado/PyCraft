"""
Widget Factory - Factory for common widgets with consistent styles
Reduces repetitive code and ensures visual consistency
"""

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QTextEdit, QScrollArea, QProgressBar, QVBoxLayout
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt
from typing import Optional, Callable


class WidgetFactory:
    """
    Factory for creating widgets with predefined and consistent styles

    Usage:
        button = WidgetFactory.create_button(
            parent, "Click me", style="primary"
        )
    """

    # Predefined button styles
    BUTTON_STYLES = {
        "primary": {"bg_color": "#2196F3", "hover_color": "#1976D2"},
        "success": {"bg_color": "#4CAF50", "hover_color": "#388E3C"},
        "danger": {"bg_color": "#f44336", "hover_color": "#d32f2f"},
        "warning": {"bg_color": "#FFA726", "hover_color": "#F57C00"},
        "secondary": {"bg_color": "#424242", "hover_color": "#616161"},
    }

    @staticmethod
    def create_button(
        parent: QWidget,
        text: str,
        callback: Optional[Callable] = None,
        style: str = "primary",
        width: int = 200,
        height: int = 35
    ) -> QPushButton:
        """
        Create a styled button

        Args:
            parent: Parent widget
            text: Button text
            callback: Function to call when clicked
            style: Predefined style (primary, success, danger, warning, secondary)
            width: Button width
            height: Button height

        Returns:
            The created button
        """
        style_config = WidgetFactory.BUTTON_STYLES.get(
            style, WidgetFactory.BUTTON_STYLES["primary"]
        )
        bg_color = style_config["bg_color"]
        hover_color = style_config["hover_color"]

        button = QPushButton(text, parent)
        button.setFixedSize(width, height)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        if callback:
            button.clicked.connect(callback)

        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                padding: 5px 15px;
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
                background-color: transparent;
            }}
        """)
        return label

    @staticmethod
    def create_title(parent: QWidget, text: str) -> QLabel:
        """
        Create a large title

        Args:
            parent: Parent widget
            text: Title text

        Returns:
            The title label
        """
        return WidgetFactory.create_label(
            parent, text, font_size=22, font_weight="bold"
        )

    @staticmethod
    def create_section_title(parent: QWidget, text: str) -> QLabel:
        """
        Create a section title

        Args:
            parent: Parent widget
            text: Title text

        Returns:
            The section title label
        """
        return WidgetFactory.create_label(
            parent, text, font_size=18, font_weight="bold"
        )

    @staticmethod
    def create_frame(
        parent: QWidget,
        bg_color: str = "#252525",
        corner_radius: int = 10
    ) -> QFrame:
        """
        Create a styled frame

        Args:
            parent: Parent widget
            bg_color: Background color
            corner_radius: Corner radius

        Returns:
            The created frame
        """
        frame = QFrame(parent)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: {corner_radius}px;
            }}
        """)
        return frame

    @staticmethod
    def create_scroll_area(
        parent: QWidget,
        width: int = 900,
        height: int = 600
    ) -> QScrollArea:
        """
        Create a scrollable area

        Args:
            parent: Parent widget
            width: Scroll area width
            height: Scroll area height

        Returns:
            The scrollable area
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
        """)
        return scroll

    @staticmethod
    def create_entry(
        parent: QWidget,
        placeholder: str = "",
        width: int = 400,
        height: int = 35
    ) -> QLineEdit:
        """
        Create an entry field

        Args:
            parent: Parent widget
            placeholder: Placeholder text
            width: Field width
            height: Field height

        Returns:
            The entry field
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
        font_family: str = "Consolas",
        font_size: int = 11,
        read_only: bool = False
    ) -> QTextEdit:
        """
        Create a textbox for logs/console

        Args:
            parent: Parent widget
            width: Textbox width
            height: Textbox height
            font_family: Font family
            font_size: Font size
            read_only: Whether the textbox is read-only

        Returns:
            The created textbox
        """
        textbox = QTextEdit(parent)
        textbox.setFixedSize(width, height)
        textbox.setReadOnly(read_only)
        textbox.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px;
                font-family: '{font_family}', 'Courier New', monospace;
                font-size: {font_size}px;
            }}
            QTextEdit:focus {{
                border: 1px solid #2196F3;
            }}
            QScrollBar:vertical {{
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #555555;
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #666666;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        return textbox

    @staticmethod
    def create_progress_bar(
        parent: QWidget,
        width: int = 400,
        height: int = 20
    ) -> QProgressBar:
        """
        Create a progress bar

        Args:
            parent: Parent widget
            width: Progress bar width
            height: Progress bar height

        Returns:
            The progress bar
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

    @staticmethod
    def create_separator(parent: QWidget, height: int = 2) -> QFrame:
        """
        Create a horizontal separator

        Args:
            parent: Parent widget
            height: Separator height

        Returns:
            The separator (thin frame)
        """
        separator = QFrame(parent)
        separator.setFixedHeight(height)
        separator.setStyleSheet("""
            QFrame {
                background-color: #404040;
                border: none;
            }
        """)
        return separator
