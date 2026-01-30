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

import qtawesome as qta

from ..core.api import MinecraftAPIHandler, APIConfig
from ..core.download import ServerDownloader
from ..managers.server import ServerManager
from ..managers.modpack import ModpackManager
from ..managers.java import JavaManager
from ..utils import system_utils
from ..utils.updater import UpdateChecker
from ..__version__ import __version__

# Import extracted widgets
from .widgets import (
    NonPropagatingScrollArea,
    NonPropagatingTextEdit,
    NoFocusRectStyle,
    SidebarButton,
    OptionCard,
    FooterLink,
    ToastNotification,
)

# Import services (for future use when pages are extracted)
from .services import FolderValidator, VersionDetector

# Import dialogs
from .dialogs import ServerCrashDialog, ServerConfigDialog

# Import controllers
from .controllers import (
    VanillaInstallController,
    VanillaRunController,
    ModpackInstallController,
    ModpackRunController,
    ClientInstallController,
)

# Import pages (for future use - can be gradually adopted)
from .pages import BasePage, HomePage, VanillaPage, ModdedPage, InfoPage


class PyCraftGUI(QMainWindow):
    """Main PyCraft Application Window"""

    # Core signals
    log_signal = Signal(str, str, str)
    progress_signal = Signal(int)
    status_signal = Signal(str, str)

    # Java modal signals (thread-safe)
    java_status_signal = Signal(str)
    java_progress_signal = Signal(int, int)  # value, maximum
    java_console_signal = Signal(str, str)  # text, color
    java_complete_signal = Signal(bool)  # success

    # Server crash signal
    server_crashed_signal = Signal(str)  # server path for crash modal

    # Modal signals (thread-safe)
    vanilla_install_success_signal = Signal(str, str)  # version, folder
    server_modpack_install_success_signal = Signal(str, str, str)  # name, mc_version, loader

    # Update signals
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
        self.modpack_manager = ModpackManager()
        self.java_manager = JavaManager()
        self.api_config = APIConfig()
        self.update_checker = UpdateChecker(__version__)

        cf_key = self.api_config.get_curseforge_key()
        if cf_key:
            self.modpack_manager.set_curseforge_api_key(cf_key)

        # Provider selection state (kept for _select_mp_provider)
        self.mp_selected_provider = "modrinth"
        self.selected_modpack = None

        # RAM settings
        self.vanilla_ram = 2048
        self.modpack_ram = 4096

        self.sidebar_buttons = {}

        self._setup_window()
        self._build_ui()
        self._connect_signals()

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
        self.server_crashed_signal.connect(self._show_server_crash_dialog)
        # Modal signals - use lambdas with QTimer to avoid blocking
        self.vanilla_install_success_signal.connect(
            lambda v, f: QTimer.singleShot(100, lambda: self._show_vanilla_install_success(v, f))
        )
        self.server_modpack_install_success_signal.connect(
            lambda n, m, l: QTimer.singleShot(100, lambda: self._show_server_install_notice(n, m, l))
        )

    def _on_log(self, msg: str, level: str, target: str):
        """Handle log signal"""
        targets = {
            "v_create": getattr(self, "vanilla_create_console", None),
            "v_run": getattr(self, "vanilla_run_console", None),
            "m_install": getattr(self, "modpack_install_console", None),
            "m_run": getattr(self, "modpack_run_console", None),
        }
        if target in targets and targets[target]:
            self._log(targets[target], msg, level)

        # Detect when server is ready (shows "Done" message)
        if target in ("v_run", "m_run") and "Done" in msg and "For help, type" in msg:
            self._show_server_ready_notification(target)

    def _on_progress(self, value: int):
        """Handle progress signal"""
        if hasattr(self, "active_progress") and self.active_progress:
            self.active_progress.setValue(value)
        if hasattr(self, "active_progress_label") and self.active_progress_label:
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
        
        # Use extracted controllers for vanilla/modpack pages
        self.vanilla_install_ctrl = VanillaInstallController(
            colors=self.colors,
            api_handler=self.api_handler,
            downloader=self.downloader,
            java_manager=self.java_manager,
            navigate_callback=self._go_to,
            log_signal=self.log_signal,
            progress_signal=self.progress_signal,
            check_java_callback=self._check_and_get_java,
        )
        self.vanilla_install_ctrl.install_success.connect(self._show_vanilla_install_success, Qt.ConnectionType.QueuedConnection)
        self.page_stack.addWidget(self.vanilla_install_ctrl)        # 5
        
        self.vanilla_run_ctrl = VanillaRunController(
            colors=self.colors,
            java_manager=self.java_manager,
            navigate_callback=self._go_to,
            log_signal=self.log_signal,
            check_java_callback=self._check_and_get_java,
            open_config_callback=self._open_config_dialog,
            server_crashed_signal=self.server_crashed_signal,
        )
        self.vanilla_run_ctrl.server_started.connect(self.vanilla_run_ctrl.on_server_started, Qt.ConnectionType.QueuedConnection)
        self.vanilla_run_ctrl.server_stopped.connect(self.vanilla_run_ctrl.on_server_stopped, Qt.ConnectionType.QueuedConnection)
        self.vanilla_run_ctrl.server_ready.connect(lambda: self._show_server_ready_notification("v_run"))
        self.page_stack.addWidget(self.vanilla_run_ctrl)            # 6
        
        self.modpack_install_ctrl = ModpackInstallController(
            colors=self.colors,
            modpack_manager=self.modpack_manager,
            navigate_callback=self._go_to,
            log_signal=self.log_signal,
            check_java_callback=self._check_and_get_java,
            warn_dangerous_folder=self._warn_dangerous_folder,
            warn_existing_server=self._warn_existing_server,
        )
        self.modpack_install_ctrl.install_success.connect(self._show_server_install_notice, Qt.ConnectionType.QueuedConnection)
        self.page_stack.addWidget(self.modpack_install_ctrl)        # 7
        
        self.modpack_run_ctrl = ModpackRunController(
            colors=self.colors,
            java_manager=self.java_manager,
            navigate_callback=self._go_to,
            log_signal=self.log_signal,
            check_java_callback=self._check_and_get_java,
            open_config_callback=self._open_config_dialog,
            server_crashed_signal=self.server_crashed_signal,
        )
        self.modpack_run_ctrl.server_started.connect(self.modpack_run_ctrl.on_server_started, Qt.ConnectionType.QueuedConnection)
        self.modpack_run_ctrl.server_stopped.connect(self.modpack_run_ctrl.on_server_stopped, Qt.ConnectionType.QueuedConnection)
        self.modpack_run_ctrl.server_install_done.connect(self.modpack_run_ctrl.on_server_install_done, Qt.ConnectionType.QueuedConnection)
        self.modpack_run_ctrl.server_ready.connect(lambda: self._show_server_ready_notification("m_run"))
        self.page_stack.addWidget(self.modpack_run_ctrl)            # 8

        self.client_install_ctrl = ClientInstallController(
            colors=self.colors,
            modpack_manager=self.modpack_manager,
            navigate_callback=self._go_to,
            log_signal=self.log_signal,
        )
        self.page_stack.addWidget(self.client_install_ctrl)         # 9

        self.page_stack.addWidget(self._build_java_management())    # 10

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

        # Top row with welcome text and website icon
        top_row = QWidget()
        top_row.setStyleSheet("background: transparent;")
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(0)

        welcome = QLabel("Welcome to")
        welcome.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px; background: transparent;")
        top_row_layout.addWidget(welcome)

        top_row_layout.addStretch()

        # Website icon button
        website_btn = QPushButton()
        website_btn.setIcon(qta.icon("fa5s.globe", color=self.colors['text_secondary']))
        website_btn.setIconSize(QSize(24, 24))
        website_btn.setFixedSize(28, 28)
        website_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        website_btn.setToolTip("Visit PyCraft Website")
        website_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
            }}
            QPushButton:hover {{
                background-color: transparent;
            }}
        """)
        website_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://pycraft-web.vercel.app")))
        top_row_layout.addWidget(website_btn)

        card_layout.addWidget(top_row)

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

        subtitle = QLabel("Java versions installed by PyCraft for running Minecraft servers")
        subtitle.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px;")
        layout.addWidget(subtitle)

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
        self._log(self.modpack_install_console, "Loading popular modpacks...\n", "info")

        # Load popular modpacks automatically
        self._search_modpacks(page=1, popular=True)

    # ============================================================
    # UI Helper Methods
    # ============================================================

    def _clear_layout(self, layout):
        """Clear all widgets from a layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _section_frame(self, title: str) -> QFrame:
        """Create a styled section frame"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_card']};
                border: 1px solid {self.colors['border']};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        label = QLabel(title)
        label.setStyleSheet(f"color: {self.colors['text']}; font-size: 15px; font-weight: 600; border: none;")
        layout.addWidget(label)

        return frame

    def _styled_button(self, text: str, bg: str, fg: str = "#ffffff", width: int = 200) -> QPushButton:
        """Create a styled button"""
        btn = QPushButton(text)
        btn.setFixedSize(width, 42)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
            QPushButton:disabled {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text_muted']};
            }}
        """)
        return btn

    def _text_button(self, text: str) -> QPushButton:
        """Create a text-only button"""
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
                text-decoration: underline;
            }}
        """)
        return btn

    def _input(self, placeholder: str, width: int = 400) -> QLineEdit:
        """Create a styled input field"""
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedWidth(width)
        inp.setFixedHeight(42)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
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
        """Create a console output widget"""
        console = NonPropagatingTextEdit()
        console.setReadOnly(True)
        console.setFixedHeight(180)
        console.setStyleSheet(f"""
            QTextEdit {{
                background-color: #0d0d0d;
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 10px;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
            }}
        """)
        return console

    def _scroll_style(self) -> str:
        """Return scroll area stylesheet"""
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
        """

    def _progress_style(self) -> str:
        """Return progress bar stylesheet"""
        return f"""
            QProgressBar {{
                background-color: {self.colors['bg_input']};
                border: none;
                border-radius: 4px;
                height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {self.colors['accent']};
                border-radius: 4px;
            }}
        """

    def _log(self, console: QTextEdit, msg: str, level: str = "normal", max_lines: int = 500):
        """Log message to console with color coding"""
        colors = {
            "normal": self.colors['text'],
            "info": self.colors['blue'],
            "success": self.colors['accent'],
            "warning": self.colors['yellow'],
            "error": self.colors['red'],
        }
        color = colors.get(level, self.colors['text'])

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))

        cursor = console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(msg, fmt)
        console.setTextCursor(cursor)
        console.ensureCursorVisible()

        # Limit lines
        doc = console.document()
        if doc.blockCount() > max_lines:
            cursor = console.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, doc.blockCount() - max_lines)
            cursor.removeSelectedText()

    def _go_to(self, page: str):
        """Navigate to a page"""
        pages = {
            "home": 0, "vanilla": 1, "modded": 2, "info": 3, "settings": 4,
            "vanilla_create": 5, "vanilla_run": 6, "modpack_install": 7, "modpack_run": 8,
            "client_install": 9, "client_modpacks": 9,
            "java_management": 10
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
            "java_management": "java_management"
        }
        for k, btn in self.sidebar_buttons.items():
            btn.setChecked(k == sidebar_map.get(page, ""))

    # ============================================================
    # Folder Validation Helpers
    # ============================================================

    def _is_dangerous_folder(self, folder_path: str) -> tuple:
        """Check if a folder is a dangerous/important system location"""
        if not folder_path:
            return False, ""
        path = Path(folder_path).resolve()
        path_name = path.name.lower()

        if path.parent == path:
            return True, "You selected a drive root."

        dangerous_names = {
            "downloads": "Downloads folder", "descargas": "Downloads folder",
            "desktop": "Desktop", "escritorio": "Desktop",
            "documents": "Documents folder", "documentos": "Documents folder",
            "program files": "Program Files", "program files (x86)": "Program Files",
            "windows": "Windows system folder", "system32": "Windows system folder",
            "users": "Users folder", "appdata": "AppData folder",
        }
        if path_name in dangerous_names:
            return True, f"You selected your {dangerous_names[path_name]}."
        if path == Path.home():
            return True, "You selected your user folder directly."
        return False, ""

    def _is_existing_server(self, folder_path: str) -> bool:
        """Check if folder already contains a server"""
        import os
        server_files = ["server.jar", "server.properties", "eula.txt"]
        return any(os.path.exists(os.path.join(folder_path, f)) for f in server_files)

    def _warn_existing_server(self, folder_path: str) -> bool:
        """Warn if folder already contains server files"""
        if not self._is_existing_server(folder_path):
            return True
        msg = QMessageBox(self)
        msg.setWindowTitle("Server Already Exists")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("This folder already contains a Minecraft server.")
        msg.setInformativeText("Installing here will overwrite existing server files. Continue?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        return msg.exec() == QMessageBox.StandardButton.Yes

    def _warn_dangerous_folder(self, folder_path: str) -> bool:
        """Show warning for dangerous folder locations"""
        is_dangerous, warning = self._is_dangerous_folder(folder_path)
        if not is_dangerous:
            return True
        msg = QMessageBox(self)
        msg.setWindowTitle("Warning: Folder Location")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("Are you sure you want to use this folder?")
        msg.setInformativeText(f"{warning}\n\nIt's recommended to create a dedicated folder for your server.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        return msg.exec() == QMessageBox.StandardButton.Yes

    # ============================================================
    # Success Callbacks for Controllers
    # ============================================================

    def _show_vanilla_install_success(self, mc_version: str, folder: str):
        """Show success message after vanilla server creation"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Server Created")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"Minecraft {mc_version} server created successfully!")
        msg.setInformativeText(f"Location: {folder}\n\nYou can now run the server from the 'Run Existing Server' page.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def _show_server_install_notice(self, mp_name: str, mc_version: str, loader_type: str):
        """Show notification after server modpack installation"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Modpack Installed")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"{mp_name} installed successfully!")
        msg.setInformativeText(f"Minecraft {mc_version} | {loader_type}\n\nYou can now run the server from the 'Run Modpack Server' page.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def _format_downloads(self, count: int) -> str:
        """Format download count (e.g., 1.2M, 50K)"""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count / 1_000:.0f}K"
        return str(count)

    def _open_config_dialog(self, server_type: str):
        """Open server configuration dialog"""
        if server_type == "vanilla":
            manager = self.vanilla_run_ctrl.get_server_manager()
            current_ram = self.vanilla_ram
            mc_version = self.vanilla_run_ctrl.detected_mc_version or ""
            loader_info = "Vanilla"
        else:
            manager = self.modpack_run_ctrl.get_server_manager()
            current_ram = self.modpack_ram
            mc_version = self.modpack_run_ctrl.detected_mc_version or ""
            loader_info = self.modpack_run_ctrl.detected_loader or "Modded"

        def on_save(ram, difficulty, gamemode, max_players, online_mode, pause_when_empty):
            if server_type == "vanilla":
                self.vanilla_ram = ram
                self.vanilla_run_ctrl.set_ram(ram)
            else:
                self.modpack_ram = ram
                self.modpack_run_ctrl.set_ram(ram)

            if manager:
                manager.configure_server_properties(difficulty=difficulty)
                manager.update_property("gamemode", gamemode)
                manager.update_property("max-players", str(max_players))
                manager.update_property("online-mode", online_mode)
                if pause_when_empty is not None:
                    manager.update_property("pause-when-empty-seconds", str(pause_when_empty))

        dialog = ServerConfigDialog(
            colors=self.colors,
            server_type=server_type,
            server_manager=manager,
            current_ram=current_ram,
            on_save=on_save,
            mc_version=mc_version,
            loader_info=loader_info,
            parent=self
        )
        dialog.exec()

    # ============================================================
    # Dialogs and Modals
    # ============================================================

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

    def _check_and_get_java(self, minecraft_version: str, show_modal: bool = True) -> Optional[str]:
        """
        Checks Java compatibility and returns the best Java executable to use.

        This method uses intelligent detection:
        1. First checks if system Java is compatible -> uses it
        2. Then checks if any PyCraft-installed Java is compatible -> uses it
        3. If no compatible Java found -> shows modal to install (if show_modal=True)

        Args:
            minecraft_version: Minecraft version (e.g., "1.20.1")
            show_modal: If True, shows installation modal when Java is needed

        Returns:
            Path to Java executable, or None if cancelled/failed
        """
        java_check = self.java_manager.get_best_java_for_version(minecraft_version)

        # If we already have compatible Java, return it
        if not java_check["needs_install"]:
            return java_check["java_executable"]

        # No compatible Java found - show modal if allowed
        if not show_modal:
            return None

        # Build informative message
        msg = QMessageBox(self)
        msg.setWindowTitle("Java Required")
        msg.setIcon(QMessageBox.Icon.Warning)

        required = java_check["required_java_version"]
        max_ver = java_check["max_java_version"]
        system_ver = java_check["system_java_version"]
        recommended = java_check["recommended_install_version"]

        # Title
        if max_ver:
            msg.setText(f"Minecraft {minecraft_version} requires Java {required}-{max_ver}")
        else:
            msg.setText(f"Minecraft {minecraft_version} requires Java {required}+")

        # Detailed explanation
        if system_ver:
            if max_ver and system_ver > max_ver:
                # System Java is too NEW for the version range
                if required >= 17:
                    # MC 1.18-1.20 needs Java 17-20 (Java 21 has Security Manager issues)
                    info_text = (
                        f"Your system has Java {system_ver}, but it's too new for this version.\n"
                        f"Minecraft {minecraft_version} requires Java {required}-{max_ver}.\n"
                        f"Java {system_ver} has Security Manager changes that break some mods.\n\n"
                        f"PyCraft can install Java {recommended} separately without affecting your system Java."
                    )
                else:
                    # Old MC (1.7-1.16) needs Java 8-16
                    info_text = (
                        f"Your system has Java {system_ver}, but it's too new for this version.\n"
                        f"Older Minecraft/Forge versions require Java {required}-{max_ver}.\n"
                        f"Java 17+ causes compatibility issues with module system.\n\n"
                        f"PyCraft can install Java {recommended} separately without affecting your system Java."
                    )
            else:
                # System Java is too OLD
                info_text = (
                    f"Your system has Java {system_ver}, but Java {required}+ is needed.\n\n"
                    f"PyCraft can install Java {recommended} separately without affecting your system Java."
                )
        else:
            # No Java installed at all
            info_text = (
                f"Java is not installed on your system.\n\n"
                f"PyCraft can install Java {recommended} automatically."
            )

        msg.setInformativeText(info_text)

        # Style the message box
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.colors['bg_card']};
            }}
            QMessageBox QLabel {{
                color: {self.colors['text']};
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['bg_card']};
                border-color: {self.colors['accent']};
            }}
        """)

        # Buttons
        install_btn = msg.addButton("Install Automatically", QMessageBox.ButtonRole.AcceptRole)
        install_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['accent']};
                color: #000000;
                border: none;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {self.colors['accent_hover']};
            }}
        """)
        java_btn = msg.addButton("Java Management", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        msg.exec()

        clicked = msg.clickedButton()
        if clicked == java_btn:
            self._go_to("java_management")
            return None
        elif clicked == cancel_btn or clicked is None:
            return None
        elif clicked == install_btn:
            # Install the recommended version
            if not self._show_java_install_modal(recommended):
                QMessageBox.critical(
                    self,
                    "Installation Failed",
                    f"Failed to install Java {recommended}.\n\n"
                    f"You can try again or install Java manually via Java Management."
                )
                return None

            # After successful install, get the path to the new Java
            install_dir = self.java_manager.java_installs_dir / f"java-{recommended}"
            if install_dir.exists():
                java_exe = self.java_manager._find_java_executable(install_dir)
                if java_exe:
                    return str(java_exe)

            return None

        return None

    def closeEvent(self, event):
        """Handle application close - stop all running servers"""
        servers_stopped = []

        # Stop vanilla server if running (via controller)
        if hasattr(self, 'vanilla_run_ctrl'):
            manager = self.vanilla_run_ctrl.get_server_manager()
            if manager and manager.is_server_running():
                manager.stop_server()
                servers_stopped.append("vanilla")

        # Stop modpack server if running (via controller)
        if hasattr(self, 'modpack_run_ctrl'):
            manager = self.modpack_run_ctrl.get_server_manager()
            if manager and manager.is_server_running():
                manager.stop_server()
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
