"""
Modpack Install Controller - Handles modpack search and installation UI and logic.
"""

import threading
from typing import Dict, Optional, Callable
from collections import deque

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog, QStackedWidget, QDialog, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QUrl
from PySide6.QtGui import QCursor, QPixmap, QDesktopServices

import qtawesome as qta

from ..widgets import NonPropagatingScrollArea, NonPropagatingTextEdit
from ..pages.base_page import BasePage


class ModpackInstallController(BasePage):
    """
    Controller for the Modpack Installation page.

    Handles:
    - Provider selection (Modrinth/CurseForge)
    - Modpack search and pagination
    - Version selection dialog
    - Modpack installation
    """

    # Signals for thread-safe communication
    results_signal = Signal(object)  # list of results
    pagination_signal = Signal(int)  # total results
    icon_signal = Signal(str, bytes)  # project_id, image bytes (QPixmap created in main thread)
    version_loaded_signal = Signal(object, object)  # versions, callback
    install_success = Signal(str, str, str)  # name, mc_version, loader

    def __init__(
        self,
        colors: Dict[str, str],
        modpack_manager,
        navigate_callback: Optional[Callable[[str], None]] = None,
        log_signal=None,
        check_java_callback=None,
        warn_dangerous_folder=None,
        warn_existing_server=None,
        parent=None
    ):
        super().__init__(colors, navigate_callback, parent)

        # Dependencies
        self.modpack_manager = modpack_manager
        self.log_signal = log_signal
        self._check_and_get_java = check_java_callback
        self._warn_dangerous_folder = warn_dangerous_folder or (lambda f: True)
        self._warn_existing_server = warn_existing_server or (lambda f: True)

        # State
        self.selected_provider = "modrinth"
        self.modpack_results = []
        self.selected_modpack = None
        self.selected_mp_version = None
        self.modpack_folder = None
        self.current_page = 1
        self.total_results = 0
        self.search_query = ""
        self.is_popular_search = False
        self.icon_cache = {}

        # Debounce timer for search
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self._search_modpacks)

        # Thread-safe log buffer - logs are added from worker threads, processed by timer
        self._thread_log_buffer = deque()
        self._log_lock = threading.Lock()
        self._log_timer = QTimer()
        self._log_timer.setInterval(100)  # Process logs every 100ms
        self._log_timer.timeout.connect(self._process_thread_logs)
        self._log_timer.start()  # Always running to check for new logs

        # Connect signals
        self.results_signal.connect(self._show_results)
        self.pagination_signal.connect(self._update_pagination)
        self.icon_signal.connect(self._on_icon_loaded)
        self.version_loaded_signal.connect(self._on_versions_loaded)

        self._build_ui()

    def _process_thread_logs(self):
        """Process logs from worker threads - called by timer in main thread"""
        if not self._thread_log_buffer:
            return

        # Get all pending logs (thread-safe)
        logs_to_process = []
        with self._log_lock:
            # Take up to 30 logs at a time
            for _ in range(min(30, len(self._thread_log_buffer))):
                if self._thread_log_buffer:
                    logs_to_process.append(self._thread_log_buffer.popleft())

        if logs_to_process and hasattr(self, 'console') and self.console:
            for msg, level in logs_to_process:
                self._log(self.console, msg, level)

    def _build_ui(self):
        """Build the modpack installation page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget for provider selection / search UI
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")

        # Page 0: Provider Selection
        self.stack.addWidget(self._build_provider_page())

        # Page 1: Search UI
        self.stack.addWidget(self._build_search_page())

        layout.addWidget(self.stack)

    def _build_provider_page(self) -> QWidget:
        """Build the provider selection page"""
        page = QWidget()
        page.setStyleSheet(f"background-color: {self.colors['bg_content']};")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 25, 40, 25)
        layout.setSpacing(18)

        # Back button
        back = self._text_button("< Back")
        back.clicked.connect(lambda: self.navigate_to("modded"))
        layout.addWidget(back)

        # Title
        title = QLabel("Install Modpack")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        layout.addStretch(2)

        # Provider selection
        provider_title = QLabel("Choose a modpack provider:")
        provider_title.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 15px;")
        provider_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(provider_title)

        # Provider buttons
        providers_container = QWidget()
        providers_container.setStyleSheet("background: transparent;")
        providers_h = QHBoxLayout(providers_container)
        providers_h.setSpacing(24)
        providers_h.setAlignment(Qt.AlignmentFlag.AlignCenter)

        modrinth_btn = self._create_provider_button(
            "Modrinth", "Open-source modding platform", "#1bd96a", "fa5s.leaf"
        )
        modrinth_btn.clicked.connect(lambda: self._select_provider("modrinth"))
        providers_h.addWidget(modrinth_btn)

        curseforge_btn = self._create_provider_button(
            "CurseForge", "Largest mod collection", "#f16436", "fa5s.fire"
        )
        curseforge_btn.clicked.connect(lambda: self._select_provider("curseforge"))
        providers_h.addWidget(curseforge_btn)

        layout.addWidget(providers_container)

        # Recommendation
        rec_label = QLabel("We recommend CurseForge for better stability")
        rec_label.setStyleSheet("color: #f0c040; font-size: 13px; font-style: italic;")
        rec_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(rec_label)

        layout.addStretch(3)

        return page

    def _build_search_page(self) -> QWidget:
        """Build the search page"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._scroll_style())

        content = QWidget()
        content.setStyleSheet(f"background-color: {self.colors['bg_content']};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 25, 40, 25)
        layout.setSpacing(18)

        # Back button
        back = self._text_button("< Back")
        back.clicked.connect(lambda: self.navigate_to("modded"))
        layout.addWidget(back)

        # Title
        title = QLabel("Install Modpack")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        # Provider indicator
        layout.addWidget(self._build_provider_row())

        # Search section
        layout.addWidget(self._build_search_section())

        # Folder section
        layout.addWidget(self._build_folder_section())

        # Install button
        self.install_btn = self._styled_button(
            "Download and Install", self.colors['accent'], "#000000", 280
        )
        self.install_btn.setEnabled(False)
        self.install_btn.clicked.connect(self._install_modpack)
        layout.addWidget(self.install_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Console
        console_frame = self._section_frame("Console")
        self.console = self._console()
        console_frame.layout().addWidget(self.console)
        layout.addWidget(console_frame)

        layout.addStretch()
        scroll.setWidget(content)

        return scroll

    def _build_provider_row(self) -> QWidget:
        """Build the provider indicator row"""
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 8)

        self.provider_label = QLabel("Searching on: Modrinth")
        self.provider_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px;")
        layout.addWidget(self.provider_label)

        change_btn = self._text_button("Change")
        change_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(change_btn)
        layout.addStretch()

        return row

    def _build_search_section(self) -> QFrame:
        """Build the search section"""
        frame = self._section_frame("Search Modpacks")
        layout = frame.layout()

        # Search input
        search_row = QWidget()
        search_row.setStyleSheet("background: transparent;")
        search_h = QHBoxLayout(search_row)
        search_h.setContentsMargins(0, 0, 0, 0)

        self.search_input = self._input("Search modpacks...", 560)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_h.addWidget(self.search_input)
        layout.addWidget(search_row)

        # Results label
        results_label = QLabel("Results:")
        results_label.setStyleSheet(
            f"color: {self.colors['text_secondary']}; font-size: 13px; font-weight: 600;"
        )
        layout.addWidget(results_label)

        # Results scroll area
        self.results_scroll = NonPropagatingScrollArea()
        self.results_scroll.setFixedHeight(280)
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setStyleSheet(self._scroll_style())

        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.results_layout.setSpacing(8)
        self.results_scroll.setWidget(self.results_widget)
        layout.addWidget(self.results_scroll)

        # Pagination
        layout.addWidget(self._build_pagination())

        # Selected modpack label
        self.selected_label = QLabel("No modpack selected")
        self.selected_label.setStyleSheet(
            f"color: {self.colors['yellow']}; font-size: 13px; font-weight: 600; border: none;"
        )
        layout.addWidget(self.selected_label)

        return frame

    def _build_pagination(self) -> QWidget:
        """Build pagination controls"""
        self.pagination_widget = QWidget()
        self.pagination_widget.setStyleSheet("background: transparent;")
        self.pagination_widget.setVisible(False)
        layout = QHBoxLayout(self.pagination_widget)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(5)

        self.page_info = QLabel("")
        self.page_info.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        layout.addWidget(self.page_info)
        layout.addStretch()

        pag_btn_style = f"""
            QPushButton {{
                background-color: {self.colors['bg_input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {self.colors['bg_card']}; }}
            QPushButton:disabled {{ color: {self.colors['text_muted']}; }}
        """

        self.prev_btn = QPushButton("<")
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.prev_btn.setStyleSheet(pag_btn_style)
        self.prev_btn.clicked.connect(lambda: self._go_page(self.current_page - 1))
        layout.addWidget(self.prev_btn)

        self.page_btns_layout = QHBoxLayout()
        self.page_btns_layout.setSpacing(3)
        layout.addLayout(self.page_btns_layout)

        self.next_btn = QPushButton(">")
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.next_btn.setStyleSheet(pag_btn_style)
        self.next_btn.clicked.connect(lambda: self._go_page(self.current_page + 1))
        layout.addWidget(self.next_btn)

        return self.pagination_widget

    def _build_folder_section(self) -> QFrame:
        """Build folder selection section"""
        frame = self._section_frame("Destination Folder")
        layout = frame.layout()

        folder_btn = self._styled_button(
            "Select Folder", self.colors['bg_input'], self.colors['text'], 180
        )
        folder_btn.clicked.connect(self._select_folder)
        layout.addWidget(folder_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        layout.addWidget(self.folder_label)

        return frame

    def _create_provider_button(self, name: str, desc: str, color: str, icon: str) -> QPushButton:
        """Create a styled provider button"""
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
        name_label.setStyleSheet(
            f"color: {self.colors['text']}; font-size: 18px; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(name_label)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet(
            f"color: {self.colors['text_muted']}; font-size: 12px; "
            f"background: transparent; border: none;"
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(desc_label)

        return btn

    # ============================================================
    # Provider Selection
    # ============================================================

    def _select_provider(self, provider: str):
        """Handle provider selection"""
        self.selected_provider = provider
        provider_display = "Modrinth" if provider == "modrinth" else "CurseForge"
        self.provider_label.setText(f"Searching on: {provider_display}")

        # Clear previous state
        self._clear_results()
        self.search_input.clear()
        self.selected_label.setText("No modpack selected")
        self.selected_modpack = None
        self.pagination_widget.setVisible(False)

        # Switch to search UI
        self.stack.setCurrentIndex(1)
        self._emit_log(f"Provider: {provider_display}\n", "info")
        self._emit_log("Loading popular modpacks...\n", "info")

        # Load popular modpacks
        self._search_modpacks(page=1, popular=True)

    # ============================================================
    # Search Logic
    # ============================================================

    def _on_search_changed(self, text: str):
        """Handle search text change with debounce"""
        if len(text.strip()) < 3:
            self._clear_results()
            self.pagination_widget.setVisible(False)
            self.search_timer.stop()

            if len(text.strip()) == 0:
                self._search_modpacks(page=1, popular=True)
            return

        self.is_popular_search = False
        self.search_timer.stop()
        self.search_timer.start()

    def _search_modpacks(self, page: int = 1, popular: bool = False):
        """Search for modpacks"""
        query = self.search_input.text().strip()

        if not popular and len(query) < 3:
            return

        self.search_query = query if not popular else ""
        self.current_page = page
        self.is_popular_search = popular

        self._clear_results()

        def search():
            try:
                offset = (page - 1) * 10
                search_query = "" if popular else query
                results, total = self.modpack_manager.search_modpacks(
                    search_query,
                    platform=self.selected_provider,
                    limit=10,
                    offset=offset,
                    side_filter="server"
                )
                self.modpack_results = results

                if results:
                    self.pagination_signal.emit(total)
                    self.results_signal.emit(results)
                else:
                    self.pagination_signal.emit(0)

            except Exception as e:
                self._emit_log(f"Error: {e}\n", "error")

        threading.Thread(target=search, daemon=True).start()

    def _go_page(self, page: int):
        """Navigate to a specific page"""
        total_pages = (self.total_results + 9) // 10
        if 1 <= page <= total_pages:
            self._search_modpacks(page, popular=self.is_popular_search)

    def _update_pagination(self, total: int):
        """Update pagination UI"""
        self.total_results = total
        total_pages = (total + 9) // 10

        if total_pages <= 1:
            self.pagination_widget.setVisible(False)
            return

        self.pagination_widget.setVisible(True)
        self.page_info.setText(f"{total} results")

        # Clear page buttons
        while self.page_btns_layout.count():
            child = self.page_btns_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Create page buttons (max 5)
        start_page = max(1, self.current_page - 2)
        end_page = min(total_pages, start_page + 4)
        start_page = max(1, end_page - 4)

        for p in range(start_page, end_page + 1):
            btn = QPushButton(str(p))
            btn.setFixedSize(32, 32)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            is_current = p == self.current_page
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors['accent'] if is_current else self.colors['bg_input']};
                    color: {'#000000' if is_current else self.colors['text']};
                    border: 1px solid {self.colors['accent'] if is_current else self.colors['border']};
                    border-radius: 6px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {self.colors['accent_hover'] if is_current else self.colors['bg_card']};
                }}
            """)
            btn.clicked.connect(lambda checked, page=p: self._go_page(page))
            self.page_btns_layout.addWidget(btn)

        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < total_pages)

    # ============================================================
    # Results Display
    # ============================================================

    def _clear_results(self):
        """Clear results layout"""
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _show_results(self, results: list):
        """Display search results"""
        for mp in results:
            self._create_result_item(mp)

    def _create_result_item(self, mp: dict):
        """Create a modpack result item"""
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

        # Icon
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

        icon_url = mp.get("icon_url", "")
        if project_id in self.icon_cache:
            icon_label.setPixmap(self.icon_cache[project_id])
        elif icon_url and project_id:
            self._load_icon(icon_url, project_id)

        layout.addWidget(icon_label)

        # Info section
        info = QWidget()
        info.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)

        # Name
        name = QLabel(mp.get("title", "Unknown"))
        name.setStyleSheet(
            f"color: {self.colors['text']}; font-size: 14px; font-weight: 600; border: none;"
        )
        info_layout.addWidget(name)

        # Description
        desc_text = mp.get("description", "")[:80]
        if len(mp.get("description", "")) > 80:
            desc_text += "..."
        desc = QLabel(desc_text)
        desc.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px; border: none;")
        desc.setWordWrap(True)
        info_layout.addWidget(desc)

        # Meta info
        info_layout.addWidget(self._create_meta_row(mp))
        layout.addWidget(info, 1)

        # Select button
        select = self._styled_button("Select", self.colors['accent'], "#000000", 80)
        select.setFixedHeight(36)
        select.clicked.connect(lambda: self._pick_modpack(mp))
        layout.addWidget(select)

        self.results_layout.addWidget(frame)

    def _create_meta_row(self, mp: dict) -> QWidget:
        """Create meta info row for modpack item"""
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(8)

        # Loader
        categories = mp.get("categories", [])
        loader = "Unknown"
        loader_color = self.colors['text_muted']
        if "forge" in categories:
            loader, loader_color = "Forge", "#FF6B35"
        elif "neoforge" in categories:
            loader, loader_color = "NeoForge", "#D64541"
        elif "fabric" in categories:
            loader, loader_color = "Fabric", "#C6BCA7"
        elif "quilt" in categories:
            loader, loader_color = "Quilt", "#8B5CF6"

        loader_label = QLabel(loader)
        loader_label.setStyleSheet(f"""
            color: {loader_color};
            font-size: 11px;
            font-weight: 600;
            background-color: {self.colors['bg_card']};
            padding: 2px 6px;
            border-radius: 4px;
        """)
        layout.addWidget(loader_label)

        # MC versions
        versions = mp.get("versions", [])
        if versions:
            mc_ver = versions[0] if len(versions) == 1 else f"{versions[-1]}-{versions[0]}"
            mc_label = QLabel(f"MC {mc_ver}")
            mc_label.setStyleSheet(
                f"color: {self.colors['text_secondary']}; font-size: 11px; border: none;"
            )
            layout.addWidget(mc_label)

        # Downloads
        downloads = mp.get("downloads", 0)
        dl_label = QLabel(f"{self._format_downloads(downloads)} downloads")
        dl_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px; border: none;")
        layout.addWidget(dl_label)

        layout.addStretch()

        # Link button
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
            layout.addWidget(link_btn)

        return widget

    def _format_downloads(self, count: int) -> str:
        """Format download count"""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count / 1_000:.0f}K"
        return str(count)

    # ============================================================
    # Icon Loading
    # ============================================================

    def _load_icon(self, url: str, project_id: str):
        """Load modpack icon asynchronously"""
        if project_id in self.icon_cache:
            return

        def load():
            try:
                import requests
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    # Send raw bytes to main thread - QPixmap must be created there
                    self.icon_signal.emit(project_id, response.content)
            except Exception:
                pass

        threading.Thread(target=load, daemon=True).start()

    def _on_icon_loaded(self, project_id: str, image_bytes: bytes):
        """Handle loaded icon - creates QPixmap in main thread (Qt requirement)"""
        if project_id in self.icon_cache:
            return

        pixmap = QPixmap()
        pixmap.loadFromData(image_bytes)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                56, 56,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.icon_cache[project_id] = scaled
            icon_label = self.findChild(QLabel, f"mp_icon_{project_id}")
            if icon_label:
                icon_label.setPixmap(scaled)

    # ============================================================
    # Version Selection
    # ============================================================

    def _pick_modpack(self, mp: dict):
        """Handle modpack selection - show version selector"""
        self._show_version_selector(mp)

    def _show_version_selector(self, mp: dict):
        """Show version selection dialog"""
        project_id = mp.get("project_id", "")
        mp_name = mp.get("title", "Unknown")

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Select Version - {mp_name}")
        dialog.setFixedSize(500, 400)
        dialog.setStyleSheet(f"QDialog {{ background-color: {self.colors['bg_main']}; }}")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel(f"Select version for {mp_name}")
        title.setStyleSheet(
            f"color: {self.colors['text']}; font-size: 16px; font-weight: bold; border: none;"
        )
        layout.addWidget(title)

        # Loading label
        loading = QLabel("Loading versions...")
        loading.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 13px; border: none;")
        loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(loading)

        # Versions list
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

        # Selected info
        selected_info = QLabel("")
        selected_info.setStyleSheet(
            f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600; border: none;"
        )
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

        dialog.selected_version = None

        def on_version_selected(version_data):
            dialog.selected_version = version_data
            v_name = version_data.get("name", version_data.get("version_number", ""))
            loaders = version_data.get("loaders", [])
            game_vers = version_data.get("game_versions", [])
            loader = loaders[0].capitalize() if loaders else "Unknown"
            mc_ver = game_vers[0] if game_vers else "Unknown"
            selected_info.setText(f"Selected: {v_name} ({loader}, MC {mc_ver})")
            selected_info.setVisible(True)
            confirm_btn.setEnabled(True)

        def show_versions(versions):
            loading.setVisible(False)
            versions_scroll.setVisible(True)

            for i, v in enumerate(versions[:20]):
                v_frame = self._create_version_item(v, i == 0, on_version_selected)
                versions_layout.addWidget(v_frame)

        def on_confirm():
            if dialog.selected_version:
                self.selected_modpack = mp
                self.selected_mp_version = dialog.selected_version
                v_name = dialog.selected_version.get("name", "")
                self.selected_label.setText(f"Selected: {mp_name} ({v_name})")
                self.selected_label.setStyleSheet(
                    f"color: {self.colors['accent']}; font-size: 13px; font-weight: 600;"
                )
                self._update_install_btn()
                dialog.accept()

        confirm_btn.clicked.connect(on_confirm)

        # Load versions
        self._load_versions(mp, show_versions, loading)

        dialog.exec()

    def _create_version_item(self, v: dict, is_latest: bool, on_select) -> QFrame:
        """Create a version item in the selector"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_input']};
                border-radius: 8px;
                border: 1px solid {self.colors['border']};
            }}
            QFrame:hover {{
                border: 1px solid {self.colors['accent']};
            }}
        """)
        frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)

        # Version info
        info = QWidget()
        info.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        v_name = v.get("name", v.get("version_number", "Unknown"))
        if is_latest:
            v_name += " (Latest)"
        name_label = QLabel(v_name)
        name_label.setStyleSheet(
            f"color: {self.colors['text']}; font-size: 13px; font-weight: 600; border: none;"
        )
        info_layout.addWidget(name_label)

        # Loader and MC version
        loaders = v.get("loaders", [])
        game_vers = v.get("game_versions", [])
        loader = loaders[0].capitalize() if loaders else "Unknown"
        mc_ver = game_vers[0] if game_vers else "Unknown"

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
        info_layout.addWidget(meta_label)

        layout.addWidget(info, 1)

        # Downloads
        downloads = v.get("downloads", 0)
        dl_label = QLabel(f"{self._format_downloads(downloads)}")
        dl_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px; border: none;")
        layout.addWidget(dl_label)

        frame.mousePressEvent = lambda e, ver=v: on_select(ver)

        return frame

    def _load_versions(self, mp: dict, on_success, loading_label):
        """Load versions for a modpack"""
        project_id = mp.get("project_id", "")
        source = mp.get("source", "modrinth")

        def load():
            try:
                if source == "curseforge":
                    versions = self._load_curseforge_versions(mp, project_id)
                else:
                    versions = self.modpack_manager.modrinth_api.get_modpack_versions(project_id)

                if versions:
                    self.version_loaded_signal.emit(versions, on_success)
                else:
                    self.version_loaded_signal.emit(
                        None, lambda v: loading_label.setText("No versions found")
                    )
            except Exception as e:
                self.version_loaded_signal.emit(
                    None, lambda v: loading_label.setText(f"Error: {e}")
                )

        threading.Thread(target=load, daemon=True).start()

    def _load_curseforge_versions(self, mp: dict, project_id: str) -> list:
        """Load CurseForge versions"""
        curseforge_id = mp.get("_curseforge_id")
        if not curseforge_id:
            curseforge_id = int(project_id)

        if self.modpack_manager.curseforge_api is None:
            from ...core.api import CurseForgeAPI
            self.modpack_manager.curseforge_api = CurseForgeAPI()

        files = self.modpack_manager.curseforge_api.get_modpack_files(curseforge_id)
        if not files:
            return []

        versions = []
        for f in files:
            server_pack_file_id = f.get("serverPackFileId")
            if not server_pack_file_id:
                continue

            loader = "unknown"
            file_name = f.get("fileName", "").lower()
            game_versions_raw = f.get("gameVersions", [])

            mc_versions = []
            for gv in game_versions_raw:
                gv_lower = gv.lower()
                if gv_lower in ("forge", "neoforge", "fabric", "quilt"):
                    loader = gv_lower
                elif gv and gv[0].isdigit():
                    mc_versions.append(gv)

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
                "_server_pack_file_id": server_pack_file_id
            })

        return versions

    def _on_versions_loaded(self, versions, callback):
        """Handle versions loaded from thread"""
        if callback:
            callback(versions)

    # ============================================================
    # Folder Selection
    # ============================================================

    def _select_folder(self):
        """Handle folder selection"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            if not self._warn_dangerous_folder(folder):
                return
            if not self._warn_existing_server(folder):
                return
            self.modpack_folder = folder
            self.folder_label.setText(f"Folder: {folder}")
            self._update_install_btn()

    def _update_install_btn(self):
        """Update install button state"""
        self.install_btn.setEnabled(bool(self.selected_modpack and self.modpack_folder))

    # ============================================================
    # Installation
    # ============================================================

    def _install_modpack(self):
        """Start modpack installation"""
        print("[DEBUG] _install_modpack: INICIO", flush=True)
        if not self.selected_modpack or not self.modpack_folder:
            return

        project_id = self.selected_modpack.get("project_id", "")
        version_id = self.selected_mp_version.get("id", "") if self.selected_mp_version else None
        mp_name = self.selected_modpack.get("title", "Unknown")
        source = self.selected_modpack.get("source", "modrinth")
        print(f"[DEBUG] Modpack: {mp_name}, source: {source}", flush=True)

        version_info = self.selected_mp_version or {}
        game_versions = version_info.get("game_versions", [])
        mc_versions = [v for v in game_versions if v and v[0].isdigit()]
        mc_version = mc_versions[0] if mc_versions else (game_versions[0] if game_versions else "Unknown")
        loaders = version_info.get("loaders", ["Unknown"])
        loader_type = loaders[0] if loaders else "Unknown"

        # Check Java compatibility BEFORE starting the thread (shows modal if needed)
        print("[DEBUG] Verificando Java...", flush=True)
        java_executable = None
        if mc_version and mc_version != "Unknown" and self._check_and_get_java:
            java_executable = self._check_and_get_java(mc_version)
            print(f"[DEBUG] Java = {java_executable}", flush=True)
            if not java_executable:
                return  # User cancelled or Java install failed

        self.install_btn.setEnabled(False)
        print("[DEBUG] Lanzando thread de instalacion...", flush=True)

        def install():
            print("[DEBUG] THREAD: Inicio instalacion", flush=True)
            try:
                self._emit_log(f"\nInstalling {mp_name}...\n", "info")

                if source == "curseforge":
                    print("[DEBUG] THREAD: Instalando CurseForge...", flush=True)
                    success = self._install_curseforge(project_id, version_info, java_executable)
                else:
                    print("[DEBUG] THREAD: Instalando Modrinth...", flush=True)
                    success = self.modpack_manager.install_modrinth_modpack(
                        project_id, version_id, self.modpack_folder,
                        log_callback=lambda m: self._emit_log(m, "normal"),
                        java_executable=java_executable
                    )

                print(f"[DEBUG] THREAD: Resultado = {success}", flush=True)
                if success:
                    self._emit_log("\n" + "="*50 + "\n", "success")
                    self._emit_log("MODPACK INSTALLED SUCCESSFULLY\n", "success")
                    self._emit_log("="*50 + "\n", "success")
                    print("[DEBUG] THREAD: Emitiendo signal...", flush=True)
                    self.install_success.emit(mp_name, mc_version, loader_type)
                    print("[DEBUG] THREAD: Signal emitida", flush=True)
                else:
                    self._emit_log("Installation failed\n", "error")

            except Exception as e:
                print(f"[DEBUG] THREAD: ERROR: {e}", flush=True)
                self._emit_log(f"Error: {e}\n", "error")

            finally:
                print("[DEBUG] THREAD: Finally...", flush=True)
                QTimer.singleShot(0, lambda: self.install_btn.setEnabled(True))
                print("[DEBUG] THREAD: FIN", flush=True)

        threading.Thread(target=install, daemon=True).start()
        print("[DEBUG] Thread lanzado", flush=True)

    def _install_curseforge(self, project_id: str, version_info: dict, java_executable: str = None) -> bool:
        """Install CurseForge modpack"""
        curseforge_id = self.selected_modpack.get("_curseforge_id")
        if not curseforge_id:
            curseforge_id = int(project_id)

        curseforge_file = version_info.get("_curseforge_file", {})
        file_id = curseforge_file.get("id") if curseforge_file else int(version_info.get("id", ""))

        if self.modpack_manager.curseforge_api is None:
            from ...core.api import CurseForgeAPI
            self.modpack_manager.curseforge_api = CurseForgeAPI()

        return self.modpack_manager.install_curseforge_modpack(
            curseforge_id, file_id, self.modpack_folder,
            log_callback=lambda m: self._emit_log(m, "normal"),
            java_executable=java_executable
        )

    def _emit_log(self, msg: str, level: str):
        """Add log message to thread-safe buffer (processed by timer in main thread)"""
        with self._log_lock:
            self._thread_log_buffer.append((msg, level))

    # ============================================================
    # Public Methods
    # ============================================================

    def get_selected_modpack(self):
        """Return selected modpack"""
        return self.selected_modpack

    def get_modpack_folder(self):
        """Return modpack folder"""
        return self.modpack_folder
