"""
Run Item Widget for displaying a single run in the runs list.

Displays run status, timing info, and allows selection.

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
    QWidget,
)

from claude_code_scheduler.models.enums import RunStatus
from claude_code_scheduler.models.run import Run


class RunItemWidget(QFrame):
    """Widget representing a single run in the runs list."""

    clicked = pyqtSignal(UUID)
    delete_requested = pyqtSignal(UUID)
    stop_requested = pyqtSignal(UUID)
    restart_requested = pyqtSignal(UUID)
    open_session_clicked = pyqtSignal(UUID)
    open_log_directory_requested = pyqtSignal(UUID)
    run_in_terminal_requested = pyqtSignal(UUID)

    def __init__(self, run: Run) -> None:
        super().__init__()
        self.run = run
        self.setObjectName("runItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget layout."""
        self.setMinimumHeight(60)
        self.setMaximumHeight(80)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Status indicator (Unicode icon style, consistent with task/job items)
        self.status_indicator = QLabel()
        self.status_indicator.setObjectName("statusIndicator")
        self.status_indicator.setFixedWidth(24)
        self._update_status_indicator()
        layout.addWidget(self.status_indicator)

        # Main content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)

        # Task name and status
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        self.task_name_label = QLabel(self.run.task_name or "Unknown Task")
        self.task_name_label.setObjectName("runTaskName")
        top_layout.addWidget(self.task_name_label)

        self.status_badge = QLabel(self._get_status_text())
        self.status_badge.setObjectName("runStatusBadge")
        self.status_badge.setProperty("status", self.run.status.value)
        top_layout.addWidget(self.status_badge)

        top_layout.addStretch()
        content_layout.addWidget(top_row)

        # Time info
        self.time_label = QLabel(self._get_time_text())
        self.time_label.setObjectName("runTimeLabel")
        content_layout.addWidget(self.time_label)

        layout.addWidget(content, 1)

        # Duration (if completed)
        if self.run.duration:
            duration_text = self._format_duration()
            self.duration_label = QLabel(duration_text)
            self.duration_label.setObjectName("runDurationLabel")
            layout.addWidget(self.duration_label)

        # Stop button (only visible/enabled when running)
        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setObjectName("actionButton")
        self.stop_btn.setToolTip("Stop running task")
        self.stop_btn.setFixedSize(28, 28)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.stop_btn)

        # Restart button (only visible/enabled when not running)
        self.restart_btn = QPushButton("🔄")
        self.restart_btn.setObjectName("actionButton")
        self.restart_btn.setToolTip("Restart task")
        self.restart_btn.setFixedSize(28, 28)
        self.restart_btn.clicked.connect(self._on_restart_clicked)
        layout.addWidget(self.restart_btn)

        # Open session button (only visible when session_id is not None)
        self.open_session_btn = QPushButton("⎋")
        self.open_session_btn.setObjectName("actionButton")
        self.open_session_btn.setToolTip("Open session in iTerm")
        self.open_session_btn.setFixedSize(28, 28)
        self.open_session_btn.clicked.connect(self._on_open_session_clicked)
        layout.addWidget(self.open_session_btn)

        # Delete button (disabled when running)
        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setObjectName("actionButton")
        self.delete_btn.setToolTip("Delete run")
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self.delete_btn)

        # Apply initial button states
        self._update_button_states()

    def _update_status_indicator(self) -> None:
        """Update the status indicator icon.

        Uses Unicode symbols consistent with task/job items:
        - ○ (gray): Upcoming/scheduled
        - ◐ (orange): Running
        - ● (green): Success
        - ✗ (red): Failed
        - ◌ (gray): Cancelled
        """
        icons = {
            RunStatus.UPCOMING: ("○", "#3498db"),  # blue empty circle
            RunStatus.RUNNING: ("◐", "#f39c12"),  # orange half circle
            RunStatus.SUCCESS: ("●", "#27ae60"),  # green filled circle
            RunStatus.FAILED: ("✗", "#e74c3c"),  # red X
            RunStatus.CANCELLED: ("◌", "#95a5a6"),  # gray dashed circle
        }
        icon, color = icons.get(self.run.status, ("○", "#95a5a6"))
        self.status_indicator.setText(icon)
        self.status_indicator.setStyleSheet(f"color: {color}; font-size: 18px;")

    def _get_status_text(self) -> str:
        """Get human-readable status text."""
        return {
            RunStatus.UPCOMING: "Upcoming",
            RunStatus.RUNNING: "Running",
            RunStatus.SUCCESS: "Success",
            RunStatus.FAILED: "Failed",
            RunStatus.CANCELLED: "Cancelled",
        }.get(self.run.status, "Unknown")

    def _get_time_text(self) -> str:
        """Get time information text."""
        if self.run.status == RunStatus.UPCOMING:
            return f"Scheduled: {self.run.scheduled_time.strftime('%Y-%m-%d %H:%M')}"
        elif self.run.status == RunStatus.RUNNING:
            if self.run.start_time:
                return f"Started: {self.run.start_time.strftime('%H:%M:%S')}"
            return "Starting..."
        else:
            if self.run.end_time:
                return f"Completed: {self.run.end_time.strftime('%Y-%m-%d %H:%M')}"
            elif self.run.start_time:
                return f"Started: {self.run.start_time.strftime('%Y-%m-%d %H:%M')}"
            return f"Scheduled: {self.run.scheduled_time.strftime('%Y-%m-%d %H:%M')}"

    def _format_duration(self) -> str:
        """Format duration for display."""
        if not self.run.duration:
            return ""
        total_seconds = int(self.run.duration.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def mousePressEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        """Handle mouse press to emit clicked signal."""
        if event:
            self.clicked.emit(self.run.id)
        super().mousePressEvent(event)

    def _on_delete_clicked(self) -> None:
        """Handle delete button click."""
        self.delete_requested.emit(self.run.id)

    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        self.stop_requested.emit(self.run.id)

    def _on_restart_clicked(self) -> None:
        """Handle restart button click."""
        self.restart_requested.emit(self.run.id)

    def _on_open_session_clicked(self) -> None:
        """Handle open session button click."""
        self.open_session_clicked.emit(self.run.id)

    def contextMenuEvent(self, event: QContextMenuEvent | None) -> None:  # noqa: N802
        """Handle right-click context menu."""
        if event:
            menu = QMenu(self)

            # Open Log Directory action
            open_log_action = menu.addAction("📂 Open Log Directory")
            if open_log_action:
                open_log_action.setToolTip("Open the log directory in Finder")
                open_log_action.triggered.connect(self._on_open_log_directory)

            # Run in Terminal action
            run_terminal_action = menu.addAction("💻 Run in Terminal")
            if run_terminal_action:
                run_terminal_action.setToolTip("Run the task command in Terminal.app")
                run_terminal_action.triggered.connect(self._on_run_in_terminal)

            menu.addSeparator()

            # Standard actions
            if self.run.status == RunStatus.RUNNING:
                stop_action = menu.addAction("⏹ Stop")
                if stop_action:
                    stop_action.triggered.connect(self._on_stop_clicked)
            else:
                restart_action = menu.addAction("🔄 Restart")
                if restart_action:
                    restart_action.triggered.connect(self._on_restart_clicked)

                if self.run.session_id is not None:
                    open_session_action = menu.addAction("⎋ Open Session")
                    if open_session_action:
                        open_session_action.triggered.connect(self._on_open_session_clicked)

            if self.run.status != RunStatus.RUNNING:
                delete_action = menu.addAction("🗑 Delete")
                if delete_action:
                    delete_action.triggered.connect(self._on_delete_clicked)

            menu.exec(event.globalPos())
        super().contextMenuEvent(event)

    def _on_open_log_directory(self) -> None:
        """Handle open log directory action."""
        self.open_log_directory_requested.emit(self.run.id)

    def _on_run_in_terminal(self) -> None:
        """Handle run in terminal action."""
        self.run_in_terminal_requested.emit(self.run.id)

    def _update_button_states(self) -> None:
        """Update button visibility and enabled state based on run status.

        Button logic:
        - Stop: only visible/enabled when RUNNING
        - Restart: only visible/enabled when NOT RUNNING (completed states)
        - Delete: disabled when RUNNING
        - Open Session: only visible when session_id is not None
        """
        is_running = self.run.status == RunStatus.RUNNING
        has_session_id = self.run.session_id is not None

        # Stop button: only when running
        self.stop_btn.setVisible(is_running)
        self.stop_btn.setEnabled(is_running)

        # Restart button: only when not running
        self.restart_btn.setVisible(not is_running)
        self.restart_btn.setEnabled(not is_running)

        # Open session button: only when session_id exists
        self.open_session_btn.setVisible(has_session_id)
        self.open_session_btn.setEnabled(has_session_id)

        # Delete button: disabled when running
        self.delete_btn.setEnabled(not is_running)
        if is_running:
            self.delete_btn.setToolTip("Cannot delete while running")
        else:
            self.delete_btn.setToolTip("Delete run")

    def update_run(self, run: Run) -> None:
        """Update the widget with new run data."""
        self.run = run
        self.task_name_label.setText(run.task_name or "Unknown Task")
        self.status_badge.setText(self._get_status_text())
        self.status_badge.setProperty("status", run.status.value)
        self.time_label.setText(self._get_time_text())
        self._update_status_indicator()
        self._update_button_states()
