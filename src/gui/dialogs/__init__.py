"""
PyCraft GUI Dialogs.
Modal dialog components for the application.
"""

from .crash_dialog import ServerCrashDialog
from .config_dialog import ServerConfigDialog

__all__ = [
    "ServerCrashDialog",
    "ServerConfigDialog",
]
