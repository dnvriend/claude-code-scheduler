"""
JobItemWidget - Individual job item in the jobs list.

Displays job with status icon, name, task count, and action buttons (edit, delete).

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from uuid import UUID

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QContextMenuEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
)

from claude_code_scheduler.models.enums import JobStatus
from claude_code_scheduler.models.job import Job


class JobItemWidget(QFrame):
    """Widget representing a single job in the jobs list."""

    # Signals
    clicked = pyqtSignal(UUID)  # Job selected
    run_requested = pyqtSignal(UUID)  # Run button clicked
    stop_requested = pyqtSignal(UUID)  # Stop button clicked
    edit_requested = pyqtSignal(UUID)  # Edit button clicked
    delete_requested = pyqtSignal(UUID)  # Delete button clicked
    export_requested = pyqtSignal(UUID)  # Export button clicked

    def __init__(self, job: Job, task_count: int = 0) -> None:
        super().__init__()
        self.job = job
        self.task_count = task_count
        self._selected = False
        self.setObjectName("jobItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
        self._update_display()

    def _setup_ui(self) -> None:
        """Set up the widget layout."""
        self.setFrameShape(QFrame.Shape.StyledPanel)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(6)

        # Top row: Status icon, Name, Task count badge
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Status icon
        self.status_icon = QLabel()
        self.status_icon.setObjectName("statusIcon")
        self.status_icon.setFixedWidth(20)
        top_row.addWidget(self.status_icon)

        # Job name
        self.name_label = QLabel()
        self.name_label.setObjectName("jobName")
        top_row.addWidget(self.name_label, 1)

        # Task count badge
        self.count_badge = QLabel()
        self.count_badge.setObjectName("countBadge")
        self.count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self.count_badge)

        main_layout.addLayout(top_row)

        # Bottom row: Description + Action buttons
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        # Description (truncated)
        self.description_label = QLabel()
        self.description_label.setObjectName("descriptionLabel")
        bottom_row.addWidget(self.description_label, 1)

        # Action buttons
        self.run_btn = QPushButton("▶")
        self.run_btn.setObjectName("actionButton")
        self.run_btn.setToolTip("Run job sequence")
        self.run_btn.setFixedSize(28, 28)
        self.run_btn.clicked.connect(self._on_run_clicked)
        bottom_row.addWidget(self.run_btn)

        self.stop_btn = QPushButton("■")
        self.stop_btn.setObjectName("actionButton")
        self.stop_btn.setToolTip("Stop job")
        self.stop_btn.setFixedSize(28, 28)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn.setStyleSheet("color: #F44336;")  # Red for stop
        bottom_row.addWidget(self.stop_btn)

        self.edit_btn = QPushButton("✏️")
        self.edit_btn.setObjectName("actionButton")
        self.edit_btn.setToolTip("Edit job")
        self.edit_btn.setFixedSize(28, 28)
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        bottom_row.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setObjectName("actionButton")
        self.delete_btn.setToolTip("Delete job")
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        bottom_row.addWidget(self.delete_btn)

        main_layout.addLayout(bottom_row)

    def _update_display(self) -> None:
        """Update the display based on job data."""
        # Status icon based on job status
        status_icons = {
            JobStatus.PENDING: "○",
            JobStatus.IN_PROGRESS: "◐",
            JobStatus.COMPLETED: "●",
            JobStatus.FAILED: "✗",
        }
        self.status_icon.setText(status_icons.get(self.job.status, "○"))

        # Apply status-specific styling
        status_colors = {
            JobStatus.PENDING: "#888888",
            JobStatus.IN_PROGRESS: "#4A9EFF",
            JobStatus.COMPLETED: "#4CAF50",
            JobStatus.FAILED: "#F44336",
        }
        color = status_colors.get(self.job.status, "#888888")
        self.status_icon.setStyleSheet(f"color: {color}; font-size: 16px;")

        # Job name
        self.name_label.setText(self.job.name)

        # Task count badge
        self.count_badge.setText(f"{self.task_count} tasks")

        # Description (truncated to 50 chars)
        desc = self.job.description or ""
        if len(desc) > 50:
            desc = desc[:47] + "..."
        self.description_label.setText(desc)

        # Show/hide buttons based on status
        is_running = self.job.status == JobStatus.IN_PROGRESS
        self.run_btn.setVisible(not is_running)
        self.stop_btn.setVisible(is_running)

    def set_selected(self, selected: bool) -> None:
        """Set the selection state of this item."""
        self._selected = selected
        self.setProperty("selected", selected)
        style = self.style()
        if style:
            style.unpolish(self)
            style.polish(self)

    def update_job(self, job: Job, task_count: int | None = None) -> None:
        """Update the displayed job."""
        self.job = job
        if task_count is not None:
            self.task_count = task_count
        self._update_display()

    def mousePressEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """Handle mouse press to emit clicked signal."""
        super().mousePressEvent(event)
        self.clicked.emit(self.job.id)

    def contextMenuEvent(self, event: QContextMenuEvent | None) -> None:  # noqa: N802
        """Show context menu on right-click."""
        if event is None:
            return

        menu = QMenu(self)

        # Export action
        export_action = menu.addAction("Export...")
        if export_action is not None:
            export_action.triggered.connect(lambda: self.export_requested.emit(self.job.id))

        # Add separator
        menu.addSeparator()

        # Add other actions for consistency
        edit_action = menu.addAction("Edit")
        if edit_action is not None:
            edit_action.triggered.connect(lambda: self.edit_requested.emit(self.job.id))

        delete_action = menu.addAction("Delete")
        if delete_action is not None:
            delete_action.triggered.connect(lambda: self.delete_requested.emit(self.job.id))

        # Show menu at cursor position
        menu.exec(event.globalPos())

    def _on_run_clicked(self) -> None:
        """Handle run button click."""
        self.run_requested.emit(self.job.id)

    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        self.stop_requested.emit(self.job.id)

    def _on_edit_clicked(self) -> None:
        """Handle edit button click."""
        self.edit_requested.emit(self.job.id)

    def _on_delete_clicked(self) -> None:
        """Handle delete button click."""
        self.delete_requested.emit(self.job.id)
