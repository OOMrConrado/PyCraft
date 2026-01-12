"""
Navigation Controller for PyCraft GUI.
Handles page navigation and sidebar state management.
"""

from typing import Dict, Optional
from PySide6.QtWidgets import QStackedWidget, QWidget


class NavigationController:
    """
    Handles page navigation and sidebar state management.

    This controller centralizes navigation logic, making it easier to:
    - Switch between pages in the QStackedWidget
    - Update sidebar button states
    - Show/hide footer based on current page
    - Manage notification indicators
    """

    # Page ID to index mapping
    PAGE_MAP = {
        "home": 0,
        "vanilla": 1,
        "modded": 2,
        "info": 3,
        "settings": 4,
        "vanilla_create": 5,
        "vanilla_run": 6,
        "modpack_install": 7,
        "modpack_run": 8,
        "client_install": 9,
        "java": 10,
    }

    # Page ID to sidebar button mapping (which button should be highlighted)
    SIDEBAR_MAP = {
        "home": "home",
        "vanilla": "vanilla",
        "vanilla_create": "vanilla",
        "vanilla_run": "vanilla",
        "modded": "modded",
        "modpack_install": "modded",
        "modpack_run": "modded",
        "client_install": "modded",
        "info": "info",
        "settings": "settings",
        "java": "java",
    }

    # Pages where footer should be visible
    FOOTER_PAGES = {"home"}

    def __init__(
        self,
        page_stack: QStackedWidget,
        sidebar_buttons: Dict[str, QWidget],
        footer: Optional[QWidget] = None,
    ):
        """
        Initialize the navigation controller.

        Args:
            page_stack: The QStackedWidget containing all pages
            sidebar_buttons: Dict mapping button IDs to SidebarButton widgets
            footer: Optional footer widget to show/hide based on page
        """
        self.page_stack = page_stack
        self.sidebar_buttons = sidebar_buttons
        self.footer = footer
        self.current_page = "home"

    def navigate_to(self, page_id: str) -> bool:
        """
        Navigate to a specific page.

        Args:
            page_id: The ID of the page to navigate to

        Returns:
            True if navigation was successful, False otherwise
        """
        if page_id not in self.PAGE_MAP:
            return False

        # Update current page
        self.current_page = page_id

        # Switch the stacked widget
        self.page_stack.setCurrentIndex(self.PAGE_MAP[page_id])

        # Update sidebar button states
        sidebar_id = self.SIDEBAR_MAP.get(page_id)
        for btn_id, button in self.sidebar_buttons.items():
            button.setChecked(btn_id == sidebar_id)

        # Show/hide footer
        if self.footer:
            self.footer.setVisible(page_id in self.FOOTER_PAGES)

        return True

    def get_current_page(self) -> str:
        """Get the current page ID."""
        return self.current_page

    def get_page_index(self, page_id: str) -> int:
        """Get the index for a page ID, or -1 if not found."""
        return self.PAGE_MAP.get(page_id, -1)
