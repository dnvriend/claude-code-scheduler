"""
TaskItemWidget - Individual task item in the task list.

Displays task with toggle, name, model badge, schedule info,
status indicator, and action buttons.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from uuid import UUID

from PyQt6.QtCore import QMimeData, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QDrag, QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from claude_code_scheduler.models.enums import RunStatus
from claude_code_scheduler.models.profile import Profile
from claude_code_scheduler.models.run import Run
from claude_code_scheduler.models.task import Task


class ClickableLabel(QLabel):
    """QLabel that emits a signal when clicked."""

    clicked = pyqtSignal()

    def mousePressEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """Emit clicked signal on mouse press."""
        super().mousePressEvent(event)
        self.clicked.emit()


class TaskRunStats:
    """Statistics for task runs."""

    def __init__(
        self, running: int = 0, success: int = 0, failed: int = 0, cancelled: int = 0
    ) -> None:
        self.running = running
        self.success = success
        self.failed = failed
        self.cancelled = cancelled

    @classmethod
    def from_runs(cls, runs: list[Run]) -> TaskRunStats:
        """Calculate statistics from a list of runs."""
        running = sum(1 for r in runs if r.status == RunStatus.RUNNING)
        success = sum(1 for r in runs if r.status == RunStatus.SUCCESS)
        failed = sum(1 for r in runs if r.status == RunStatus.FAILED)
        cancelled = sum(1 for r in runs if r.status == RunStatus.CANCELLED)
        return cls(running=running, success=success, failed=failed, cancelled=cancelled)

    def format_short(self) -> str:
        """Format as short string: 0R,0S,0F,0C."""
        return f"{self.running}R,{self.success}S,{self.failed}F,{self.cancelled}C"


class TaskItemWidget(QFrame):
    """Widget representing a single task in the task list."""

    # Signals
    clicked = pyqtSignal(UUID)  # Task selected
    toggled = pyqtSignal(UUID, bool)  # Task enabled/disabled
    run_requested = pyqtSignal(UUID)  # Run now button clicked
    stop_requested = pyqtSignal(UUID)  # Stop button clicked (run_id)
    duplicate_requested = pyqtSignal(UUID)  # Duplicate button clicked
    delete_requested = pyqtSignal(UUID)  # Delete button clicked

    # Drag-and-drop MIME type for task reordering
    MIME_TYPE = "application/x-claude-scheduler-task"

    def __init__(
        self,
        task: Task,
        profiles: list[Profile] | None = None,
        runs: list[Run] | None = None,
        drag_enabled: bool = False,
    ) -> None:
        super().__init__()
        self.task = task
        self.profiles: list[Profile] = profiles or []
        self._runs: list[Run] = runs or []
        self._selected = False
        self._drag_enabled = drag_enabled
        self._drag_start_pos: QPoint | None = None
        self.setObjectName("taskItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
        self._update_display()

    def _setup_ui(self) -> None:
        """Set up the widget layout."""
        self.setFrameShape(QFrame.Shape.StyledPanel)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(6)

        # Top row: Status icon, Name, Model badge
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Status icon (clickable to toggle enabled/disabled)
        self.status_icon = ClickableLabel()
        self.status_icon.setObjectName("statusIcon")
        self.status_icon.setFixedWidth(24)
        self.status_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_icon.setToolTip("Click to toggle enabled/disabled")
        self.status_icon.clicked.connect(self._on_status_icon_clicked)
        top_row.addWidget(self.status_icon)

        # Task name
        self.name_label = QLabel()
        self.name_label.setObjectName("taskName")
        top_row.addWidget(self.name_label, 1)

        # Model badge
        self.model_badge = QLabel()
        self.model_badge.setObjectName("modelBadge")
        self.model_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self.model_badge)

        # Profile badge
        self.profile_badge = QLabel()
        self.profile_badge.setObjectName("profileBadge")
        self.profile_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self.profile_badge)

        main_layout.addLayout(top_row)

        # Middle row: Schedule description
        self.schedule_label = QLabel()
        self.schedule_label.setObjectName("scheduleLabel")
        main_layout.addWidget(self.schedule_label)

        # Run statistics row (0R,0S,0F,0C)
        self.stats_label = QLabel()
        self.stats_label.setObjectName("statsLabel")
        main_layout.addWidget(self.stats_label)

        # Bottom row: Action buttons
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)
        bottom_row.addStretch()

        # Action buttons
        self.run_btn = QPushButton("▶")
        self.run_btn.setObjectName("actionButton")
        self.run_btn.setToolTip("Run now")
        self.run_btn.setFixedSize(28, 28)
        self.run_btn.clicked.connect(self._on_run_clicked)
        bottom_row.addWidget(self.run_btn)

        self.duplicate_btn = QPushButton("📋")
        self.duplicate_btn.setObjectName("actionButton")
        self.duplicate_btn.setToolTip("Duplicate")
        self.duplicate_btn.setFixedSize(28, 28)
        self.duplicate_btn.clicked.connect(self._on_duplicate_clicked)
        bottom_row.addWidget(self.duplicate_btn)

        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setObjectName("actionButton")
        self.delete_btn.setToolTip("Delete")
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        bottom_row.addWidget(self.delete_btn)

        main_layout.addLayout(bottom_row)

    def _update_display(self) -> None:
        """Update the display based on task data."""
        self._update_status_icon()

        self.name_label.setText(self.task.name)

        # Model badge
        model_text = self.task.model.capitalize()
        self.model_badge.setText(model_text)
        self.model_badge.setProperty("model", self.task.model)

        # Profile badge
        profile_name = self._get_profile_name()
        if profile_name:
            self.profile_badge.setText(profile_name)
            self.profile_badge.setVisible(True)
        else:
            self.profile_badge.setVisible(False)

        # Schedule description
        schedule_text = self._get_schedule_description()
        self.schedule_label.setText(schedule_text)

        # Run statistics (0R,0S,0F,0C)
        stats = TaskRunStats.from_runs(self._runs)
        self.stats_label.setText(stats.format_short())

    def _get_schedule_description(self) -> str:
        """Get human-readable schedule description."""
        sched = self.task.schedule
        stype = sched.schedule_type.value

        if stype == "manual":
            return "Manual (run on demand)"
        elif stype == "startup":
            return "Runs on startup"
        elif stype == "calendar":
            freq = sched.calendar_frequency or "daily"
            time_str = sched.calendar_time.strftime("%H:%M") if sched.calendar_time else "00:00"
            if freq == "daily":
                return f"Daily at {time_str}"
            elif freq == "weekly":
                days = sched.calendar_days_of_week or [0]
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                day_str = ", ".join(day_names[d] for d in days)
                return f"Weekly on {day_str} at {time_str}"
            elif freq == "monthly":
                day = sched.calendar_day_of_month or 1
                return f"Monthly on day {day} at {time_str}"
        elif stype == "interval":
            if sched.interval_type and sched.interval_type.value == "cron":
                return f"Cron: {sched.interval_cron or '* * * * *'}"
            elif sched.interval_preset:
                return f"Every {sched.interval_preset}"
            elif sched.interval_value and sched.interval_unit:
                return f"Every {sched.interval_value} {sched.interval_unit}"
        elif stype == "file_watch":
            dir_path = sched.watch_directory or "~"
            return f"On file change in {dir_path}"
        elif stype == "sequential":
            return "Sequential (runs in job order)"

        return "Unknown schedule"

    def _update_status_icon(self) -> None:
        """Update status icon based on task state and run status.

        Icon meanings:
        - ○ (gray): Disabled
        - ● (green): Enabled, ready
        - ◐ (blue): Running
        - ✗ (red): Last run failed
        """
        # Check if currently running
        is_running = any(r.status == RunStatus.RUNNING for r in self._runs)
        last_failed = self.task.last_run_status == "failed"

        if is_running:
            # Running - blue half circle
            self.status_icon.setText("◐")
            self.status_icon.setStyleSheet("color: #4A9EFF; font-size: 18px;")
        elif not self.task.enabled:
            # Disabled - gray empty circle
            self.status_icon.setText("○")
            self.status_icon.setStyleSheet("color: #888888; font-size: 18px;")
        elif last_failed:
            # Enabled but last run failed - red X
            self.status_icon.setText("✗")
            self.status_icon.setStyleSheet("color: #F44336; font-size: 18px;")
        else:
            # Enabled and ready - green filled circle
            self.status_icon.setText("●")
            self.status_icon.setStyleSheet("color: #4CAF50; font-size: 18px;")

    def set_selected(self, selected: bool) -> None:
        """Set the selection state of this item."""
        self._selected = selected
        self.setProperty("selected", selected)
        style = self.style()
        if style:
            style.unpolish(self)
            style.polish(self)

    def update_task(
        self,
        task: Task,
        profiles: list[Profile] | None = None,
        runs: list[Run] | None = None,
    ) -> None:
        """Update the displayed task."""
        self.task = task
        if profiles is not None:
            self.profiles = profiles
        if runs is not None:
            self._runs = runs
        self._update_display()

    def update_runs(self, runs: list[Run]) -> None:
        """Update the run statistics and status icon for this task."""
        self._runs = runs
        stats = TaskRunStats.from_runs(self._runs)
        self.stats_label.setText(stats.format_short())
        # Update status icon to reflect running state
        self._update_status_icon()
        # Update run/stop button state
        self._update_run_button()

    def _get_profile_name(self) -> str | None:
        """Get the profile name for this task."""
        if not self.task.profile:
            return None
        try:
            target_id = UUID(self.task.profile)
            for profile in self.profiles:
                if profile.id == target_id:
                    return profile.name
        except ValueError:
            pass
        return None

    def set_drag_enabled(self, enabled: bool) -> None:
        """Enable or disable drag-and-drop for this item."""
        self._drag_enabled = enabled

    def mousePressEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """Handle mouse press to emit clicked signal and start drag tracking."""
        if event and self._drag_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)
        self.clicked.emit(self.task.id)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """Handle mouse move to initiate drag if threshold exceeded."""
        if not event or not self._drag_enabled or not self._drag_start_pos:
            return

        # Check if we've moved far enough to start a drag
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return

        # Create drag operation
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(self.MIME_TYPE, str(self.task.id).encode())
        drag.setMimeData(mime_data)

        # Create a pixmap of this widget for the drag preview
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())

        # Execute drag
        drag.exec(Qt.DropAction.MoveAction)
        self._drag_start_pos = None

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """Handle mouse release to reset drag state."""
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def _on_status_icon_clicked(self) -> None:
        """Handle status icon click to toggle enabled state."""
        new_enabled = not self.task.enabled
        self.task.enabled = new_enabled
        self._update_status_icon()
        self.toggled.emit(self.task.id, new_enabled)

    def _update_run_button(self) -> None:
        """Update run/stop button based on running state."""
        is_running = any(r.status == RunStatus.RUNNING for r in self._runs)
        if is_running:
            self.run_btn.setText("⏹")
            self.run_btn.setToolTip("Stop running task")
        else:
            self.run_btn.setText("▶")
            self.run_btn.setToolTip("Run now")

    def _get_running_run_id(self) -> UUID | None:
        """Get the ID of the currently running run, if any."""
        for run in self._runs:
            if run.status == RunStatus.RUNNING:
                return run.id
        return None

    def _on_run_clicked(self) -> None:
        """Handle run/stop button click."""
        running_run_id = self._get_running_run_id()
        if running_run_id:
            self.stop_requested.emit(running_run_id)
        else:
            self.run_requested.emit(self.task.id)

    def _on_duplicate_clicked(self) -> None:
        """Handle duplicate button click."""
        self.duplicate_requested.emit(self.task.id)

    def _on_delete_clicked(self) -> None:
        """Handle delete button click."""
        self.delete_requested.emit(self.task.id)
