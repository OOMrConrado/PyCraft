"""
Custom styles and style generators for PyCraft GUI.
"""

from PySide6.QtWidgets import QStyle, QProxyStyle


class NoFocusRectStyle(QProxyStyle):
    """Custom style that removes focus rectangles from all widgets"""

    def drawPrimitive(self, element, option, painter, widget=None):
        # Skip drawing focus rectangles
        if element == QStyle.PrimitiveElement.PE_FrameFocusRect:
            return
        super().drawPrimitive(element, option, painter, widget)


class StyleGenerator:
    """Generates consistent CSS stylesheets for common widgets"""

    @staticmethod
    def scroll_style(colors: dict) -> str:
        """Generate stylesheet for scroll areas"""
        return f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {colors['bg_card']};
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

    @staticmethod
    def progress_style(colors: dict) -> str:
        """Generate stylesheet for progress bars"""
        return f"""
            QProgressBar {{
                background-color: {colors['bg_input']};
                border: none;
                border-radius: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {colors['accent']};
                border-radius: 6px;
            }}
        """
