"""
Logger Mixin - Utility for unified log handling in textboxes
Simplifies repetitive logging code in the GUI
"""

from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor


class LoggerMixin:
    """
    Mixin that provides logging functionality for GUI components

    Usage:
        class MyComponent(LoggerMixin):
            def __init__(self):
                self.log_textbox = QTextEdit(...)
    """

    # Standard colors for logs
    LOG_COLORS = {
        "normal": "#ffffff",
        "info": "#42A5F5",
        "success": "#4CAF50",
        "warning": "#FFA726",
        "error": "#EF5350"
    }

    @staticmethod
    def add_log(textbox: QTextEdit, message: str, log_type: str = "normal"):
        """
        Adds a message to the log with the appropriate color

        Args:
            textbox: The textbox where to add the log
            message: The message to add
            log_type: Log type (normal, info, success, warning, error)
        """
        # Validate log type
        if log_type not in LoggerMixin.LOG_COLORS:
            log_type = "normal"

        color = LoggerMixin.LOG_COLORS[log_type]

        # Move cursor to end
        cursor = textbox.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Set text format with color
        format = QTextCharFormat()
        format.setForeground(QColor(color))

        # Insert text with format
        cursor.insertText(message, format)

        # Update cursor and scroll to end
        textbox.setTextCursor(cursor)
        textbox.ensureCursorVisible()

        # Limit log size to prevent memory issues (keep last 100 lines)
        document = textbox.document()
        if document.blockCount() > 100:
            cursor = textbox.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(document.blockCount() - 100):
                cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()

    @staticmethod
    def clear_log(textbox: QTextEdit):
        """
        Clears all log content

        Args:
            textbox: The textbox to clear
        """
        textbox.clear()

    @staticmethod
    def add_separator(textbox: QTextEdit):
        """
        Adds a visual separator to the log

        Args:
            textbox: The textbox where to add the separator
        """
        LoggerMixin.add_log(textbox, "\n" + "=" * 50 + "\n\n", "info")
