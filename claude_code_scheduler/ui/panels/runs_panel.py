"""
Runs Panel - Right-top panel showing run history.

Displays list of scheduled and completed runs with filtering and sorting.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from uuid import UUID

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from claude_code_scheduler.models.enums import RunStatus
from claude_code_scheduler.models.run import Run
from claude_code_scheduler.ui.widgets.run_item import RunItemWidget


class RunsPanel(QFrame):
    """Right-top panel containing run history list."""

    # Signals
    run_selected = pyqtSignal(UUID)
    run_cancelled = pyqtSignal(UUID)
    run_deleted = pyqtSignal(UUID)
    run_stopped = pyqtSignal(UUID)
    run_restarted = pyqtSignal(UUID)
    open_session_requested = pyqtSignal(UUID)
    open_log_directory_requested = pyqtSignal()
    run_in_terminal_requested = pyqtSignal(UUID)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("runsPanel")
        self.runs: list[Run] = []
        self.run_widgets: dict[UUID, RunItemWidget] = {}
        self.current_filter = "All"
        self.task_filter: UUID | None = None  # Filter by task ID
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with filters
        header = self._create_header()
        layout.addWidget(header)

        # Scrollable runs list area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Runs list container
        self.runs_list_container = QWidget()
        self.runs_list_container.setObjectName("runsListContainer")
        self.runs_list_layout = QVBoxLayout(self.runs_list_container)
        self.runs_list_layout.setContentsMargins(12, 12, 12, 12)
        self.runs_list_layout.setSpacing(4)
        self.runs_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state placeholder
        self.empty_state = self._create_empty_state()
        self.runs_list_layout.addWidget(self.empty_state)

        scroll_area.setWidget(self.runs_list_container)
        layout.addWidget(scroll_area, 1)

    def _create_header(self) -> QWidget:
        """Create the panel header with filter controls."""
        header = QWidget()
        header.setObjectName("panelHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("Runs")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        layout.addStretch()

        # Status filter dropdown
        self.status_filter = QComboBox()
        self.status_filter.setObjectName("filterComboBox")
        self.status_filter.addItems(
            ["All", "Upcoming", "Running", "Success", "Failed", "Cancelled"]
        )
        self.status_filter.currentTextChanged.connect(self._on_filter_changed)
        layout.addWidget(self.status_filter)

        # Sort toggle button placeholder
        sort_label = QLabel("Time")
        sort_label.setObjectName("sortLabel")
        layout.addWidget(sort_label)

        return header

    def _create_empty_state(self) -> QWidget:
        """Create the empty state widget shown when no runs exist."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel(
            "No runs yet.\nRuns will appear here when tasks\nare scheduled or executed manually."
        )
        label.setObjectName("emptyStateLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        return widget

    def set_runs(self, runs: list[Run]) -> None:
        """Set the list of runs to display."""
        self.runs = runs
        self._refresh_list()

    def clear(self) -> None:
        """Clear the runs panel display (show empty state)."""
        for widget in self.run_widgets.values():
            widget.deleteLater()
        self.run_widgets.clear()
        self.task_filter = None
        self.empty_state.show()

    def add_run(self, run: Run) -> None:
        """Add a new run to the list."""
        self.runs.insert(0, run)  # Add at beginning (newest first)
        self._refresh_list()

    def update_run(self, run: Run) -> None:
        """Update an existing run in the list."""
        for i, r in enumerate(self.runs):
            if r.id == run.id:
                self.runs[i] = run
                if run.id in self.run_widgets:
                    self.run_widgets[run.id].update_run(run)
                return

    def select_run(self, run_id: UUID) -> None:
        """Select a run by ID and emit the selection signal.

        Args:
            run_id: UUID of the run to select.
        """
        if run_id in self.run_widgets:
            self.run_selected.emit(run_id)

    def _refresh_list(self) -> None:
        """Refresh the displayed runs list."""
        # Clear existing widgets
        for widget in self.run_widgets.values():
            widget.deleteLater()
        self.run_widgets.clear()

        # Filter runs
        filtered_runs = self._filter_runs()

        # Sort by scheduled time (newest first)
        filtered_runs.sort(key=lambda r: r.scheduled_time, reverse=True)

        # Show empty state if no runs
        if not filtered_runs:
            self.empty_state.show()
            return

        self.empty_state.hide()

        # Create widgets for each run
        for run in filtered_runs:
            widget = RunItemWidget(run)
            widget.clicked.connect(self._on_run_clicked)
            widget.delete_requested.connect(self._on_run_delete_requested)
            widget.stop_requested.connect(self._on_run_stop_requested)
            widget.restart_requested.connect(self._on_run_restart_requested)
            widget.open_session_clicked.connect(
                lambda run_id=run.id: self.open_session_requested.emit(run_id)
            )
            widget.open_log_directory_requested.connect(
                lambda run_id=run.id: self._on_open_log_directory_requested()
            )
            widget.run_in_terminal_requested.connect(self._on_run_terminal_requested)
            self.runs_list_layout.addWidget(widget)
            self.run_widgets[run.id] = widget

    def _filter_runs(self) -> list[Run]:
        """Filter runs based on current filter selection and task filter."""
        # Start with all runs or task-filtered runs
        if self.task_filter:
            filtered = [r for r in self.runs if r.task_id == self.task_filter]
        else:
            filtered = list(self.runs)

        # Apply status filter
        if self.current_filter == "All":
            return filtered

        status_map = {
            "Upcoming": RunStatus.UPCOMING,
            "Running": RunStatus.RUNNING,
            "Success": RunStatus.SUCCESS,
            "Failed": RunStatus.FAILED,
            "Cancelled": RunStatus.CANCELLED,
        }

        target_status = status_map.get(self.current_filter)
        if target_status:
            return [r for r in filtered if r.status == target_status]

        return filtered

    def _on_filter_changed(self, filter_text: str) -> None:
        """Handle filter dropdown change."""
        self.current_filter = filter_text
        self._refresh_list()

    def _on_run_clicked(self, run_id: UUID) -> None:
        """Handle run item click."""
        self.run_selected.emit(run_id)

    def _on_run_delete_requested(self, run_id: UUID) -> None:
        """Handle run delete request."""
        self.run_deleted.emit(run_id)

    def _on_run_stop_requested(self, run_id: UUID) -> None:
        """Handle run stop request."""
        self.run_stopped.emit(run_id)

    def _on_run_restart_requested(self, run_id: UUID) -> None:
        """Handle run restart request."""
        self.run_restarted.emit(run_id)

    def _on_open_log_directory_requested(self) -> None:
        """Handle open log directory request."""
        self.open_log_directory_requested.emit()

    def _on_run_terminal_requested(self, run_id: UUID) -> None:
        """Handle run in terminal request."""
        self.run_in_terminal_requested.emit(run_id)

    def get_run_by_id(self, run_id: UUID) -> Run | None:
        """Get a run by its ID."""
        for run in self.runs:
            if run.id == run_id:
                return run
        return None

    def set_task_filter(self, task_id: UUID | None) -> None:
        """Set task filter to show only runs for a specific task.

        Args:
            task_id: UUID of the task to filter by, or None to show all runs.
        """
        self.task_filter = task_id
        self._refresh_list()
