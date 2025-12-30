"""
PyCraft Main Window - Modern UI with Sidebar Navigation
Inspired by Revision Tool design
"""

import sys
import os
import time
import threading
import webbrowser
import subprocess
import json
from typing import Optional, List, Dict
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QFrame,
    QScrollArea, QProgressBar, QFileDialog, QMessageBox, QDialog,
    QSlider, QStackedWidget, QInputDialog,
    QStyle, QProxyStyle, QComboBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QUrl
from PySide6.QtGui import QPixmap, QIcon, QTextCharFormat, QColor, QTextCursor, QCursor, QFont, QDesktopServices


class NoFocusRectStyle(QProxyStyle):
    """Custom style that removes focus rectangles from all widgets"""

    def drawPrimitive(self, element, option, painter, widget=None):
        # Skip drawing focus rectangles
        if element == QStyle.PrimitiveElement.PE_FrameFocusRect:
            return
        super().drawPrimitive(element, option, painter, widget)


class NonPropagatingScrollArea(QScrollArea):
    """ScrollArea that doesn't propagate wheel events to parent when at limits"""

    def wheelEvent(self, event):
        # Get the vertical scrollbar
        scrollbar = self.verticalScrollBar()

        # Check if we're at the limits
        at_top = scrollbar.value() == scrollbar.minimum()
        at_bottom = scrollbar.value() == scrollbar.maximum()

        # Determine scroll direction
        scrolling_up = event.angleDelta().y() > 0
        scrolling_down = event.angleDelta().y() < 0

        # If at limit and trying to scroll past it, accept event to prevent propagation
        if (at_top and scrolling_up) or (at_bottom and scrolling_down):
            event.accept()
            return

        # Otherwise, handle normally
        super().wheelEvent(event)


class NonPropagatingTextEdit(QTextEdit):
    """TextEdit that doesn't propagate wheel events to parent when at limits"""

    def wheelEvent(self, event):
        scrollbar = self.verticalScrollBar()
        at_top = scrollbar.value() == scrollbar.minimum()
        at_bottom = scrollbar.value() == scrollbar.maximum()
        scrolling_up = event.angleDelta().y() > 0
        scrolling_down = event.angleDelta().y() < 0

        if (at_top and scrolling_up) or (at_bottom and scrolling_down):
            event.accept()
            return

        super().wheelEvent(event)

import qtawesome as qta

from ..core.api import MinecraftAPIHandler, APIConfig
from ..core.download import ServerDownloader
from ..managers.server import ServerManager
from ..managers.modpack import ModpackManager
from ..managers.java import JavaManager
from ..utils import system_utils
from ..utils.updater import UpdateChecker
from ..__version__ import __version__


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
        close_btn = QPushButton("×")
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


class PyCraftGUI(QMainWindow):
    """Main PyCraft Application Window"""

    log_signal = Signal(str, str, str)
    progress_signal = Signal(int)
    status_signal = Signal(str, str)
    # Java modal signals (thread-safe)
    java_status_signal = Signal(str)
    java_progress_signal = Signal(int, int)  # value, maximum
    java_console_signal = Signal(str, str)  # text, color
    java_complete_signal = Signal(bool)  # success
    modpack_results_signal = Signal(object)  # modpack search results
    mp_icon_signal = Signal(str, object)  # project_id, QPixmap
    mp_pagination_signal = Signal(int)  # total results
    client_mp_results_signal = Signal(object)  # client modpack search results
    client_mp_pagination_signal = Signal(int)  # client total results
    version_loaded_signal = Signal(object, object)  # versions list, callback function
    server_crashed_signal = Signal(str)  # server path for crash modal
    vanilla_server_stopped_signal = Signal(bool)  # success (True = normal stop, False = crash)
    modpack_server_stopped_signal = Signal(bool)  # success (True = normal stop, False = crash)
    vanilla_server_started_signal = Signal(bool)  # success
    modpack_server_started_signal = Signal(bool)  # success
    # Modal signals (thread-safe)
    vanilla_install_success_signal = Signal(str, str)  # version, folder
    server_modpack_install_success_signal = Signal(str, str, str)  # name, mc_version, loader
    client_modpack_install_success_signal = Signal(str, str, str, str, str)  # name, mc_ver, loader, loader_ver, path
    update_check_complete_signal = Signal(object)  # update_info dict or None
    update_download_progress_signal = Signal(int, float, float)  # progress%, downloaded_mb, total_mb
    update_download_complete_signal = Signal(str)  # installer_path or empty string if failed
    startup_update_check_signal = Signal(object)  # update_info dict or None (for startup check)

    def __init__(self):
        super().__init__()

        # Color scheme
        self.colors = {
            "bg_main": "#141414",
            "bg_sidebar": "#1a1a1a",
            "bg_content": "#1e1e1e",
            "bg_card": "#222222",
            "bg_input": "#2a2a2a",
            "border": "#333333",
            "border_hover": "#404040",
            "text": "#ffffff",
            "text_secondary": "#8b949e",
            "text_muted": "#6e7681",
            "accent": "#4ade80",
            "accent_hover": "#22c55e",
            "blue": "#60a5fa",
            "yellow": "#fbbf24",
            "red": "#f87171",
        }

        # Managers
        self.api_handler = MinecraftAPIHandler()
        self.downloader = ServerDownloader()
        self.server_manager: Optional[ServerManager] = None
        self.modpack_manager = ModpackManager()
        self.java_manager = JavaManager()
        self.api_config = APIConfig()
        self.update_checker = UpdateChecker(__version__)

        cf_key = self.api_config.get_curseforge_key()
        if cf_key:
            self.modpack_manager.set_curseforge_api_key(cf_key)

        # State
        self.versions_list = []
        self.filtered_versions = []
        self.selected_version = None
        self.server_folder = None
        self.is_server_configured = False
        self.detected_mc_version = None

        self.modpack_results = []
        self.selected_modpack = None
        self.modpack_folder = None
        self.mp_current_page = 1
        self.mp_total_results = 0
        self.mp_search_query = ""
        self.mp_icon_cache = {}  # Cache for modpack icons

        # Client modpack install state
        self.client_mp_results = []
        self.client_selected_modpack = None
        self.client_mp_current_page = 1
        self.client_mp_total_results = 0
        self.client_mp_search_query = ""

        # Debounce timers for real-time search (300ms delay)
        self.mp_search_timer = QTimer()
        self.mp_search_timer.setSingleShot(True)
        self.mp_search_timer.setInterval(350)
        self.mp_search_timer.timeout.connect(self._search_modpacks)

        self.client_mp_search_timer = QTimer()
        self.client_mp_search_timer.setSingleShot(True)
        self.client_mp_search_timer.setInterval(350)
        self.client_mp_search_timer.timeout.connect(self._search_client_modpacks)

        # Version selection state
        self.selected_mp_version = None  # For server install
        self.client_selected_mp_version = None  # For client install

        # Provider selection state
        self.mp_selected_provider = "modrinth"  # For server modpack install
        self.client_mp_selected_provider = "modrinth"  # For client modpack install

        self.modpack_server_manager: Optional[ServerManager] = None
        self.modpack_server_path = None
        self.is_modpack_configured = False

        self.vanilla_ram = 2048
        self.modpack_ram = 4096

        self.sidebar_buttons = {}

        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._load_versions()

    def _setup_window(self):
        """Configure window properties"""
        self.setWindowTitle("PyCraft")
        self.setFixedSize(1100, 750)
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors['bg_main']};
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        try:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            icon_path = os.path.join(base_path, "PyCraft-Files", "icon.ico")

            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

    def _connect_signals(self):
        """Connect thread-safe signals"""
        self.log_signal.connect(self._on_log)
        self.progress_signal.connect(self._on_progress)
        self.status_signal.connect(self._on_status)
        self.modpack_results_signal.connect(self._show_mp_results)
        self.mp_icon_signal.connect(self._on_mp_icon_loaded)
        self.mp_pagination_signal.connect(self._update_mp_pagination)
        self.client_mp_results_signal.connect(self._show_client_mp_results)
        self.client_mp_pagination_signal.connect(self._update_client_mp_pagination)
        self.version_loaded_signal.connect(self._on_versions_loaded)
        self.server_crashed_signal.connect(self._show_server_crash_dialog)
        self.vanilla_server_stopped_signal.connect(self._on_vanilla_server_stopped)
        self.modpack_server_stopped_signal.connect(self._on_modpack_server_stopped)
        self.vanilla_server_started_signal.connect(self._on_vanilla_server_started)
        self.modpack_server_started_signal.connect(self._on_modpack_server_started)
        # Modal signals - use lambdas with QTimer to avoid blocking
        self.vanilla_install_success_signal.connect(
            lambda v, f: QTimer.singleShot(100, lambda: self._show_vanilla_install_success(v, f))
        )
        self.server_modpack_install_success_signal.connect(
            lambda n, m, l: QTimer.singleShot(100, lambda: self._show_server_install_notice(n, m, l))
        )
        self.client_modpack_install_success_signal.connect(
            lambda n, m, l, v, p: QTimer.singleShot(100, lambda: self._show_client_install_success(n, m, l, v, p))
        )

    def _on_log(self, msg: str, level: str, target: str):
        """Handle log signal"""
        targets = {
            "v_create": getattr(self, "vanilla_create_console", None),
            "v_run": getattr(self, "vanilla_run_console", None),
            "m_install": getattr(self, "modpack_install_console", None),
            "m_run": getattr(self, "modpack_run_console", None),
            "c_install": getattr(self, "client_install_console", None),
        }
        if target in targets and targets[target]:
            self._log(targets[target], msg, level)

        # Detect when server is ready (shows "Done" message)
        if target in ("v_run", "m_run") and "Done" in msg and "For help, type" in msg:
            self._show_server_ready_notification(target)

    def _on_progress(self, value: int):
        """Handle progress signal"""
        if hasattr(self, "active_progress"):
            self.active_progress.setValue(value)
        if hasattr(self, "active_progress_label"):
            self.active_progress_label.setText(f"{value}/100%")

    def _on_status(self, msg: str, color: str):
        """Handle status signal"""
        if hasattr(self, "active_status"):
            self.active_status.setText(msg)
            self.active_status.setStyleSheet(f"color: {color}; font-size: 12px;")

    def _show_server_ready_notification(self, target: str):
        """Show notification when server is ready"""
        server_type = "Vanilla" if target == "v_run" else "Modpack"

        # Create a non-blocking message box
        msg = QMessageBox(self)
        msg.setWindowTitle("Server Ready")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"{server_type} server is ready!")
        msg.setInformativeText("Players can now connect.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setDefaultButton(QMessageBox.StandardButton.Ok)

        # Style the message box
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.colors['bg_content']};
                color: {self.colors['text']};
            }}
            QMessageBox QLabel {{
                color: {self.colors['text']};
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {self.colors['accent']};
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colors['accent_hover']};
            }}
        """)

        msg.show()

    def _build_ui(self):
        """Build main UI structure"""
        central = QWidget()
        central.setStyleSheet(f"background-color: {self.colors['bg_main']};")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        main_layout.addWidget(self._build_sidebar())

        # Content
        content_wrapper = QWidget()
        content_wrapper.setObjectName("contentWrapper")
        content_wrapper.setStyleSheet(f"""
            #contentWrapper {{
                background-color: {self.colors['bg_content']};
                border: none;
            }}
        """)
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.page_stack = QStackedWidget()
        self.page_stack.setStyleSheet("QStackedWidget { border: none; background: transparent; }")
        content_layout.addWidget(self.page_stack, 1)

        # Pages
        self.page_stack.addWidget(self._build_home_page())          # 0
        self.page_stack.addWidget(self._build_vanilla_page())       # 1
        self.page_stack.addWidget(self._build_modded_page())        # 2
        self.page_stack.addWidget(self._build_info_page())          # 3
        self.page_stack.addWidget(self._build_settings_page())      # 4
        self.page_stack.addWidget(self._build_vanilla_create())     # 5
        self.page_stack.addWidget(self._build_vanilla_run())        # 6
        self.page_stack.addWidget(self._build_modpack_install())    # 7
        self.page_stack.addWidget(self._build_modpack_run())        # 8
        self.page_stack.addWidget(self._build_client_install())     # 9
        self.page_stack.addWidget(self._build_java_management())    # 10
        self.page_stack.addWidget(self._build_modpack_management()) # 11

        # Footer (will be shown/hidden based on current page)
        self.footer = self._build_footer()
        content_layout.addWidget(self.footer)
        self.footer.setVisible(True)  # Visible on home by default

        main_layout.addWidget(content_wrapper, 1)

        # Remove borders from ALL QLabels
        self._remove_label_borders()

        # Toast notification for updates (positioned in bottom-right)
        self.update_toast = ToastNotification(self)
        self.update_toast.hide()
        self.update_toast.clicked.connect(lambda: self._go_to("settings"))
        self.startup_update_check_signal.connect(self._on_startup_update_check)

        # Store pending update info
        self._pending_update_info = None

        # Check for updates on startup (small delay to let UI load first)
        QTimer.singleShot(500, self._check_for_updates_startup)

    def _position_toast(self):
        """Position the toast in the bottom-right corner"""
        if self.update_toast:
            margin = 20
            x = self.width() - self.update_toast.width() - margin
            y = self.height() - self.update_toast.height() - margin - 80  # 80 for footer
            self.update_toast.move(x, y)

    def resizeEvent(self, event):
        """Handle window resize to reposition toast"""
        super().resizeEvent(event)
        self._position_toast()

    def _check_for_updates_startup(self):
        """Check for updates in background on startup"""
        def check_thread():
            try:
                update_info = self.update_checker.check_for_updates()
            except Exception:
                update_info = None
            self.startup_update_check_signal.emit(update_info)

        threading.Thread(target=check_thread, daemon=True).start()

    def _on_startup_update_check(self, update_info):
        """Handle startup update check result"""
        if update_info:
            # Store update info for later use
            self._pending_update_info = update_info
            new_version = update_info['version']

            # Show blinking dot on Settings tab
            self.sidebar_buttons["settings"].show_notification(True)

            # Show toast notification
            self._position_toast()
            self.update_toast.show_update(new_version, duration_ms=15000)

    def _remove_label_borders(self):
        """Remove borders from all QLabel widgets to fix PySide6 rendering bug"""
        for label in self.findChildren(QLabel):
            # Preserve existing style but add border: none
            current_style = label.styleSheet()
            if "border" not in current_style.lower():
                label.setStyleSheet(current_style + " border: none;")
            elif "border: none" not in current_style.lower() and "border:none" not in current_style.lower():
                label.setStyleSheet(current_style.replace("}", " border: none; }") if "}" in current_style else current_style + " border: none;")

    def _build_sidebar(self) -> QWidget:
        """Build sidebar navigation"""
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_sidebar']};
                border-right: 1px solid {self.colors['border']};
            }}
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(110)
        header.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 20, 20, 15)

        # Logo circle
        logo_frame = QFrame()
        logo_frame.setFixedSize(78, 78)
        logo_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_card']};
                border-radius: 39px;
                border: 2px solid {self.colors['accent']};
            }}
        """)

        # Use layout for consistent centering across different DPI/screens
        logo_inner_layout = QVBoxLayout(logo_frame)
        logo_inner_layout.setContentsMargins(0, 0, 0, 0)
        logo_inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        try:
            logo_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "PyCraft-Files", "logo.png"
            )
            if os.path.exists(logo_path):
                logo_label = QLabel()
                pix = QPixmap(logo_path).scaled(74, 74, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(pix)
                logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                logo_label.setStyleSheet("background: transparent; border: none;")
                logo_label.setFixedSize(74, 74)
                logo_inner_layout.addWidget(logo_label)
        except Exception:
            pass

        header_layout.addWidget(logo_frame)

        title_widget = QLabel()
        title_widget.setStyleSheet("background: transparent; margin-left: 12px;")
        title_widget.setText(f"""
            <div style="line-height: 1.1;">
                <span style="font-size: 18px; font-weight: bold; color: {self.colors['text']};">PyCraft</span><br>
                <span style="font-size: 11px; color: {self.colors['text_secondary']};">Server Manager</span>
            </div>
        """)

        header_layout.addWidget(title_widget)
        header_layout.addStretch()
        layout.addWidget(header)

        # Horizontal separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {self.colors['border']}; border: none;")
        layout.addWidget(separator)

        # Navigation
        nav_widget = QWidget()
        nav_widget.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 15, 0, 5)
        nav_layout.setSpacing(2)

        nav_items = [
            ("home", "Home", "fa5s.home"),
            ("vanilla", "Vanilla Server", "fa5s.cube"),
            ("modded", "Modded Server", "fa5s.puzzle-piece"),
            ("client_modpacks", "Client Modpacks", "fa5s.desktop"),
        ]

        for page_id, text, icon in nav_items:
            btn = SidebarButton(text, icon)
            btn.clicked.connect(lambda _, p=page_id: self._go_to(p))
            self.sidebar_buttons[page_id] = btn
            nav_layout.addWidget(btn)

        # Management section label
        mgmt_label = QLabel("  Management")
        mgmt_label.setStyleSheet(f"""
            color: {self.colors['text_muted']};
            font-size: 11px;
            font-weight: bold;
            padding: 12px 15px 6px 15px;
            text-transform: uppercase;
            background: transparent;
        """)
        nav_layout.addWidget(mgmt_label)

        # Management items
        mgmt_items = [
            ("java_management", "Java", "fa5s.coffee"),
            ("modpack_management", "Modpacks", "fa5s.box-open"),
        ]

        for page_id, text, icon in mgmt_items:
            btn = SidebarButton(text, icon)
            btn.clicked.connect(lambda _, p=page_id: self._go_to(p))
            self.sidebar_buttons[page_id] = btn
            nav_layout.addWidget(btn)

        layout.addWidget(nav_widget)
        layout.addStretch()

        # Bottom nav
        bottom = QWidget()
        bottom.setStyleSheet("background: transparent;")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 10, 0, 20)
        bottom_layout.setSpacing(2)

        settings_btn = SidebarButton("Settings", "fa5s.cog")
        settings_btn.clicked.connect(lambda: self._go_to("settings"))
        self.sidebar_buttons["settings"] = settings_btn
        bottom_layout.addWidget(settings_btn)

        layout.addWidget(bottom)

        self.sidebar_buttons["home"].setChecked(True)

        return sidebar

    def _build_footer(self) -> QWidget:
        """Build footer with links"""
        footer = QWidget()
        footer.setFixedHeight(80)
        footer.setStyleSheet(f"background-color: {self.colors['bg_main']}; border: none;")

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(25, 12, 25, 12)
        layout.setSpacing(15)

        github = FooterLink("GitHub", "Source Code", "fa5b.github")
        github.clicked.connect(lambda: self._open_url("https://github.com/OOMrConrado/PyCraft"))
        layout.addWidget(github)

        documentation = FooterLink("Documentation", "User Guide", "fa5s.book")
        documentation.clicked.connect(lambda: self._open_url("https://pycraft-web.vercel.app/guide/introduction"))
        layout.addWidget(documentation)

        support = FooterLink("Support", "Report Issue", "fa5s.bug")
        support.clicked.connect(lambda: self._open_url("https://github.com/OOMrConrado/PyCraft/issues/new"))
        layout.addWidget(support)

        return footer

    def _build_home_page(self) -> QWidget:
        """Build home/welcome page"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']}; border: none;")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 20)

        # Welcome card
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_card']};
                border-radius: 16px;
                border: 1px solid {self.colors['border']};
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(8)

        welcome = QLabel("Welcome to")
        welcome.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px; background: transparent;")
        card_layout.addWidget(welcome)

        title = QLabel("PyCraft")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 36px; font-weight: bold; background: transparent;")
        card_layout.addWidget(title)

        desc = QLabel("A modern tool to create and manage Minecraft servers")
        desc.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px; background: transparent;")
        card_layout.addWidget(desc)

        card_layout.addSpacing(24)

        # Buttons
        btn_container = QWidget()
        btn_container.setStyleSheet("background: transparent;")
        btn_layout = QVBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)

        vanilla_btn = self._styled_button("Create Vanilla Server", self.colors['bg_input'], self.colors['text'])
        vanilla_btn.clicked.connect(lambda: self._go_to("vanilla"))
        btn_layout.addWidget(vanilla_btn)

        modded_btn = self._styled_button("Install Modpack Server", self.colors['accent'], "#000000")
        modded_btn.clicked.connect(lambda: self._go_to("modded"))
        btn_layout.addWidget(modded_btn)

        card_layout.addWidget(btn_container)

        layout.addWidget(card)
        layout.addStretch()

        return page

    def _build_vanilla_page(self) -> QWidget:
        """Build vanilla server selection page"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']}; border: none;")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 20)

        title = QLabel("Vanilla Server")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 26px; font-weight: bold;")
        layout.addWidget(title)

        sub = QLabel("What would you like to do?")
        sub.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px;")
        layout.addWidget(sub)

        layout.addSpacing(30)

        cards = QWidget()
        cards.setStyleSheet("background: transparent;")
        cards_layout = QHBoxLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(20)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        create_card = OptionCard("Create Server", "Download and setup a new Minecraft server", "fa5s.plus-circle")
        create_card.clicked.connect(lambda: self._go_to("vanilla_create"))
        cards_layout.addWidget(create_card)

        run_card = OptionCard("Run Server", "Open and manage an existing server", "fa5s.play-circle")
        run_card.clicked.connect(lambda: self._go_to("vanilla_run"))
        cards_layout.addWidget(run_card)

        layout.addWidget(cards)
        layout.addStretch()

        return page

    def _build_modded_page(self) -> QWidget:
        """Build modded server selection page"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']}; border: none;")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 20)

        title = QLabel("Modded Server")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 26px; font-weight: bold;")
        layout.addWidget(title)

        sub = QLabel("What would you like to do?")
        sub.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px;")
        layout.addWidget(sub)

        layout.addSpacing(30)

        cards = QWidget()
        cards.setStyleSheet("background: transparent;")
        cards_layout = QVBoxLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(15)

        # First row: Install Server and Run Server
        row1 = QWidget()
        row1.setStyleSheet("background: transparent;")
        row1_layout = QHBoxLayout(row1)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(20)
        row1_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        install_card = OptionCard("Install Server", "Download modpack server from Modrinth", "fa5s.server")
        install_card.clicked.connect(lambda: self._go_to("modpack_install"))
        row1_layout.addWidget(install_card)

        run_card = OptionCard("Run Server", "Manage an existing modded server", "fa5s.play-circle")
        run_card.clicked.connect(lambda: self._go_to("modpack_run"))
        row1_layout.addWidget(run_card)

        cards_layout.addWidget(row1)

        layout.addWidget(cards)
        layout.addStretch()

        return page

    def _build_info_page(self) -> QWidget:
        """Build info/help page"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']}; border: none;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._scroll_style())

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        title = QLabel("Info & Help")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 26px; font-weight: bold;")
        layout.addWidget(title)

        sections = [
            ("Playing with Friends", "1. Install Hamachi or ZeroTier VPN\n2. Create a network and share with friends\n3. Friends connect using your VPN IP\n4. Disable firewall or allow Minecraft\n\nPyCraft sets online-mode=false automatically."),
            ("Common Issues", "Server won't start:\n- Check Java in the Management section\n- Verify enough RAM is available\n\nFriends can't connect:\n- Ensure same VPN network\n- Check firewall settings\n- Use correct IP address"),
            ("System Requirements", "- Java 17+ (installable via Java Management)\n- 4GB RAM minimum (8GB for modded)\n- 2GB disk space\n- Internet connection"),
        ]

        for sec_title, sec_content in sections:
            frame = self._section_frame(sec_title)
            label = QLabel(sec_content)
            label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px; background: transparent;")
            label.setWordWrap(True)
            frame.layout().addWidget(label)
            layout.addWidget(frame)

        layout.addStretch()
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        return page

    def _build_settings_page(self) -> QWidget:
        """Build settings page"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']}; border: none;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._scroll_style())

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        title = QLabel("Settings")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 26px; font-weight: bold;")
        layout.addWidget(title)

        # About section
        about_frame = self._section_frame("About PyCraft")
        about_layout = about_frame.layout()

        about_text = QLabel(
            "PyCraft is a Minecraft server manager that makes it easy to run\n"
            "vanilla and modded servers with your friends.\n\n"
            "Use the sidebar to manage Java installations and client modpacks."
        )
        about_text.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px; background: transparent;")
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)

        layout.addWidget(about_frame)

        # Updates section
        updates_frame = self._section_frame("Application Updates")
        updates_layout = updates_frame.layout()

        # Current version info
        version_container = QWidget()
        version_container.setStyleSheet("background: transparent;")
        version_layout = QHBoxLayout(version_container)
        version_layout.setContentsMargins(0, 0, 0, 0)
        version_layout.setSpacing(10)

        version_label = QLabel(f"Current version: {__version__}")
        version_label.setStyleSheet(f"color: {self.colors['text']}; font-size: 13px; background: transparent;")
        version_layout.addWidget(version_label)
        version_layout.addStretch()

        updates_layout.addWidget(version_container)

        # Update button container
        update_container = QWidget()
        update_container.setStyleSheet("background: transparent;")
        update_btn_layout = QHBoxLayout(update_container)
        update_btn_layout.setContentsMargins(0, 5, 0, 0)
        update_btn_layout.setSpacing(10)

        self.check_update_btn = QPushButton("Check for Updates")
        self.check_update_btn.setFixedHeight(36)
        self.check_update_btn.setMinimumWidth(160)
        self.check_update_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.check_update_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['accent']};
                color: #000000;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['accent_hover']};
            }}
            QPushButton:disabled {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text_muted']};
            }}
        """)
        self.check_update_btn.clicked.connect(self._check_for_updates)
        update_btn_layout.addWidget(self.check_update_btn)

        self.update_status_label = QLabel("")
        self.update_status_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 12px; background: transparent; border: none;")
        update_btn_layout.addWidget(self.update_status_label)
        update_btn_layout.addStretch()

        updates_layout.addWidget(update_container)

        # Download progress bar (hidden by default)
        self.download_progress_widget = QWidget()
        self.download_progress_widget.setStyleSheet("background: transparent;")
        progress_layout = QVBoxLayout(self.download_progress_widget)
        progress_layout.setContentsMargins(0, 10, 0, 0)
        progress_layout.setSpacing(5)

        # Progress bar
        self.download_progress_bar = QProgressBar()
        self.download_progress_bar.setFixedHeight(24)
        self.download_progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: {self.colors['bg_input']};
                text-align: center;
                color: {self.colors['text']};
                font-size: 11px;
            }}
            QProgressBar::chunk {{
                border-radius: 4px;
                background-color: {self.colors['accent']};
            }}
        """)
        progress_layout.addWidget(self.download_progress_bar)

        # Progress label
        self.download_progress_label = QLabel("")
        self.download_progress_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px; background: transparent;")
        progress_layout.addWidget(self.download_progress_label)

        self.download_progress_widget.hide()  # Hidden by default
        updates_layout.addWidget(self.download_progress_widget)

        # Install button (hidden by default)
        self.install_update_btn = QPushButton("Install Update Now")
        self.install_update_btn.setFixedHeight(36)
        self.install_update_btn.setMinimumWidth(160)
        self.install_update_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.install_update_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['accent']};
                color: #000000;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['accent_hover']};
            }}
            QPushButton:disabled {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text_muted']};
            }}
        """)
        self.install_update_btn.clicked.connect(self._install_downloaded_update)
        self.install_update_btn.hide()  # Hidden by default
        updates_layout.addWidget(self.install_update_btn)

        # Store downloaded installer path
        self.downloaded_installer_path = None

        # Update check animation timer
        self.update_check_timer = QTimer(self)
        self.update_check_timer.timeout.connect(self._animate_update_dots)
        self.update_dot_count = 0
        self.update_check_complete_signal.connect(self._on_update_check_complete)
        self.update_download_progress_signal.connect(self._on_download_progress)
        self.update_download_complete_signal.connect(self._on_download_complete)

        layout.addWidget(updates_frame)

        layout.addStretch()
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        return page

    def _build_java_management(self) -> QWidget:
        """Build Java management page"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']}; border: none;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._scroll_style())

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        title = QLabel("Java Management")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 26px; font-weight: bold;")
        layout.addWidget(title)

        # Java section
        java_frame = self._section_frame("Installed Java Versions")
        java_layout = java_frame.layout()

        self.java_info = QWidget()
        self.java_info.setStyleSheet("background: transparent;")
        self.java_info_layout = QVBoxLayout(self.java_info)
        self.java_info_layout.setContentsMargins(0, 0, 0, 0)
        self.java_info_layout.setSpacing(8)
        java_layout.addWidget(self.java_info)

        layout.addWidget(java_frame)

        QTimer.singleShot(100, self._check_java)

        layout.addStretch()
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        return page

    def _build_modpack_management(self) -> QWidget:
        """Build modpack management page"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']}; border: none;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._scroll_style())

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        title = QLabel("Client Modpacks")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 26px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Manage modpacks installed for your Minecraft launcher")
        subtitle.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px;")
        layout.addWidget(subtitle)

        # Modpack Management section
        modpack_frame = self._section_frame("Installed Modpacks")
        modpack_layout = modpack_frame.layout()

        # Modpack list container
        self.modpack_list_widget = QWidget()
        self.modpack_list_widget.setStyleSheet("background: transparent;")
        self.modpack_list_layout = QVBoxLayout(self.modpack_list_widget)
        self.modpack_list_layout.setContentsMargins(0, 0, 0, 0)
        self.modpack_list_layout.setSpacing(8)
        modpack_layout.addWidget(self.modpack_list_widget)

        layout.addWidget(modpack_frame)

        # Load modpacks after UI is ready
        QTimer.singleShot(200, self._refresh_modpack_list)

        layout.addStretch()
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        return page

    def _build_vanilla_create(self) -> QWidget:
        """Build vanilla server creation page"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']}; border: none;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._scroll_style())

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 25, 40, 25)
        layout.setSpacing(18)

        back = self._text_button("< Back")
        back.clicked.connect(lambda: self._go_to("vanilla"))
        layout.addWidget(back)

        title = QLabel("Create New Server")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        # Version
        ver_frame = self._section_frame("Minecraft Version")
        ver_layout = ver_frame.layout()

        self.ver_search = self._input("Search version...", 400)
        self.ver_search.textChanged.connect(self._filter_versions)
        self.ver_search.mousePressEvent = lambda e: self._show_version_dropdown()
        # Also show dropdown on focus (for keyboard navigation)
        original_focus_in = self.ver_search.focusInEvent
        def on_focus_in(event):
            self._show_version_dropdown()
            original_focus_in(event)
        self.ver_search.focusInEvent = on_focus_in
        ver_layout.addWidget(self.ver_search)

        self.ver_scroll = NonPropagatingScrollArea()
        self.ver_scroll.setFixedHeight(140)
        self.ver_scroll.setWidgetResizable(True)
        self.ver_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {self.colors['bg_card']};
                width: 12px;
                border-radius: 6px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: #4a4a4a;
                border-radius: 6px;
                border: none;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #5a5a5a;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                border: none;
            }}
            QScrollBar:horizontal {{
                height: 0px;
            }}
        """)

        self.ver_list = QWidget()
        self.ver_list_layout = QVBoxLayout(self.ver_list)
        self.ver_list_layout.setSpacing(4)
        self.ver_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.ver_scroll.setWidget(self.ver_list)
        ver_layout.addWidget(self.ver_scroll)

        self.ver_selected = QLabel("No version selected")
        self.ver_selected.setStyleSheet(f"color: {self.colors['yellow']}; font-size: 13px; font-weight: 600; border: none;")
        ver_layout.addWidget(self.ver_selected)

        layout.addWidget(ver_frame)

        # Folder
        folder_frame = self._section_frame("Destination Folder")
        folder_layout = folder_frame.layout()

        folder_btn = self._styled_button("Select Folder", self.colors['bg_input'], self.colors['text'], 180)
        folder_btn.clicked.connect(self._select_create_folder)
        folder_layout.addWidget(folder_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.create_folder_label = QLabel("No folder selected")
        self.create_folder_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        folder_layout.addWidget(self.create_folder_label)

        layout.addWidget(folder_frame)

        # Download
        self.download_btn = self._styled_button("Download and Install", self.colors['accent'], "#000000", 280)
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._download_server)
        layout.addWidget(self.download_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Console
        console_frame = self._section_frame("Console")
        self.vanilla_create_console = self._console()
        console_frame.layout().addWidget(self.vanilla_create_console)
        layout.addWidget(console_frame)

        # Progress bar with percentage label (below console)
        progress_container = QWidget()
        progress_container.setStyleSheet("background: transparent;")
        progress_layout = QHBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(12)

        self.create_progress = QProgressBar()
        self.create_progress.setFixedWidth(350)
        self.create_progress.setFixedHeight(12)
        self.create_progress.setTextVisible(False)
        self.create_progress.setStyleSheet(self._progress_style())
        progress_layout.addWidget(self.create_progress)

        self.create_progress_label = QLabel("0/100%")
        self.create_progress_label.setStyleSheet(f"color: {self.colors['text']}; font-size: 13px; font-weight: 600; border: none;")
        self.create_progress_label.setFixedWidth(60)
        progress_layout.addWidget(self.create_progress_label)
        progress_layout.addStretch()

        layout.addWidget(progress_container)

        self.create_status = QLabel("")
        self.create_status.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        layout.addWidget(self.create_status)

        layout.addStretch()
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        self._log(self.vanilla_create_console, "Ready to create a new server.\n", "info")

        return page

    def _build_vanilla_run(self) -> QWidget:
        """Build vanilla server run page"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']}; border: none;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._scroll_style())

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 25, 40, 25)
        layout.setSpacing(18)

        back = self._text_button("< Back")
        back.clicked.connect(lambda: self._go_to("vanilla"))
        layout.addWidget(back)

        title = QLabel("Run Existing Server")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        # Select
        select_frame = self._section_frame("Server Folder")
        select_layout = select_frame.layout()

        select_btn = self._styled_button("Select Folder", self.colors['bg_input'], self.colors['text'], 180)
        select_btn.clicked.connect(self._select_run_folder)
        select_layout.addWidget(select_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.run_folder_label = QLabel("No folder selected")
        self.run_folder_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        select_layout.addWidget(self.run_folder_label)

        layout.addWidget(select_frame)

        # Console
        console_frame = self._section_frame("Console")
        console_layout = console_frame.layout()

        self.vanilla_run_console = self._console()
        console_layout.addWidget(self.vanilla_run_console)

        # Command
        cmd_row = QWidget()
        cmd_row.setStyleSheet("background: transparent;")
        cmd_layout = QHBoxLayout(cmd_row)
        cmd_layout.setContentsMargins(0, 10, 0, 0)

        self.run_cmd = self._input("/command", 500)
        self.run_cmd.returnPressed.connect(self._send_vanilla_cmd)
        cmd_layout.addWidget(self.run_cmd)

        self.run_cmd_btn = self._styled_button("Send", self.colors['accent'], "#000000", 80)
        self.run_cmd_btn.setEnabled(False)
        self.run_cmd_btn.clicked.connect(self._send_vanilla_cmd)
        cmd_layout.addWidget(self.run_cmd_btn)

        console_layout.addWidget(cmd_row)

        # Controls
        ctrl_row = QWidget()
        ctrl_row.setStyleSheet("background: transparent;")
        ctrl_layout = QHBoxLayout(ctrl_row)
        ctrl_layout.setContentsMargins(0, 10, 0, 0)
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        ctrl_layout.setSpacing(12)

        self.run_start = self._styled_button("Start", self.colors['accent'], "#000000", 120)
        self.run_start.setEnabled(False)
        self.run_start.clicked.connect(self._start_vanilla)
        ctrl_layout.addWidget(self.run_start)

        self.run_stop = self._styled_button("Stop", self.colors['red'], "#ffffff", 120)
        self.run_stop.setEnabled(False)
        self.run_stop.clicked.connect(self._stop_vanilla)
        ctrl_layout.addWidget(self.run_stop)

        self.run_config = self._styled_button("Config", self.colors['yellow'], "#000000", 120)
        self.run_config.setEnabled(False)
        self.run_config.clicked.connect(self._config_vanilla)
        ctrl_layout.addWidget(self.run_config)

        console_layout.addWidget(ctrl_row)

        # Status bar (below controls)
        self.run_status = QLabel("")
        self.run_status.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px; font-weight: 600;")
        console_layout.addWidget(self.run_status)

        # Server info footer
        self.vanilla_server_info = QLabel("")
        self.vanilla_server_info.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px; margin-top: 8px;")
        self.vanilla_server_info.setVisible(False)
        console_layout.addWidget(self.vanilla_server_info)

        layout.addWidget(console_frame)

        layout.addStretch()
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        self._log(self.vanilla_run_console, "Select a server folder to begin.\n", "info")

        return page

    def _build_modpack_install(self) -> QWidget:
        """Build modpack installation page with provider selection"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']}; border: none;")

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget for provider selection / search UI
        self.mp_stack = QStackedWidget()
        self.mp_stack.setStyleSheet("background: transparent;")

        # === Page 0: Provider Selection (no scroll) ===
        provider_page = QWidget()
        provider_page.setStyleSheet(f"background-color: {self.colors['bg_content']};")
        provider_page_layout = QVBoxLayout(provider_page)
        provider_page_layout.setContentsMargins(40, 25, 40, 25)
        provider_page_layout.setSpacing(18)

        back_provider = self._text_button("< Back")
        back_provider.clicked.connect(lambda: self._go_to("modded"))
        provider_page_layout.addWidget(back_provider)

        title_provider = QLabel("Install Modpack")
        title_provider.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        provider_page_layout.addWidget(title_provider)

        # Center content vertically (2:3 ratio to account for header)
        provider_page_layout.addStretch(2)

        provider_title = QLabel("Choose a modpack provider:")
        provider_title.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 15px;")
        provider_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        provider_page_layout.addWidget(provider_title)

        # Provider buttons container
        providers_container = QWidget()
        providers_container.setStyleSheet("background: transparent;")
        providers_h = QHBoxLayout(providers_container)
        providers_h.setSpacing(24)
        providers_h.setContentsMargins(0, 0, 0, 0)
        providers_h.setAlignment(Qt.AlignmentFlag.AlignCenter)

        modrinth_btn = self._create_provider_button(
            "Modrinth",
            "Open-source modding platform",
            "#1bd96a",
            "fa5s.leaf"
        )
        modrinth_btn.clicked.connect(lambda: self._select_mp_provider("modrinth"))
        providers_h.addWidget(modrinth_btn)

        curseforge_btn = self._create_provider_button(
            "CurseForge",
            "Largest mod collection",
            "#f16436",
            "fa5s.fire"
        )
        curseforge_btn.clicked.connect(lambda: self._select_mp_provider("curseforge"))
        providers_h.addWidget(curseforge_btn)

        provider_page_layout.addWidget(providers_container)
        provider_page_layout.addStretch(3)

        self.mp_stack.addWidget(provider_page)

        # === Page 1: Search UI (with scroll) ===
        search_scroll = QScrollArea()
        search_scroll.setWidgetResizable(True)
        search_scroll.setStyleSheet(self._scroll_style())

        search_content = QWidget()
        search_content.setStyleSheet(f"background-color: {self.colors['bg_content']};")
        search_page_layout = QVBoxLayout(search_content)
        search_page_layout.setContentsMargins(40, 25, 40, 25)
        search_page_layout.setSpacing(18)

        back_search = self._text_button("< Back")
        back_search.clicked.connect(lambda: self._go_to("modded"))
        search_page_layout.addWidget(back_search)

        title_search = QLabel("Install Modpack")
        title_search.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        search_page_layout.addWidget(title_search)

        # Provider indicator with change button
        provider_row = QWidget()
        provider_row.setStyleSheet("background: transparent;")
        provider_row_layout = QHBoxLayout(provider_row)
        provider_row_layout.setContentsMargins(0, 0, 0, 8)

        self.mp_provider_label = QLabel("Searching on: Modrinth")
        self.mp_provider_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px;")
        provider_row_layout.addWidget(self.mp_provider_label)

        change_provider_btn = self._text_button("Change")
        change_provider_btn.clicked.connect(lambda: self.mp_stack.setCurrentIndex(0))
        provider_row_layout.addWidget(change_provider_btn)
        provider_row_layout.addStretch()

        search_page_layout.addWidget(provider_row)

        # Search frame
        search_frame = self._section_frame("Search Modpacks")
        search_layout = search_frame.layout()

        search_row = QWidget()
        search_row.setStyleSheet("background: transparent;")
        search_h = QHBoxLayout(search_row)
        search_h.setContentsMargins(0, 0, 0, 0)

        self.mp_search = self._input("Search modpacks (min. 3 characters)...", 560)
        self.mp_search.textChanged.connect(self._on_mp_search_changed)
        search_h.addWidget(self.mp_search)

        search_layout.addWidget(search_row)

        results_label = QLabel("Results:")
        results_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px; font-weight: 600;")
        search_layout.addWidget(results_label)

        self.mp_results_scroll = NonPropagatingScrollArea()
        self.mp_results_scroll.setFixedHeight(280)
        self.mp_results_scroll.setWidgetResizable(True)
        self.mp_results_scroll.setStyleSheet(self._scroll_style())

        self.mp_results = QWidget()
        self.mp_results_layout = QVBoxLayout(self.mp_results)
        self.mp_results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.mp_results_layout.setSpacing(8)
        self.mp_results_scroll.setWidget(self.mp_results)

        search_layout.addWidget(self.mp_results_scroll)

        # Pagination controls
        self.mp_pagination_widget = QWidget()
        self.mp_pagination_widget.setStyleSheet("background: transparent;")
        self.mp_pagination_widget.setVisible(False)
        pag_layout = QHBoxLayout(self.mp_pagination_widget)
        pag_layout.setContentsMargins(0, 5, 0, 5)
        pag_layout.setSpacing(5)

        self.mp_page_info = QLabel("")
        self.mp_page_info.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        pag_layout.addWidget(self.mp_page_info)

        pag_layout.addStretch()

        self.mp_prev_btn = QPushButton("<")
        self.mp_prev_btn.setFixedSize(32, 32)
        self.mp_prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.mp_prev_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {self.colors['bg_card']}; }}
            QPushButton:disabled {{ color: {self.colors['text_muted']}; }}
        """)
        self.mp_prev_btn.clicked.connect(lambda: self._mp_go_page(self.mp_current_page - 1))
        pag_layout.addWidget(self.mp_prev_btn)

        self.mp_page_btns_layout = QHBoxLayout()
        self.mp_page_btns_layout.setSpacing(3)
        pag_layout.addLayout(self.mp_page_btns_layout)

        self.mp_next_btn = QPushButton(">")
        self.mp_next_btn.setFixedSize(32, 32)
        self.mp_next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.mp_next_btn.setStyleSheet(self.mp_prev_btn.styleSheet())
        self.mp_next_btn.clicked.connect(lambda: self._mp_go_page(self.mp_current_page + 1))
        pag_layout.addWidget(self.mp_next_btn)

        search_layout.addWidget(self.mp_pagination_widget)

        self.mp_selected = QLabel("No modpack selected")
        self.mp_selected.setStyleSheet(f"color: {self.colors['yellow']}; font-size: 13px; font-weight: 600; border: none;")
        search_layout.addWidget(self.mp_selected)

        search_page_layout.addWidget(search_frame)

        # Folder
        folder_frame = self._section_frame("Destination Folder")
        folder_layout = folder_frame.layout()

        folder_btn = self._styled_button("Select Folder", self.colors['bg_input'], self.colors['text'], 180)
        folder_btn.clicked.connect(self._select_mp_folder)
        folder_layout.addWidget(folder_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.mp_folder_label = QLabel("No folder selected")
        self.mp_folder_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        folder_layout.addWidget(self.mp_folder_label)

        search_page_layout.addWidget(folder_frame)

        # Install button
        self.mp_install_btn = self._styled_button("Download and Install", self.colors['accent'], "#000000", 280)
        self.mp_install_btn.setEnabled(False)
        self.mp_install_btn.clicked.connect(self._install_modpack)
        search_page_layout.addWidget(self.mp_install_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Console
        console_frame = self._section_frame("Console")
        self.modpack_install_console = self._console()
        console_frame.layout().addWidget(self.modpack_install_console)
        search_page_layout.addWidget(console_frame)

        search_page_layout.addStretch()
        search_scroll.setWidget(search_content)

        self.mp_stack.addWidget(search_scroll)

        page_layout.addWidget(self.mp_stack)

        return page

    def _create_provider_button(self, name: str, description: str, color: str, icon: str) -> QPushButton:
        """Create a styled provider selection button"""
        btn = QPushButton()
        btn.setFixedSize(220, 160)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['bg_card']};
                border: 2px solid {self.colors['border']};
                border-radius: 14px;
            }}
            QPushButton:hover {{
                border-color: {color};
                background-color: {self.colors['bg_input']};
            }}
        """)

        btn_layout = QVBoxLayout(btn)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon, color=color).pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")
        btn_layout.addWidget(icon_label)

        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {self.colors['text']}; font-size: 18px; font-weight: bold; background: transparent; border: none;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(name_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px; background: transparent; border: none;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(desc_label)

        return btn

    def _select_mp_provider(self, provider: str):
        """Handle provider selection for server modpack install"""
        self.mp_selected_provider = provider
        provider_display = "Modrinth" if provider == "modrinth" else "CurseForge"
        self.mp_provider_label.setText(f"Searching on: {provider_display}")

        # Clear previous results
        self._clear_layout(self.mp_results_layout)
        self.mp_search.clear()
        self.mp_selected.setText("No modpack selected")
        self.selected_modpack = None
        self.mp_pagination_widget.setVisible(False)

        # Switch to search UI
        self.mp_stack.setCurrentIndex(1)
        self._log(self.modpack_install_console, f"Provider: {provider_display}\n", "info")
        self._log(self.modpack_install_console, "Search for a modpack to begin.\n", "info")

    def _build_modpack_run(self) -> QWidget:
        """Build modpack run page"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']}; border: none;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._scroll_style())

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 25, 40, 25)
        layout.setSpacing(18)

        back = self._text_button("< Back")
        back.clicked.connect(lambda: self._go_to("modded"))
        layout.addWidget(back)

        title = QLabel("Run Modded Server")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        # Select
        select_frame = self._section_frame("Server Folder")
        select_layout = select_frame.layout()

        select_btn = self._styled_button("Select Folder", self.colors['bg_input'], self.colors['text'], 180)
        select_btn.clicked.connect(self._select_mp_run_folder)
        select_layout.addWidget(select_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.mp_run_folder_label = QLabel("No folder selected")
        self.mp_run_folder_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        select_layout.addWidget(self.mp_run_folder_label)

        self.mp_run_status = QLabel("")
        self.mp_run_status.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px; font-weight: 600;")
        select_layout.addWidget(self.mp_run_status)

        layout.addWidget(select_frame)

        # Console
        console_frame = self._section_frame("Console")
        console_layout = console_frame.layout()

        self.modpack_run_console = self._console()
        console_layout.addWidget(self.modpack_run_console)

        # Command
        cmd_row = QWidget()
        cmd_row.setStyleSheet("background: transparent;")
        cmd_layout = QHBoxLayout(cmd_row)
        cmd_layout.setContentsMargins(0, 10, 0, 0)

        self.mp_run_cmd = self._input("/command", 500)
        self.mp_run_cmd.returnPressed.connect(self._send_mp_cmd)
        cmd_layout.addWidget(self.mp_run_cmd)

        self.mp_cmd_btn = self._styled_button("Send", self.colors['accent'], "#000000", 80)
        self.mp_cmd_btn.setEnabled(False)
        self.mp_cmd_btn.clicked.connect(self._send_mp_cmd)
        cmd_layout.addWidget(self.mp_cmd_btn)

        console_layout.addWidget(cmd_row)

        # Controls
        ctrl_row = QWidget()
        ctrl_row.setStyleSheet("background: transparent;")
        ctrl_layout = QHBoxLayout(ctrl_row)
        ctrl_layout.setContentsMargins(0, 10, 0, 0)
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        ctrl_layout.setSpacing(12)

        self.mp_start = self._styled_button("Start", self.colors['accent'], "#000000", 120)
        self.mp_start.setEnabled(False)
        self.mp_start.clicked.connect(self._start_mp)
        ctrl_layout.addWidget(self.mp_start)

        self.mp_stop = self._styled_button("Stop", self.colors['red'], "#ffffff", 120)
        self.mp_stop.setEnabled(False)
        self.mp_stop.clicked.connect(self._stop_mp)
        ctrl_layout.addWidget(self.mp_stop)

        self.mp_config = self._styled_button("Config", self.colors['yellow'], "#000000", 120)
        self.mp_config.setEnabled(False)
        self.mp_config.clicked.connect(self._config_mp)
        ctrl_layout.addWidget(self.mp_config)

        console_layout.addWidget(ctrl_row)

        # Server info footer (MC version + loader)
        self.modpack_server_info = QLabel("")
        self.modpack_server_info.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px; margin-top: 8px;")
        self.modpack_server_info.setVisible(False)
        console_layout.addWidget(self.modpack_server_info)

        layout.addWidget(console_frame)

        layout.addStretch()
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        self._log(self.modpack_run_console, "Select a server folder to begin.\n", "info")

        return page

    def _build_client_install(self) -> QWidget:
        """Build client modpack installation page with provider selection"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']}; border: none;")

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget for provider selection / search UI
        self.client_mp_stack = QStackedWidget()
        self.client_mp_stack.setStyleSheet("background: transparent;")

        # === Page 0: Provider Selection (no scroll) ===
        provider_page = QWidget()
        provider_page.setStyleSheet(f"background-color: {self.colors['bg_content']};")
        provider_page_layout = QVBoxLayout(provider_page)
        provider_page_layout.setContentsMargins(40, 25, 40, 25)
        provider_page_layout.setSpacing(18)

        back_provider = self._text_button("< Back")
        back_provider.clicked.connect(lambda: self._go_to("modded"))
        provider_page_layout.addWidget(back_provider)

        title_provider = QLabel("Install Modpack (Client)")
        title_provider.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        provider_page_layout.addWidget(title_provider)

        # Info box
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_card']};
                border-radius: 10px;
                border: 1px solid {self.colors['accent']};
            }}
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(16, 12, 16, 12)

        info_icon = QLabel()
        info_icon.setPixmap(qta.icon("fa5s.info-circle", color=self.colors['accent']).pixmap(24, 24))
        info_icon.setFixedSize(24, 24)
        info_layout.addWidget(info_icon)

        info_text = QLabel("Client modpacks are installed to ~/.pycraft/modpacks/ for use with your launcher (SKLauncher, MultiMC, etc.)")
        info_text.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 12px;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text, 1)

        provider_page_layout.addWidget(info_frame)

        # Center content vertically (2:3 ratio to account for header)
        provider_page_layout.addStretch(2)

        provider_title = QLabel("Choose a modpack provider:")
        provider_title.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 15px;")
        provider_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        provider_page_layout.addWidget(provider_title)

        # Provider buttons container
        providers_container = QWidget()
        providers_container.setStyleSheet("background: transparent;")
        providers_h = QHBoxLayout(providers_container)
        providers_h.setSpacing(24)
        providers_h.setContentsMargins(0, 0, 0, 0)
        providers_h.setAlignment(Qt.AlignmentFlag.AlignCenter)

        modrinth_btn = self._create_provider_button(
            "Modrinth",
            "Open-source modding platform",
            "#1bd96a",
            "fa5s.leaf"
        )
        modrinth_btn.clicked.connect(lambda: self._select_client_mp_provider("modrinth"))
        providers_h.addWidget(modrinth_btn)

        curseforge_btn = self._create_provider_button(
            "CurseForge",
            "Largest mod collection",
            "#f16436",
            "fa5s.fire"
        )
        curseforge_btn.clicked.connect(lambda: self._select_client_mp_provider("curseforge"))
        providers_h.addWidget(curseforge_btn)

        provider_page_layout.addWidget(providers_container)
        provider_page_layout.addStretch(3)

        self.client_mp_stack.addWidget(provider_page)

        # === Page 1: Search UI (with scroll) ===
        search_scroll = QScrollArea()
        search_scroll.setWidgetResizable(True)
        search_scroll.setStyleSheet(self._scroll_style())

        search_content = QWidget()
        search_content.setStyleSheet(f"background-color: {self.colors['bg_content']};")
        search_page_layout = QVBoxLayout(search_content)
        search_page_layout.setContentsMargins(40, 25, 40, 25)
        search_page_layout.setSpacing(18)

        back_search = self._text_button("< Back")
        back_search.clicked.connect(lambda: self._go_to("modded"))
        search_page_layout.addWidget(back_search)

        title_search = QLabel("Install Modpack (Client)")
        title_search.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        search_page_layout.addWidget(title_search)

        # Provider indicator with change button
        provider_row = QWidget()
        provider_row.setStyleSheet("background: transparent;")
        provider_row_layout = QHBoxLayout(provider_row)
        provider_row_layout.setContentsMargins(0, 0, 0, 8)

        self.client_mp_provider_label = QLabel("Searching on: Modrinth")
        self.client_mp_provider_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px;")
        provider_row_layout.addWidget(self.client_mp_provider_label)

        change_provider_btn = self._text_button("Change")
        change_provider_btn.clicked.connect(lambda: self.client_mp_stack.setCurrentIndex(0))
        provider_row_layout.addWidget(change_provider_btn)
        provider_row_layout.addStretch()

        search_page_layout.addWidget(provider_row)

        # Search frame
        search_frame = self._section_frame("Search Modpacks")
        search_layout = search_frame.layout()

        search_row = QWidget()
        search_row.setStyleSheet("background: transparent;")
        search_h = QHBoxLayout(search_row)
        search_h.setContentsMargins(0, 0, 0, 0)

        self.client_mp_search = self._input("Search modpacks (min. 3 characters)...", 560)
        self.client_mp_search.textChanged.connect(self._on_client_mp_search_changed)
        search_h.addWidget(self.client_mp_search)

        search_layout.addWidget(search_row)

        results_label = QLabel("Results:")
        results_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px; font-weight: 600;")
        search_layout.addWidget(results_label)

        self.client_mp_results_scroll = NonPropagatingScrollArea()
        self.client_mp_results_scroll.setFixedHeight(280)
        self.client_mp_results_scroll.setWidgetResizable(True)
        self.client_mp_results_scroll.setStyleSheet(self._scroll_style())

        self.client_mp_results = QWidget()
        self.client_mp_results_layout = QVBoxLayout(self.client_mp_results)
        self.client_mp_results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.client_mp_results_layout.setSpacing(8)
        self.client_mp_results_scroll.setWidget(self.client_mp_results)

        search_layout.addWidget(self.client_mp_results_scroll)

        # Pagination controls
        self.client_mp_pagination_widget = QWidget()
        self.client_mp_pagination_widget.setStyleSheet("background: transparent;")
        self.client_mp_pagination_widget.setVisible(False)
        cpag_layout = QHBoxLayout(self.client_mp_pagination_widget)
        cpag_layout.setContentsMargins(0, 5, 0, 5)
        cpag_layout.setSpacing(5)

        self.client_mp_page_info = QLabel("")
        self.client_mp_page_info.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        cpag_layout.addWidget(self.client_mp_page_info)

        cpag_layout.addStretch()

        self.client_mp_prev_btn = QPushButton("<")
        self.client_mp_prev_btn.setFixedSize(32, 32)
        self.client_mp_prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.client_mp_prev_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {self.colors['bg_card']}; }}
            QPushButton:disabled {{ color: {self.colors['text_muted']}; }}
        """)
        self.client_mp_prev_btn.clicked.connect(lambda: self._client_mp_go_page(self.client_mp_current_page - 1))
        cpag_layout.addWidget(self.client_mp_prev_btn)

        self.client_mp_page_btns_layout = QHBoxLayout()
        self.client_mp_page_btns_layout.setSpacing(3)
        cpag_layout.addLayout(self.client_mp_page_btns_layout)

        self.client_mp_next_btn = QPushButton(">")
        self.client_mp_next_btn.setFixedSize(32, 32)
        self.client_mp_next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.client_mp_next_btn.setStyleSheet(self.client_mp_prev_btn.styleSheet())
        self.client_mp_next_btn.clicked.connect(lambda: self._client_mp_go_page(self.client_mp_current_page + 1))
        cpag_layout.addWidget(self.client_mp_next_btn)

        search_layout.addWidget(self.client_mp_pagination_widget)

        self.client_mp_selected = QLabel("No modpack selected")
        self.client_mp_selected.setStyleSheet(f"color: {self.colors['yellow']}; font-size: 13px; font-weight: 600;")
        search_layout.addWidget(self.client_mp_selected)

        search_page_layout.addWidget(search_frame)

        # Install button
        self.client_mp_install_btn = self._styled_button("Install to Client", self.colors['accent'], "#000000", 200)
        self.client_mp_install_btn.setEnabled(False)
        self.client_mp_install_btn.clicked.connect(self._install_client_modpack)
        search_page_layout.addWidget(self.client_mp_install_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Console
        console_frame = self._section_frame("Console")
        self.client_install_console = self._console()
        console_frame.layout().addWidget(self.client_install_console)
        search_page_layout.addWidget(console_frame)

        search_page_layout.addStretch()
        search_scroll.setWidget(search_content)

        self.client_mp_stack.addWidget(search_scroll)

        page_layout.addWidget(self.client_mp_stack)

        return page

    def _select_client_mp_provider(self, provider: str):
        """Handle provider selection for client modpack install"""
        self.client_mp_selected_provider = provider
        provider_display = "Modrinth" if provider == "modrinth" else "CurseForge"
        self.client_mp_provider_label.setText(f"Searching on: {provider_display}")

        # Clear previous results
        self._clear_layout(self.client_mp_results_layout)
        self.client_mp_search.clear()
        self.client_mp_selected.setText("No modpack selected")
        self.client_selected_modpack = None
        self.client_mp_pagination_widget.setVisible(False)

        # Switch to search UI
        self.client_mp_stack.setCurrentIndex(1)
        self._log(self.client_install_console, f"Provider: {provider_display}\n", "info")
        self._log(self.client_install_console, f"Install location: {Path.home() / '.pycraft' / 'modpacks'}\n", "info")
        self._log(self.client_install_console, "Search for a modpack to install.\n", "info")

    def _open_url(self, url: str):
        """Open URL in browser without blocking UI"""
        threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()

    def _clear_layout(self, layout):
        """Clear all widgets from a layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    # UI Helpers
    def _section_frame(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_card']};
                border-radius: 12px;
                border: 1px solid {self.colors['border']};
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {self.colors['text']}; font-size: 15px; font-weight: 600; background: transparent;")
        layout.addWidget(lbl)

        return frame

    def _styled_button(self, text: str, bg: str, fg: str = "#ffffff", width: int = 200) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(width, 42)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
            QPushButton:disabled {{
                background-color: #3a3a3a;
                color: #666666;
            }}
        """)
        return btn

    def _text_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colors['accent']};
                border: none;
                font-size: 13px;
                text-align: left;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {self.colors['accent_hover']};
            }}
        """)
        return btn

    def _input(self, placeholder: str, width: int = 400) -> QLineEdit:
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedSize(width, 42)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 10px;
                padding: 0 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colors['accent']};
            }}
            QLineEdit::placeholder {{
                color: {self.colors['text_muted']};
            }}
        """)
        return inp

    def _console(self) -> NonPropagatingTextEdit:
        console = NonPropagatingTextEdit()
        console.setFixedHeight(250)
        console.setReadOnly(True)
        console.setStyleSheet(f"""
            QTextEdit {{
                background-color: #0a0a0a;
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 10px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
            QScrollBar:vertical {{
                background-color: #1a1a1a;
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #3a3a3a;
                border-radius: 5px;
            }}
        """)
        return console

    def _scroll_style(self) -> str:
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

    def _log(self, console: QTextEdit, msg: str, level: str = "normal", max_lines: int = 500):
        colors = {
            "normal": "#ffffff", "info": "#60a5fa",
            "success": "#4ade80", "warning": "#fbbf24", "error": "#f87171"
        }
        color = colors.get(level, "#ffffff")

        cursor = console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.insertText(msg, fmt)

        # Limit console to max_lines to prevent memory issues
        doc = console.document()
        line_count = doc.blockCount()
        if line_count > max_lines:
            # Remove excess lines from the beginning
            excess = line_count - max_lines
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(excess):
                cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            # Move back to end
            cursor.movePosition(QTextCursor.MoveOperation.End)

        console.setTextCursor(cursor)
        console.ensureCursorVisible()

    # Navigation
    def _go_to(self, page: str):
        pages = {
            "home": 0, "vanilla": 1, "modded": 2, "info": 3, "settings": 4,
            "vanilla_create": 5, "vanilla_run": 6, "modpack_install": 7, "modpack_run": 8,
            "client_install": 9, "client_modpacks": 9,
            "java_management": 10, "modpack_management": 11
        }
        if page in pages:
            self.page_stack.setCurrentIndex(pages[page])

        # Show footer only on home page
        self.footer.setVisible(page == "home")

        # Hide update toast when leaving Home
        if page != "home" and hasattr(self, 'update_toast'):
            self.update_toast.close_immediately()

        # Hide notification dot when entering Settings
        if page == "settings":
            self.sidebar_buttons["settings"].show_notification(False)

        sidebar_map = {
            "home": "home", "vanilla": "vanilla", "vanilla_create": "vanilla", "vanilla_run": "vanilla",
            "modded": "modded", "modpack_install": "modded", "modpack_run": "modded",
            "client_install": "client_modpacks", "client_modpacks": "client_modpacks",
            "settings": "settings",
            "java_management": "java_management", "modpack_management": "modpack_management"
        }
        for k, btn in self.sidebar_buttons.items():
            btn.setChecked(k == sidebar_map.get(page, ""))

    # Logic
    def _load_versions(self):
        def load():
            versions = self.api_handler.get_version_names()
            if versions:
                self.versions_list = versions
                self.filtered_versions = versions.copy()
                QTimer.singleShot(0, lambda: self._show_versions(versions))

        threading.Thread(target=load, daemon=True).start()

    def _show_versions(self, versions: list):
        while self.ver_list_layout.count():
            child = self.ver_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for v in versions[:50]:
            btn = QPushButton(v)
            btn.setFixedHeight(34)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {self.colors['text']};
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                    padding-left: 12px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {self.colors['bg_input']};
                }}
            """)
            btn.clicked.connect(lambda _, ver=v: self._pick_version(ver))
            self.ver_list_layout.addWidget(btn)

    def _show_version_dropdown(self):
        """Show version dropdown and focus input"""
        # Show all versions when dropdown opens
        if self.versions_list:
            self._show_versions(self.versions_list)
        self.ver_scroll.show()
        self.ver_search.setFocus()
        # Restore placeholder if a version was selected
        if self.selected_version:
            self.ver_search.setPlaceholderText("Search version...")

    def _collapse_version_dropdown(self, ver: str):
        """Collapse version dropdown after selection"""
        # Disconnect textChanged to prevent dropdown from re-showing when we clear text
        self.ver_search.textChanged.disconnect(self._filter_versions)
        self.ver_scroll.hide()
        self.ver_search.setText("")
        self.ver_search.setPlaceholderText(f"✓ {ver} (click to change)")
        self.ver_search.clearFocus()
        # Reconnect textChanged
        self.ver_search.textChanged.connect(self._filter_versions)

    def _filter_versions(self, text: str):
        # Show dropdown when typing
        if not self.ver_scroll.isVisible():
            self.ver_scroll.show()
        if not text:
            self.filtered_versions = self.versions_list.copy()
        else:
            self.filtered_versions = [v for v in self.versions_list if text.lower() in v.lower()]
        self._show_versions(self.filtered_versions)

    def _pick_version(self, ver: str):
        self.selected_version = ver
        self.ver_selected.setText(f"✓ Selected: {ver}")
        self.ver_selected.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600; border: none;")
        self._update_download_btn()
        # Collapse version list after selection - use timer to ensure it happens after click
        QTimer.singleShot(50, lambda: self._collapse_version_dropdown(ver))

    def _is_dangerous_folder(self, folder_path: str) -> tuple[bool, str]:
        """
        Check if a folder is a dangerous/important system location.

        Returns:
            Tuple of (is_dangerous, warning_message)
        """
        if not folder_path:
            return False, ""

        path = Path(folder_path).resolve()
        path_str = str(path).lower()
        path_name = path.name.lower()

        # Check if it's a drive root (C:\, D:\, etc.)
        if path.parent == path:  # Root of a drive
            return True, "You selected a drive root. This will create server files directly in your drive, which can cause clutter and issues."

        # Dangerous folder names (case-insensitive)
        dangerous_names = {
            "downloads": "Downloads folder",
            "descargas": "Downloads folder",
            "desktop": "Desktop",
            "escritorio": "Desktop",
            "documents": "Documents folder",
            "documentos": "Documents folder",
            "my documents": "Documents folder",
            "mis documentos": "Documents folder",
            "program files": "Program Files",
            "program files (x86)": "Program Files",
            "archivos de programa": "Program Files",
            "windows": "Windows system folder",
            "system32": "Windows system folder",
            "users": "Users folder",
            "appdata": "AppData folder",
        }

        # Check folder name
        if path_name in dangerous_names:
            location = dangerous_names[path_name]
            return True, f"You selected your {location}. Creating a Minecraft server here is not recommended as it may cause data loss or clutter."

        # Check if path contains dangerous folders at top level
        for part in path.parts:
            part_lower = part.lower()
            if part_lower in ["program files", "program files (x86)", "windows", "system32"]:
                return True, f"You selected a folder inside '{part}'. This is a system location and is not recommended for Minecraft servers."

        return False, ""

    def _is_existing_server(self, folder_path: str) -> bool:
        """
        Check if folder already contains a Minecraft server.
        Returns True if server files are detected.
        """
        path = Path(folder_path)

        # Check for exact files
        if (path / "server.jar").exists():
            return True
        if (path / "server.properties").exists():
            return True

        # Check for pattern-based files (forge, fabric, paper, spigot)
        for pattern in ["forge-*.jar", "fabric-server-*.jar", "paper-*.jar", "spigot-*.jar"]:
            if list(path.glob(pattern)):
                return True

        return False

    def _warn_existing_server(self, folder_path: str) -> bool:
        """
        Show error if folder already contains a server. Returns True if folder is clean, False to cancel.
        """
        if not self._is_existing_server(folder_path):
            return True

        msg = QMessageBox(self)
        msg.setWindowTitle("Server Already Exists")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("This folder already contains a Minecraft server!")
        msg.setInformativeText("Please select an empty folder or create a new one to avoid conflicts with existing server files.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

        return False

    def _warn_dangerous_folder(self, folder_path: str) -> bool:
        """
        Show warning if folder is dangerous. Returns True if user wants to continue, False to cancel.
        """
        is_dangerous, warning = self._is_dangerous_folder(folder_path)
        if not is_dangerous:
            return True

        msg = QMessageBox(self)
        msg.setWindowTitle("Warning: Folder Location")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("Are you sure you want to use this folder?")
        msg.setInformativeText(f"{warning}\n\nIt's recommended to create a dedicated folder for your server (e.g., 'MinecraftServers/MyServer').")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        return msg.exec() == QMessageBox.StandardButton.Yes

    def _select_create_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            if not self._warn_dangerous_folder(folder):
                return  # User cancelled
            if not self._warn_existing_server(folder):
                return  # Server already exists
            self.server_folder = folder
            self.create_folder_label.setText(f"Folder: {folder}")
            self._update_download_btn()

    def _update_download_btn(self):
        self.download_btn.setEnabled(bool(self.selected_version and self.server_folder))

    def _download_server(self):
        if not self.selected_version or not self.server_folder:
            return

        # Check Java compatibility BEFORE downloading
        required_java = self.java_manager.get_required_java_version(self.selected_version)
        min_java, max_java = self.java_manager.get_java_version_range(self.selected_version)
        java_info = self.java_manager.detect_java_version()

        # Check if we have a compatible Java already installed by PyCraft
        pycraft_java = None
        install_dir = self.java_manager.java_installs_dir / f"java-{required_java}"
        if install_dir.exists():
            java_exe = self.java_manager._find_java_executable(install_dir)
            if java_exe:
                pycraft_java = str(java_exe)

        # Determine if we need Java (check both min and max)
        needs_java = False
        java_too_new = False
        if pycraft_java:
            # We have PyCraft-installed Java, use it
            pass
        elif java_info:
            _, installed_major = java_info
            if installed_major < min_java:
                needs_java = True
            elif max_java is not None and installed_major > max_java:
                needs_java = True
                java_too_new = True
        else:
            needs_java = True

        if needs_java:
            # Show dialog with options
            msg = QMessageBox(self)
            msg.setWindowTitle("Java Required")
            msg.setIcon(QMessageBox.Icon.Warning)

            if max_java:
                msg.setText(f"Minecraft {self.selected_version} requires Java {min_java}-{max_java}")
            else:
                msg.setText(f"Minecraft {self.selected_version} requires Java {required_java}+")

            if java_info:
                _, installed_major = java_info
                if java_too_new:
                    msg.setInformativeText(
                        f"You have Java {installed_major} installed, but it's too new.\n"
                        f"Forge/modded servers for MC < 1.17 require Java 8-{max_java}.\n"
                        f"Java 17+ breaks due to module system changes.\n\n"
                        f"What would you like to do?"
                    )
                else:
                    msg.setInformativeText(
                        f"You have Java {installed_major} installed, but Java {required_java} or higher is needed.\n\n"
                        f"What would you like to do?"
                    )
            else:
                msg.setInformativeText(
                    f"Java is not installed on your system.\n\n"
                    f"What would you like to do?"
                )

            install_btn = msg.addButton("Install Automatically", QMessageBox.ButtonRole.AcceptRole)
            java_btn = msg.addButton("Java Management", QMessageBox.ButtonRole.ActionRole)
            cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

            msg.exec()

            clicked = msg.clickedButton()
            if clicked == java_btn:
                self._go_to("java_management")
                return
            elif clicked == cancel_btn or clicked is None:
                return
            # If install_btn clicked, show installation modal first
            elif clicked == install_btn:
                if not self._show_java_install_modal(required_java):
                    # Installation failed, don't continue
                    QMessageBox.critical(self, "Error", f"Failed to install Java {required_java}. Cannot create server.")
                    return
                # Update pycraft_java reference after successful install
                install_dir = self.java_manager.java_installs_dir / f"java-{required_java}"
                if install_dir.exists():
                    java_exe = self.java_manager._find_java_executable(install_dir)
                    if java_exe:
                        pycraft_java = str(java_exe)

        # Proceed with download
        self.download_btn.setEnabled(False)
        self.active_progress = self.create_progress
        self.active_progress_label = self.create_progress_label
        self.active_status = self.create_status

        # Capture java path for the thread
        java_to_use = pycraft_java

        def process():
            nonlocal java_to_use
            try:
                self.log_signal.emit(f"\nDownloading Minecraft {self.selected_version}...\n", "info", "v_create")

                url = self.api_handler.get_server_jar_url(self.selected_version)
                if not url:
                    self.log_signal.emit("Error: Could not get URL\n", "error", "v_create")
                    return

                server_path = self.downloader.download_server(
                    url, self.server_folder, self.selected_version,
                    progress_callback=lambda p: self.progress_signal.emit(p)
                )

                if not server_path:
                    self.log_signal.emit("Download failed\n", "error", "v_create")
                    return

                self.log_signal.emit("Download complete\n", "success", "v_create")

                # Use pre-installed Java if available, otherwise find it quietly
                if java_to_use:
                    java = java_to_use
                    self.log_signal.emit(f"Using Java: {java}\n", "info", "v_create")
                else:
                    # Simplified callback - only show key messages
                    def quiet_log(msg):
                        msg_lower = msg.lower()
                        if any(x in msg_lower for x in ["✓", "✗", "error"]):
                            self.log_signal.emit(msg, "normal", "v_create")

                    java = self.java_manager.ensure_java_installed(
                        self.selected_version,
                        log_callback=quiet_log
                    )

                if not java:
                    self.log_signal.emit("Java not available\n", "error", "v_create")
                    return

                self.log_signal.emit("\nConfiguring server...\n", "info", "v_create")

                self.server_manager = ServerManager(self.server_folder, java_executable=java)
                success = self.server_manager.run_server_first_time(
                    log_callback=lambda m: self.log_signal.emit(m, "normal", "v_create")
                )

                if success:
                    self.log_signal.emit("\n" + "="*50 + "\n", "success", "v_create")
                    self.log_signal.emit("SERVER CREATED SUCCESSFULLY\n", "success", "v_create")
                    self.log_signal.emit("="*50 + "\n", "success", "v_create")

                    # Show success modal via signal (thread-safe)
                    self.vanilla_install_success_signal.emit(self.selected_version, self.server_folder)

            except Exception as e:
                self.log_signal.emit(f"Error: {e}\n", "error", "v_create")

            finally:
                QTimer.singleShot(0, lambda: self.download_btn.setEnabled(True))
                QTimer.singleShot(0, lambda: self.create_progress.setValue(0))
                QTimer.singleShot(0, lambda: self.create_progress_label.setText("0/100%"))

        threading.Thread(target=process, daemon=True).start()

    def _show_vanilla_install_success(self, mc_version: str, folder: str):
        """Show success modal after vanilla server installation"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Server Created Successfully")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"Vanilla server Minecraft {mc_version} has been created!")
        msg.setInformativeText(
            f"Location: {folder}\n\n"
            f"Go to 'Vanilla' > 'Run' tab to start your server."
        )
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.colors['bg_card']};
            }}
            QMessageBox QLabel {{
                color: {self.colors['text']};
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {self.colors['accent']};
                color: #000000;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: 600;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['accent_hover']};
            }}
        """)
        msg.exec()

    def _select_run_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Server Folder")
        if folder:
            # Clear previous state
            self.vanilla_run_console.clear()
            self.run_cmd.clear()
            self.run_cmd_btn.setEnabled(False)
            self._log(self.vanilla_run_console, "Loading server folder...\n", "info")

            if os.path.exists(os.path.join(folder, "server.jar")):
                self.server_folder = folder
                self.run_folder_label.setText(f"Folder: {folder}")

                self.server_manager = ServerManager(folder)
                self.is_server_configured = True

                # Detect Minecraft version
                mc_version = self.server_manager.detect_minecraft_version()
                self.detected_mc_version = mc_version  # Store for later use

                if mc_version:
                    self.run_status.setText(f"Minecraft {mc_version}")
                    self._log(self.vanilla_run_console, f"\nServer found: {folder}\n", "success")
                    self._log(self.vanilla_run_console, f"Detected version: Minecraft {mc_version}\n", "info")
                    # Show server info footer
                    self.vanilla_server_info.setText(f"Minecraft {mc_version}")
                    self.vanilla_server_info.setVisible(True)
                else:
                    self.run_status.setText("Server found (version unknown)")
                    self._log(self.vanilla_run_console, f"\nServer found: {folder}\n", "success")
                    self._log(self.vanilla_run_console, "Could not detect Minecraft version\n", "warning")
                    self.vanilla_server_info.setVisible(False)

                self.run_status.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600; border: none;")
                self.run_start.setEnabled(True)

                # Enable config only if server.properties exists
                has_properties = os.path.exists(os.path.join(folder, "server.properties"))
                self.run_config.setEnabled(has_properties)
                if not has_properties:
                    self._log(self.vanilla_run_console, "Run server once to generate server.properties\n", "warning")

                self.run_stop.setEnabled(False)
            else:
                self.server_folder = None
                self.run_folder_label.setText(f"Folder: {folder}")
                self.run_status.setText("server.jar not found")
                self.run_status.setStyleSheet(f"color: {self.colors['red']}; font-size: 13px; font-weight: 600; border: none;")
                self.vanilla_server_info.setVisible(False)
                self.run_start.setEnabled(False)
                self.run_config.setEnabled(False)
                self.run_stop.setEnabled(False)
                self.run_cmd_btn.setEnabled(False)
                self.server_manager = None
                self.is_server_configured = False
                self.detected_mc_version = None

    def _start_vanilla(self):
        if not self.server_manager:
            return

        # Get Minecraft version (from detection or default to 1.20)
        mc_version = self.detected_mc_version or self.server_manager.detect_minecraft_version()
        if not mc_version:
            mc_version = "1.20"  # Default assumption for unknown versions
            self._log(self.vanilla_run_console, "\nCould not detect version, assuming Java 17+ required\n", "warning")

        # Check Java compatibility
        required_java = self.java_manager.get_required_java_version(mc_version)
        min_java, max_java = self.java_manager.get_java_version_range(mc_version)
        java_info = self.java_manager.detect_java_version()

        needs_java = False
        java_too_new = False
        pycraft_java = None

        # Check if we have a PyCraft-installed Java
        install_dir = self.java_manager.java_installs_dir / f"java-{required_java}"
        if install_dir.exists():
            java_exe = self.java_manager._find_java_executable(install_dir)
            if java_exe:
                pycraft_java = str(java_exe)

        if not pycraft_java:
            if not java_info:
                needs_java = True
            else:
                _, installed_major = java_info
                if installed_major < min_java:
                    needs_java = True
                elif max_java is not None and installed_major > max_java:
                    needs_java = True
                    java_too_new = True

        if needs_java:
            # Show dialog with options (same as create server)
            msg = QMessageBox(self)
            msg.setWindowTitle("Java Required")
            msg.setIcon(QMessageBox.Icon.Warning)

            if max_java:
                msg.setText(f"Minecraft {mc_version} requires Java {min_java}-{max_java}")
            else:
                msg.setText(f"Minecraft {mc_version} requires Java {required_java}+")

            if java_info:
                _, installed_major = java_info
                if java_too_new:
                    msg.setInformativeText(
                        f"You have Java {installed_major} installed, but it's too new.\n"
                        f"Forge/modded servers for MC < 1.17 require Java 8-{max_java}.\n"
                        f"Java 17+ breaks due to module system changes.\n\n"
                        f"What would you like to do?"
                    )
                else:
                    msg.setInformativeText(
                        f"You have Java {installed_major} installed, but Java {required_java} or higher is needed.\n\n"
                        f"What would you like to do?"
                    )
            else:
                msg.setInformativeText(
                    f"Java is not installed on your system.\n\n"
                    f"What would you like to do?"
                )

            install_btn = msg.addButton("Install Automatically", QMessageBox.ButtonRole.AcceptRole)
            java_btn = msg.addButton("Java Management", QMessageBox.ButtonRole.ActionRole)
            cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

            msg.exec()

            clicked = msg.clickedButton()
            if clicked == java_btn:
                self._go_to("java_management")
                return
            elif clicked == cancel_btn or clicked is None:
                return
            elif clicked == install_btn:
                if not self._show_java_install_modal(required_java):
                    QMessageBox.critical(self, "Error", f"Failed to install Java {required_java}. Cannot start server.")
                    return
                # Update java reference after successful install
                install_dir = self.java_manager.java_installs_dir / f"java-{required_java}"
                if install_dir.exists():
                    java_exe = self.java_manager._find_java_executable(install_dir)
                    if java_exe:
                        pycraft_java = str(java_exe)

        # Update server manager with correct Java executable
        if pycraft_java:
            self.server_manager.java_executable = pycraft_java
            self._log(self.vanilla_run_console, f"\nUsing Java: {pycraft_java}\n", "info")

        # Configure online-mode=false automatically for LAN/Hamachi play
        self.server_manager.set_online_mode(False)

        self._log(self.vanilla_run_console, "\n=== STARTING SERVER ===\n", "info")
        self.run_start.setEnabled(False)
        self.run_config.setEnabled(False)
        self.run_stop.setEnabled(True)

        # Track if server started successfully
        self._vanilla_server_started_successfully = False

        def on_server_stopped():
            """Called when server process ends (crash or normal stop)"""
            # Emit signal to update UI from main thread
            self.vanilla_server_stopped_signal.emit(self._vanilla_server_started_successfully)

        def log_callback(line: str):
            """Monitor server output"""
            # Check for successful start
            if "Done" in line and "!" in line:
                self._vanilla_server_started_successfully = True
            # Forward to UI
            self.log_signal.emit(line, "normal", "v_run")

        def start():
            success = self.server_manager.start_server(
                ram_mb=self.vanilla_ram,
                log_callback=log_callback,
                detached=True,
                on_stopped=on_server_stopped
            )
            # Emit signal to update UI from main thread
            self.vanilla_server_started_signal.emit(success)

        threading.Thread(target=start, daemon=True).start()

    def _on_vanilla_server_started(self, success: bool):
        """Handle vanilla server started (called from main thread via signal)"""
        if success:
            self.run_cmd_btn.setEnabled(True)
        else:
            # Re-enable start button if failed
            self.run_start.setEnabled(True)
            self.run_config.setEnabled(True)
            self.run_stop.setEnabled(False)

    def _on_vanilla_server_stopped(self, started_successfully: bool):
        """Handle vanilla server stopped (called from main thread via signal)"""
        # Re-enable UI elements
        self.run_start.setEnabled(True)

        # Enable config only if server.properties exists (may have been generated on first run)
        if self.server_folder:
            has_properties = os.path.exists(os.path.join(self.server_folder, "server.properties"))
            self.run_config.setEnabled(has_properties)
        else:
            self.run_config.setEnabled(False)

        self.run_stop.setEnabled(False)
        self.run_cmd_btn.setEnabled(False)

        if started_successfully:
            self.log_signal.emit("\n[Server stopped - Ready to restart]\n", "info", "v_run")
        else:
            # Server crashed before "Done"
            self.log_signal.emit("\n[Server crashed - Ready to restart]\n", "error", "v_run")
            # Show crash dialog after a brief delay to ensure UI is updated
            QTimer.singleShot(100, lambda: self.server_crashed_signal.emit(self.server_folder))

    def _stop_vanilla(self):
        if not self.server_manager:
            return

        # Check if server is actually running
        if not self.server_manager.is_server_running():
            self._log(self.vanilla_run_console, "\nServer is not running\n", "warning")
            return

        # Disable all buttons immediately to prevent double-clicks
        self.run_stop.setEnabled(False)
        self.run_start.setEnabled(False)
        self.run_config.setEnabled(False)
        self.run_cmd_btn.setEnabled(False)
        self._log(self.vanilla_run_console, "\nStopping server...\n", "warning")

        def stop():
            try:
                self.server_manager.stop_server()

                # stop_server() is blocking, so when it returns the server is stopped
                # Re-enable buttons on main thread
                def enable_buttons():
                    self._log(self.vanilla_run_console, "Server stopped - Ready to restart\n", "success")
                    self.run_start.setEnabled(True)
                    self.run_config.setEnabled(True)
                    self.run_stop.setEnabled(False)
                    self.run_cmd_btn.setEnabled(False)

                QTimer.singleShot(0, enable_buttons)
            except Exception as e:
                # If stop_server() fails, still re-enable buttons
                def enable_buttons_on_error():
                    self._log(self.vanilla_run_console, f"Error stopping server: {e}\n", "error")
                    self.run_start.setEnabled(True)
                    self.run_config.setEnabled(True)
                    self.run_stop.setEnabled(False)
                    self.run_cmd_btn.setEnabled(False)

                QTimer.singleShot(0, enable_buttons_on_error)

        threading.Thread(target=stop, daemon=True).start()

    def _blink_send_button(self, btn: QPushButton, manager):
        """Blink the send button for visual feedback when sending a command."""
        blink_count = [0]  # Use list to modify in nested function

        def toggle():
            if blink_count[0] >= 2:  # 2 full blinks (on-off-on-off)
                btn.setEnabled(manager is not None and manager.is_server_running())
                return

            # Toggle enabled state
            btn.setEnabled(not btn.isEnabled())
            blink_count[0] += 1
            QTimer.singleShot(400, toggle)  # 400ms = half of 0.8s cycle

        btn.setEnabled(False)
        QTimer.singleShot(400, toggle)

    def _send_vanilla_cmd(self):
        cmd = self.run_cmd.text().strip()
        if cmd and self.server_manager:
            if not cmd.startswith("/"):
                self._log(self.vanilla_run_console, "Commands must start with /\n", "warning")
                return
            # Remove "/" prefix for server console (server doesn't use /)
            server_cmd = cmd[1:]
            self._log(self.vanilla_run_console, f"> {cmd}\n", "info")
            self.server_manager.send_command(server_cmd)
            self.run_cmd.clear()

            # Blink button for visual feedback
            self._blink_send_button(self.run_cmd_btn, self.server_manager)

    def _config_vanilla(self):
        if self.server_manager and self.server_manager.is_server_running():
            QMessageBox.warning(self, "Warning", "Stop server first")
            return

        self._open_config_dialog("vanilla")

    def _open_config_dialog(self, server_type: str):
        dialog = QDialog(self)
        dialog.setWindowTitle("Server Configuration")
        # Vanilla needs more height for pause-when-empty option
        dialog_height = 720 if server_type == "vanilla" else 620
        dialog.setFixedSize(420, dialog_height)
        dialog.setStyleSheet(f"background-color: {self.colors['bg_card']};")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Get manager
        manager = self.server_manager if server_type == "vanilla" else self.modpack_server_manager

        # Get total system RAM
        total_ram = system_utils.get_total_ram()
        if total_ram == -1:
            total_ram = 8192  # Default fallback if can't detect

        # Combo style
        combo_style = f"""
            QComboBox {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 10px 14px;
                padding-right: 35px;
                font-size: 13px;
            }}
            QComboBox:hover {{
                border: 1px solid {self.colors['accent']};
            }}
            QComboBox:on {{
                border: 1px solid {self.colors['accent']};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 30px;
                border: none;
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
                image: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                selection-background-color: {self.colors['accent']};
                selection-color: #000000;
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: rgba(74, 222, 128, 0.2);
            }}
        """

        # Helper to create combo with icon
        def create_combo_with_arrow(items, current_value):
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(0)

            combo = QComboBox()
            combo.addItems(items)
            combo.setCurrentText(current_value)
            combo.setStyleSheet(combo_style)
            combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            # Add arrow label
            arrow_label = QLabel("▼")
            arrow_label.setFixedWidth(30)
            arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            arrow_label.setStyleSheet(f"""
                color: {self.colors['text_secondary']};
                font-size: 10px;
                background: transparent;
                margin-right: 10px;
            """)

            # Update arrow on popup show/hide
            def on_show():
                arrow_label.setText("▲")
                arrow_label.setStyleSheet(f"color: {self.colors['accent']}; font-size: 10px; background: transparent; margin-right: 10px;")

            def on_hide():
                arrow_label.setText("▼")
                arrow_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 10px; background: transparent; margin-right: 10px;")

            combo.showPopup = lambda orig=combo.showPopup: (on_show(), orig())[-1]
            combo.hidePopup = lambda orig=combo.hidePopup: (on_hide(), orig())[-1]

            h_layout.addWidget(combo, 1)
            h_layout.addWidget(arrow_label)

            return container, combo

        slider_style = f"""
            QSlider::groove:horizontal {{
                background: {self.colors['bg_input']};
                height: 8px;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {self.colors['accent']};
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.colors['accent']};
                border-radius: 4px;
            }}
        """

        # === RAM Section ===
        ram_section = QLabel("RAM Allocation")
        ram_section.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600;")
        layout.addWidget(ram_section)

        ram = self.vanilla_ram if server_type == "vanilla" else self.modpack_ram
        ram_label = QLabel(f"{ram} MB ({ram / 1024:.1f} GB)")
        ram_label.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 500;")
        layout.addWidget(ram_label)

        ram_slider = QSlider(Qt.Orientation.Horizontal)
        min_ram = 1024 if server_type == "vanilla" else 2048
        max_ram = min(total_ram - 1024, 32768)
        max_ram = max(max_ram, min_ram + 1024)

        ram_slider.setMinimum(min_ram)
        ram_slider.setMaximum(max_ram)
        ram_slider.setSingleStep(512)
        ram_slider.setValue(ram)
        ram_slider.setStyleSheet(slider_style)
        ram_slider.valueChanged.connect(lambda v: ram_label.setText(f"{v} MB ({v / 1024:.1f} GB)"))
        layout.addWidget(ram_slider)

        ram_info = QLabel(f"System: {total_ram / 1024:.1f} GB | Max: {max_ram / 1024:.1f} GB")
        ram_info.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
        layout.addWidget(ram_info)

        layout.addSpacing(4)

        # === Gamemode Section ===
        gamemode_section = QLabel("Gamemode")
        gamemode_section.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600;")
        layout.addWidget(gamemode_section)

        current_gamemode = "survival"
        if manager:
            saved_gm = manager.get_property("gamemode")
            if saved_gm:
                current_gamemode = saved_gm

        gamemode_container, gamemode_combo = create_combo_with_arrow(
            ["survival", "creative", "adventure", "spectator"],
            current_gamemode
        )
        layout.addWidget(gamemode_container)

        layout.addSpacing(4)

        # === Difficulty Section ===
        diff_section = QLabel("Difficulty")
        diff_section.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600;")
        layout.addWidget(diff_section)

        current_difficulty = "normal"
        if manager:
            saved_diff = manager.get_property("difficulty")
            if saved_diff:
                current_difficulty = saved_diff

        diff_container, diff_combo = create_combo_with_arrow(
            ["peaceful", "easy", "normal", "hard"],
            current_difficulty
        )
        layout.addWidget(diff_container)

        layout.addSpacing(4)

        # === Max Players Section ===
        players_section = QLabel("Max Players")
        players_section.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600;")
        layout.addWidget(players_section)

        current_max_players = 20
        if manager:
            saved_players = manager.get_property("max-players")
            if saved_players:
                try:
                    current_max_players = int(saved_players)
                except ValueError:
                    pass

        players_label = QLabel(f"{current_max_players} players")
        players_label.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 500;")
        layout.addWidget(players_label)

        players_slider = QSlider(Qt.Orientation.Horizontal)
        players_slider.setMinimum(1)
        players_slider.setMaximum(100)
        players_slider.setValue(current_max_players)
        players_slider.setStyleSheet(slider_style)
        players_slider.valueChanged.connect(lambda v: players_label.setText(f"{v} players"))
        layout.addWidget(players_slider)

        layout.addSpacing(4)

        # === Online Mode Section ===
        online_section = QLabel("Online Mode")
        online_section.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600;")
        layout.addWidget(online_section)

        online_hint = QLabel("Set to OFF to allow non-premium players (LAN/Hamachi)")
        online_hint.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
        online_hint.setWordWrap(True)
        layout.addWidget(online_hint)

        # Get current value (default to false for easier LAN play)
        current_online_mode = "false"
        if manager:
            saved_online = manager.get_property("online-mode")
            if saved_online:
                current_online_mode = saved_online.lower()

        online_container, online_combo = create_combo_with_arrow(
            ["false", "true"],
            current_online_mode
        )
        layout.addWidget(online_container)

        layout.addSpacing(4)

        # === Pause When Empty Section (only for vanilla) ===
        pause_spinbox = None  # Will be set only for vanilla
        if server_type == "vanilla":
            pause_section = QLabel("Pause When Empty")
            pause_section.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600;")
            layout.addWidget(pause_section)

            pause_hint = QLabel("Server pauses when no players connected (saves resources)")
            pause_hint.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
            pause_hint.setWordWrap(True)
            layout.addWidget(pause_hint)

            # Get current value
            current_pause = 0  # 0 = disabled
            if manager:
                saved_pause = manager.get_property("pause-when-empty-seconds")
                if saved_pause:
                    try:
                        current_pause = int(saved_pause)
                    except ValueError:
                        pass

            # Container for input
            pause_container = QWidget()
            pause_container.setStyleSheet("background: transparent;")
            pause_h_layout = QHBoxLayout(pause_container)
            pause_h_layout.setContentsMargins(0, 4, 0, 0)
            pause_h_layout.setSpacing(8)

            # Spinbox for seconds (0-7200 = up to 2 hours)
            pause_spinbox = QSpinBox()
            pause_spinbox.setMinimum(0)
            pause_spinbox.setMaximum(7200)
            pause_spinbox.setValue(current_pause)
            pause_spinbox.setSingleStep(60)
            pause_spinbox.setSpecialValueText("Disabled")
            # Fix input validation for high values
            pause_spinbox.setKeyboardTracking(False)
            pause_spinbox.lineEdit().setMaxLength(4)
            pause_spinbox.setCorrectionMode(QSpinBox.CorrectionMode.CorrectToNearestValue)
            pause_spinbox.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {self.colors['bg_input']};
                    color: {self.colors['text']};
                    border: 1px solid {self.colors['border']};
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 13px;
                    min-width: 100px;
                }}
                QSpinBox:hover {{
                    border: 1px solid {self.colors['accent']};
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    width: 20px;
                    border: none;
                    background: transparent;
                }}
            """)

            # Label showing human-readable time
            pause_time_label = QLabel()
            pause_time_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 12px;")

            def update_pause_label(value):
                if value == 0:
                    pause_time_label.setText("")
                elif value < 60:
                    pause_time_label.setText(f"= {value} sec")
                elif value < 3600:
                    mins = value // 60
                    secs = value % 60
                    if secs == 0:
                        pause_time_label.setText(f"= {mins} min")
                    else:
                        pause_time_label.setText(f"= {mins}m {secs}s")
                else:
                    hours = value // 3600
                    mins = (value % 3600) // 60
                    if mins == 0:
                        pause_time_label.setText(f"= {hours}h")
                    else:
                        pause_time_label.setText(f"= {hours}h {mins}m")

            update_pause_label(current_pause)
            pause_spinbox.valueChanged.connect(update_pause_label)

            # Quick presets
            preset_5m = QPushButton("5m")
            preset_5m.setFixedSize(36, 28)
            preset_5m.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            preset_5m.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors['bg_input']};
                    color: {self.colors['text_secondary']};
                    border: 1px solid {self.colors['border']};
                    border-radius: 6px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {self.colors['accent']};
                    color: #000000;
                }}
            """)
            preset_5m.clicked.connect(lambda: pause_spinbox.setValue(300))

            preset_30m = QPushButton("30m")
            preset_30m.setFixedSize(36, 28)
            preset_30m.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            preset_30m.setStyleSheet(preset_5m.styleSheet())
            preset_30m.clicked.connect(lambda: pause_spinbox.setValue(1800))

            preset_1h = QPushButton("1h")
            preset_1h.setFixedSize(36, 28)
            preset_1h.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            preset_1h.setStyleSheet(preset_5m.styleSheet())
            preset_1h.clicked.connect(lambda: pause_spinbox.setValue(3600))

            pause_h_layout.addWidget(pause_spinbox)
            pause_h_layout.addWidget(pause_time_label)
            pause_h_layout.addStretch()
            pause_h_layout.addWidget(preset_5m)
            pause_h_layout.addWidget(preset_30m)
            pause_h_layout.addWidget(preset_1h)

            layout.addWidget(pause_container)

        layout.addStretch()

        # Save button
        save = self._styled_button("Save", self.colors['accent'], "#000000", 120)
        save.clicked.connect(lambda: self._save_config(
            server_type,
            ram_slider.value(),
            diff_combo.currentText(),
            gamemode_combo.currentText(),
            players_slider.value(),
            online_combo.currentText(),
            pause_spinbox.value() if pause_spinbox else None,
            dialog
        ))
        layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignCenter)

        # Footer with version info
        layout.addSpacing(12)
        footer_line = QFrame()
        footer_line.setFrameShape(QFrame.Shape.HLine)
        footer_line.setStyleSheet(f"background-color: {self.colors['border']}; max-height: 1px;")
        layout.addWidget(footer_line)

        # Get version info
        mc_version = ""
        loader_info = ""

        if server_type == "vanilla":
            if self.server_manager:
                mc_version = self.server_manager.detect_minecraft_version() or ""
            loader_info = "Vanilla"
        else:
            if self.modpack_server_path:
                # Try ServerManager first, then fallback to our detection
                if self.modpack_server_manager:
                    mc_version = self.modpack_server_manager.detect_minecraft_version() or ""
                if not mc_version:
                    mc_version = self._detect_modpack_mc_version(self.modpack_server_path)
                loader_info = self._detect_modpack_loader(self.modpack_server_path) or "Modded"

        version_text = ""
        if mc_version:
            version_text = f"Minecraft {mc_version}"
        if loader_info:
            if version_text:
                version_text += f" | {loader_info}"
            else:
                version_text = loader_info

        if version_text:
            footer_label = QLabel(version_text)
            footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            footer_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
            layout.addWidget(footer_label)

        dialog.exec()

    def _save_config(self, server_type: str, ram: int, difficulty: str, gamemode: str, max_players: int, online_mode: str, pause_when_empty: Optional[int], dialog: QDialog):
        if server_type == "vanilla":
            self.vanilla_ram = ram
            if self.server_manager:
                self.server_manager.configure_server_properties(difficulty=difficulty)
                self.server_manager.update_property("gamemode", gamemode)
                self.server_manager.update_property("max-players", str(max_players))
                self.server_manager.update_property("online-mode", online_mode)
                if pause_when_empty is not None:
                    self.server_manager.update_property("pause-when-empty-seconds", str(pause_when_empty))
        else:
            self.modpack_ram = ram
            if self.modpack_server_manager:
                self.modpack_server_manager.configure_server_properties(difficulty=difficulty)
                self.modpack_server_manager.update_property("gamemode", gamemode)
                self.modpack_server_manager.update_property("max-players", str(max_players))
                self.modpack_server_manager.update_property("online-mode", online_mode)
        dialog.accept()

    # Modpack search with debounce
    def _on_mp_search_changed(self, text: str):
        """Handle text changes with debounce for real-time search"""
        # Clear results if text is too short
        if len(text.strip()) < 3:
            # Clear previous results
            while self.mp_results_layout.count():
                child = self.mp_results_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self.mp_pagination_widget.setVisible(False)
            self.mp_search_timer.stop()
            return

        # Restart debounce timer
        self.mp_search_timer.stop()
        self.mp_search_timer.start()

    def _search_modpacks(self, page: int = 1):
        query = self.mp_search.text().strip()
        if len(query) < 3:
            return

        self.mp_search_query = query
        self.mp_current_page = page

        # Clear previous results
        while self.mp_results_layout.count():
            child = self.mp_results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        def search():
            try:
                offset = (page - 1) * 10
                # Filter for server-compatible modpacks only
                results, total = self.modpack_manager.search_modpacks(
                    query,
                    platform=self.mp_selected_provider,
                    limit=10,
                    offset=offset,
                    side_filter="server"
                )
                self.modpack_results = results

                if results:
                    self.mp_pagination_signal.emit(total)
                    self.modpack_results_signal.emit(results)
                else:
                    self.mp_pagination_signal.emit(0)

            except Exception as e:
                self.log_signal.emit(f"Error: {e}\n", "error", "m_install")

        threading.Thread(target=search, daemon=True).start()

    def _mp_go_page(self, page: int):
        """Navigate to a specific page"""
        total_pages = (self.mp_total_results + 9) // 10
        if 1 <= page <= total_pages:
            self._search_modpacks(page)

    def _update_mp_pagination(self, total: int):
        """Update pagination UI"""
        self.mp_total_results = total
        total_pages = (total + 9) // 10

        if total_pages <= 1:
            self.mp_pagination_widget.setVisible(False)
            return

        self.mp_pagination_widget.setVisible(True)
        self.mp_page_info.setText(f"{total} results")

        # Clear existing page buttons
        while self.mp_page_btns_layout.count():
            child = self.mp_page_btns_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Create page buttons (show max 5 pages)
        start_page = max(1, self.mp_current_page - 2)
        end_page = min(total_pages, start_page + 4)
        start_page = max(1, end_page - 4)

        for p in range(start_page, end_page + 1):
            btn = QPushButton(str(p))
            btn.setFixedSize(32, 32)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            is_current = p == self.mp_current_page
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors['accent'] if is_current else self.colors['bg_input']};
                    color: {'#000000' if is_current else self.colors['text']};
                    border: 1px solid {self.colors['accent'] if is_current else self.colors['border']};
                    border-radius: 6px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background-color: {self.colors['accent_hover'] if is_current else self.colors['bg_card']}; }}
            """)
            btn.clicked.connect(lambda checked, page=p: self._mp_go_page(page))
            self.mp_page_btns_layout.addWidget(btn)

        self.mp_prev_btn.setEnabled(self.mp_current_page > 1)
        self.mp_next_btn.setEnabled(self.mp_current_page < total_pages)

    def _show_mp_results(self, results: list):
        for mp in results:
            self._create_mp_item(mp)

    def _format_downloads(self, count: int) -> str:
        """Format download count (e.g., 1.2M, 50K)"""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count / 1_000:.0f}K"
        return str(count)

    def _create_mp_item(self, mp: dict):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_input']};
                border-radius: 10px;
                border: 1px solid {self.colors['border']};
            }}
            QFrame:hover {{
                border: 1px solid {self.colors['accent']};
            }}
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Icon placeholder
        icon_label = QLabel()
        icon_label.setFixedSize(56, 56)
        icon_label.setStyleSheet(f"""
            background-color: {self.colors['bg_card']};
            border-radius: 8px;
            border: none;
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        project_id = mp.get("project_id", "")
        icon_label.setObjectName(f"mp_icon_{project_id}")

        # Check cache first and set directly, otherwise load async
        icon_url = mp.get("icon_url", "")
        if project_id in self.mp_icon_cache:
            icon_label.setPixmap(self.mp_icon_cache[project_id])
        elif icon_url and project_id:
            self._load_mp_icon(icon_url, project_id)

        layout.addWidget(icon_label)

        # Info section
        info = QWidget()
        info.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)

        # Title
        name = QLabel(mp.get("title", "Unknown"))
        name.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600; border: none;")
        info_layout.addWidget(name)

        # Description
        desc_text = mp.get("description", "")[:80]
        if len(mp.get("description", "")) > 80:
            desc_text += "..."
        desc = QLabel(desc_text)
        desc.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px; border: none;")
        desc.setWordWrap(True)
        info_layout.addWidget(desc)

        # Meta info row (loader, MC version, downloads)
        meta_widget = QWidget()
        meta_widget.setStyleSheet("background: transparent;")
        meta_layout = QHBoxLayout(meta_widget)
        meta_layout.setContentsMargins(0, 2, 0, 0)
        meta_layout.setSpacing(8)

        # Get categories to detect loader
        categories = mp.get("categories", [])
        loader = "Unknown"
        loader_color = self.colors['text_muted']
        if "forge" in categories:
            loader = "Forge"
            loader_color = "#FF6B35"
        elif "neoforge" in categories:
            loader = "NeoForge"
            loader_color = "#D64541"
        elif "fabric" in categories:
            loader = "Fabric"
            loader_color = "#C6BCA7"
        elif "quilt" in categories:
            loader = "Quilt"
            loader_color = "#8B5CF6"

        loader_label = QLabel(loader)
        loader_label.setStyleSheet(f"""
            color: {loader_color};
            font-size: 11px;
            font-weight: 600;
            background-color: {self.colors['bg_card']};
            padding: 2px 6px;
            border-radius: 4px;
        """)
        meta_layout.addWidget(loader_label)

        # MC versions
        versions = mp.get("versions", [])
        if versions:
            mc_ver = versions[0] if len(versions) == 1 else f"{versions[-1]}-{versions[0]}"
            mc_label = QLabel(f"MC {mc_ver}")
            mc_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 11px; border: none;")
            meta_layout.addWidget(mc_label)

        # Downloads
        downloads = mp.get("downloads", 0)
        dl_label = QLabel(f"{self._format_downloads(downloads)} downloads")
        dl_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px; border: none;")
        meta_layout.addWidget(dl_label)

        meta_layout.addStretch()

        # Link to provider
        slug = mp.get("slug", "")
        source = mp.get("source", "modrinth")
        if slug:
            link_btn = QPushButton()
            link_btn.setIcon(qta.icon("fa5s.external-link-alt", color=self.colors['text_muted']))
            link_btn.setFixedSize(24, 24)
            link_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if source == "curseforge":
                link_btn.setToolTip("Open in CurseForge")
                link_url = f"https://www.curseforge.com/minecraft/modpacks/{slug}"
            else:
                link_btn.setToolTip("Open in Modrinth")
                link_url = f"https://modrinth.com/modpack/{slug}"
            link_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {self.colors['bg_card']};
                    border-radius: 4px;
                }}
            """)
            link_btn.clicked.connect(lambda _, url=link_url: QDesktopServices.openUrl(QUrl(url)))
            meta_layout.addWidget(link_btn)

        info_layout.addWidget(meta_widget)
        layout.addWidget(info, 1)

        # Select button
        select = self._styled_button("Select", self.colors['accent'], "#000000", 80)
        select.setFixedHeight(36)
        select.clicked.connect(lambda: self._pick_mp(mp))
        layout.addWidget(select)

        self.mp_results_layout.addWidget(frame)

    def _load_mp_icon(self, url: str, project_id: str):
        """Load modpack icon asynchronously"""
        # Skip if already in cache (will be set directly)
        if project_id in self.mp_icon_cache:
            return

        def load():
            try:
                import requests
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    pixmap = QPixmap()
                    pixmap.loadFromData(response.content)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.mp_icon_cache[project_id] = scaled
                        self.mp_icon_signal.emit(project_id, scaled)
            except Exception:
                pass

        threading.Thread(target=load, daemon=True).start()

    def _on_mp_icon_loaded(self, project_id: str, pixmap):
        """Handle loaded icon"""
        icon_label = self.findChild(QLabel, f"mp_icon_{project_id}")
        if icon_label and pixmap:
            icon_label.setPixmap(pixmap)

    def _on_versions_loaded(self, versions, callback):
        """Handle versions loaded from thread"""
        if callback:
            callback(versions)

    def _pick_mp(self, mp: dict):
        """Show version selector dialog for server install"""
        self._show_version_selector(mp, is_client=False)

    def _show_version_selector(self, mp: dict, is_client: bool = False):
        """Show dialog to select modpack version"""
        project_id = mp.get("project_id", "")
        mp_name = mp.get("title", "Unknown")

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Select Version - {mp_name}")
        dialog.setFixedSize(500, 400)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['bg_main']};
            }}
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel(f"Select version for {mp_name}")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 16px; font-weight: bold; border: none;")
        layout.addWidget(title)

        # Loading label
        loading = QLabel("Loading versions...")
        loading.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 13px; border: none;")
        loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(loading)

        # Versions list (hidden initially)
        versions_scroll = QScrollArea()
        versions_scroll.setWidgetResizable(True)
        versions_scroll.setStyleSheet(self._scroll_style())
        versions_scroll.setVisible(False)

        versions_widget = QWidget()
        versions_layout = QVBoxLayout(versions_widget)
        versions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        versions_layout.setSpacing(8)
        versions_scroll.setWidget(versions_widget)

        layout.addWidget(versions_scroll, 1)

        # Selected version info
        selected_info = QLabel("")
        selected_info.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600; border: none;")
        selected_info.setVisible(False)
        layout.addWidget(selected_info)

        # Buttons
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()

        cancel_btn = self._styled_button("Cancel", self.colors['bg_input'], self.colors['text'], 100)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = self._styled_button("Select", self.colors['accent'], "#000000", 100)
        confirm_btn.setEnabled(False)
        btn_layout.addWidget(confirm_btn)

        layout.addWidget(btn_row)

        # Store selected version in dialog
        dialog.selected_version = None

        def on_version_selected(version_data):
            dialog.selected_version = version_data
            v_name = version_data.get("name", version_data.get("version_number", ""))
            loaders = version_data.get("loaders", [])
            game_vers = version_data.get("game_versions", [])
            loader = loaders[0].capitalize() if loaders else "Unknown"
            mc_ver = game_vers[0] if game_vers else "Unknown"
            # Clear format: version name (Loader, MC version)
            selected_info.setText(f"Selected: {v_name} ({loader}, MC {mc_ver})")
            selected_info.setVisible(True)
            confirm_btn.setEnabled(True)

        def load_versions():
            try:
                source = mp.get("source", "modrinth")
                if source == "curseforge":
                    # Use CurseForge API
                    curseforge_id = mp.get("_curseforge_id")
                    if not curseforge_id:
                        curseforge_id = int(project_id)

                    if self.modpack_manager.curseforge_api is None:
                        from ..core.api import CurseForgeAPI
                        self.modpack_manager.curseforge_api = CurseForgeAPI()

                    files = self.modpack_manager.curseforge_api.get_modpack_files(curseforge_id)
                    if files:
                        # Normalize CurseForge files to Modrinth-like format
                        # IMPORTANT: For server modpacks, only show versions that have a server pack
                        versions = []
                        for f in files:
                            # Skip versions without server pack (for server installation)
                            server_pack_file_id = f.get("serverPackFileId")
                            if not server_pack_file_id:
                                continue  # Skip this version - no server pack available

                            # Get loader from file name or gameVersions
                            loader = "unknown"
                            file_name = f.get("fileName", "").lower()
                            game_versions_raw = f.get("gameVersions", [])

                            # Separate MC versions from loaders
                            mc_versions = []
                            for gv in game_versions_raw:
                                gv_lower = gv.lower()
                                if gv_lower in ("forge", "neoforge", "fabric", "quilt"):
                                    loader = gv_lower
                                elif gv and gv[0].isdigit():
                                    mc_versions.append(gv)

                            # Also check file name for loader
                            if loader == "unknown":
                                if "forge" in file_name and "neoforge" not in file_name:
                                    loader = "forge"
                                elif "neoforge" in file_name:
                                    loader = "neoforge"
                                elif "fabric" in file_name:
                                    loader = "fabric"
                                elif "quilt" in file_name:
                                    loader = "quilt"

                            versions.append({
                                "id": str(f.get("id", "")),
                                "name": f.get("displayName", f.get("fileName", "Unknown")),
                                "version_number": f.get("displayName", ""),
                                "loaders": [loader],
                                "game_versions": mc_versions if mc_versions else game_versions_raw,
                                "downloads": f.get("downloadCount", 0),
                                "source": "curseforge",
                                "_curseforge_file": f,
                                "_server_pack_file_id": server_pack_file_id  # Store for later use
                            })

                        if not versions:
                            self.version_loaded_signal.emit(None, lambda v: loading.setText("No server pack versions available"))
                        else:
                            self.version_loaded_signal.emit(versions, show_versions)
                    else:
                        self.version_loaded_signal.emit(None, lambda v: loading.setText("No versions found"))
                else:
                    # Use Modrinth API
                    versions = self.modpack_manager.modrinth_api.get_modpack_versions(project_id)
                    if versions:
                        self.version_loaded_signal.emit(versions, show_versions)
                    else:
                        self.version_loaded_signal.emit(None, lambda v: loading.setText("No versions found"))
            except Exception as e:
                self.version_loaded_signal.emit(None, lambda v: loading.setText(f"Error: {e}"))

        def show_versions(versions):
            loading.setVisible(False)
            versions_scroll.setVisible(True)

            for i, v in enumerate(versions[:20]):  # Show max 20 versions
                v_frame = QFrame()
                v_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {self.colors['bg_input']};
                        border-radius: 8px;
                        border: 1px solid {self.colors['border']};
                    }}
                    QFrame:hover {{
                        border: 1px solid {self.colors['accent']};
                    }}
                """)
                v_frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

                v_layout = QHBoxLayout(v_frame)
                v_layout.setContentsMargins(12, 10, 12, 10)

                # Version info
                v_info = QWidget()
                v_info.setStyleSheet("background: transparent;")
                v_info_layout = QVBoxLayout(v_info)
                v_info_layout.setContentsMargins(0, 0, 0, 0)
                v_info_layout.setSpacing(2)

                v_name = v.get("name", v.get("version_number", "Unknown"))
                if i == 0:
                    v_name += " (Latest)"
                name_label = QLabel(v_name)
                name_label.setStyleSheet(f"color: {self.colors['text']}; font-size: 13px; font-weight: 600; border: none;")
                v_info_layout.addWidget(name_label)

                # Loader and MC version
                loaders = v.get("loaders", [])
                game_vers = v.get("game_versions", [])
                loader = loaders[0].capitalize() if loaders else "Unknown"
                mc_ver = game_vers[0] if game_vers else "Unknown"

                # Loader color
                loader_color = self.colors['text_muted']
                if loader.lower() == "forge":
                    loader_color = "#FF6B35"
                elif loader.lower() == "neoforge":
                    loader_color = "#D64541"
                elif loader.lower() == "fabric":
                    loader_color = "#C6BCA7"
                elif loader.lower() == "quilt":
                    loader_color = "#8B5CF6"

                meta_label = QLabel(f"{loader} • MC {mc_ver}")
                meta_label.setStyleSheet(f"color: {loader_color}; font-size: 11px; border: none;")
                v_info_layout.addWidget(meta_label)

                v_layout.addWidget(v_info, 1)

                # Downloads
                downloads = v.get("downloads", 0)
                dl_label = QLabel(f"{self._format_downloads(downloads)}")
                dl_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px; border: none;")
                v_layout.addWidget(dl_label)

                # Make frame clickable
                v_frame.mousePressEvent = lambda e, ver=v: on_version_selected(ver)

                versions_layout.addWidget(v_frame)

        def on_confirm():
            if dialog.selected_version:
                if is_client:
                    self.client_selected_modpack = mp
                    self.client_selected_mp_version = dialog.selected_version
                    v_name = dialog.selected_version.get("name", "")
                    self.client_mp_selected.setText(f"Selected: {mp_name} ({v_name})")
                    self.client_mp_selected.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600;")
                    self.client_mp_install_btn.setEnabled(True)
                else:
                    self.selected_modpack = mp
                    self.selected_mp_version = dialog.selected_version
                    v_name = dialog.selected_version.get("name", "")
                    self.mp_selected.setText(f"Selected: {mp_name} ({v_name})")
                    self.mp_selected.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600;")
                    self._update_mp_btn()
                dialog.accept()

        confirm_btn.clicked.connect(on_confirm)

        # Load versions in thread
        threading.Thread(target=load_versions, daemon=True).start()

        dialog.exec()

    def _select_mp_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            if not self._warn_dangerous_folder(folder):
                return  # User cancelled
            if not self._warn_existing_server(folder):
                return  # Server already exists
            self.modpack_folder = folder
            self.mp_folder_label.setText(f"Folder: {folder}")
            self._update_mp_btn()

    def _update_mp_btn(self):
        self.mp_install_btn.setEnabled(bool(self.selected_modpack and self.modpack_folder))

    def _install_modpack(self):
        if not self.selected_modpack or not self.modpack_folder:
            return

        self.mp_install_btn.setEnabled(False)
        project_id = self.selected_modpack.get("project_id", "")
        version_id = self.selected_mp_version.get("id", "") if self.selected_mp_version else None
        mp_name = self.selected_modpack.get("title", "Unknown")
        source = self.selected_modpack.get("source", "modrinth")

        # Get version info for post-install message
        version_info = self.selected_mp_version or {}
        game_versions = version_info.get("game_versions", [])
        # Filter to get only MC versions (start with digit), exclude loader names
        mc_versions = [v for v in game_versions if v and v[0].isdigit()]
        mc_version = mc_versions[0] if mc_versions else (game_versions[0] if game_versions else "Unknown")
        loaders = version_info.get("loaders", ["Unknown"])
        loader_type = loaders[0] if loaders else "Unknown"

        def install():
            try:
                self.log_signal.emit(f"\nInstalling {mp_name}...\n", "info", "m_install")

                if source == "curseforge":
                    # CurseForge installation
                    curseforge_id = self.selected_modpack.get("_curseforge_id")
                    if not curseforge_id:
                        curseforge_id = int(project_id)

                    # Get file_id from the selected version
                    curseforge_file = version_info.get("_curseforge_file", {})
                    file_id = curseforge_file.get("id") if curseforge_file else int(version_id)

                    # Initialize CurseForge API if needed
                    if self.modpack_manager.curseforge_api is None:
                        from ..core.api import CurseForgeAPI
                        self.modpack_manager.curseforge_api = CurseForgeAPI()

                    success = self.modpack_manager.install_curseforge_modpack(
                        curseforge_id,
                        file_id,
                        self.modpack_folder,
                        log_callback=lambda m: self.log_signal.emit(m, "normal", "m_install")
                    )
                else:
                    # Modrinth installation
                    success = self.modpack_manager.install_modrinth_modpack(
                        project_id,
                        version_id,
                        self.modpack_folder,
                        log_callback=lambda m: self.log_signal.emit(m, "normal", "m_install")
                    )

                if success:
                    self.log_signal.emit("\n" + "="*50 + "\n", "success", "m_install")
                    self.log_signal.emit("SERVER MODPACK INSTALLED\n", "success", "m_install")
                    self.log_signal.emit("="*50 + "\n", "success", "m_install")

                    # Show success modal via signal (thread-safe)
                    self.server_modpack_install_success_signal.emit(mp_name, mc_version, loader_type)

            except Exception as e:
                self.log_signal.emit(f"Error: {e}\n", "error", "m_install")

            finally:
                QTimer.singleShot(0, lambda: self.mp_install_btn.setEnabled(True))

        threading.Thread(target=install, daemon=True).start()

    def _show_server_install_notice(self, mp_name: str, mc_version: str, loader_type: str):
        """Show notification after server modpack installation"""
        try:
            loader_display = loader_type.capitalize() if loader_type else "Unknown"
        except:
            loader_display = "Unknown"

        msg = QMessageBox(self)
        msg.setWindowTitle("Server Installed Successfully")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"Server modpack '{mp_name}' has been installed!")
        msg.setInformativeText(
            f"Minecraft: {mc_version}\n"
            f"Loader: {loader_display}\n\n"
            f"IMPORTANT: To play on this server, you need to\n"
            f"install the same modpack on your client.\n\n"
            f"Go to 'Client Modpacks' in the sidebar to download\n"
            f"the modpack for your launcher."
        )

        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.colors['bg_card']};
            }}
            QMessageBox QLabel {{
                color: {self.colors['text']};
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {self.colors['accent']};
                color: #000000;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: 600;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['accent_hover']};
            }}
        """)

        msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        client_btn = msg.addButton("Client Modpacks", QMessageBox.ButtonRole.ActionRole)

        msg.exec()

        if msg.clickedButton() == client_btn:
            self._go_to("client_modpacks")

    # Client Modpack Installation with debounce
    def _on_client_mp_search_changed(self, text: str):
        """Handle text changes with debounce for real-time search (client)"""
        # Clear results if text is too short
        if len(text.strip()) < 3:
            # Clear previous results
            while self.client_mp_results_layout.count():
                child = self.client_mp_results_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self.client_mp_pagination_widget.setVisible(False)
            self.client_mp_search_timer.stop()
            return

        # Restart debounce timer
        self.client_mp_search_timer.stop()
        self.client_mp_search_timer.start()

    def _search_client_modpacks(self, page: int = 1):
        query = self.client_mp_search.text().strip()
        if len(query) < 3:
            return

        self.client_mp_search_query = query
        self.client_mp_current_page = page

        # Clear previous results
        while self.client_mp_results_layout.count():
            child = self.client_mp_results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        def search():
            try:
                offset = (page - 1) * 10
                # Filter for client-compatible modpacks
                results, total = self.modpack_manager.search_modpacks(
                    query,
                    platform=self.client_mp_selected_provider,
                    limit=10,
                    offset=offset,
                    side_filter="client"
                )
                self.client_mp_results = results

                if results:
                    self.client_mp_pagination_signal.emit(total)
                    self.client_mp_results_signal.emit(results)
                else:
                    self.client_mp_pagination_signal.emit(0)

            except Exception as e:
                self.log_signal.emit(f"Error: {e}\n", "error", "c_install")

        threading.Thread(target=search, daemon=True).start()

    def _client_mp_go_page(self, page: int):
        """Navigate to a specific page (client)"""
        total_pages = (self.client_mp_total_results + 9) // 10
        if 1 <= page <= total_pages:
            self._search_client_modpacks(page)

    def _update_client_mp_pagination(self, total: int):
        """Update pagination UI (client)"""
        self.client_mp_total_results = total
        total_pages = (total + 9) // 10

        if total_pages <= 1:
            self.client_mp_pagination_widget.setVisible(False)
            return

        self.client_mp_pagination_widget.setVisible(True)
        self.client_mp_page_info.setText(f"{total} results")

        # Clear existing page buttons
        while self.client_mp_page_btns_layout.count():
            child = self.client_mp_page_btns_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Create page buttons (show max 5 pages)
        start_page = max(1, self.client_mp_current_page - 2)
        end_page = min(total_pages, start_page + 4)
        start_page = max(1, end_page - 4)

        for p in range(start_page, end_page + 1):
            btn = QPushButton(str(p))
            btn.setFixedSize(32, 32)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            is_current = p == self.client_mp_current_page
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors['accent'] if is_current else self.colors['bg_input']};
                    color: {'#000000' if is_current else self.colors['text']};
                    border: 1px solid {self.colors['accent'] if is_current else self.colors['border']};
                    border-radius: 6px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background-color: {self.colors['accent_hover'] if is_current else self.colors['bg_card']}; }}
            """)
            btn.clicked.connect(lambda checked, page=p: self._client_mp_go_page(page))
            self.client_mp_page_btns_layout.addWidget(btn)

        self.client_mp_prev_btn.setEnabled(self.client_mp_current_page > 1)
        self.client_mp_next_btn.setEnabled(self.client_mp_current_page < total_pages)

    def _show_client_mp_results(self, results: list):
        for mp in results:
            self._create_client_mp_item(mp)

    def _create_client_mp_item(self, mp: dict):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_input']};
                border-radius: 10px;
                border: 1px solid {self.colors['border']};
            }}
            QFrame:hover {{
                border: 1px solid {self.colors['accent']};
            }}
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Icon placeholder
        icon_label = QLabel()
        icon_label.setFixedSize(56, 56)
        icon_label.setStyleSheet(f"""
            background-color: {self.colors['bg_card']};
            border-radius: 8px;
            border: none;
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        project_id = mp.get("project_id", "")
        icon_label.setObjectName(f"mp_icon_{project_id}")

        # Check cache first and set directly, otherwise load async
        icon_url = mp.get("icon_url", "")
        if project_id in self.mp_icon_cache:
            icon_label.setPixmap(self.mp_icon_cache[project_id])
        elif icon_url and project_id:
            self._load_mp_icon(icon_url, project_id)

        layout.addWidget(icon_label)

        # Info section
        info = QWidget()
        info.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)

        # Title
        name = QLabel(mp.get("title", "Unknown"))
        name.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600; border: none;")
        info_layout.addWidget(name)

        # Description
        desc_text = mp.get("description", "")[:80]
        if len(mp.get("description", "")) > 80:
            desc_text += "..."
        desc = QLabel(desc_text)
        desc.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px; border: none;")
        desc.setWordWrap(True)
        info_layout.addWidget(desc)

        # Meta info row
        meta_widget = QWidget()
        meta_widget.setStyleSheet("background: transparent;")
        meta_layout = QHBoxLayout(meta_widget)
        meta_layout.setContentsMargins(0, 2, 0, 0)
        meta_layout.setSpacing(8)

        categories = mp.get("categories", [])
        loader = "Unknown"
        loader_color = self.colors['text_muted']
        if "forge" in categories:
            loader = "Forge"
            loader_color = "#FF6B35"
        elif "neoforge" in categories:
            loader = "NeoForge"
            loader_color = "#D64541"
        elif "fabric" in categories:
            loader = "Fabric"
            loader_color = "#C6BCA7"
        elif "quilt" in categories:
            loader = "Quilt"
            loader_color = "#8B5CF6"

        loader_label = QLabel(loader)
        loader_label.setStyleSheet(f"""
            color: {loader_color};
            font-size: 11px;
            font-weight: 600;
            background-color: {self.colors['bg_card']};
            padding: 2px 6px;
            border-radius: 4px;
        """)
        meta_layout.addWidget(loader_label)

        versions = mp.get("versions", [])
        if versions:
            mc_ver = versions[0] if len(versions) == 1 else f"{versions[-1]}-{versions[0]}"
            mc_label = QLabel(f"MC {mc_ver}")
            mc_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 11px;")
            meta_layout.addWidget(mc_label)

        downloads = mp.get("downloads", 0)
        dl_label = QLabel(f"{self._format_downloads(downloads)} downloads")
        dl_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
        meta_layout.addWidget(dl_label)

        meta_layout.addStretch()

        # Link to provider
        slug = mp.get("slug", "")
        source = mp.get("source", "modrinth")
        if slug:
            link_btn = QPushButton()
            link_btn.setIcon(qta.icon("fa5s.external-link-alt", color=self.colors['text_muted']))
            link_btn.setFixedSize(24, 24)
            link_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if source == "curseforge":
                link_btn.setToolTip("Open in CurseForge")
                link_url = f"https://www.curseforge.com/minecraft/modpacks/{slug}"
            else:
                link_btn.setToolTip("Open in Modrinth")
                link_url = f"https://modrinth.com/modpack/{slug}"
            link_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {self.colors['bg_card']};
                    border-radius: 4px;
                }}
            """)
            link_btn.clicked.connect(lambda _, url=link_url: QDesktopServices.openUrl(QUrl(url)))
            meta_layout.addWidget(link_btn)

        info_layout.addWidget(meta_widget)
        layout.addWidget(info, 1)

        # Select button
        select = self._styled_button("Select", self.colors['accent'], "#000000", 80)
        select.setFixedHeight(36)
        select.clicked.connect(lambda: self._pick_client_mp(mp))
        layout.addWidget(select)

        self.client_mp_results_layout.addWidget(frame)

    def _pick_client_mp(self, mp: dict):
        """Show version selector dialog for client install"""
        self._show_version_selector(mp, is_client=True)

    def _install_client_modpack(self):
        if not self.client_selected_modpack:
            return

        self.client_mp_install_btn.setEnabled(False)
        mp = self.client_selected_modpack
        project_id = mp.get("project_id", "")
        mp_name = mp.get("title", "Unknown")
        source = mp.get("source", "modrinth")
        version_info = self.client_selected_mp_version or {}
        version_id = version_info.get("id", "") if version_info else None

        def install():
            try:
                self.log_signal.emit(f"\nInstalling '{mp_name}' for client...\n", "info", "c_install")

                if source == "curseforge":
                    # CurseForge client installation
                    curseforge_id = mp.get("_curseforge_id")
                    if not curseforge_id:
                        curseforge_id = int(project_id)

                    # Get file_id from the selected version
                    curseforge_file = version_info.get("_curseforge_file", {})
                    file_id = curseforge_file.get("id") if curseforge_file else int(version_id)

                    result = self.modpack_manager.install_client_curseforge_modpack(
                        curseforge_id,
                        file_id,
                        modpack_name=mp_name,
                        log_callback=lambda m: self.log_signal.emit(m, "normal", "c_install")
                    )
                else:
                    # Modrinth client installation
                    result = self.modpack_manager.install_client_modpack(
                        project_id,
                        version_id=version_id,
                        log_callback=lambda m: self.log_signal.emit(m, "normal", "c_install")
                    )

                if result and result.get("success"):
                    install_path = result.get("install_path", "")
                    mc_ver = result.get("minecraft_version", "Unknown")
                    loader = result.get("loader_type", "Unknown")
                    loader_ver = result.get("loader_version", "")

                    self.log_signal.emit("\n" + "="*50 + "\n", "success", "c_install")
                    self.log_signal.emit("CLIENT MODPACK INSTALLED SUCCESSFULLY\n", "success", "c_install")
                    self.log_signal.emit("="*50 + "\n\n", "success", "c_install")
                    self.log_signal.emit(f"Location: {install_path}\n", "info", "c_install")
                    self.log_signal.emit(f"Minecraft: {mc_ver}\n", "info", "c_install")
                    self.log_signal.emit(f"Loader: {loader} {loader_ver}\n", "info", "c_install")
                    self.log_signal.emit("\nTo use in your launcher:\n", "info", "c_install")
                    self.log_signal.emit(f"1. Create a new profile with Minecraft {mc_ver} and {loader} {loader_ver}\n", "normal", "c_install")
                    self.log_signal.emit(f"2. Set game directory to: {install_path}\n", "normal", "c_install")

                    # Show success modal via signal (thread-safe)
                    self.client_modpack_install_success_signal.emit(mp_name, mc_ver, loader, loader_ver, install_path)
                else:
                    self.log_signal.emit("\nInstallation failed\n", "error", "c_install")

            except Exception as e:
                self.log_signal.emit(f"Error: {e}\n", "error", "c_install")

            finally:
                QTimer.singleShot(0, lambda: self.client_mp_install_btn.setEnabled(True))

        threading.Thread(target=install, daemon=True).start()

    def _show_client_install_success(self, mp_name: str, mc_ver: str, loader: str, loader_ver: str, install_path: str):
        """Show success modal after client modpack installation"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Modpack Installed Successfully")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"Client modpack '{mp_name}' has been installed!")
        msg.setInformativeText(
            f"Minecraft: {mc_ver}\n"
            f"Loader: {loader} {loader_ver}\n\n"
            f"To use in your launcher:\n"
            f"1. Create a new profile with Minecraft {mc_ver} and {loader} {loader_ver}\n"
            f"2. Set game directory to:\n{install_path}"
        )
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.colors['bg_card']};
            }}
            QMessageBox QLabel {{
                color: {self.colors['text']};
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {self.colors['accent']};
                color: #000000;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: 600;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['accent_hover']};
            }}
        """)
        msg.exec()

    def _select_mp_run_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Server Folder")
        if folder:
            # Clear previous state
            self.modpack_run_console.clear()
            self.mp_run_cmd.clear()
            self.mp_cmd_btn.setEnabled(False)
            self._log(self.modpack_run_console, "Loading server folder...\n", "info")

            if self._has_server(folder):
                self.modpack_server_path = folder
                self.mp_run_folder_label.setText(f"Folder: {folder}")
                self.mp_run_status.setText("Server found")
                self.mp_run_status.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600; border: none;")

                self.modpack_server_manager = ServerManager(folder)
                self.is_modpack_configured = True

                self.mp_start.setEnabled(True)

                # Enable config only if server.properties exists
                has_properties = os.path.exists(os.path.join(folder, "server.properties"))
                self.mp_config.setEnabled(has_properties)
                if not has_properties:
                    self._log(self.modpack_run_console, "Run server once to generate server.properties\n", "warning")

                self.mp_stop.setEnabled(False)

                self._log(self.modpack_run_console, f"\nServer found: {folder}\n", "success")

                # Detect loader and MC version for modpack server
                loader_info = self._detect_modpack_loader(folder)
                mc_version = self.modpack_server_manager.detect_minecraft_version()
                # Fallback to our detection for modded servers
                if not mc_version:
                    mc_version = self._detect_modpack_mc_version(folder)

                info_parts = []
                if mc_version:
                    info_parts.append(f"Minecraft {mc_version}")
                if loader_info:
                    info_parts.append(loader_info)

                if info_parts:
                    self.modpack_server_info.setText(" | ".join(info_parts))
                    self.modpack_server_info.setVisible(True)
                    self._log(self.modpack_run_console, f"Detected: {' | '.join(info_parts)}\n", "info")
                else:
                    self.modpack_server_info.setVisible(False)
            else:
                self.modpack_server_path = None
                self.mp_run_folder_label.setText(f"Folder: {folder}")
                self.mp_run_status.setText("Server not found")
                self.mp_run_status.setStyleSheet(f"color: {self.colors['red']}; font-size: 13px; font-weight: 600; border: none;")
                self.mp_start.setEnabled(False)
                self.mp_config.setEnabled(False)
                self.mp_stop.setEnabled(False)
                self.mp_cmd_btn.setEnabled(False)
                self.modpack_server_manager = None
                self.is_modpack_configured = False
                self.modpack_server_info.setVisible(False)

    def _has_server(self, folder: str) -> bool:
        """Check if folder contains a Minecraft server (vanilla or modded)"""
        import glob

        # Check for common server jar patterns
        jar_patterns = [
            "server.jar",
            "forge-*.jar",
            "neoforge-*.jar",
            "fabric-server-*.jar",
            "quilt-server-*.jar",
            "minecraft_server*.jar"
        ]

        for p in jar_patterns:
            if glob.glob(os.path.join(folder, p)):
                return True

        # Check for run scripts (common in modded servers)
        if os.path.exists(os.path.join(folder, "run.bat")) or os.path.exists(os.path.join(folder, "run.sh")):
            return True

        # Check for start scripts
        if os.path.exists(os.path.join(folder, "start.bat")) or os.path.exists(os.path.join(folder, "start.sh")):
            return True

        # Check for libraries folder with forge/neoforge (modern Forge structure)
        libraries_path = os.path.join(folder, "libraries", "net", "minecraftforge")
        if os.path.exists(libraries_path):
            return True

        neoforge_path = os.path.join(folder, "libraries", "net", "neoforged")
        if os.path.exists(neoforge_path):
            return True

        return False

    def _detect_modpack_mc_version(self, folder: str) -> str:
        """Detect Minecraft version from modded server folder"""
        import glob
        import re

        # First check modpack_info.json (created by PyCraft during install)
        info_file = os.path.join(folder, "modpack_info.json")
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                mc_ver = info.get("minecraft_version")
                if mc_ver:
                    return mc_ver
            except Exception:
                pass

        # Check libraries folder for forge (has MC version in folder name)
        forge_libs = os.path.join(folder, "libraries", "net", "minecraftforge", "forge")
        if os.path.exists(forge_libs):
            try:
                versions = os.listdir(forge_libs)
                if versions:
                    # Folder name is like "1.20.1-47.2.0"
                    version_folder = versions[0]
                    if '-' in version_folder:
                        mc_ver = version_folder.split('-')[0]
                        return mc_ver
            except Exception:
                pass

        # Check for forge jar name
        forge_jars = glob.glob(os.path.join(folder, "forge-*.jar"))
        if forge_jars:
            jar_name = os.path.basename(forge_jars[0])
            match = re.search(r'forge-([\d.]+)-', jar_name)
            if match:
                return match.group(1)

        # Check for neoforge libs
        neoforge_libs = os.path.join(folder, "libraries", "net", "neoforged", "neoforge")
        if os.path.exists(neoforge_libs):
            try:
                # NeoForge version starts with MC version (e.g., 21.1.77 for MC 1.21.1)
                versions = os.listdir(neoforge_libs)
                if versions:
                    # Parse NeoForge version to get MC version
                    # Format: MAJOR.MINOR.PATCH where MAJOR.MINOR maps to MC 1.MAJOR.MINOR
                    version = versions[0]
                    match = re.match(r'(\d+)\.(\d+)\.', version)
                    if match:
                        major, minor = match.groups()
                        return f"1.{major}.{minor}" if minor != "0" else f"1.{major}"
            except Exception:
                pass

        # Check variables.txt (ServerPackCreator format by Griefed)
        variables_path = os.path.join(folder, "variables.txt")
        if os.path.exists(variables_path):
            try:
                with open(variables_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Parse MINECRAFT_VERSION=1.20.1
                    match = re.search(r'^MINECRAFT_VERSION=(.+)$', content, re.MULTILINE)
                    if match:
                        return match.group(1).strip()
            except Exception:
                pass

        # Check run.bat/run.sh for version info
        for script in ["run.bat", "run.sh"]:
            script_path = os.path.join(folder, script)
            if os.path.exists(script_path):
                try:
                    with open(script_path, 'r') as f:
                        content = f.read()
                        # Look for MC version pattern
                        match = re.search(r'minecraft[_-]?server[_-]?([\d.]+)', content, re.IGNORECASE)
                        if match:
                            return match.group(1)
                        match = re.search(r'forge[/-]([\d.]+)-[\d.]+', content, re.IGNORECASE)
                        if match:
                            return match.group(1)
                except Exception:
                    pass

        return ""

    def _detect_modpack_loader(self, folder: str) -> str:
        """Detect modpack loader type and version from server folder"""
        import glob
        import re

        # Check variables.txt (ServerPackCreator format by Griefed)
        variables_path = os.path.join(folder, "variables.txt")
        if os.path.exists(variables_path):
            try:
                with open(variables_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    loader_match = re.search(r'^MODLOADER=(.+)$', content, re.MULTILINE)
                    version_match = re.search(r'^MODLOADER_VERSION=(.+)$', content, re.MULTILINE)
                    if loader_match:
                        loader = loader_match.group(1).strip()
                        version = version_match.group(1).strip() if version_match else ""
                        if version:
                            return f"{loader} {version}"
                        return loader
            except Exception:
                pass

        # Check for Forge
        forge_jars = glob.glob(os.path.join(folder, "forge-*.jar"))
        if forge_jars:
            jar_name = os.path.basename(forge_jars[0])
            # Extract version from forge-1.20.1-47.2.0.jar
            match = re.search(r'forge-[\d.]+-(\d+\.\d+\.\d+)', jar_name)
            if match:
                return f"Forge {match.group(1)}"
            return "Forge"

        # Check for NeoForge
        neoforge_jars = glob.glob(os.path.join(folder, "neoforge-*.jar"))
        if neoforge_jars:
            jar_name = os.path.basename(neoforge_jars[0])
            match = re.search(r'neoforge-([\d.]+)', jar_name)
            if match:
                return f"NeoForge {match.group(1)}"
            return "NeoForge"

        # Check for Fabric - multiple detection methods
        fabric_launch_jar = os.path.join(folder, "fabric-server-launch.jar")
        fabric_jars = glob.glob(os.path.join(folder, "fabric-server-*.jar"))

        if os.path.exists(fabric_launch_jar) or fabric_jars:
            # Try to get version from libraries folder
            fabric_loader_libs = os.path.join(folder, "libraries", "net", "fabricmc", "fabric-loader")
            if os.path.exists(fabric_loader_libs):
                try:
                    versions = os.listdir(fabric_loader_libs)
                    if versions:
                        return f"Fabric Loader {versions[0]}"
                except:
                    pass

            # Try to get version from server log
            logs_path = os.path.join(folder, "logs", "latest.log")
            if os.path.exists(logs_path):
                try:
                    with open(logs_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f):
                            if i > 50:
                                break
                            # Look for "Fabric Loader 0.16.14"
                            if 'fabric loader' in line.lower():
                                match = re.search(r'fabric\s+loader\s+([\d.]+)', line, re.IGNORECASE)
                                if match:
                                    return f"Fabric Loader {match.group(1)}"
                except:
                    pass

            # Fallback: try old naming pattern
            if fabric_jars:
                jar_name = os.path.basename(fabric_jars[0])
                match = re.search(r'fabric-server-mc\.[\d.]+-(\d+\.\d+\.\d+)', jar_name)
                if match:
                    return f"Fabric Loader {match.group(1)}"

            return "Fabric"

        # Check for Quilt
        quilt_jars = glob.glob(os.path.join(folder, "quilt-server-*.jar"))
        if quilt_jars:
            jar_name = os.path.basename(quilt_jars[0])
            match = re.search(r'quilt-server-[\d.]+-([\d.]+)', jar_name)
            if match:
                return f"Quilt {match.group(1)}"
            return "Quilt"

        # Check libraries folder structure (modern Forge/NeoForge)
        forge_libs = os.path.join(folder, "libraries", "net", "minecraftforge", "forge")
        if os.path.exists(forge_libs):
            try:
                versions = os.listdir(forge_libs)
                if versions:
                    # Get first version folder (e.g., "1.20.1-47.2.0")
                    version_folder = versions[0]
                    # Extract just the forge version part
                    if '-' in version_folder:
                        forge_ver = version_folder.split('-')[-1]
                        return f"Forge {forge_ver}"
                    return f"Forge {version_folder}"
            except Exception:
                pass

        neoforge_libs = os.path.join(folder, "libraries", "net", "neoforged", "neoforge")
        if os.path.exists(neoforge_libs):
            try:
                versions = os.listdir(neoforge_libs)
                if versions:
                    return f"NeoForge {versions[0]}"
            except Exception:
                pass

        # Check for run scripts that might indicate loader (fallback)
        if os.path.exists(os.path.join(folder, "run.bat")) or os.path.exists(os.path.join(folder, "run.sh")):
            # Try to detect from run script content
            for script in ["run.bat", "run.sh"]:
                script_path = os.path.join(folder, script)
                if os.path.exists(script_path):
                    try:
                        with open(script_path, 'r') as f:
                            content = f.read()
                            # Look for forge version in script
                            match = re.search(r'forge[/-]([\d.]+)-([\d.]+)', content, re.IGNORECASE)
                            if match:
                                return f"Forge {match.group(2)}"
                            match = re.search(r'neoforge[/-]([\d.]+)', content, re.IGNORECASE)
                            if match:
                                return f"NeoForge {match.group(1)}"
                            # Generic detection
                            content_lower = content.lower()
                            if 'neoforge' in content_lower:
                                return "NeoForge"
                            elif 'forge' in content_lower:
                                return "Forge"
                            elif 'fabric' in content_lower:
                                return "Fabric"
                            elif 'quilt' in content_lower:
                                return "Quilt"
                    except Exception:
                        pass

        return ""

    def _start_mp(self):
        """Start modded server"""
        if not self.modpack_server_manager:
            return

        # Get Minecraft version (from our detection)
        mc_version = None
        if self.modpack_server_path:
            mc_version = self._detect_modpack_mc_version(self.modpack_server_path)

        if not mc_version:
            mc_version = "1.20"  # Default assumption for unknown versions
            self._log(self.modpack_run_console, "\nCould not detect MC version, assuming Java 17+ required\n", "warning")

        # Check Java compatibility
        required_java = self.java_manager.get_required_java_version(mc_version)
        min_java, max_java = self.java_manager.get_java_version_range(mc_version)
        java_info = self.java_manager.detect_java_version()

        needs_java = False
        java_too_new = False
        pycraft_java = None

        # Check if we have a PyCraft-installed Java
        install_dir = self.java_manager.java_installs_dir / f"java-{required_java}"
        if install_dir.exists():
            java_exe = self.java_manager._find_java_executable(install_dir)
            if java_exe:
                pycraft_java = str(java_exe)

        if not pycraft_java:
            if not java_info:
                needs_java = True
            else:
                _, installed_major = java_info
                if installed_major < min_java:
                    needs_java = True
                elif max_java is not None and installed_major > max_java:
                    needs_java = True
                    java_too_new = True

        if needs_java:
            # Show dialog with options
            msg = QMessageBox(self)
            msg.setWindowTitle("Java Required")
            msg.setIcon(QMessageBox.Icon.Warning)

            if max_java:
                msg.setText(f"Minecraft {mc_version} requires Java {min_java}-{max_java}")
            else:
                msg.setText(f"Minecraft {mc_version} requires Java {required_java}+")

            if java_info:
                _, installed_major = java_info
                if java_too_new:
                    msg.setInformativeText(
                        f"You have Java {installed_major} installed, but it's too new.\n"
                        f"Forge/modded servers for MC < 1.17 require Java 8-{max_java}.\n"
                        f"Java 17+ breaks due to module system changes.\n\n"
                        f"What would you like to do?"
                    )
                else:
                    msg.setInformativeText(
                        f"You have Java {installed_major} installed, but Java {required_java} or higher is needed.\n\n"
                        f"What would you like to do?"
                    )
            else:
                msg.setInformativeText(
                    f"Java is not installed on your system.\n\n"
                    f"What would you like to do?"
                )

            install_btn = msg.addButton("Install Automatically", QMessageBox.ButtonRole.AcceptRole)
            java_btn = msg.addButton("Java Management", QMessageBox.ButtonRole.ActionRole)
            cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

            msg.exec()

            clicked = msg.clickedButton()
            if clicked == java_btn:
                self._go_to("java_management")
                return
            elif clicked == cancel_btn or clicked is None:
                return
            elif clicked == install_btn:
                if not self._show_java_install_modal(required_java):
                    QMessageBox.critical(self, "Error", f"Failed to install Java {required_java}. Cannot start server.")
                    return
                # Update java reference after successful install
                install_dir = self.java_manager.java_installs_dir / f"java-{required_java}"
                if install_dir.exists():
                    java_exe = self.java_manager._find_java_executable(install_dir)
                    if java_exe:
                        pycraft_java = str(java_exe)

        # Update server manager with correct Java executable
        if pycraft_java:
            self.modpack_server_manager.java_executable = pycraft_java
            self._log(self.modpack_run_console, f"\nUsing Java: {pycraft_java}\n", "info")

        # Check and accept EULA if needed
        eula_path = os.path.join(self.modpack_server_path, "eula.txt")
        if os.path.exists(eula_path):
            try:
                with open(eula_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if 'eula=false' in content:
                    self._log(self.modpack_run_console, "Accepting EULA automatically...\n", "info")
                    self.modpack_server_manager.accept_eula()
            except Exception:
                pass

        # Configure online-mode=false automatically for LAN/Hamachi play
        self.modpack_server_manager.set_online_mode(False)

        # Detect server type (forge/fabric) for proper startup
        server_type = self.modpack_server_manager.detect_server_type()
        if server_type == "unknown":
            self._log(self.modpack_run_console, "Could not detect server type (Forge/Fabric).", "error")
            return

        java_exe = self.modpack_server_manager.java_executable

        self._log(self.modpack_run_console, "\n=== STARTING SERVER ===\n", "info")

        # Track if server started successfully
        self._server_started_successfully = False

        def on_stopped():
            """Called when server process ends (crash or normal stop)"""
            # Emit signal to update UI from main thread
            self.modpack_server_stopped_signal.emit(self._server_started_successfully)

        def log_callback(line: str):
            """Forward server output to UI"""
            # Check for successful start
            if "Done" in line and "!" in line:
                self._server_started_successfully = True

            # Forward to UI
            self.log_signal.emit(line, "normal", "m_run")

        # Disable start, enable stop
        self.mp_start.setEnabled(False)
        self.mp_config.setEnabled(False)
        self.mp_stop.setEnabled(True)

        def start():
            # Use start_modded_server which handles the server type properly
            if server_type in ("forge", "fabric", "neoforge", "quilt"):
                success = self.modpack_server_manager.start_modded_server(
                    server_type=server_type,
                    ram_mb=self.modpack_ram,
                    java_executable=java_exe,
                    log_callback=log_callback,
                    detached=True,
                    on_stopped=on_stopped
                )
            else:
                # Fallback to generic start_server for unknown types
                success = self.modpack_server_manager.start_server(
                    ram_mb=self.modpack_ram,
                    log_callback=log_callback,
                    detached=True,
                    on_stopped=on_stopped
                )

            # Emit signal to update UI from main thread
            self.modpack_server_started_signal.emit(success)

        threading.Thread(target=start, daemon=True).start()

    def _on_modpack_server_started(self, success: bool):
        """Handle modpack server started (called from main thread via signal)"""
        if success:
            self.mp_cmd_btn.setEnabled(True)
        else:
            # Re-enable start button if failed
            self._on_server_stopped_normal()

    def _show_server_crash_dialog(self, server_path: str):
        """Displays a simple modal dialog when server crashes."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Server Crashed")
        dialog.setFixedSize(420, 220)
        dialog.setStyleSheet(f"background-color: {self.colors['bg_card']};")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        # Icon and title row
        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        try:
            icon_label = QLabel()
            icon = qta.icon("fa5s.exclamation-triangle", color=self.colors['red'])
            icon_label.setPixmap(icon.pixmap(32, 32))
            title_row.addWidget(icon_label)
        except Exception:
            pass

        title = QLabel("Server Crashed")
        title.setStyleSheet(f"color: {self.colors['red']}; font-size: 18px; font-weight: bold;")
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)

        # Message
        msg = QLabel("The server has stopped unexpectedly.\nCheck the logs or crash reports for more details.")
        msg.setStyleSheet(f"color: {self.colors['text']}; font-size: 13px;")
        msg.setWordWrap(True)
        layout.addWidget(msg)

        layout.addStretch()

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        # Open Logs button
        logs_folder = os.path.join(server_path, "logs") if server_path else None
        if logs_folder and os.path.exists(logs_folder):
            logs_btn = self._styled_button("Open Logs", self.colors['bg_input'], self.colors['text'], 120)

            def open_logs():
                try:
                    if sys.platform == 'win32':
                        os.startfile(logs_folder)
                    elif sys.platform == 'darwin':
                        subprocess.run(['open', logs_folder])
                    else:
                        subprocess.run(['xdg-open', logs_folder])
                except Exception:
                    pass

            logs_btn.clicked.connect(open_logs)
            btn_row.addWidget(logs_btn)

        # Open Crash Reports button
        crash_folder = os.path.join(server_path, "crash-reports") if server_path else None
        if crash_folder and os.path.exists(crash_folder):
            crash_btn = self._styled_button("Crash Reports", self.colors['bg_input'], self.colors['text'], 120)

            def open_crash():
                try:
                    if sys.platform == 'win32':
                        os.startfile(crash_folder)
                    elif sys.platform == 'darwin':
                        subprocess.run(['open', crash_folder])
                    else:
                        subprocess.run(['xdg-open', crash_folder])
                except Exception:
                    pass

            crash_btn.clicked.connect(open_crash)
            btn_row.addWidget(crash_btn)

        btn_row.addStretch()

        # OK button
        ok_btn = self._styled_button("OK", self.colors['accent'], "#000000", 80)
        ok_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

        dialog.exec()

    def _on_server_stopped_normal(self):
        """Reset UI state when server stops normally"""
        self.mp_start.setEnabled(True)
        self.mp_config.setEnabled(True)
        self.mp_stop.setEnabled(False)
        self.mp_cmd_btn.setEnabled(False)

    def _on_modpack_server_stopped(self, started_successfully: bool):
        """Handle modpack server stopped (called from main thread via signal)"""
        # Re-enable UI elements
        self.mp_start.setEnabled(True)

        # Enable config only if server.properties exists (may have been generated on first run)
        if self.modpack_server_path:
            has_properties = os.path.exists(os.path.join(self.modpack_server_path, "server.properties"))
            self.mp_config.setEnabled(has_properties)
        else:
            self.mp_config.setEnabled(False)

        self.mp_stop.setEnabled(False)
        self.mp_cmd_btn.setEnabled(False)

        if started_successfully:
            self.log_signal.emit("\n[Server stopped - Ready to restart]\n", "info", "m_run")
        else:
            # Server crashed before "Done"
            self.log_signal.emit("\n[Server crashed - Ready to restart]\n", "error", "m_run")
            # Show crash dialog after a brief delay to ensure UI is updated
            QTimer.singleShot(100, lambda: self.server_crashed_signal.emit(self.modpack_server_path))

    def _stop_mp(self):
        if not self.modpack_server_manager:
            return

        # Check if server is actually running
        if not self.modpack_server_manager.is_server_running():
            self._log(self.modpack_run_console, "\nServer is not running\n", "warning")
            return

        # Disable all buttons immediately to prevent double-clicks
        self.mp_stop.setEnabled(False)
        self.mp_start.setEnabled(False)
        self.mp_config.setEnabled(False)
        self.mp_cmd_btn.setEnabled(False)
        self._log(self.modpack_run_console, "\nStopping server...\n", "warning")

        def stop():
            try:
                self.modpack_server_manager.stop_server()

                # stop_server() is blocking, so when it returns the server is stopped
                # Re-enable buttons on main thread
                def enable_buttons():
                    self._log(self.modpack_run_console, "Server stopped - Ready to restart\n", "success")
                    self.mp_start.setEnabled(True)
                    self.mp_config.setEnabled(True)
                    self.mp_stop.setEnabled(False)
                    self.mp_cmd_btn.setEnabled(False)

                QTimer.singleShot(0, enable_buttons)
            except Exception as e:
                # If stop_server() fails, still re-enable buttons
                def enable_buttons_on_error():
                    self._log(self.modpack_run_console, f"Error stopping server: {e}\n", "error")
                    self.mp_start.setEnabled(True)
                    self.mp_config.setEnabled(True)
                    self.mp_stop.setEnabled(False)
                    self.mp_cmd_btn.setEnabled(False)

                QTimer.singleShot(0, enable_buttons_on_error)

        threading.Thread(target=stop, daemon=True).start()

    def _send_mp_cmd(self):
        cmd = self.mp_run_cmd.text().strip()
        if cmd and self.modpack_server_manager:
            if not cmd.startswith("/"):
                self._log(self.modpack_run_console, "Commands must start with /\n", "warning")
                return
            # Remove "/" prefix for server console (server doesn't use /)
            server_cmd = cmd[1:]
            self._log(self.modpack_run_console, f"> {cmd}\n", "info")
            self.modpack_server_manager.send_command(server_cmd)
            self.mp_run_cmd.clear()

            # Blink button for visual feedback
            self._blink_send_button(self.mp_cmd_btn, self.modpack_server_manager)

    def _config_mp(self):
        if self.modpack_server_manager and self.modpack_server_manager.is_server_running():
            QMessageBox.warning(self, "Warning", "Stop server first")
            return

        self._open_config_dialog("modpack")

    # Settings
    def _check_java(self):
        while self.java_info_layout.count():
            child = self.java_info_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        installations = self.java_manager.get_java_installations()

        if not installations:
            label = QLabel("No Java found")
            label.setStyleSheet(f"color: {self.colors['yellow']}; font-size: 13px; border: none;")
            self.java_info_layout.addWidget(label)

            # Spacer
            self.java_info_layout.addSpacing(10)

            # Buttons row
            btn_widget = QWidget()
            btn_widget.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(10)

            install = self._styled_button("Install Java", self.colors['accent'], "#000000", 140)
            install.clicked.connect(self._install_java)
            btn_layout.addWidget(install)

            check = self._styled_button("Check Java", self.colors['bg_input'], self.colors['text'], 140)
            check.clicked.connect(self._check_java)
            btn_layout.addWidget(check)

            btn_layout.addStretch()
            self.java_info_layout.addWidget(btn_widget)
        else:
            for ver, path, _ in installations:
                frame = QFrame()
                frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {self.colors['bg_input']};
                        border-radius: 10px;
                        padding: 10px;
                    }}
                """)
                frame_layout = QHBoxLayout(frame)
                frame_layout.setContentsMargins(12, 10, 12, 10)

                # Info column
                info_widget = QWidget()
                info_widget.setStyleSheet("background: transparent;")
                info_layout = QVBoxLayout(info_widget)
                info_layout.setContentsMargins(0, 0, 0, 0)
                info_layout.setSpacing(2)

                v = QLabel(f"Java {ver}")
                v.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600;")
                info_layout.addWidget(v)

                p = QLabel(f"Path: {path}")
                p.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
                info_layout.addWidget(p)

                frame_layout.addWidget(info_widget, 1)

                # Delete button
                delete_btn = QPushButton()
                delete_btn.setFixedSize(36, 36)
                delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                delete_btn.setIcon(qta.icon("fa5s.trash-alt", color=self.colors['red']))
                delete_btn.setIconSize(QSize(16, 16))
                delete_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: 1px solid {self.colors['border']};
                        border-radius: 8px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(248, 113, 113, 0.2);
                        border: 1px solid {self.colors['red']};
                    }}
                """)
                delete_btn.clicked.connect(lambda _, version=ver: self._delete_java(version))
                frame_layout.addWidget(delete_btn)

                self.java_info_layout.addWidget(frame)

            # Buttons row
            self.java_info_layout.addSpacing(8)
            btn_widget = QWidget()
            btn_widget.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(10)

            install_another = self._styled_button("+ Install Java", self.colors['bg_input'], self.colors['text'], 140)
            install_another.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            install_another.clicked.connect(self._install_java)
            btn_layout.addWidget(install_another)

            check = self._styled_button("Check Java", self.colors['bg_input'], self.colors['text'], 140)
            check.clicked.connect(self._check_java)
            btn_layout.addWidget(check)

            btn_layout.addStretch()
            self.java_info_layout.addWidget(btn_widget)

    def _install_java(self):
        ver, ok = QInputDialog.getText(self, "Install Java", "Version (8, 17, or 21):")
        if ok and ver:
            try:
                v = int(ver)
                if v not in [8, 17, 21]:
                    QMessageBox.critical(self, "Error", "Use 8, 17, or 21")
                    return

                # Use the modal installer
                self._show_java_install_modal(v)

            except ValueError:
                QMessageBox.critical(self, "Error", "Invalid version")

    def _delete_java(self, version: int):
        reply = QMessageBox.question(
            self,
            "Delete Java",
            f"Are you sure you want to delete Java {version}?\n\nThis will also remove it from your system PATH.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.java_manager.delete_java_installation(version)

            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Java {version} deleted successfully."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Admin Permissions Required",
                    f"Could not delete Java {version}.\n\n"
                    f"You must accept the administrator permissions\n"
                    f"when Windows prompts you.\n\n"
                    f"Please try again and click 'Yes' on the\n"
                    f"Windows permission dialog."
                )
            self._check_java()

    def _animate_update_dots(self):
        """Animate the dots in 'Checking for updates' label"""
        self.update_dot_count = (self.update_dot_count % 3) + 1
        dots = "." * self.update_dot_count
        self.update_status_label.setText(f"Checking for updates{dots}")

    def _on_update_check_complete(self, update_info):
        """Handle update check completion (called via signal from thread)"""
        # Stop animation
        self.update_check_timer.stop()
        self.check_update_btn.setEnabled(True)

        if update_info:
            # Update available
            new_version = update_info['version']
            self.update_status_label.setText(f"Update available: v{new_version}")
            self.update_status_label.setStyleSheet(f"color: {self.colors['yellow']}; font-size: 12px; font-weight: 600; background: transparent; border: none;")

            # Show update dialog with download option
            reply = QMessageBox.question(
                self,
                "Update Available",
                f"A new version is available!\n\n"
                f"Current version: {__version__}\n"
                f"New version: {new_version}\n\n"
                f"Would you like to download and install the update automatically?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._download_and_install_update(update_info)
        else:
            # No update available
            self.update_status_label.setText("Already up to date")
            self.update_status_label.setStyleSheet(f"color: {self.colors['accent']}; font-size: 12px; font-weight: 600; background: transparent; border: none;")

    def _check_for_updates(self):
        """Check for application updates from GitHub"""
        # Disable button during check
        self.check_update_btn.setEnabled(False)

        # Start animated dots
        self.update_dot_count = 0
        self.update_status_label.setText("Checking for updates.")
        self.update_status_label.setStyleSheet(f"color: {self.colors['yellow']}; font-size: 12px; font-weight: 600; background: transparent; border: none;")
        self.update_check_timer.start(400)  # Update dots every 400ms

        def check_thread():
            try:
                update_info = self.update_checker.check_for_updates()
            except Exception:
                update_info = None
            # Emit signal to main thread
            self.update_check_complete_signal.emit(update_info)

        threading.Thread(target=check_thread, daemon=True).start()

    def _on_download_progress(self, progress: int, downloaded_mb: float, total_mb: float):
        """Handle download progress update (called via signal from thread)"""
        self.download_progress_bar.setValue(progress)
        self.download_progress_label.setText(
            f"Downloading: {downloaded_mb:.1f} MB / {total_mb:.1f} MB ({progress}%)"
        )

    def _on_download_complete(self, installer_path: str):
        """Handle download completion (called via signal from thread)"""
        if installer_path:
            # Download successful
            self.downloaded_installer_path = installer_path
            self.download_progress_widget.hide()
            self.install_update_btn.show()
            self.update_status_label.setText("Download complete! Ready to install.")
            self.update_status_label.setStyleSheet(f"color: {self.colors['accent']}; font-size: 12px; font-weight: 600; background: transparent; border: none;")

            # Ask if user wants to install now
            reply = QMessageBox.question(
                self,
                "Download Complete",
                "Update downloaded successfully!\n\n"
                "Would you like to install it now?\n\n"
                "Note: PyCraft will close and restart after installation.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._install_downloaded_update()
        else:
            # Download failed
            self.download_progress_widget.hide()
            self.check_update_btn.show()
            self.update_status_label.setText("Download failed. Please try again.")
            self.update_status_label.setStyleSheet(f"color: {self.colors['red']}; font-size: 12px; font-weight: 600; background: transparent; border: none;")

    def _download_and_install_update(self, update_info: dict):
        """Download and prepare update for installation"""
        # Hide check button, show progress
        self.check_update_btn.hide()
        self.download_progress_widget.show()
        self.download_progress_bar.setValue(0)
        self.download_progress_label.setText("Downloading update...")
        self.update_status_label.setText("Downloading...")

        def progress_callback(downloaded: int, total: int):
            """Update progress bar from download thread"""
            if total > 0:
                progress = int((downloaded / total) * 100)
                downloaded_mb = downloaded / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                self.update_download_progress_signal.emit(progress, downloaded_mb, total_mb)

        def download_thread():
            """Download installer in background thread"""
            try:
                installer_path = self.update_checker.download_update(
                    update_info['download_url'],
                    progress_callback
                )
                self.update_download_complete_signal.emit(installer_path or "")
            except Exception:
                self.update_download_complete_signal.emit("")

        threading.Thread(target=download_thread, daemon=True).start()

    def _install_downloaded_update(self):
        """Install the downloaded update"""
        if not self.downloaded_installer_path:
            return

        # Confirm installation
        reply = QMessageBox.question(
            self,
            "Install Update",
            "PyCraft will now close and install the update.\n\n"
            "The application will restart automatically after installation.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Install update (this will close the application)
            self.update_checker.install_update(self.downloaded_installer_path, silent=True)

    def _refresh_modpack_list(self):
        """Refresh the list of installed client modpacks in Settings"""
        # Clear existing items
        while self.modpack_list_layout.count():
            child = self.modpack_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        modpacks = self.modpack_manager.get_installed_client_modpacks()

        if not modpacks:
            label = QLabel("No modpacks installed")
            label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 13px; border: none;")
            self.modpack_list_layout.addWidget(label)

            tip = QLabel("Install modpacks from Modded Server > Install Modpack (Client)")
            tip.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px; border: none;")
            self.modpack_list_layout.addWidget(tip)
        else:
            for mp in modpacks:
                frame = QFrame()
                frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {self.colors['bg_input']};
                        border-radius: 10px;
                        padding: 10px;
                    }}
                """)
                frame_layout = QHBoxLayout(frame)
                frame_layout.setContentsMargins(12, 10, 12, 10)

                # Source icon (Modrinth/CurseForge)
                source = mp.get("source", "modrinth")
                source_icon = QLabel()
                if source == "curseforge":
                    source_icon.setPixmap(qta.icon("fa5s.fire", color="#f16436").pixmap(20, 20))
                    source_icon.setToolTip("CurseForge")
                else:
                    source_icon.setPixmap(qta.icon("fa5s.leaf", color="#1bd96a").pixmap(20, 20))
                    source_icon.setToolTip("Modrinth")
                source_icon.setFixedSize(24, 24)
                source_icon.setStyleSheet("background: transparent; border: none;")
                frame_layout.addWidget(source_icon)

                # Info column
                info_widget = QWidget()
                info_widget.setStyleSheet("background: transparent;")
                info_layout = QVBoxLayout(info_widget)
                info_layout.setContentsMargins(8, 0, 0, 0)
                info_layout.setSpacing(2)

                name = QLabel(mp.get("name", mp.get("folder_name", "Unknown")))
                name.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600;")
                info_layout.addWidget(name)

                # Version info
                mc_ver = mp.get("minecraft_version", "Unknown")
                loader = mp.get("loader", "Unknown")
                loader_ver = mp.get("loader_version", "")

                # Loader color
                loader_color = self.colors['text_muted']
                if loader.lower() == "forge":
                    loader_color = "#FF6B35"
                elif loader.lower() == "neoforge":
                    loader_color = "#D64541"
                elif loader.lower() == "fabric":
                    loader_color = "#C6BCA7"
                elif loader.lower() == "quilt":
                    loader_color = "#8B5CF6"

                loader_text = f"{loader.capitalize()} {loader_ver}" if loader_ver else loader.capitalize()
                meta = QLabel(f"MC {mc_ver} | {loader_text}")
                meta.setStyleSheet(f"color: {loader_color}; font-size: 12px;")
                info_layout.addWidget(meta)

                # Path info
                path = QLabel(mp.get("path", ""))
                path.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 10px;")
                info_layout.addWidget(path)

                frame_layout.addWidget(info_widget, 1)

                # Link button (open in browser)
                link_url = mp.get("curseforge_url") or mp.get("modrinth_url")
                if link_url:
                    link_btn = QPushButton()
                    link_btn.setFixedSize(36, 36)
                    link_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    link_btn.setIcon(qta.icon("fa5s.external-link-alt", color=self.colors['text']))
                    link_btn.setIconSize(QSize(16, 16))
                    link_btn.setToolTip("Open in browser")
                    link_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            border: 1px solid {self.colors['border']};
                            border-radius: 8px;
                        }}
                        QPushButton:hover {{
                            background-color: {self.colors['bg_card']};
                            border: 1px solid {self.colors['text_muted']};
                        }}
                    """)
                    link_btn.clicked.connect(lambda _, url=link_url: QDesktopServices.openUrl(QUrl(url)))
                    frame_layout.addWidget(link_btn)

                # Open folder button
                open_btn = QPushButton()
                open_btn.setFixedSize(36, 36)
                open_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                open_btn.setIcon(qta.icon("fa5s.folder-open", color=self.colors['text']))
                open_btn.setIconSize(QSize(16, 16))
                open_btn.setToolTip("Open folder")
                open_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: 1px solid {self.colors['border']};
                        border-radius: 8px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.colors['bg_card']};
                        border: 1px solid {self.colors['text_muted']};
                    }}
                """)
                open_btn.clicked.connect(lambda _, p=mp.get("path", ""): self._open_folder(p))
                frame_layout.addWidget(open_btn)

                # Delete button
                delete_btn = QPushButton()
                delete_btn.setFixedSize(36, 36)
                delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                delete_btn.setIcon(qta.icon("fa5s.trash-alt", color=self.colors['red']))
                delete_btn.setIconSize(QSize(16, 16))
                delete_btn.setToolTip("Uninstall modpack")
                delete_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: 1px solid {self.colors['border']};
                        border-radius: 8px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(248, 113, 113, 0.2);
                        border: 1px solid {self.colors['red']};
                    }}
                """)
                delete_btn.clicked.connect(lambda _, folder=mp.get("folder_name", ""), name=mp.get("name", ""): self._uninstall_modpack(folder, name))
                frame_layout.addWidget(delete_btn)

                self.modpack_list_layout.addWidget(frame)

        # Buttons row at bottom (like Java Management)
        self.modpack_list_layout.addSpacing(8)
        btn_widget = QWidget()
        btn_widget.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        refresh_btn = self._styled_button("Refresh", self.colors['bg_input'], self.colors['text'], 140)
        refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        refresh_btn.clicked.connect(self._refresh_modpack_list)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()
        self.modpack_list_layout.addWidget(btn_widget)

    def _uninstall_modpack(self, folder_name: str, display_name: str):
        """Uninstall a client modpack"""
        reply = QMessageBox.question(
            self,
            "Uninstall Modpack",
            f"Are you sure you want to uninstall '{display_name}'?\n\nThis will delete all modpack files including mods and configs.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.modpack_manager.uninstall_client_modpack(folder_name)

            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"'{display_name}' has been uninstalled."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Could not uninstall '{display_name}'.\n\nThe folder may be in use or you may not have permissions."
                )
            self._refresh_modpack_list()

    def _open_folder(self, path: str):
        """Open a folder in file explorer"""
        if path and os.path.exists(path):
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])

    def _show_java_install_modal(self, java_version: int, on_complete: Optional[callable] = None):
        """Shows a modal dialog with progress bar for Java installation"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Installing Java {java_version}")
        dialog.setFixedSize(420, 400)
        dialog.setModal(True)
        dialog.setStyleSheet(f"background-color: {self.colors['bg_card']};")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel(f"Installing Java {java_version}")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 16px; font-weight: 600;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Status label
        status_label = QLabel("Preparing download...")
        status_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px;")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_label)

        # Progress bar
        progress = QProgressBar()
        progress.setMinimum(0)
        progress.setMaximum(0)  # Indeterminate initially
        progress.setFixedHeight(8)
        progress.setTextVisible(False)
        progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.colors['bg_input']};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {self.colors['accent']};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(progress)

        # Mini console (compact)
        mini_console = QTextEdit()
        mini_console.setReadOnly(True)
        mini_console.setFixedHeight(180)
        mini_console.setStyleSheet(f"""
            QTextEdit {{
                background-color: #0a0a0a;
                color: {self.colors['text_muted']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }}
        """)
        layout.addWidget(mini_console)

        layout.addStretch()

        # Accept button (hidden initially)
        accept_btn = QPushButton("Accept")
        accept_btn.setFixedSize(120, 36)
        accept_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        accept_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['accent']};
                color: #000000;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {self.colors['accent_hover']};
            }}
        """)
        accept_btn.clicked.connect(dialog.accept)
        accept_btn.hide()
        layout.addWidget(accept_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # State tracking
        install_result = {"success": False, "java_path": None}

        # Connect signals to UI updates (thread-safe via Qt signal mechanism)
        def on_status(text):
            status_label.setText(text)

        def on_progress(value, maximum):
            if maximum >= 0:
                progress.setMaximum(maximum)
            if value >= 0:
                progress.setValue(value)

        def on_console(text, color):
            cursor = mini_console.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            cursor.insertText(text + "\n", fmt)
            mini_console.setTextCursor(cursor)
            mini_console.ensureCursorVisible()

        def on_complete_signal(success):
            progress.hide()
            accept_btn.show()
            if success:
                title.setText(f"Java {java_version} Installed")
                title.setStyleSheet(f"color: {self.colors['accent']}; font-size: 16px; font-weight: 600;")
                status_label.setText("Java is ready to use")
            else:
                title.setText("Configuration Required")
                title.setStyleSheet(f"color: {self.colors['yellow']}; font-size: 16px; font-weight: 600;")
                status_label.setText("Accept admin permissions to complete setup")

        # Connect signals
        self.java_status_signal.connect(on_status)
        self.java_progress_signal.connect(on_progress)
        self.java_console_signal.connect(on_console)
        self.java_complete_signal.connect(on_complete_signal)

        def log_to_modal(msg: str):
            """Filter and display relevant messages in the modal (thread-safe via signals)"""
            msg_lower = msg.lower()

            # Update status based on message content
            if "descargando" in msg_lower and ("java" in msg_lower or "archivo" in msg_lower):
                self.java_status_signal.emit("Downloading Java...")
                self.java_progress_signal.emit(-1, 100)
            elif "progreso:" in msg_lower:
                try:
                    pct = int(msg.replace("%", "").split()[-1])
                    self.java_progress_signal.emit(pct, -1)
                except Exception:
                    pass
                return
            elif "extrayendo" in msg_lower or "extracción" in msg_lower:
                self.java_status_signal.emit("Extracting files...")
                self.java_progress_signal.emit(-1, 0)
            elif "configurando" in msg_lower and ("path" in msg_lower or "java" in msg_lower):
                self.java_status_signal.emit("Configuring system...")
            elif "instalado correctamente" in msg_lower:
                self.java_status_signal.emit("Finishing...")
                self.java_progress_signal.emit(100, 100)
                install_result["success"] = True

            # Only show key messages in console
            if any(x in msg for x in ["✓", "✗", "⚠"]) or "error" in msg_lower:
                clean_msg = msg.strip()
                if clean_msg:
                    if "✓" in msg:
                        color = self.colors['accent']
                    elif "✗" in msg or "error" in msg_lower:
                        color = self.colors['red']
                    elif "⚠" in msg:
                        color = self.colors['yellow']
                    else:
                        color = self.colors['text_muted']
                    self.java_console_signal.emit(clean_msg, color)

        def run_install():
            try:
                result = self.java_manager.download_java(java_version, log_to_modal)
                if result:
                    install_result["java_path"] = result
                    install_result["success"] = True
            except Exception as e:
                self.java_console_signal.emit(f"✗ Error: {str(e)}", self.colors['red'])
            finally:
                self.java_complete_signal.emit(install_result["success"])

        # Start installation in background
        threading.Thread(target=run_install, daemon=True).start()

        # Show dialog (blocks until closed)
        dialog.exec()

        # Disconnect signals to avoid issues with multiple calls
        self.java_status_signal.disconnect(on_status)
        self.java_progress_signal.disconnect(on_progress)
        self.java_console_signal.disconnect(on_console)
        self.java_complete_signal.disconnect(on_complete_signal)

        # Refresh Java list if in settings
        self._check_java()

        # Call completion callback if provided
        if on_complete:
            on_complete(install_result["success"], install_result.get("java_path"))

        return install_result["success"]

    def closeEvent(self, event):
        """Handle application close - stop all running servers"""
        servers_stopped = []

        # Stop vanilla server if running
        if self.server_manager and self.server_manager.is_server_running():
            self.server_manager.stop_server()
            servers_stopped.append("vanilla")

        # Stop modpack server if running
        if hasattr(self, 'modpack_server_manager') and self.modpack_server_manager and self.modpack_server_manager.is_server_running():
            self.modpack_server_manager.stop_server()
            servers_stopped.append("modpack")

        if servers_stopped:
            print(f"Stopped servers on exit: {', '.join(servers_stopped)}")

        event.accept()

    def run(self):
        self.show()


def main():
    import os

    # Force software rendering to avoid Intel/AMD graphics bugs
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["QSG_RHI_BACKEND"] = "software"

    app = QApplication(sys.argv)

    # Use Fusion style with custom proxy to remove focus rectangles
    app.setStyle(NoFocusRectStyle("Fusion"))

    # Global stylesheet to remove borders from all QLabels
    app.setStyleSheet("""
        QLabel {
            border: none;
        }
    """)

    window = PyCraftGUI()
    window.run()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
