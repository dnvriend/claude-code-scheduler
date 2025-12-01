"""
Collapsible Widget with triangle indicator.

A container widget that can be collapsed/expanded with a clickable header.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class CollapsibleWidget(QFrame):
    """A widget with a collapsible content area and triangle indicator."""

    toggled = pyqtSignal(bool)  # True when expanded

    def __init__(self, title: str, collapsed: bool = True) -> None:
        super().__init__()
        self.setObjectName("collapsibleWidget")
        self._collapsed = collapsed
        self._title = title
        self._setup_ui()
        self._update_state()

    def _setup_ui(self) -> None:
        """Set up the widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header (clickable)
        self.header = QWidget()
        self.header.setObjectName("collapsibleHeader")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 8, 0, 8)
        header_layout.setSpacing(8)

        # Triangle indicator
        self.triangle = QLabel()
        self.triangle.setObjectName("collapsibleTriangle")
        self.triangle.setFixedWidth(16)
        header_layout.addWidget(self.triangle)

        # Title
        self.title_label = QLabel(self._title)
        self.title_label.setObjectName("collapsibleTitle")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        layout.addWidget(self.header)

        # Content container
        self.content = QWidget()
        self.content.setObjectName("collapsibleContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(24, 8, 0, 8)
        self.content_layout.setSpacing(0)

        layout.addWidget(self.content)

    def _update_state(self) -> None:
        """Update the visual state based on collapsed/expanded."""
        if self._collapsed:
            self.triangle.setText("\u25b6")  # Right-pointing triangle
            self.content.hide()
        else:
            self.triangle.setText("\u25bc")  # Down-pointing triangle
            self.content.show()

    def mousePressEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """Handle mouse press on header."""
        if event and event.button() == Qt.MouseButton.LeftButton:
            # Check if click is in header area
            header_rect = self.header.geometry()
            if header_rect.contains(event.pos()):
                self.toggle()
        super().mousePressEvent(event)

    def toggle(self) -> None:
        """Toggle the collapsed/expanded state."""
        self._collapsed = not self._collapsed
        self._update_state()
        self.toggled.emit(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        """Set the collapsed state."""
        self._collapsed = collapsed
        self._update_state()

    def is_collapsed(self) -> bool:
        """Check if widget is collapsed."""
        return self._collapsed

    def set_content_widget(self, widget: QWidget) -> None:
        """Set the content widget to display when expanded."""
        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.setParent(None)

        self.content_layout.addWidget(widget)
