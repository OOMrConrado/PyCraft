"""
Non-propagating scroll area widgets.
Prevents scroll events from bubbling up to parent when at scroll limits.
"""

from PySide6.QtWidgets import QScrollArea, QTextEdit


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
