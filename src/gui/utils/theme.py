"""
PyCraft Theme Configuration.
Centralized color scheme and theme constants.
"""


class Theme:
    """Application color scheme and theme constants"""

    COLORS = {
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

    @classmethod
    def get_colors(cls) -> dict:
        """Get a copy of the color scheme dictionary"""
        return cls.COLORS.copy()
