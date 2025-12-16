"""
PyCraft Main Window - Modern UI with Sidebar Navigation
Inspired by Revision Tool design
"""

import sys
import os
import threading
import webbrowser
from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QFrame,
    QScrollArea, QProgressBar, QFileDialog, QMessageBox, QDialog,
    QSlider, QStackedWidget, QInputDialog, QGraphicsDropShadowEffect,
    QStyle, QProxyStyle, QStyleOption, QComboBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QIcon, QTextCharFormat, QColor, QTextCursor, QCursor, QFont, QPainter


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

        cf_key = self.api_config.get_curseforge_key()
        if cf_key:
            self.modpack_manager.set_curseforge_api_key(cf_key)

        # State
        self.versions_list = []
        self.filtered_versions = []
        self.selected_version = None
        self.server_folder = None
        self.is_server_configured = False

        self.modpack_results = []
        self.selected_modpack = None
        self.modpack_folder = None

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
        except:
            pass

    def _connect_signals(self):
        """Connect thread-safe signals"""
        self.log_signal.connect(self._on_log)
        self.progress_signal.connect(self._on_progress)
        self.status_signal.connect(self._on_status)

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

        # Footer
        content_layout.addWidget(self._build_footer())

        main_layout.addWidget(content_wrapper, 1)

        # Remove borders from ALL QLabels
        self._remove_label_borders()

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
        header.setFixedHeight(90)
        header.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 20, 20, 10)

        # Logo circle
        logo_frame = QFrame()
        logo_frame.setFixedSize(64, 64)
        logo_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_card']};
                border-radius: 32px;
                border: 2px solid {self.colors['accent']};
            }}
        """)

        try:
            logo_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "PyCraft-Files", "logo.png"
            )
            if os.path.exists(logo_path):
                logo_label = QLabel(logo_frame)
                pix = QPixmap(logo_path).scaled(58, 58, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(pix)
                logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                logo_label.setStyleSheet("background: transparent; border: none;")
                logo_label.setGeometry(3, 3, 58, 58)
        except:
            pass

        header_layout.addWidget(logo_frame)

        title_widget = QWidget()
        title_widget.setStyleSheet("background: transparent;")
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(12, 0, 0, 0)
        title_layout.setSpacing(0)

        name = QLabel("PyCraft")
        name.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {self.colors['text']};")
        title_layout.addWidget(name)

        sub = QLabel("Server Manager")
        sub.setStyleSheet(f"font-size: 11px; color: {self.colors['text_secondary']};")
        title_layout.addWidget(sub)

        header_layout.addWidget(title_widget)
        header_layout.addStretch()
        layout.addWidget(header)

        # Search
        search_container = QWidget()
        search_container.setStyleSheet("background: transparent;")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(15, 5, 15, 15)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find a setting")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colors['accent']};
            }}
            QLineEdit::placeholder {{
                color: {self.colors['text_muted']};
            }}
        """)
        search_layout.addWidget(self.search_input)
        layout.addWidget(search_container)

        # Navigation
        nav_widget = QWidget()
        nav_widget.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 5, 0, 5)
        nav_layout.setSpacing(2)

        nav_items = [
            ("home", "Home", "fa5s.home"),
            ("vanilla", "Vanilla Server", "fa5s.cube"),
            ("modded", "Modded Server", "fa5s.puzzle-piece"),
            ("info", "Info & Help", "fa5s.info-circle"),
        ]

        for page_id, text, icon in nav_items:
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
        github.clicked.connect(lambda: webbrowser.open("https://github.com/OOMrConrado/PyCraft"))
        layout.addWidget(github)

        modrinth = FooterLink("Modrinth", "Browse Modpacks", "fa5s.box-open")
        modrinth.clicked.connect(lambda: webbrowser.open("https://modrinth.com/modpacks"))
        layout.addWidget(modrinth)

        help_link = FooterLink("Documentation", "Get Help", "fa5s.book")
        help_link.clicked.connect(lambda: self._go_to("info"))
        layout.addWidget(help_link)

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
        cards_layout = QHBoxLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(20)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        install_card = OptionCard("Install Modpack", "Download and install from Modrinth", "fa5s.download")
        install_card.clicked.connect(lambda: self._go_to("modpack_install"))
        cards_layout.addWidget(install_card)

        run_card = OptionCard("Run Server", "Manage an existing modded server", "fa5s.play-circle")
        run_card.clicked.connect(lambda: self._go_to("modpack_run"))
        cards_layout.addWidget(run_card)

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
            ("Common Issues", "Server won't start:\n- Check Java installation in Settings\n- Verify enough RAM is available\n\nFriends can't connect:\n- Ensure same VPN network\n- Check firewall settings\n- Use correct IP address"),
            ("System Requirements", "- Java 17+ (installable via Settings)\n- 4GB RAM minimum (8GB for modded)\n- 2GB disk space\n- Internet connection"),
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

        # Java section
        java_frame = self._section_frame("Java Management")
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

        # Progress bar with percentage label outside
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

        # Console
        console_frame = self._section_frame("Console")
        self.vanilla_create_console = self._console()
        console_frame.layout().addWidget(self.vanilla_create_console)
        layout.addWidget(console_frame)

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

        self.run_status = QLabel("")
        self.run_status.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px; font-weight: 600;")
        select_layout.addWidget(self.run_status)

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

        self.run_cmd = self._input("Enter command...", 500)
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
        layout.addWidget(console_frame)

        layout.addStretch()
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        self._log(self.vanilla_run_console, "Select a server folder to begin.\n", "info")

        return page

    def _build_modpack_install(self) -> QWidget:
        """Build modpack installation page"""
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

        title = QLabel("Install Modpack")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        # Search
        search_frame = self._section_frame("Search Modpacks")
        search_layout = search_frame.layout()

        search_row = QWidget()
        search_row.setStyleSheet("background: transparent;")
        search_h = QHBoxLayout(search_row)
        search_h.setContentsMargins(0, 0, 0, 0)

        self.mp_search = self._input("Search (e.g., Create, ATM9)...", 450)
        self.mp_search.returnPressed.connect(self._search_modpacks)
        search_h.addWidget(self.mp_search)

        search_btn = self._styled_button("Search", self.colors['accent'], "#000000", 100)
        search_btn.clicked.connect(self._search_modpacks)
        search_h.addWidget(search_btn)

        search_layout.addWidget(search_row)

        results_label = QLabel("Results:")
        results_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px; font-weight: 600;")
        search_layout.addWidget(results_label)

        self.mp_results_scroll = NonPropagatingScrollArea()
        self.mp_results_scroll.setFixedHeight(180)
        self.mp_results_scroll.setWidgetResizable(True)
        self.mp_results_scroll.setStyleSheet(self._scroll_style())

        self.mp_results = QWidget()
        self.mp_results_layout = QVBoxLayout(self.mp_results)
        self.mp_results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.mp_results_scroll.setWidget(self.mp_results)

        search_layout.addWidget(self.mp_results_scroll)

        self.mp_selected = QLabel("No modpack selected")
        self.mp_selected.setStyleSheet(f"color: {self.colors['yellow']}; font-size: 13px; font-weight: 600;")
        search_layout.addWidget(self.mp_selected)

        layout.addWidget(search_frame)

        # Folder
        folder_frame = self._section_frame("Destination Folder")
        folder_layout = folder_frame.layout()

        folder_btn = self._styled_button("Select Folder", self.colors['bg_input'], self.colors['text'], 180)
        folder_btn.clicked.connect(self._select_mp_folder)
        folder_layout.addWidget(folder_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.mp_folder_label = QLabel("No folder selected")
        self.mp_folder_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        folder_layout.addWidget(self.mp_folder_label)

        layout.addWidget(folder_frame)

        # Install
        self.mp_install_btn = self._styled_button("Download and Install", self.colors['accent'], "#000000", 280)
        self.mp_install_btn.setEnabled(False)
        self.mp_install_btn.clicked.connect(self._install_modpack)
        layout.addWidget(self.mp_install_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Console
        console_frame = self._section_frame("Console")
        self.modpack_install_console = self._console()
        console_frame.layout().addWidget(self.modpack_install_console)
        layout.addWidget(console_frame)

        layout.addStretch()
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        self._log(self.modpack_install_console, "Search for a modpack to begin.\n", "info")

        return page

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

        self.mp_run_cmd = self._input("Enter command...", 500)
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
        layout.addWidget(console_frame)

        layout.addStretch()
        scroll.setWidget(content)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        self._log(self.modpack_run_console, "Select a server folder to begin.\n", "info")

        return page

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

    def _log(self, console: QTextEdit, msg: str, level: str = "normal", max_lines: int = 200):
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
            "vanilla_create": 5, "vanilla_run": 6, "modpack_install": 7, "modpack_run": 8
        }
        if page in pages:
            self.page_stack.setCurrentIndex(pages[page])

        sidebar_map = {
            "home": "home", "vanilla": "vanilla", "vanilla_create": "vanilla", "vanilla_run": "vanilla",
            "modded": "modded", "modpack_install": "modded", "modpack_run": "modded",
            "info": "info", "settings": "settings"
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

    def _select_create_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
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
        java_info = self.java_manager.detect_java_version()

        # Check if we have a compatible Java already installed by PyCraft
        pycraft_java = None
        install_dir = self.java_manager.java_installs_dir / f"java-{required_java}"
        if install_dir.exists():
            java_exe = self.java_manager._find_java_executable(install_dir)
            if java_exe:
                pycraft_java = str(java_exe)

        # Determine if we need Java
        needs_java = False
        if pycraft_java:
            # We have PyCraft-installed Java, use it
            pass
        elif java_info:
            _, installed_major = java_info
            if installed_major < required_java:
                needs_java = True
        else:
            needs_java = True

        if needs_java:
            # Show dialog with options
            msg = QMessageBox(self)
            msg.setWindowTitle("Java Required")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText(f"Minecraft {self.selected_version} requires Java {required_java}+")

            if java_info:
                _, installed_major = java_info
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
            settings_btn = msg.addButton("Go to Settings", QMessageBox.ButtonRole.ActionRole)
            cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

            msg.exec()

            clicked = msg.clickedButton()
            if clicked == settings_btn:
                self._go_to("settings")
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

            except Exception as e:
                self.log_signal.emit(f"Error: {e}\n", "error", "v_create")

            finally:
                QTimer.singleShot(0, lambda: self.download_btn.setEnabled(True))
                QTimer.singleShot(0, lambda: self.create_progress.setValue(0))
                QTimer.singleShot(0, lambda: self.create_progress_label.setText("0/100%"))

        threading.Thread(target=process, daemon=True).start()

    def _select_run_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Server Folder")
        if folder:
            if os.path.exists(os.path.join(folder, "server.jar")):
                self.server_folder = folder
                self.run_folder_label.setText(f"Folder: {folder}")
                self.run_status.setText("Server found")
                self.run_status.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600; border: none;")

                self.server_manager = ServerManager(folder)
                self.is_server_configured = True

                self.run_start.setEnabled(True)
                self.run_config.setEnabled(True)

                self._log(self.vanilla_run_console, f"\nServer found: {folder}\n", "success")
            else:
                self.server_folder = None
                self.run_folder_label.setText(f"Folder: {folder}")
                self.run_status.setText("server.jar not found")
                self.run_status.setStyleSheet(f"color: {self.colors['red']}; font-size: 13px; font-weight: 600; border: none;")
                self.run_start.setEnabled(False)
                self.run_config.setEnabled(False)
                self.run_stop.setEnabled(False)
                self.run_cmd_btn.setEnabled(False)
                self.server_manager = None
                self.is_server_configured = False

    def _start_vanilla(self):
        if not self.server_manager:
            return

        self._log(self.vanilla_run_console, "\n=== STARTING SERVER ===\n", "info")
        self.run_start.setEnabled(False)
        self.run_config.setEnabled(False)
        self.run_stop.setEnabled(True)

        def start():
            success = self.server_manager.start_server(
                ram_mb=self.vanilla_ram,
                log_callback=lambda m: self.log_signal.emit(m, "normal", "v_run"),
                detached=True
            )
            if success:
                QTimer.singleShot(0, lambda: self.run_cmd_btn.setEnabled(True))

        threading.Thread(target=start, daemon=True).start()

    def _stop_vanilla(self):
        if self.server_manager:
            self.server_manager.stop_server()
            self._log(self.vanilla_run_console, "\nServer stopped\n", "warning")

        self.run_start.setEnabled(True)
        self.run_config.setEnabled(True)
        self.run_stop.setEnabled(False)
        self.run_cmd_btn.setEnabled(False)

    def _send_vanilla_cmd(self):
        cmd = self.run_cmd.text().strip()
        if cmd and self.server_manager:
            self._log(self.vanilla_run_console, f"> {cmd}\n", "info")
            self.server_manager.send_command(cmd)
            self.run_cmd.clear()

    def _config_vanilla(self):
        if self.server_manager and self.server_manager.is_server_running():
            QMessageBox.warning(self, "Warning", "Stop server first")
            return

        self._open_config_dialog("vanilla")

    def _open_config_dialog(self, server_type: str):
        dialog = QDialog(self)
        dialog.setWindowTitle("Server Configuration")
        # Vanilla needs more height for pause-when-empty option
        dialog_height = 620 if server_type == "vanilla" else 520
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
            pause_spinbox.value() if pause_spinbox else None,
            dialog
        ))
        layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.exec()

    def _save_config(self, server_type: str, ram: int, difficulty: str, gamemode: str, max_players: int, pause_when_empty: Optional[int], dialog: QDialog):
        if server_type == "vanilla":
            self.vanilla_ram = ram
            if self.server_manager:
                self.server_manager.configure_server_properties(difficulty=difficulty)
                self.server_manager.update_property("gamemode", gamemode)
                self.server_manager.update_property("max-players", str(max_players))
                if pause_when_empty is not None:
                    self.server_manager.update_property("pause-when-empty-seconds", str(pause_when_empty))
        else:
            self.modpack_ram = ram
            if self.modpack_server_manager:
                self.modpack_server_manager.configure_server_properties(difficulty=difficulty)
                self.modpack_server_manager.update_property("gamemode", gamemode)
                self.modpack_server_manager.update_property("max-players", str(max_players))
        dialog.accept()

    # Modpack
    def _search_modpacks(self):
        query = self.mp_search.text().strip()
        if not query:
            return

        while self.mp_results_layout.count():
            child = self.mp_results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._log(self.modpack_install_console, f"\nSearching '{query}'...\n", "info")

        def search():
            try:
                results = self.modpack_manager.search_modpacks(query, platform="modrinth")
                self.modpack_results = results

                if results:
                    self.log_signal.emit(f"Found {len(results)} modpacks\n", "success", "m_install")
                    QTimer.singleShot(0, lambda: self._show_mp_results(results))
                else:
                    self.log_signal.emit("No results\n", "warning", "m_install")

            except Exception as e:
                self.log_signal.emit(f"Error: {e}\n", "error", "m_install")

        threading.Thread(target=search, daemon=True).start()

    def _show_mp_results(self, results: list):
        for mp in results[:10]:
            self._create_mp_item(mp)

    def _create_mp_item(self, mp: dict):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_input']};
                border-radius: 10px;
                border: 1px solid {self.colors['border']};
            }}
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)

        info = QWidget()
        info.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        name = QLabel(mp.get("title", "Unknown"))
        name.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600;")
        info_layout.addWidget(name)

        desc = QLabel(mp.get("description", "")[:70] + "...")
        desc.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
        info_layout.addWidget(desc)

        layout.addWidget(info)

        select = self._styled_button("Select", self.colors['accent'], "#000000", 80)
        select.setFixedHeight(34)
        select.clicked.connect(lambda: self._pick_mp(mp))
        layout.addWidget(select)

        self.mp_results_layout.addWidget(frame)

    def _pick_mp(self, mp: dict):
        self.selected_modpack = mp
        name = mp.get("title", "Unknown")
        self.mp_selected.setText(f"Selected: {name}")
        self.mp_selected.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600;")
        self._update_mp_btn()

    def _select_mp_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
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

        def install():
            try:
                self.log_signal.emit("\nInstalling modpack...\n", "info", "m_install")

                success = self.modpack_manager.install_modpack(
                    project_id, self.modpack_folder,
                    log_callback=lambda m: self.log_signal.emit(m, "normal", "m_install")
                )

                if success:
                    self.log_signal.emit("\n" + "="*50 + "\n", "success", "m_install")
                    self.log_signal.emit("MODPACK INSTALLED\n", "success", "m_install")
                    self.log_signal.emit("="*50 + "\n", "success", "m_install")

            except Exception as e:
                self.log_signal.emit(f"Error: {e}\n", "error", "m_install")

            finally:
                QTimer.singleShot(0, lambda: self.mp_install_btn.setEnabled(True))

        threading.Thread(target=install, daemon=True).start()

    def _select_mp_run_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Server Folder")
        if folder:
            if self._has_server(folder):
                self.modpack_server_path = folder
                self.mp_run_folder_label.setText(f"Folder: {folder}")
                self.mp_run_status.setText("Server found")
                self.mp_run_status.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600; border: none;")

                self.modpack_server_manager = ServerManager(folder)
                self.is_modpack_configured = True

                self.mp_start.setEnabled(True)
                self.mp_config.setEnabled(True)

                self._log(self.modpack_run_console, f"\nServer found: {folder}\n", "success")
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

    def _has_server(self, folder: str) -> bool:
        import glob
        for p in ["server.jar", "forge-*.jar", "fabric-server-*.jar"]:
            if glob.glob(os.path.join(folder, p)):
                return True
        return False

    def _start_mp(self):
        if not self.modpack_server_manager:
            return

        self._log(self.modpack_run_console, "\n=== STARTING SERVER ===\n", "info")
        self.mp_start.setEnabled(False)
        self.mp_config.setEnabled(False)
        self.mp_stop.setEnabled(True)

        def start():
            success = self.modpack_server_manager.start_server(
                ram_mb=self.modpack_ram,
                log_callback=lambda m: self.log_signal.emit(m, "normal", "m_run"),
                detached=True
            )
            if success:
                QTimer.singleShot(0, lambda: self.mp_cmd_btn.setEnabled(True))

        threading.Thread(target=start, daemon=True).start()

    def _stop_mp(self):
        if self.modpack_server_manager:
            self.modpack_server_manager.stop_server()
            self._log(self.modpack_run_console, "\nServer stopped\n", "warning")

        self.mp_start.setEnabled(True)
        self.mp_config.setEnabled(True)
        self.mp_stop.setEnabled(False)
        self.mp_cmd_btn.setEnabled(False)

    def _send_mp_cmd(self):
        cmd = self.mp_run_cmd.text().strip()
        if cmd and self.modpack_server_manager:
            self._log(self.modpack_run_console, f"> {cmd}\n", "info")
            self.modpack_server_manager.send_command(cmd)
            self.mp_run_cmd.clear()

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
                except:
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
