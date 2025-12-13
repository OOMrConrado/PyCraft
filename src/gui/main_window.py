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
    QStyle, QProxyStyle, QStyleOption
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
            icon_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "PyCraft-Files", "icon.ico"
            )
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
        logo_frame.setFixedSize(48, 48)
        logo_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_card']};
                border-radius: 24px;
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
                pix = QPixmap(logo_path).scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(pix)
                logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                logo_label.setStyleSheet("background: transparent; border: none;")
                logo_label.setGeometry(2, 2, 44, 44)
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
        java_layout.addWidget(self.java_info)

        java_btn = self._styled_button("Check Java", self.colors['bg_input'], self.colors['text'], 180)
        java_btn.clicked.connect(self._check_java)
        java_layout.addWidget(java_btn, alignment=Qt.AlignmentFlag.AlignLeft)

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

    def _log(self, console: QTextEdit, msg: str, level: str = "normal"):
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
        self.ver_scroll.hide()
        self.ver_search.setText("")
        self.ver_search.setPlaceholderText(f"✓ {ver} (click to change)")
        self.ver_search.clearFocus()

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

        self.download_btn.setEnabled(False)
        self.active_progress = self.create_progress
        self.active_progress_label = self.create_progress_label
        self.active_status = self.create_status

        def process():
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

                java = self.java_manager.ensure_java_installed(
                    self.selected_version,
                    log_callback=lambda m: self.log_signal.emit(m, "normal", "v_create")
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
                self.run_status.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600;")

                self.server_manager = ServerManager(folder)
                self.is_server_configured = True

                self.run_start.setEnabled(True)
                self.run_config.setEnabled(True)

                self._log(self.vanilla_run_console, f"\nServer found: {folder}\n", "success")
            else:
                self.run_status.setText("server.jar not found")
                self.run_status.setStyleSheet(f"color: {self.colors['red']}; font-size: 13px; font-weight: 600;")

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
        dialog.setFixedSize(380, 180)
        dialog.setStyleSheet(f"background-color: {self.colors['bg_card']};")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)

        ram = self.vanilla_ram if server_type == "vanilla" else self.modpack_ram
        ram_label = QLabel(f"RAM: {ram} MB")
        ram_label.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px;")
        layout.addWidget(ram_label)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(1024 if server_type == "vanilla" else 2048)
        slider.setMaximum(16384 if server_type == "vanilla" else 32768)
        slider.setValue(ram)
        slider.valueChanged.connect(lambda v: ram_label.setText(f"RAM: {v} MB"))
        layout.addWidget(slider)

        save = self._styled_button("Save", self.colors['accent'], "#000000", 100)
        save.clicked.connect(lambda: self._save_config(server_type, slider.value(), dialog))
        layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.exec()

    def _save_config(self, server_type: str, ram: int, dialog: QDialog):
        if server_type == "vanilla":
            self.vanilla_ram = ram
        else:
            self.modpack_ram = ram
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
                self.mp_run_status.setStyleSheet(f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600;")

                self.modpack_server_manager = ServerManager(folder)
                self.is_modpack_configured = True

                self.mp_start.setEnabled(True)
                self.mp_config.setEnabled(True)

                self._log(self.modpack_run_console, f"\nServer found: {folder}\n", "success")
            else:
                self.mp_run_status.setText("Server not found")
                self.mp_run_status.setStyleSheet(f"color: {self.colors['red']}; font-size: 13px; font-weight: 600;")

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
            label.setStyleSheet(f"color: {self.colors['yellow']}; font-size: 13px;")
            self.java_info_layout.addWidget(label)

            install = self._styled_button("Install Java", self.colors['accent'], "#000000", 150)
            install.clicked.connect(self._install_java)
            self.java_info_layout.addWidget(install)
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
                frame_layout = QVBoxLayout(frame)
                frame_layout.setContentsMargins(12, 10, 12, 10)

                v = QLabel(f"Java {ver}")
                v.setStyleSheet(f"color: {self.colors['text']}; font-size: 14px; font-weight: 600;")
                frame_layout.addWidget(v)

                p = QLabel(f"Path: {path}")
                p.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
                frame_layout.addWidget(p)

                self.java_info_layout.addWidget(frame)

    def _install_java(self):
        ver, ok = QInputDialog.getText(self, "Install Java", "Version (8, 17, or 21):")
        if ok and ver:
            try:
                v = int(ver)
                if v not in [8, 17, 21]:
                    QMessageBox.critical(self, "Error", "Use 8, 17, or 21")
                    return

                self.java_manager.download_java(v, lambda m: print(m))
                QTimer.singleShot(1000, self._check_java)

            except ValueError:
                QMessageBox.critical(self, "Error", "Invalid version")

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
