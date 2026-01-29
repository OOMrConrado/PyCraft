"""
Client Install Controller - Handles client modpack browsing UI and logic.
"""

import threading
from typing import Dict, Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QCursor, QPixmap

import qtawesome as qta

from ..widgets import NonPropagatingScrollArea
from ..pages.base_page import BasePage


class ClientInstallController(BasePage):
    """
    Controller for the Client Modpack Browsing page.

    Handles:
    - Provider selection (Modrinth, CurseForge)
    - Modpack search with debounce
    - Pagination
    - Results display
    """

    # Signals
    results_signal = Signal(object)  # search results
    pagination_signal = Signal(int)  # total results

    def __init__(
        self,
        colors: Dict[str, str],
        modpack_manager,
        navigate_callback: Optional[Callable[[str], None]] = None,
        log_signal=None,
        parent=None
    ):
        super().__init__(colors, navigate_callback, parent)

        # Dependencies
        self.modpack_manager = modpack_manager
        self.log_signal = log_signal

        # State
        self.results = []
        self.current_page = 1
        self.total_results = 0
        self.search_query = ""
        self.selected_provider = "modrinth"
        self.is_popular_search = False
        self.icon_cache = {}

        # Debounce timer
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self._search_modpacks)

        # Connect signals
        self.results_signal.connect(self._show_results)
        self.pagination_signal.connect(self._update_pagination)

        self._build_ui()

    def _build_ui(self):
        """Build the client modpack browsing UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget for provider selection / search UI
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")

        # === Page 0: Provider Selection ===
        self.stack.addWidget(self._build_provider_page())

        # === Page 1: Search UI ===
        self.stack.addWidget(self._build_search_page())

        layout.addWidget(self.stack)

    def _build_provider_page(self) -> QWidget:
        """Build provider selection page"""
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
        title = QLabel("Browse Modpacks (Client)")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        layout.addStretch(2)

        # Provider selection prompt
        prompt = QLabel("Choose a modpack provider:")
        prompt.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 15px;")
        prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(prompt)

        # Provider buttons
        providers = QWidget()
        providers.setStyleSheet("background: transparent;")
        h_layout = QHBoxLayout(providers)
        h_layout.setSpacing(24)
        h_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        modrinth_btn = self._create_provider_button(
            "Modrinth", "Open-source modding platform", "#1bd96a", "fa5s.leaf"
        )
        modrinth_btn.clicked.connect(lambda: self._select_provider("modrinth"))
        h_layout.addWidget(modrinth_btn)

        curseforge_btn = self._create_provider_button(
            "CurseForge", "Largest mod collection", "#f16436", "fa5s.fire"
        )
        curseforge_btn.clicked.connect(lambda: self._select_provider("curseforge"))
        h_layout.addWidget(curseforge_btn)

        layout.addWidget(providers)
        layout.addStretch(3)

        return page

    def _build_search_page(self) -> QWidget:
        """Build search page with results"""
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
        back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(back)

        # Title
        title = QLabel("Browse Modpacks (Client)")
        title.setStyleSheet(f"color: {self.colors['text']}; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        # Provider indicator
        provider_row = QWidget()
        provider_row.setStyleSheet("background: transparent;")
        pr_layout = QHBoxLayout(provider_row)
        pr_layout.setContentsMargins(0, 0, 0, 8)

        self.provider_label = QLabel("Searching on: Modrinth")
        self.provider_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px;")
        pr_layout.addWidget(self.provider_label)

        change_btn = self._text_button("Change")
        change_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        pr_layout.addWidget(change_btn)
        pr_layout.addStretch()

        layout.addWidget(provider_row)

        # Search section
        search_frame = self._section_frame("Search Modpacks")
        search_layout = search_frame.layout()

        self.search_input = self._input("Search modpacks...", 560)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input)

        results_label = QLabel("Results:")
        results_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 13px; font-weight: 600;")
        search_layout.addWidget(results_label)

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

        search_layout.addWidget(self.results_scroll)

        # Pagination
        self.pagination_widget = QWidget()
        self.pagination_widget.setStyleSheet("background: transparent;")
        self.pagination_widget.setVisible(False)
        pag_layout = QHBoxLayout(self.pagination_widget)
        pag_layout.setContentsMargins(0, 5, 0, 5)
        pag_layout.setSpacing(5)

        self.page_info = QLabel("")
        self.page_info.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        pag_layout.addWidget(self.page_info)

        pag_layout.addStretch()

        self.prev_btn = self._nav_button("<")
        self.prev_btn.clicked.connect(lambda: self._go_page(self.current_page - 1))
        pag_layout.addWidget(self.prev_btn)

        self.page_btns_layout = QHBoxLayout()
        self.page_btns_layout.setSpacing(3)
        pag_layout.addLayout(self.page_btns_layout)

        self.next_btn = self._nav_button(">")
        self.next_btn.clicked.connect(lambda: self._go_page(self.current_page + 1))
        pag_layout.addWidget(self.next_btn)

        search_layout.addWidget(self.pagination_widget)
        layout.addWidget(search_frame)

        layout.addStretch()
        scroll.setWidget(content)

        return scroll

    def _create_provider_button(self, name: str, desc: str, color: str, icon: str) -> QPushButton:
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
        btn_layout.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon, color=color).pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(icon_label)

        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {self.colors['text']}; font-size: 16px; font-weight: 600;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(name_label)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(desc_label)

        return btn

    def _nav_button(self, text: str) -> QPushButton:
        """Create a navigation button"""
        btn = QPushButton(text)
        btn.setFixedSize(32, 32)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
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
        self.pagination_widget.setVisible(False)

        # Switch to search page
        self.stack.setCurrentIndex(1)

        # Load popular modpacks
        self._search_modpacks(page=1, popular=True)

    def _clear_results(self):
        """Clear results layout"""
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    # ============================================================
    # Search
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
                    side_filter="client"
                )
                self.results = results

                if results:
                    self.pagination_signal.emit(total)
                    self.results_signal.emit(results)
                else:
                    self.pagination_signal.emit(0)

            except Exception as e:
                if self.log_signal:
                    self.log_signal.emit(f"Error: {e}\n", "error", "c_install")

        threading.Thread(target=search, daemon=True).start()

    def _go_page(self, page: int):
        """Navigate to page"""
        total_pages = (self.total_results + 9) // 10
        if 1 <= page <= total_pages:
            self._search_modpacks(page, popular=self.is_popular_search)

    # ============================================================
    # Results Display
    # ============================================================

    def _update_pagination(self, total: int):
        """Update pagination UI"""
        self.total_results = total
        total_pages = (total + 9) // 10

        if total_pages <= 1:
            self.pagination_widget.setVisible(False)
            return

        self.pagination_widget.setVisible(True)
        self.page_info.setText(f"{total} results")

        # Clear existing page buttons
        while self.page_btns_layout.count():
            child = self.page_btns_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Create page buttons
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
                QPushButton:hover {{ background-color: {self.colors['accent']}; color: #000000; }}
            """)
            btn.clicked.connect(lambda checked, page=p: self._go_page(page))
            self.page_btns_layout.addWidget(btn)

        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < total_pages)

    def _show_results(self, results: list):
        """Display search results"""
        for mp in results:
            self.results_layout.addWidget(self._create_result_item(mp))

    def _create_result_item(self, mp: dict) -> QFrame:
        """Create a modpack result item"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['bg_card']};
                border: 1px solid {self.colors['border']};
                border-radius: 10px;
            }}
            QFrame:hover {{
                border-color: {self.colors['accent']};
            }}
        """)
        frame.setFixedHeight(70)
        frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Icon
        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setStyleSheet(f"background: {self.colors['bg_input']}; border: none; border-radius: 8px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_url = mp.get("icon_url") or mp.get("logo", {}).get("thumbnailUrl", "")
        project_id = str(mp.get("project_id") or mp.get("id", ""))

        if icon_url and project_id:
            if project_id in self.icon_cache:
                icon_label.setPixmap(self.icon_cache[project_id])
            else:
                self._load_icon(icon_url, project_id, icon_label)

        layout.addWidget(icon_label)

        # Info
        info = QVBoxLayout()
        info.setSpacing(2)

        name = mp.get("title") or mp.get("name", "Unknown")
        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {self.colors['text']}; font-size: 13px; font-weight: 600; border: none;")
        info.addWidget(name_label)

        author = mp.get("author") or (mp.get("authors", [{}])[0].get("name", "") if mp.get("authors") else "")
        downloads = mp.get("downloads", 0)
        meta = f"by {author}" if author else ""
        if downloads:
            dl_str = self._format_downloads(downloads)
            meta = f"{meta} • {dl_str} downloads" if meta else f"{dl_str} downloads"

        meta_label = QLabel(meta)
        meta_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 11px; border: none;")
        info.addWidget(meta_label)

        layout.addLayout(info, 1)

        # Open button
        slug = mp.get("slug", "")
        if slug:
            open_btn = self._styled_button("Open", self.colors['accent'], "#000000", 80)
            open_btn.clicked.connect(lambda: self._open_modpack(slug))
            layout.addWidget(open_btn)

        return frame

    def _format_downloads(self, count: int) -> str:
        """Format download count"""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count / 1_000:.0f}K"
        return str(count)

    def _load_icon(self, url: str, project_id: str, label: QLabel):
        """Load icon from URL"""
        def load():
            try:
                import urllib.request
                req = urllib.request.Request(url, headers={'User-Agent': 'PyCraft/1.0'})
                data = urllib.request.urlopen(req, timeout=5).read()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.icon_cache[project_id] = scaled
                    # Use default arg to capture label reference
                    QTimer.singleShot(0, lambda lbl=label, px=scaled: lbl.setPixmap(px) if lbl else None)
            except Exception:
                pass

        threading.Thread(target=load, daemon=True).start()

    def _open_modpack(self, slug: str):
        """Open modpack page in browser"""
        import webbrowser
        if self.selected_provider == "modrinth":
            webbrowser.open(f"https://modrinth.com/modpack/{slug}")
        else:
            webbrowser.open(f"https://www.curseforge.com/minecraft/modpacks/{slug}")
