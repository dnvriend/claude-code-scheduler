"""
Jobs Panel - Leftmost panel showing list of jobs as row widgets.

Displays jobs with status icon, name, task count, and action buttons.
Clicking a job filters the task list to show tasks belonging to that job.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from uuid import UUID

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from claude_code_scheduler.models.enums import JobStatus
from claude_code_scheduler.models.job import Job
from claude_code_scheduler.models.task import Task
from claude_code_scheduler.ui.widgets.job_item import JobItemWidget


class JobsPanel(QFrame):
    """Left panel showing jobs as row widgets."""

    # Signals
    job_selected = pyqtSignal(object)  # UUID | None
    new_job_requested = pyqtSignal()
    run_job_requested = pyqtSignal(object)  # UUID
    stop_job_requested = pyqtSignal(object)  # UUID
    edit_job_requested = pyqtSignal(object)  # UUID
    delete_job_requested = pyqtSignal(object)  # UUID
    export_job_requested = pyqtSignal(object)  # UUID

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("jobsPanel")
        self.setMinimumWidth(180)
        self.jobs: list[Job] = []
        self.tasks: list[Task] = []
        self.job_widgets: dict[UUID, JobItemWidget] = {}
        self._selected_job_id: UUID | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Scrollable job list area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Job list container
        self.job_list_container = QWidget()
        self.job_list_container.setObjectName("jobListContainer")
        self.job_list_layout = QVBoxLayout(self.job_list_container)
        self.job_list_layout.setContentsMargins(12, 12, 12, 12)
        self.job_list_layout.setSpacing(8)
        self.job_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state placeholder
        self.empty_state = self._create_empty_state()
        self.job_list_layout.addWidget(self.empty_state)

        scroll_area.setWidget(self.job_list_container)
        layout.addWidget(scroll_area, 1)

        # Bottom buttons container
        bottom_buttons = QWidget()
        bottom_layout = QVBoxLayout(bottom_buttons)
        bottom_layout.setContentsMargins(12, 8, 12, 12)
        bottom_layout.setSpacing(8)

        # Show All button
        show_all_btn = QPushButton("Show All Tasks")
        show_all_btn.setObjectName("showAllButton")
        show_all_btn.clicked.connect(self._on_show_all_clicked)
        bottom_layout.addWidget(show_all_btn)

        # New Job button
        new_job_btn = QPushButton("New Job")
        new_job_btn.setObjectName("newJobButton")
        new_job_btn.clicked.connect(self.new_job_requested.emit)
        bottom_layout.addWidget(new_job_btn)

        layout.addWidget(bottom_buttons)

    def _create_header(self) -> QWidget:
        """Create the panel header with title and new button."""
        header = QWidget()
        header.setObjectName("panelHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Jobs")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        layout.addStretch()

        new_btn = QPushButton("+")
        new_btn.setObjectName("newJobButton")
        new_btn.setFixedSize(24, 24)
        new_btn.setToolTip("Create New Job")
        new_btn.clicked.connect(self.new_job_requested.emit)
        layout.addWidget(new_btn)

        return header

    def _create_empty_state(self) -> QWidget:
        """Create the empty state widget shown when no jobs exist."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        label = QLabel("No jobs yet.\nCreate your first job!")
        label.setObjectName("emptyStateLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        return widget

    def set_data(self, jobs: list[Job], tasks: list[Task]) -> None:
        """Update the panel with jobs and tasks data."""
        self.jobs = jobs
        self.tasks = tasks
        self._refresh_list()

    def _refresh_list(self) -> None:
        """Rebuild the job list from current data."""
        # Clear existing widgets
        for widget in self.job_widgets.values():
            self.job_list_layout.removeWidget(widget)
            widget.deleteLater()
        self.job_widgets.clear()

        # Sort jobs: in_progress first, then pending, then others
        status_order = {
            JobStatus.IN_PROGRESS: 0,
            JobStatus.PENDING: 1,
            JobStatus.COMPLETED: 2,
            JobStatus.FAILED: 3,
        }
        sorted_jobs = sorted(self.jobs, key=lambda j: (status_order.get(j.status, 9), j.name))

        # Show/hide empty state
        if sorted_jobs:
            self.empty_state.hide()
            for job in sorted_jobs:
                self._add_job_widget(job)
        else:
            self.empty_state.show()

    def _add_job_widget(self, job: Job) -> None:
        """Add a job widget to the list."""
        # Count tasks for this job
        task_count = len([t for t in self.tasks if t.job_id == job.id])

        widget = JobItemWidget(job, task_count)
        widget.clicked.connect(self._on_job_clicked)
        widget.run_requested.connect(self.run_job_requested.emit)
        widget.stop_requested.connect(self.stop_job_requested.emit)
        widget.edit_requested.connect(self.edit_job_requested.emit)
        widget.delete_requested.connect(self.delete_job_requested.emit)
        widget.export_requested.connect(self.export_job_requested.emit)

        self.job_widgets[job.id] = widget
        self.job_list_layout.addWidget(widget)

    def _on_job_clicked(self, job_id: UUID) -> None:
        """Handle job item click."""
        # Update selection state
        if self._selected_job_id and self._selected_job_id in self.job_widgets:
            self.job_widgets[self._selected_job_id].set_selected(False)

        self._selected_job_id = job_id
        if job_id in self.job_widgets:
            self.job_widgets[job_id].set_selected(True)

        self.job_selected.emit(job_id)

    def _on_show_all_clicked(self) -> None:
        """Handle 'Show All Tasks' button click."""
        # Clear selection
        if self._selected_job_id and self._selected_job_id in self.job_widgets:
            self.job_widgets[self._selected_job_id].set_selected(False)
        self._selected_job_id = None
        self.job_selected.emit(None)

    def select_job(self, job_id: UUID | None) -> None:
        """Programmatically select a job in the list."""
        # Clear previous selection
        if self._selected_job_id and self._selected_job_id in self.job_widgets:
            self.job_widgets[self._selected_job_id].set_selected(False)

        self._selected_job_id = job_id
        if job_id and job_id in self.job_widgets:
            self.job_widgets[job_id].set_selected(True)

    def get_selected_job_id(self) -> UUID | None:
        """Get the currently selected job ID."""
        return self._selected_job_id
