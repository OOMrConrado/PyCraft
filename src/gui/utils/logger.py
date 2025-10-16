"""
Logger Mixin - Utility for unified log handling in textboxes
Simplifies repetitive logging code in the GUI
"""

import customtkinter as ctk


class LoggerMixin:
    """
    Mixin that provides logging functionality for GUI components

    Usage:
        class MyComponent(LoggerMixin):
            def __init__(self):
                self.log_textbox = ctk.CTkTextbox(...)
                self._configure_log_tags(self.log_textbox)
    """

    # Standard colors for logs
    LOG_COLORS = {
        "normal": "white",
        "info": "#42A5F5",
        "success": "#4CAF50",
        "warning": "#FFA726",
        "error": "#EF5350"
    }

    @staticmethod
    def _configure_log_tags(textbox: ctk.CTkTextbox):
        """
        Configures color tags for a textbox

        Args:
            textbox: The textbox where to configure the tags
        """
        if hasattr(textbox, "_tags_configured"):
            return

        for tag_name, color in LoggerMixin.LOG_COLORS.items():
            textbox.tag_config(tag_name, foreground=color)

        textbox._tags_configured = True

    @staticmethod
    def add_log(textbox: ctk.CTkTextbox, message: str, log_type: str = "normal"):
        """
        Adds a message to the log with the appropriate color

        Args:
            textbox: The textbox where to add the log
            message: The message to add
            log_type: Log type (normal, info, success, warning, error)
        """
        # Configure tags if not configured
        LoggerMixin._configure_log_tags(textbox)

        # Validate log type
        if log_type not in LoggerMixin.LOG_COLORS:
            log_type = "normal"

        # Insert message with appropriate tag
        textbox.insert("end", message, log_type)
        textbox.see("end")

    @staticmethod
    def clear_log(textbox: ctk.CTkTextbox):
        """
        Clears all log content

        Args:
            textbox: The textbox to clear
        """
        textbox.delete("1.0", "end")

    @staticmethod
    def add_separator(textbox: ctk.CTkTextbox):
        """
        Adds a visual separator to the log

        Args:
            textbox: The textbox where to add the separator
        """
        LoggerMixin.add_log(textbox, "\n" + "="*50 + "\n\n", "info")
