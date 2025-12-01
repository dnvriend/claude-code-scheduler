"""
Task List Panel - Left panel showing list of scheduled tasks.

Displays tasks with enable/disable toggle, name, model badge, schedule info,
and action buttons (run, duplicate, delete).

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from uuid import UUID

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from claude_code_scheduler.models.profile import Profile
from claude_code_scheduler.models.run import Run
from claude_code_scheduler.models.task import Task
from claude_code_scheduler.ui.widgets.task_item import TaskItemWidget


class TaskListPanel(QFrame):
    """Left panel containing the list of tasks and bottom action buttons."""

    # Signals
    task_selected = pyqtSignal(UUID)
    task_toggled = pyqtSignal(UUID, bool)
    task_run_requested = pyqtSignal(UUID)
    task_stop_requested = pyqtSignal(UUID)  # run_id to stop
    task_duplicate_requested = pyqtSignal(UUID)
    task_delete_requested = pyqtSignal(UUID)
    new_task_requested = pyqtSignal()
    view_runs_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    task_order_changed = pyqtSignal(UUID, list)  # (job_id, new_task_order)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("taskListPanel")
        self.task_widgets: dict[UUID, TaskItemWidget] = {}
        self.selected_task_id: UUID | None = None
        self.profiles: list[Profile] = []
        self._all_tasks: list[Task] = []  # Full task list (unfiltered)
        self._all_runs: list[Run] = []  # All runs for statistics
        self._job_filter: UUID | str | None = None  # Current job filter
        self._task_order: list[UUID] = []  # Current display order for filtered tasks
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Scrollable task list area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Task list container
        self.task_list_container = QWidget()
        self.task_list_container.setObjectName("taskListContainer")
        self.task_list_layout = QVBoxLayout(self.task_list_container)
        self.task_list_layout.setContentsMargins(12, 12, 12, 12)
        self.task_list_layout.setSpacing(8)
        self.task_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state placeholder
        self.empty_state = self._create_empty_state()
        self.task_list_layout.addWidget(self.empty_state)

        scroll_area.setWidget(self.task_list_container)
        layout.addWidget(scroll_area, 1)

        # Bottom action buttons
        bottom_buttons = self._create_bottom_buttons()
        layout.addWidget(bottom_buttons)

        # Version label
        version_label = QLabel("Claude Code Scheduler v0.1.0")
        version_label.setObjectName("versionLabel")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

    def _create_header(self) -> QWidget:
        """Create the panel header with app title."""
        header = QWidget()
        header.setObjectName("panelHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Tasks")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        return header

    def _create_empty_state(self) -> QWidget:
        """Create the empty state widget shown when no tasks exist."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        label = QLabel("No tasks yet.\nCreate your first Claude task!")
        label.setObjectName("emptyStateLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        return widget

    def _create_bottom_buttons(self) -> QWidget:
        """Create the bottom action buttons."""
        widget = QWidget()
        widget.setObjectName("bottomButtons")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # New Task button
        self.new_task_btn = QPushButton("New Task")
        self.new_task_btn.setObjectName("primaryButton")
        self.new_task_btn.clicked.connect(self.new_task_requested.emit)
        layout.addWidget(self.new_task_btn)

        # View All Runs button
        self.view_runs_btn = QPushButton("View All Runs")
        self.view_runs_btn.setObjectName("secondaryButton")
        self.view_runs_btn.clicked.connect(self.view_runs_requested.emit)
        layout.addWidget(self.view_runs_btn)

        # Settings button
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setObjectName("secondaryButton")
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self.settings_btn)

        return widget

    def set_profiles(self, profiles: list[Profile]) -> None:
        """Set the list of profiles for resolving profile names."""
        self.profiles = profiles

    def set_tasks(self, tasks: list[Task]) -> None:
        """Set the list of tasks to display (stores full list and applies filter)."""
        self._all_tasks = tasks
        self._refresh_display()

    def set_runs(self, runs: list[Run]) -> None:
        """Set runs and update task widget statistics."""
        self._all_runs = runs
        # Update statistics on existing widgets
        for task_id, widget in self.task_widgets.items():
            task_runs = self._get_runs_for_task(task_id)
            widget.update_runs(task_runs)

    def set_job_filter(self, job_filter: object) -> None:
        """Set job filter and refresh display.

        Args:
            job_filter: UUID to filter by job, "UNASSIGNED" for tasks without job,
                        or None to show all tasks.
        """
        if job_filter is None:
            self._job_filter = None
        elif isinstance(job_filter, UUID):
            self._job_filter = job_filter
        elif job_filter == "UNASSIGNED":
            self._job_filter = "UNASSIGNED"
        else:
            self._job_filter = None
        self._refresh_display()

    def clear_job_filter(self) -> None:
        """Clear job filter and show all tasks."""
        self._job_filter = None
        self._refresh_display()

    def _get_filtered_tasks(self) -> list[Task]:
        """Get tasks filtered by current job filter."""
        if self._job_filter is None:
            return self._all_tasks
        elif self._job_filter == "UNASSIGNED":
            return [t for t in self._all_tasks if t.job_id is None]
        elif isinstance(self._job_filter, UUID):
            return [t for t in self._all_tasks if t.job_id == self._job_filter]
        return self._all_tasks

    def _refresh_display(self) -> None:
        """Refresh the displayed task list based on current filter."""
        # Clear existing widgets
        for widget in self.task_widgets.values():
            self.task_list_layout.removeWidget(widget)
            widget.deleteLater()
        self.task_widgets.clear()

        # Get filtered tasks
        filtered_tasks = self._get_filtered_tasks()

        # Enable drag-and-drop only when filtering by a specific job (not UNASSIGNED/None)
        drag_enabled = isinstance(self._job_filter, UUID)

        # Update task order tracking
        self._task_order = [t.id for t in filtered_tasks]

        # Show/hide empty state
        if filtered_tasks:
            self.empty_state.hide()
            for task in filtered_tasks:
                self._add_task_widget(task, drag_enabled)
        else:
            self.empty_state.show()

    def _add_task_widget(self, task: Task, drag_enabled: bool = False) -> None:
        """Add a task widget to the list."""
        task_runs = self._get_runs_for_task(task.id)
        widget = TaskItemWidget(task, self.profiles, task_runs, drag_enabled)
        widget.clicked.connect(self._on_task_clicked)
        widget.toggled.connect(self.task_toggled.emit)
        widget.run_requested.connect(self.task_run_requested.emit)
        widget.stop_requested.connect(self.task_stop_requested.emit)
        widget.duplicate_requested.connect(self.task_duplicate_requested.emit)
        widget.delete_requested.connect(self.task_delete_requested.emit)

        self.task_widgets[task.id] = widget
        self.task_list_layout.addWidget(widget)

    def _get_runs_for_task(self, task_id: UUID) -> list[Run]:
        """Get all runs for a specific task."""
        return [r for r in self._all_runs if r.task_id == task_id]

    def _on_task_clicked(self, task_id: UUID) -> None:
        """Handle task item click."""
        # Update selection state
        if self.selected_task_id and self.selected_task_id in self.task_widgets:
            self.task_widgets[self.selected_task_id].set_selected(False)

        self.selected_task_id = task_id
        if task_id in self.task_widgets:
            self.task_widgets[task_id].set_selected(True)

        self.task_selected.emit(task_id)

    def update_task(self, task: Task) -> None:
        """Update a specific task in the list."""
        if task.id in self.task_widgets:
            self.task_widgets[task.id].update_task(task, self.profiles)

    def select_task(self, task_id: UUID | None) -> None:
        """Programmatically select a task."""
        if self.selected_task_id and self.selected_task_id in self.task_widgets:
            self.task_widgets[self.selected_task_id].set_selected(False)

        self.selected_task_id = task_id
        if task_id and task_id in self.task_widgets:
            self.task_widgets[task_id].set_selected(True)

    def get_selected_task_id(self) -> UUID | None:
        """Get the currently selected task ID."""
        return self.selected_task_id

    # Drag-and-drop event handlers

    def dragEnterEvent(self, event: QDragEnterEvent | None) -> None:  # noqa: N802
        """Accept drag if it contains task data and we're filtering by job."""
        if event is None:
            return
        mime_data = event.mimeData()
        if (
            mime_data is not None
            and mime_data.hasFormat(TaskItemWidget.MIME_TYPE)
            and isinstance(self._job_filter, UUID)
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent | None) -> None:  # noqa: N802
        """Handle drag move to show drop indicator."""
        if event is None:
            return
        mime_data = event.mimeData()
        if (
            mime_data is not None
            and mime_data.hasFormat(TaskItemWidget.MIME_TYPE)
            and isinstance(self._job_filter, UUID)
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent | None) -> None:  # noqa: N802
        """Handle drop to reorder tasks."""
        if event is None or not isinstance(self._job_filter, UUID):
            return

        mime_data = event.mimeData()
        if not mime_data or not mime_data.hasFormat(TaskItemWidget.MIME_TYPE):
            event.ignore()
            return

        # Get dragged task ID
        data = mime_data.data(TaskItemWidget.MIME_TYPE).data()
        try:
            dragged_task_id = UUID(data.decode())
        except (ValueError, UnicodeDecodeError):
            event.ignore()
            return

        # Find drop position based on y coordinate
        drop_y = event.position().y()
        target_index = len(self._task_order)

        for i, task_id in enumerate(self._task_order):
            widget = self.task_widgets.get(task_id)
            if widget:
                widget_y = widget.geometry().y() + widget.height() / 2
                if drop_y < widget_y:
                    target_index = i
                    break

        # Remove from current position
        if dragged_task_id in self._task_order:
            current_index = self._task_order.index(dragged_task_id)
            self._task_order.remove(dragged_task_id)
            # Adjust target index if dragging downward
            if current_index < target_index:
                target_index -= 1

        # Insert at new position
        self._task_order.insert(target_index, dragged_task_id)

        # Emit signal with job_id and new order
        self.task_order_changed.emit(self._job_filter, self._task_order.copy())

        # Reorder widgets in layout
        self._reorder_widgets()

        event.acceptProposedAction()

    def _reorder_widgets(self) -> None:
        """Reorder task widgets in layout according to current order."""
        # Remove all widgets from layout (but don't delete)
        for task_id in self._task_order:
            widget = self.task_widgets.get(task_id)
            if widget:
                self.task_list_layout.removeWidget(widget)

        # Re-add in new order
        for task_id in self._task_order:
            widget = self.task_widgets.get(task_id)
            if widget:
                self.task_list_layout.addWidget(widget)
