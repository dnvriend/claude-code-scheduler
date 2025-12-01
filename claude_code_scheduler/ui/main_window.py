"""Main window for Claude Code Scheduler.

This module implements the main application window with a 4-panel layout:
Jobs (optional) | Tasks | Editor | Runs/Logs.

Key Components:
    - MainWindow: QMainWindow with splitter-based panel layout
    - Data signals: task_changed, run_changed, profile_changed, job_changed

Dependencies:
    - PyQt6: GUI framework (QMainWindow, QSplitter, QMenuBar)
    - models: Task, Run, Job, Profile, Settings
    - services: TaskScheduler, SequentialScheduler, DebugServer
    - storage: ConfigStorage for persistence

Related Modules:
    - main: Creates MainWindow instance
    - ui.panels: All panel components
    - ui.dialogs: Dialog components
    - services.debug_server: REST API server

Calls:
    - ConfigStorage: Load/save all data
    - TaskScheduler: Schedule tasks
    - SequentialScheduler: Sequential job execution
    - DebugServer: Start REST API

Called By:
    - main.main: Application entry point

Layout:
    - Left (optional): JobsPanel - Job management
    - Center-Left: TaskListPanel - Task list
    - Center: TaskEditorPanel - Task configuration
    - Right: RunsPanel + LogsPanel in vertical splitter

Example:
    >>> from claude_code_scheduler.ui.main_window import MainWindow
    >>> window = MainWindow(restport=5679)
    >>> window.show()

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from pathlib import Path
from uuid import UUID

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QWidget,
)

from claude_code_scheduler.logging_config import get_logger
from claude_code_scheduler.models.enums import JobStatus, ScheduleType
from claude_code_scheduler.models.job import Job
from claude_code_scheduler.models.profile import Profile
from claude_code_scheduler.models.run import Run
from claude_code_scheduler.models.settings import Settings
from claude_code_scheduler.models.task import Task
from claude_code_scheduler.services import FileWatcher, TaskScheduler
from claude_code_scheduler.services.applescript_service import AppleScriptService
from claude_code_scheduler.services.debug_server import DebugServer
from claude_code_scheduler.services.env_resolver import EnvVarResolver
from claude_code_scheduler.services.export_service import ExportService
from claude_code_scheduler.services.iterm_service import ITermService
from claude_code_scheduler.services.sequential_scheduler import (
    SequentialScheduler,
    SequentialSchedulerConfig,
)
from claude_code_scheduler.storage import ConfigStorage
from claude_code_scheduler.ui.dialogs.job_editor_dialog import JobEditorDialog
from claude_code_scheduler.ui.dialogs.profile_editor_dialog import ProfileEditorDialog
from claude_code_scheduler.ui.dialogs.settings_dialog import SettingsDialog
from claude_code_scheduler.ui.panels.logs_panel import LogsPanel
from claude_code_scheduler.ui.panels.runs_panel import RunsPanel
from claude_code_scheduler.ui.panels.task_editor_panel import TaskEditorPanel
from claude_code_scheduler.ui.panels.task_list_panel import TaskListPanel

logger = get_logger(__name__)


class SchedulerSignalBridge(QObject):
    """Bridge to marshal scheduler callbacks from worker thread to main Qt thread.

    APScheduler runs tasks in background threads, but Qt GUI updates must
    happen on the main thread. This bridge uses Qt signals to safely communicate.
    """

    run_started = pyqtSignal(object)  # Run object
    run_completed = pyqtSignal(object)  # Run object
    file_watch_triggered = pyqtSignal(object)  # Task object
    output_received = pyqtSignal(object, str)  # (run_id UUID, output line)
    state_changed = pyqtSignal()  # Signal for REST API to trigger UI refresh
    api_run_task = pyqtSignal(object)  # Task UUID - marshal API run requests to main thread
    api_run_job = pyqtSignal(object)  # Job UUID - marshal API job run requests to main thread


class MainWindow(QMainWindow):
    """Main application window with 4-panel layout."""

    def __init__(self, restport: int = 5679) -> None:
        super().__init__()
        self._restport = restport

        # Initialize storage
        self.storage = ConfigStorage()

        # Load application state (settings loaded first for scheduler config)
        self.tasks: list[Task] = []
        self.runs: list[Run] = []
        self.profiles: list[Profile] = []
        self.jobs: list[Job] = []
        self.settings: Settings = self.storage.load_settings()

        # Signal bridge for thread-safe scheduler callbacks
        self._signal_bridge = SchedulerSignalBridge()
        self._signal_bridge.run_started.connect(self._on_run_started)
        self._signal_bridge.run_completed.connect(self._on_run_completed)
        self._signal_bridge.file_watch_triggered.connect(self._on_file_watch_triggered)
        self._signal_bridge.output_received.connect(self._on_output_received)
        self._signal_bridge.state_changed.connect(self._refresh_ui)
        self._signal_bridge.api_run_task.connect(self._on_task_run_requested)
        self._signal_bridge.api_run_job.connect(self._on_api_run_job_requested)

        # Initialize scheduler and file watcher with settings
        # Use lambda to emit signals from worker thread - Qt handles thread marshalling
        self._scheduler = TaskScheduler(
            on_run_started=lambda run: self._signal_bridge.run_started.emit(run),
            on_run_completed=lambda run: self._signal_bridge.run_completed.emit(run),
            on_output=lambda run_id, line: self._signal_bridge.output_received.emit(run_id, line),
            profile_resolver=self._resolve_profile,
            job_resolver=self._resolve_job_by_id,
            mock_mode=self.settings.mock_mode,
            unmask_env_vars=self.settings.unmask_env_vars,
        )
        self._file_watcher = FileWatcher(
            on_trigger=lambda task: self._signal_bridge.file_watch_triggered.emit(task),
        )

        # Sequential scheduler for job sequence execution
        self._sequential_scheduler = SequentialScheduler(
            config=SequentialSchedulerConfig(
                task_resolver=self._resolve_task_by_id,
                job_resolver=self._resolve_job_by_id,
                task_runner=lambda task: self._scheduler.run_task_now(task),
                job_status_updater=self._update_job_status,
                on_job_started=self._on_job_sequence_started,
                on_job_progress=self._on_job_sequence_progress,
                on_job_completed=self._on_job_sequence_completed,
            )
        )

        # Debug server for runtime inspection and control
        self._debug_server = DebugServer(
            port=self._restport,
            # Read providers
            state_provider=self._get_debug_state,
            ui_state_provider=self._get_ui_state,
            ui_analysis_provider=self._get_ui_analysis,
            screenshot_provider=self._capture_screenshot,
            # Single item read providers
            task_get_provider=self._api_get_task,
            run_get_provider=self._api_get_run,
            # Write providers - tasks
            task_create_provider=self._api_create_task,
            task_update_provider=self._api_update_task,
            task_delete_provider=self._api_delete_task,
            task_run_provider=self._api_run_task,
            task_enable_provider=self._api_enable_task,
            # Write providers - runs
            run_stop_provider=self._api_stop_run,
            run_restart_provider=self._api_restart_run,
            run_delete_provider=self._api_delete_run,
            # Run logs provider
            run_logs_provider=self._api_get_run_logs,
            # Profile providers
            profile_list_provider=self._api_list_profiles,
            profile_get_provider=self._api_get_profile,
            profile_create_provider=self._api_create_profile,
            profile_update_provider=self._api_update_profile,
            profile_delete_provider=self._api_delete_profile,
            # Job providers
            job_list_provider=self._api_list_jobs,
            job_get_provider=self._api_get_job,
            job_create_provider=self._api_create_job,
            job_update_provider=self._api_update_job,
            job_delete_provider=self._api_delete_job,
            job_tasks_provider=self._api_get_job_tasks,
            job_run_provider=self._api_run_job,
            job_stop_provider=self._api_stop_job,
        )

        # Initialize environment resolver and iTerm service
        self.env_resolver = EnvVarResolver()
        self.iterm_service = ITermService()
        self.applescript_service = AppleScriptService()

        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        self._load_state()
        self._apply_ui_settings()
        self._refresh_ui()
        self._start_services()

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowTitle("Claude Code Scheduler")
        self.setMinimumSize(1250, 800)
        self.resize(1450, 900)
        self._setup_menu_bar()

    def _setup_menu_bar(self) -> None:
        """Set up the application menu bar."""
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # File menu
        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)

        new_task_action = QAction("&New Task", self)
        new_task_action.setShortcut(QKeySequence.StandardKey.New)
        new_task_action.triggered.connect(self._on_new_task_requested)
        file_menu.addAction(new_task_action)

        file_menu.addSeparator()

        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._on_settings_requested)
        file_menu.addAction(settings_action)

        # Task menu
        task_menu = QMenu("&Task", self)
        menu_bar.addMenu(task_menu)

        run_now_action = QAction("&Run Now", self)
        run_now_action.setShortcut(QKeySequence("Ctrl+R"))
        run_now_action.triggered.connect(self._run_selected_task)
        task_menu.addAction(run_now_action)

        duplicate_action = QAction("&Duplicate", self)
        duplicate_action.setShortcut(QKeySequence("Ctrl+D"))
        duplicate_action.triggered.connect(self._duplicate_selected_task)
        task_menu.addAction(duplicate_action)

        task_menu.addSeparator()

        delete_action = QAction("De&lete", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self._delete_selected_task)
        task_menu.addAction(delete_action)

        # Job menu
        job_menu = QMenu("&Job", self)
        menu_bar.addMenu(job_menu)

        new_job_action = QAction("&New Job", self)
        new_job_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        new_job_action.triggered.connect(self._on_new_job_requested)
        job_menu.addAction(new_job_action)

        run_job_action = QAction("&Run Job", self)
        run_job_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        run_job_action.triggered.connect(self._run_selected_job)
        job_menu.addAction(run_job_action)

        job_menu.addSeparator()

        export_job_action = QAction("&Export Job...", self)
        export_job_action.setShortcut(QKeySequence("Ctrl+E"))
        export_job_action.triggered.connect(self._on_export_job)
        job_menu.addAction(export_job_action)

        # View menu
        view_menu = QMenu("&View", self)
        menu_bar.addMenu(view_menu)

        # Toggle Jobs panel visibility
        self.toggle_jobs_action = QAction("Show &Jobs Panel", self)
        self.toggle_jobs_action.setCheckable(True)
        self.toggle_jobs_action.setChecked(True)
        self.toggle_jobs_action.triggered.connect(self._toggle_jobs_panel)
        view_menu.addAction(self.toggle_jobs_action)

        view_menu.addSeparator()

        view_runs_action = QAction("View All &Runs", self)
        view_runs_action.triggered.connect(self._on_view_runs_requested)
        view_menu.addAction(view_runs_action)

    def _run_selected_task(self) -> None:
        """Run the currently selected task."""
        selected_id = self.task_list_panel.get_selected_task_id()
        if selected_id:
            self._on_task_run_requested(selected_id)

    def _duplicate_selected_task(self) -> None:
        """Duplicate the currently selected task."""
        selected_id = self.task_list_panel.get_selected_task_id()
        if selected_id:
            self._on_task_duplicate_requested(selected_id)

    def _delete_selected_task(self) -> None:
        """Delete the currently selected task."""
        selected_id = self.task_list_panel.get_selected_task_id()
        if selected_id:
            self._on_task_delete_requested(selected_id)

    def _run_selected_job(self) -> None:
        """Run the currently selected job (start sequential execution)."""
        selected_id = self.jobs_panel.get_selected_job_id()
        if selected_id:
            self._on_run_job_requested(selected_id)

    def _on_export_job(self) -> None:
        """Export the currently selected job to a JSON file."""
        # Get selected job
        selected_id = self.jobs_panel.get_selected_job_id()
        if not selected_id:
            QMessageBox.warning(self, "No Job Selected", "Please select a job to export.")
            return

        # Find job for display name
        job = next((j for j in self.jobs if j.id == selected_id), None)
        if not job:
            QMessageBox.warning(self, "Job Not Found", "The selected job could not be found.")
            return

        # Show file save dialog
        suggested_filename = f"{job.name.replace(' ', '_')}_export.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Job", suggested_filename, "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:  # User cancelled
            return

        try:
            # Export job using export service
            export_service = ExportService(self.storage)
            output_path = Path(file_path)
            export_service.export_to_file(selected_id, output_path)

            # Show success message
            QMessageBox.information(
                self,
                "Export Successful",
                f"Job '{job.name}' exported successfully to:\n{output_path}",
            )
            logger.info("Job '%s' exported to %s", job.name, output_path)

        except ValueError as e:
            # Handle export errors (e.g., job not found)
            QMessageBox.critical(self, "Export Failed", f"Failed to export job: {e}")
            logger.error("Export failed for job %s: %s", selected_id, e)

        except OSError as e:
            # Handle file I/O errors
            QMessageBox.critical(self, "Export Failed", f"Failed to write export file: {e}")
            logger.error("File write failed for job %s: %s", selected_id, e)

        except Exception as e:
            # Handle unexpected errors
            QMessageBox.critical(self, "Export Failed", f"An unexpected error occurred: {e}")
            logger.error("Unexpected export error for job %s: %s", selected_id, e)

    def _on_export_job_with_id(self, job_id: UUID) -> None:
        """Export a specific job to a JSON file."""
        # Find job for display name
        job = next((j for j in self.jobs if j.id == job_id), None)
        if not job:
            QMessageBox.warning(self, "Job Not Found", "The job could not be found.")
            return

        # Show file save dialog
        suggested_filename = f"{job.name.replace(' ', '_')}_export.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Job", suggested_filename, "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:  # User cancelled
            return

        try:
            # Export job using export service
            export_service = ExportService(self.storage)
            output_path = Path(file_path)
            export_service.export_to_file(job_id, output_path)

            # Show success message
            QMessageBox.information(
                self,
                "Export Successful",
                f"Job '{job.name}' exported successfully to:\n{output_path}",
            )
            logger.info("Job '%s' exported to %s", job.name, output_path)

        except ValueError as e:
            # Handle export errors (e.g., job not found)
            QMessageBox.critical(self, "Export Failed", f"Failed to export job: {e}")
            logger.error("Export failed for job %s: %s", job_id, e)

        except OSError as e:
            # Handle file I/O errors
            QMessageBox.critical(self, "Export Failed", f"Failed to write export file: {e}")
            logger.error("File write failed for job %s: %s", job_id, e)

        except Exception as e:
            # Handle unexpected errors
            QMessageBox.critical(self, "Export Failed", f"An unexpected error occurred: {e}")
            logger.error("Unexpected export error for job %s: %s", job_id, e)

    def _on_run_job_requested(self, job_id: UUID) -> None:
        """Handle run job request from UI - start sequential task execution."""
        self._start_job_by_id(job_id)

    def _on_stop_job_requested(self, job_id: UUID) -> None:
        """Handle stop job request from UI - stop sequential task execution."""
        self._stop_job_by_id(job_id)

    def _stop_job_by_id(self, job_id: UUID) -> bool:
        """Stop a job by ID - shared implementation for UI and API.

        Args:
            job_id: Job UUID to stop.

        Returns:
            True if job was stopped successfully.
        """
        job = self._resolve_job_by_id(job_id)
        if not job:
            logger.warning("Job not found: %s", job_id)
            return False

        if not self._sequential_scheduler.is_job_running(job_id):
            logger.warning("Job %s is not running", job.name)
            return False

        logger.info("Stopping job: %s", job.name)
        stopped = self._sequential_scheduler.stop_job(job_id, JobStatus.FAILED)
        if not stopped:
            logger.warning("Failed to stop job %s", job.name)
        return stopped

    def _on_api_run_job_requested(self, job_id: UUID) -> None:
        """Handle run job request from REST API (marshalled to main thread)."""
        self._start_job_by_id(job_id)

    def _start_job_by_id(self, job_id: UUID) -> bool:
        """Start a job by ID - shared implementation for UI and API.

        Args:
            job_id: Job UUID to start.

        Returns:
            True if job was started successfully.
        """
        job = self._resolve_job_by_id(job_id)
        if not job:
            logger.warning("Job not found: %s", job_id)
            return False

        if not job.task_order:
            logger.warning("Job %s has no tasks in task_order", job.name)
            return False

        logger.info("Starting job: %s", job.name)
        started = self._sequential_scheduler.start_job(job)
        if not started:
            logger.warning("Failed to start job %s (may already be running)", job.name)
        return started

    def _setup_ui(self) -> None:
        """Set up the 5-panel layout using splitters."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create main horizontal splitter (stored for debug inspection)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Leftmost panel: Jobs Panel (NEW)
        from claude_code_scheduler.ui.panels import JobsPanel

        self.jobs_panel = JobsPanel()
        self.main_splitter.addWidget(self.jobs_panel)

        # Left panel: Task List
        self.task_list_panel = TaskListPanel()
        self.main_splitter.addWidget(self.task_list_panel)

        # Middle panel: Task Editor
        self.task_editor_panel = TaskEditorPanel()
        self.main_splitter.addWidget(self.task_editor_panel)

        # Right side: Vertical splitter for Runs and Logs (stored for debug inspection)
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Right-Top: Runs Panel
        self.runs_panel = RunsPanel()
        self.right_splitter.addWidget(self.runs_panel)

        # Right-Bottom: Logs Panel
        self.logs_panel = LogsPanel()
        self.right_splitter.addWidget(self.logs_panel)

        # Set right splitter proportions (50/50)
        self.right_splitter.setSizes([400, 400])

        self.main_splitter.addWidget(self.right_splitter)

        # Set main splitter proportions: Jobs(200), Tasks(250), Editor(stretch), Right(450)
        self.main_splitter.setSizes([200, 250, 400, 450])

        main_layout.addWidget(self.main_splitter)

    def _connect_signals(self) -> None:
        """Connect panel signals to handlers."""
        # Jobs panel signals
        self.jobs_panel.job_selected.connect(self._on_job_selected)
        self.jobs_panel.new_job_requested.connect(self._on_new_job_requested)
        self.jobs_panel.run_job_requested.connect(self._on_run_job_requested)
        self.jobs_panel.stop_job_requested.connect(self._on_stop_job_requested)
        self.jobs_panel.edit_job_requested.connect(self._on_edit_job_requested)
        self.jobs_panel.delete_job_requested.connect(self._on_delete_job_requested)
        self.jobs_panel.export_job_requested.connect(self._on_export_job_with_id)

        # Task list panel signals
        self.task_list_panel.task_selected.connect(self._on_task_selected)
        self.task_list_panel.task_toggled.connect(self._on_task_toggled)
        self.task_list_panel.task_run_requested.connect(self._on_task_run_requested)
        self.task_list_panel.task_stop_requested.connect(self._on_run_stopped)
        self.task_list_panel.task_duplicate_requested.connect(self._on_task_duplicate_requested)
        self.task_list_panel.task_delete_requested.connect(self._on_task_delete_requested)
        self.task_list_panel.new_task_requested.connect(self._on_new_task_requested)
        self.task_list_panel.view_runs_requested.connect(self._on_view_runs_requested)
        self.task_list_panel.settings_requested.connect(self._on_settings_requested)
        self.task_list_panel.task_order_changed.connect(self._on_task_order_changed)

        # Task editor panel signals
        self.task_editor_panel.task_saved.connect(self._on_task_saved)
        self.task_editor_panel.manage_profiles_requested.connect(self._on_manage_profiles_requested)

        # Runs panel signals
        self.runs_panel.run_selected.connect(self._on_run_selected)
        self.runs_panel.run_deleted.connect(self._on_run_deleted)
        self.runs_panel.run_stopped.connect(self._on_run_stopped)
        self.runs_panel.run_restarted.connect(self._on_run_restarted)
        self.runs_panel.open_session_requested.connect(self._on_open_session_requested)
        self.runs_panel.open_log_directory_requested.connect(self._on_open_log_directory_requested)
        self.runs_panel.run_in_terminal_requested.connect(self._on_run_in_terminal_requested)

        # Logs panel signals
        self.logs_panel.session_opened.connect(self._on_session_opened)

    def _apply_ui_settings(self) -> None:
        """Apply UI settings from loaded settings."""
        # Jobs panel visibility
        self.jobs_panel.setVisible(self.settings.show_jobs_panel)
        self.toggle_jobs_action.setChecked(self.settings.show_jobs_panel)

        # Restore window geometry
        self._restore_window_geometry()

    def _restore_window_geometry(self) -> None:
        """Restore window geometry and splitter sizes from settings."""
        # Restore window size
        width = self.settings.window_width
        height = self.settings.window_height
        self.resize(width, height)

        # Restore window position if saved
        if self.settings.window_x is not None and self.settings.window_y is not None:
            self.move(self.settings.window_x, self.settings.window_y)

        # Restore maximized state
        if self.settings.window_maximized:
            self.showMaximized()

        # Restore splitter sizes
        if self.settings.main_splitter_sizes:
            self.main_splitter.setSizes(self.settings.main_splitter_sizes)
        if self.settings.right_splitter_sizes:
            self.right_splitter.setSizes(self.settings.right_splitter_sizes)

        logger.debug("Window geometry restored")

    def _refresh_ui(self) -> None:
        """Refresh UI with current state."""
        self.jobs_panel.set_data(self.jobs, self.tasks)
        self.task_list_panel.set_profiles(self.profiles)
        self.task_list_panel.set_tasks(self.tasks)
        self.task_list_panel.set_runs(self.runs)  # Update task run statistics
        self.runs_panel.set_runs(self.runs)
        self.task_editor_panel.set_profiles(self.profiles)
        self.task_editor_panel.set_jobs(self.jobs)

    def _on_task_selected(self, task_id: UUID) -> None:
        """Handle task selection."""
        logger.debug("Task selected: %s", task_id)
        for task in self.tasks:
            if task.id == task_id:
                self.task_editor_panel.show_task(task)
                # Filter runs panel to show only runs for this task
                self.runs_panel.set_task_filter(task_id)
                # Clear logs panel
                self.logs_panel.clear()
                break

    def _on_task_toggled(self, task_id: UUID, enabled: bool) -> None:
        """Handle task enable/disable toggle."""
        logger.debug("Task toggled: %s -> %s", task_id, enabled)
        for task in self.tasks:
            if task.id == task_id:
                task.enabled = enabled
                self.storage.save_task(task)
                self._reschedule_task(task)
                break

    def _on_task_run_requested(self, task_id: UUID) -> None:
        """Handle run now request."""
        logger.info("Run requested for task: %s", task_id)
        for task in self.tasks:
            if task.id == task_id:
                self._scheduler.run_task_now(task)
                break

    def _on_task_duplicate_requested(self, task_id: UUID) -> None:
        """Handle task duplication request."""
        logger.info("Duplicate requested for task: %s", task_id)
        for task in self.tasks:
            if task.id == task_id:
                # Create a copy with new ID and modified name
                # NOTE: working_directory is now on Job, not Task
                new_task = Task(
                    name=f"{task.name} (Copy)",
                    model=task.model,
                    permissions=task.permissions,
                    session_mode=task.session_mode,
                    command_type=task.command_type,
                    command=task.command,
                    schedule=task.schedule,
                    enabled=False,  # Start disabled
                    retry=task.retry,
                    notifications=task.notifications,
                    allowed_tools=task.allowed_tools.copy(),
                    disallowed_tools=task.disallowed_tools.copy(),
                    job_id=task.job_id,  # Copy job assignment (inherits working dir)
                    profile=task.profile,
                )
                self.tasks.append(new_task)
                self.storage.save_task(new_task)
                self._refresh_ui()
                self.task_list_panel.select_task(new_task.id)
                self.task_editor_panel.show_edit(new_task)
                break

    def _on_task_delete_requested(self, task_id: UUID) -> None:
        """Handle task deletion request."""
        logger.info("Delete requested for task: %s", task_id)
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                # Unschedule and remove
                self._scheduler.unschedule_task(task_id)
                self._file_watcher.unwatch_task(task_id)
                del self.tasks[i]
                self.storage.delete_task(task_id)
                self._refresh_ui()
                self.task_editor_panel.clear()
                break

    # Job signal handlers

    def _on_job_selected(self, job_filter: object) -> None:
        """Handle job selection - filter tasks panel and clear other panels."""
        logger.debug("Job selected: %s", job_filter)
        self.task_list_panel.set_job_filter(job_filter)
        # Clear task editor, runs and logs panels when job changes
        self.task_editor_panel.clear()
        self.runs_panel.clear()
        self.logs_panel.clear()

    def _on_task_order_changed(self, job_id: UUID, task_order: list[UUID]) -> None:
        """Handle task order change from drag-and-drop reordering."""
        logger.info("Task order changed for job %s: %s", job_id, task_order)
        # Find and update the job
        for job in self.jobs:
            if job.id == job_id:
                job.task_order = task_order
                self.storage.save_jobs(self.jobs)
                logger.info("Job %s task order saved", job.name)
                break

    def _on_new_job_requested(self) -> None:
        """Handle new job request."""
        from datetime import datetime

        from claude_code_scheduler.models.job import JobWorkingDirectory

        logger.info("New job requested")
        dialog = JobEditorDialog(parent=self, profiles=self.profiles)
        if dialog.exec():
            data = dialog.get_job_data()
            # Parse working_directory from dialog data
            working_directory = JobWorkingDirectory()
            if "working_directory" in data:
                working_directory = JobWorkingDirectory.from_dict(data["working_directory"])

            job = Job(
                name=data["name"],
                description=data.get("description", ""),
                profile=data.get("profile"),
                status=JobStatus.PENDING,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                working_directory=working_directory,
            )
            self.jobs.append(job)
            self.storage.save_jobs(self.jobs)
            self._refresh_ui()
            logger.info("Job created: %s", job.name)

    def _on_edit_job_requested(self, job_id: UUID) -> None:
        """Handle job edit request."""
        from datetime import datetime

        from claude_code_scheduler.models.job import JobWorkingDirectory

        logger.info("Edit job requested: %s", job_id)
        job = next((j for j in self.jobs if j.id == job_id), None)
        if not job:
            return

        dialog = JobEditorDialog(job=job, profiles=self.profiles, parent=self)
        if dialog.exec():
            data = dialog.get_job_data()
            job.name = data["name"]
            job.description = data.get("description", "")
            job.profile = data.get("profile")
            if "working_directory" in data:
                job.working_directory = JobWorkingDirectory.from_dict(data["working_directory"])
            job.updated_at = datetime.now()
            self.storage.save_jobs(self.jobs)
            self._refresh_ui()
            logger.info("Job updated: %s", job.name)

    def _on_delete_job_requested(self, job_id: UUID) -> None:
        """Handle job delete request (cascade delete tasks and runs, keep worktree)."""
        from PyQt6.QtWidgets import QMessageBox

        logger.info("Delete job requested: %s", job_id)
        job = next((j for j in self.jobs if j.id == job_id), None)
        if not job:
            return

        # Count tasks and runs that will be deleted
        tasks_to_delete = [t for t in self.tasks if t.job_id == job_id]
        task_ids = {t.id for t in tasks_to_delete}
        runs_count = len([r for r in self.runs if r.task_id in task_ids])

        msg = f"Delete job '{job.name}'?"
        if tasks_to_delete:
            msg += f"\n\nThis will delete {len(tasks_to_delete)} task(s) and {runs_count} run(s)."
        if job.working_directory.use_git_worktree:
            msg += "\n\nNote: Git worktree will be kept on disk."

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Cascade delete tasks and runs via storage (worktree is kept)
            self.storage.delete_job(job_id, cascade=True)
            # Reload state
            self.jobs = self.storage.load_jobs()
            self.tasks = self.storage.load_tasks()
            self.runs = self.storage.load_runs()
            self._refresh_ui()
            logger.info("Job deleted: %s (kept worktree)", job_id)

    def _on_new_task_requested(self) -> None:
        """Handle new task request."""
        logger.info("New task requested")
        self.task_editor_panel.show_edit(None)
        # Clear task filter on runs panel
        self.runs_panel.set_task_filter(None)

    def _on_view_runs_requested(self) -> None:
        """Handle view all runs request."""
        logger.info("View all runs requested")
        self.runs_panel.set_task_filter(None)

    def _toggle_jobs_panel(self, checked: bool) -> None:
        """Toggle visibility of the Jobs panel."""
        self.jobs_panel.setVisible(checked)
        if checked:
            # Restore reasonable splitter sizes when showing
            sizes = self.main_splitter.sizes()
            if sizes[0] < 50:  # Jobs panel collapsed
                # Restore: Jobs(200), Tasks(250), Editor(remaining), Right(450)
                total = sum(sizes)
                sizes[0] = 200
                sizes[1] = max(sizes[1], 250)
                sizes[3] = max(sizes[3], 450)
                sizes[2] = total - sizes[0] - sizes[1] - sizes[3]
                self.main_splitter.setSizes(sizes)
        else:
            # Clear job filter when hiding panel
            self.task_list_panel.clear_job_filter()
        # Save setting
        self.settings.show_jobs_panel = checked
        self.storage.save_settings(self.settings)

    def _on_run_selected(self, run_id: UUID) -> None:
        """Handle run selection."""
        logger.debug("Run selected: %s", run_id)
        run = self.runs_panel.get_run_by_id(run_id)
        if run:
            self.logs_panel.show_run_logs(run)
            # Clear Live tab and prepare for this run's output
            self.logs_panel.clear_live()
            if run.status.value == "running":
                self.logs_panel.start_live_output(run.task_name or "Unknown Task")

    def _on_run_deleted(self, run_id: UUID) -> None:
        """Handle run deletion."""
        logger.debug("Run deleted: %s", run_id)
        # Remove from runs list
        self.runs = [r for r in self.runs if r.id != run_id]
        # Save to storage
        self.storage.save_runs(self.runs)
        # Refresh UI
        self.runs_panel.set_runs(self.runs)
        # Clear logs panel if showing deleted run
        self.logs_panel.clear()

    def _on_run_stopped(self, run_id: UUID) -> None:
        """Handle run stop request."""
        logger.info("Stop requested for run: %s", run_id)
        stopped = self._scheduler.stop_run(run_id)

        if not stopped:
            # No process found - mark run as failed so user can delete it
            logger.warning("No process found for run %s, marking as failed", run_id)
            from datetime import UTC, datetime

            from claude_code_scheduler.models.enums import RunStatus

            for i, run in enumerate(self.runs):
                if run.id == run_id:
                    run.status = RunStatus.FAILED
                    run.end_time = datetime.now(UTC)
                    run.errors = (run.errors or "") + "\n[FAILED] No running process found"
                    self.runs[i] = run
                    self.storage.save_run(run)
                    self.runs_panel.set_runs(self.runs)
                    self.logs_panel.show_run_logs(run)
                    break

    def _on_run_restarted(self, run_id: UUID) -> None:
        """Handle run restart request - re-run the task."""
        logger.info("Restart requested for run: %s", run_id)
        # Find the run and its associated task
        run = self.runs_panel.get_run_by_id(run_id)
        if not run:
            logger.warning("Run not found: %s", run_id)
            return

        # Find the task by ID
        for task in self.tasks:
            if task.id == run.task_id:
                logger.info("Restarting task: %s", task.name)
                self._scheduler.run_task_now(task)
                return

        logger.warning("Task not found for run: %s", run.task_id)

    def _on_open_session_requested(self, run_id: UUID) -> None:
        """Handle request to open iTerm session for a run."""
        logger.info("Open iTerm session requested for run: %s", run_id)

        # a) Find run in self.runs by id
        run = next((r for r in self.runs if r.id == run_id), None)
        if not run or run.session_id is None:
            QMessageBox.warning(
                self, "Cannot Open Session", "Run not found or no session ID available."
            )
            return

        # c) Find task by run.task_id
        task = next((t for t in self.tasks if t.id == run.task_id), None)
        if not task:
            QMessageBox.warning(self, "Cannot Open Session", "Task not found for this run.")
            return

        # d) Find job by task.job_id if exists
        job = next((j for j in self.jobs if j.id == task.job_id), None) if task.job_id else None

        # e) Find profile by task.profile if exists (task.profile is str, p.id is UUID)
        profile = (
            next((p for p in self.profiles if str(p.id) == task.profile), None)
            if task.profile
            else None
        )

        # f) Get working_dir from job.working_directory.get_resolved_path(job.id) or fallback
        working_dir = str(Path.home() / "projects")  # Default fallback
        if job and job.working_directory:
            resolved_dir = (
                job.working_directory.get_resolved_path(job.id)
                if job.id
                else str(job.working_directory)
            )
            # Only use resolved dir if it exists, otherwise fall back
            if Path(resolved_dir).is_dir():
                working_dir = resolved_dir
            else:
                logger.warning(
                    "Working directory does not exist, using fallback: %s -> %s",
                    resolved_dir,
                    working_dir,
                )

        # g) Resolve env vars from profile using self.env_resolver.resolve_profile if profile exists
        env_vars = self.env_resolver.resolve_profile(profile) if profile else {}
        logger.debug(
            "Profile for session: %s, env vars count: %d",
            profile.name if profile else "None",
            len(env_vars),
        )

        # h) Build command_args list - map permission mode to CLI values
        perm_map = {
            "default": "default",
            "bypass": "bypassPermissions",
            "acceptEdits": "acceptEdits",
            "plan": "plan",
        }
        perm_mode = perm_map.get(task.permissions, "default")

        command_args = [
            "--resume",
            str(run.session_id),
            "--model",
            task.model,
            "--permission-mode",
            perm_mode,
        ]

        # i) If not self.iterm_service.is_available() show warning dialog
        if not self.iterm_service.is_available():
            QMessageBox.warning(
                self, "iTerm Not Available", "iTerm2 is not available or not configured properly."
            )
            return

        # j) Call self.iterm_service.open_session(command_args, working_dir, env_vars)
        try:
            success = self.iterm_service.open_session(command_args, working_dir, env_vars)
            if success:
                logger.info("Successfully opened iTerm session for run %s", run_id)
            else:
                logger.error("Failed to open iTerm session for run %s", run_id)
                QMessageBox.warning(
                    self,
                    "Failed to Open Session",
                    f"Could not open iTerm session.\nWorking directory: {working_dir}",
                )
        except Exception as e:
            logger.error("Failed to open iTerm session: %s", e)
            QMessageBox.critical(
                self, "Failed to Open Session", f"Failed to open iTerm session: {e}"
            )

    def _on_open_log_directory_requested(self) -> None:
        """Handle request to open log directory in Finder."""
        logger.info("Open log directory requested")

        if not self.applescript_service.is_available():
            QMessageBox.warning(
                self,
                "Cannot Open Directory",
                "macOS AppleScript service is not available. This feature only works on macOS.",
            )
            return

        try:
            success = self.applescript_service.open_log_directory()
            if success:
                logger.info("Successfully opened log directory in Finder")
            else:
                QMessageBox.warning(
                    self,
                    "Failed to Open Directory",
                    "Failed to open log directory in Finder. Please check your system settings.",
                )
        except Exception as e:
            logger.error("Failed to open log directory: %s", e)
            QMessageBox.critical(
                self, "Failed to Open Directory", f"Failed to open log directory: {e}"
            )

    def _on_run_in_terminal_requested(self, run_id: UUID) -> None:
        """Handle request to run task command in Terminal.app."""
        logger.info("Run in terminal requested for run: %s", run_id)

        # a) Check if AppleScript service is available
        if not self.applescript_service.is_available():
            QMessageBox.warning(
                self,
                "Cannot Run in Terminal",
                "macOS AppleScript service is not available. This feature only works on macOS.",
            )
            return

        # b) Find run in self.runs by id
        run = next((r for r in self.runs if r.id == run_id), None)
        if not run:
            QMessageBox.warning(self, "Cannot Run in Terminal", "Run not found.")
            return

        # c) Find task by run.task_id
        task = next((t for t in self.tasks if t.id == run.task_id), None)
        if not task:
            QMessageBox.warning(self, "Cannot Run in Terminal", "Task not found for this run.")
            return

        # d) Find job by task.job_id if exists
        job = next((j for j in self.jobs if j.id == task.job_id), None) if task.job_id else None

        # e) Get working_dir from job.working_directory.get_resolved_path(job.id) or fallback
        if job and job.working_directory:
            working_dir = (
                job.working_directory.get_resolved_path(job.id)
                if job.id
                else str(job.working_directory)
            )
        else:
            working_dir = str(Path.home() / "projects")

        # f) Find profile by task.profile if exists and resolve env vars
        profile = (
            next((p for p in self.profiles if p.id == task.profile), None) if task.profile else None
        )
        env_vars = self.env_resolver.resolve_profile(profile) if profile else {}

        # g) Build claude command using AppleScript service
        command = self.applescript_service.build_claude_command(
            task_command=task.command,
            task_command_type=task.command_type,
            task_model=task.model,
            task_profile=str(task.profile) if task.profile else None,
            task_permissions=task.permissions,
            task_session_mode=task.session_mode,
        )

        # h) Run command in Terminal
        try:
            success = self.applescript_service.run_in_terminal(
                command=command,
                working_dir=working_dir,
                env_vars=env_vars,
                new_window=True,
            )
            if success:
                logger.info("Successfully started command in Terminal for run %s", run_id)
            else:
                QMessageBox.warning(
                    self,
                    "Failed to Run in Terminal",
                    "Failed to start command in Terminal. Please check your system settings.",
                )
        except Exception as e:
            logger.error("Failed to run command in Terminal: %s", e)
            QMessageBox.critical(
                self, "Failed to Run in Terminal", f"Failed to run command in Terminal: {e}"
            )

    def _on_session_opened(self, run_id: UUID) -> None:
        """Handle request to open session in terminal from logs panel."""
        logger.info("Open session requested from logs panel: %s", run_id)
        # Delegate to the main open session handler
        self._on_open_session_requested(run_id)

    def _on_settings_requested(self) -> None:
        """Handle settings request."""
        logger.info("Settings requested")
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.settings = dialog.get_settings()
            self.storage.save_settings(self.settings)
            logger.info("Settings saved")

    def _on_manage_profiles_requested(self) -> None:
        """Handle manage profiles request from task editor."""
        logger.info("Manage profiles requested")
        dialog = ProfileEditorDialog(self.profiles, self)
        if dialog.exec():
            self.profiles = dialog.get_profiles()
            self.storage.save_profiles(self.profiles)
            self.task_editor_panel.set_profiles(self.profiles)
            logger.info("Profiles saved: %d profiles", len(self.profiles))

    def _get_debug_state(self) -> dict[str, object]:
        """Get current application state for debug server.

        Returns:
            Dictionary with full application state.
        """
        from typing import Any

        def serialize_run(run: Run) -> dict[str, Any]:
            return {
                "id": str(run.id),
                "task_id": str(run.task_id),
                "task_name": run.task_name,
                "status": run.status.value,
                "scheduled_time": str(run.scheduled_time) if run.scheduled_time else None,
                "start_time": str(run.start_time) if run.start_time else None,
                "end_time": str(run.end_time) if run.end_time else None,
                "exit_code": run.exit_code,
            }

        def serialize_task(task: Task) -> dict[str, Any]:
            return {
                "id": str(task.id),
                "name": task.name,
                "enabled": task.enabled,
                "model": task.model,
                "schedule_type": task.schedule.schedule_type.value,
                "profile": task.profile,
                "job_id": str(task.job_id) if task.job_id else None,
            }

        def serialize_profile(profile: Profile) -> dict[str, Any]:
            return {
                "id": str(profile.id),
                "name": profile.name,
                "env_var_count": len(profile.env_vars),
            }

        return {
            "tasks": [serialize_task(t) for t in self.tasks],
            "runs": [serialize_run(r) for r in self.runs],
            "profiles": [serialize_profile(p) for p in self.profiles],
            "settings": self.settings.to_dict(),
            "scheduler": {
                "scheduled_tasks": [str(tid) for tid in self._scheduler.get_scheduled_tasks()],
            },
        }

    def _get_ui_state(self) -> dict[str, object]:
        """Get UI geometry and layout state for debug server.

        Returns:
            Dictionary with window, panel, and splitter geometry.
        """
        from PyQt6.QtCore import QPoint

        def widget_geometry(widget: QWidget, name: str) -> dict[str, object]:
            """Get comprehensive geometry for a widget."""
            geom = widget.geometry()
            global_pos = widget.mapToGlobal(QPoint(0, 0))
            return {
                "name": name,
                "visible": widget.isVisible(),
                "enabled": widget.isEnabled(),
                "local": {
                    "x": geom.x(),
                    "y": geom.y(),
                    "width": geom.width(),
                    "height": geom.height(),
                },
                "screen": {
                    "x": global_pos.x(),
                    "y": global_pos.y(),
                },
                "size": {
                    "width": widget.width(),
                    "height": widget.height(),
                },
            }

        # Window state
        window_geom = self.geometry()
        window_frame = self.frameGeometry()

        return {
            "window": {
                "title": self.windowTitle(),
                "visible": self.isVisible(),
                "minimized": self.isMinimized(),
                "maximized": self.isMaximized(),
                "fullscreen": self.isFullScreen(),
                "geometry": {
                    "x": window_geom.x(),
                    "y": window_geom.y(),
                    "width": window_geom.width(),
                    "height": window_geom.height(),
                },
                "frame_geometry": {
                    "x": window_frame.x(),
                    "y": window_frame.y(),
                    "width": window_frame.width(),
                    "height": window_frame.height(),
                },
            },
            "panels": {
                "task_list": widget_geometry(self.task_list_panel, "TaskListPanel"),
                "task_editor": widget_geometry(self.task_editor_panel, "TaskEditorPanel"),
                "runs": widget_geometry(self.runs_panel, "RunsPanel"),
                "logs": widget_geometry(self.logs_panel, "LogsPanel"),
            },
            "splitters": {
                "main_horizontal": {
                    "orientation": "horizontal",
                    "sizes": self.main_splitter.sizes(),
                    "count": self.main_splitter.count(),
                },
                "right_vertical": {
                    "orientation": "vertical",
                    "sizes": self.right_splitter.sizes(),
                    "count": self.right_splitter.count(),
                },
            },
            "layout_description": {
                "structure": "3-column with right column split vertically",
                "columns": [
                    "Left: Task List (task selection and actions)",
                    "Middle: Task Editor (edit task configuration)",
                    "Right-Top: Runs Panel (execution history)",
                    "Right-Bottom: Logs Panel (run output and logs)",
                ],
            },
        }

    def _get_ui_analysis(self) -> dict[str, object]:
        """Analyze UI for overlaps and layout issues.

        Returns AI-optimized analysis with grid, overlaps, and fix suggestions.
        """
        from PyQt6.QtCore import QPoint

        def get_screen_rect(widget: QWidget) -> dict[str, int]:
            """Get widget's screen rectangle."""
            pos = widget.mapToGlobal(QPoint(0, 0))
            return {
                "x": pos.x(),
                "y": pos.y(),
                "width": widget.width(),
                "height": widget.height(),
                "x2": pos.x() + widget.width(),
                "y2": pos.y() + widget.height(),
            }

        def rects_overlap(r1: dict[str, int], r2: dict[str, int]) -> bool:
            """Check if two rectangles overlap."""
            return (
                r1["x"] < r2["x2"]
                and r1["x2"] > r2["x"]
                and r1["y"] < r2["y2"]
                and r1["y2"] > r2["y"]
            )

        def get_overlap_region(r1: dict[str, int], r2: dict[str, int]) -> dict[str, int] | None:
            """Calculate the overlapping region between two rectangles."""
            if not rects_overlap(r1, r2):
                return None
            return {
                "x": max(r1["x"], r2["x"]),
                "y": max(r1["y"], r2["y"]),
                "x2": min(r1["x2"], r2["x2"]),
                "y2": min(r1["y2"], r2["y2"]),
                "width": min(r1["x2"], r2["x2"]) - max(r1["x"], r2["x"]),
                "height": min(r1["y2"], r2["y2"]) - max(r1["y"], r2["y"]),
            }

        def collect_child_widgets(
            parent: QWidget, parent_name: str, depth: int = 0
        ) -> list[dict[str, object]]:
            """Recursively collect child widget geometries."""
            widgets: list[dict[str, object]] = []
            for child in parent.findChildren(QWidget):
                if child.parent() == parent and child.isVisible():
                    rect = get_screen_rect(child)
                    widget_info: dict[str, object] = {
                        "name": child.objectName() or child.__class__.__name__,
                        "class": child.__class__.__name__,
                        "parent": parent_name,
                        "depth": depth,
                        "rect": rect,
                    }
                    widgets.append(widget_info)
            return widgets

        # Collect panel geometries
        panels = {
            "task_list": {
                "widget": self.task_list_panel,
                "rect": get_screen_rect(self.task_list_panel),
            },
            "task_editor": {
                "widget": self.task_editor_panel,
                "rect": get_screen_rect(self.task_editor_panel),
            },
            "runs": {
                "widget": self.runs_panel,
                "rect": get_screen_rect(self.runs_panel),
            },
            "logs": {
                "widget": self.logs_panel,
                "rect": get_screen_rect(self.logs_panel),
            },
        }

        # Collect important child widgets from each panel
        child_widgets: list[dict[str, object]] = []
        for panel_name, panel_info in panels.items():
            widget = panel_info["widget"]
            assert isinstance(widget, QWidget)
            children = collect_child_widgets(widget, panel_name, depth=1)
            child_widgets.extend(children)

        # Detect panel overlaps
        panel_overlaps: list[dict[str, object]] = []
        panel_names = list(panels.keys())
        for i, name1 in enumerate(panel_names):
            for name2 in panel_names[i + 1 :]:
                r1 = panels[name1]["rect"]
                r2 = panels[name2]["rect"]
                overlap = get_overlap_region(r1, r2)  # type: ignore[arg-type]
                if overlap:
                    panel_overlaps.append(
                        {
                            "panels": [name1, name2],
                            "overlap_region": overlap,
                            "severity": "high"
                            if overlap["width"] > 50 or overlap["height"] > 50
                            else "low",
                        }
                    )

        # Detect clipped widgets (children extending beyond panel bounds)
        clipped_widgets: list[dict[str, object]] = []
        for widget_info in child_widgets:
            parent_name = str(widget_info["parent"])
            if parent_name in panels:
                parent_rect = panels[parent_name]["rect"]
                widget_rect = widget_info["rect"]
                assert isinstance(widget_rect, dict)
                assert isinstance(parent_rect, dict)

                clip_right = widget_rect["x2"] - parent_rect["x2"]
                clip_bottom = widget_rect["y2"] - parent_rect["y2"]
                clip_left = parent_rect["x"] - widget_rect["x"]
                clip_top = parent_rect["y"] - widget_rect["y"]

                if clip_right > 0 or clip_bottom > 0 or clip_left > 0 or clip_top > 0:
                    clipped_widgets.append(
                        {
                            "widget": widget_info["name"],
                            "class": widget_info["class"],
                            "parent": parent_name,
                            "clipping": {
                                "right": max(0, clip_right),
                                "bottom": max(0, clip_bottom),
                                "left": max(0, clip_left),
                                "top": max(0, clip_top),
                            },
                            "widget_rect": widget_rect,
                            "parent_rect": parent_rect,
                        }
                    )

        # Generate ASCII grid (simplified, showing panel boundaries)
        window_rect = get_screen_rect(self)
        grid_width = 80
        grid_height = 20
        scale_x = window_rect["width"] / grid_width
        scale_y = window_rect["height"] / grid_height

        grid: list[list[str]] = [[" " for _ in range(grid_width)] for _ in range(grid_height)]
        panel_chars = {"task_list": "L", "task_editor": "E", "runs": "R", "logs": "G"}

        for panel_name, panel_info in panels.items():
            rect = panel_info["rect"]
            assert isinstance(rect, dict)
            # Convert to grid coordinates relative to window
            gx1 = int((rect["x"] - window_rect["x"]) / scale_x)
            gy1 = int((rect["y"] - window_rect["y"]) / scale_y)
            gx2 = int((rect["x2"] - window_rect["x"]) / scale_x)
            gy2 = int((rect["y2"] - window_rect["y"]) / scale_y)

            char = panel_chars.get(panel_name, "?")
            for y in range(max(0, gy1), min(grid_height, gy2)):
                for x in range(max(0, gx1), min(grid_width, gx2)):
                    if grid[y][x] == " ":
                        grid[y][x] = char
                    elif grid[y][x] != char:
                        grid[y][x] = "X"  # Overlap marker

        grid_str = "\n".join("".join(row) for row in grid)

        # Calculate suggested fixes
        fixes: list[dict[str, object]] = []
        splitter_sizes = self.main_splitter.sizes()
        total_width = sum(splitter_sizes)

        # Check if task_list panel is too narrow for its content
        task_list_rect = panels["task_list"]["rect"]
        assert isinstance(task_list_rect, dict)
        if task_list_rect["width"] < 350:
            current_pct = splitter_sizes[0] / total_width * 100
            fixes.append(
                {
                    "issue": "task_list_panel_narrow",
                    "current_width": task_list_rect["width"],
                    "current_splitter_size": splitter_sizes[0],
                    "current_percentage": round(current_pct, 1),
                    "suggested_min_width": 350,
                    "suggested_splitter_sizes": [350, splitter_sizes[1], splitter_sizes[2]],
                    "action": "Increase task_list panel width to at least 350px",
                }
            )

        # Check for any detected overlaps
        for overlap_info in panel_overlaps:
            overlap_region = overlap_info["overlap_region"]
            if isinstance(overlap_region, dict):
                fixes.append(
                    {
                        "issue": "panel_overlap",
                        "panels": overlap_info["panels"],
                        "overlap_width": overlap_region.get("width", 0),
                        "action": "Reduce width of overlapping panels or adjust splitter",
                    }
                )

        # Check for clipped widgets
        for clipped in clipped_widgets:
            clip_info = clipped["clipping"]
            assert isinstance(clip_info, dict)
            if clip_info["right"] > 0:
                fixes.append(
                    {
                        "issue": "widget_clipped_right",
                        "widget": clipped["widget"],
                        "parent": clipped["parent"],
                        "clipped_by": clip_info["right"],
                        "action": f"Increase {clipped['parent']} width by {clip_info['right']}px",
                    }
                )

        return {
            "analysis_version": "1.0",
            "window": get_screen_rect(self),
            "panels": {name: info["rect"] for name, info in panels.items()},
            "splitter_sizes": {
                "main_horizontal": splitter_sizes,
                "right_vertical": self.right_splitter.sizes(),
            },
            "grid": {
                "legend": "L=TaskList, E=TaskEditor, R=Runs, G=Logs, X=Overlap",
                "ascii": grid_str,
                "dimensions": {"width": grid_width, "height": grid_height},
            },
            "overlaps": {
                "panel_overlaps": panel_overlaps,
                "count": len(panel_overlaps),
                "has_overlaps": len(panel_overlaps) > 0,
            },
            "clipped_widgets": {
                "widgets": clipped_widgets,
                "count": len(clipped_widgets),
                "has_clipping": len(clipped_widgets) > 0,
            },
            "fixes": {
                "suggested": fixes,
                "count": len(fixes),
                "has_issues": len(fixes) > 0,
            },
            "child_widget_count": len(child_widgets),
        }

    def _capture_screenshot(self, panel_name: str) -> dict[str, object]:
        """Capture screenshot of a UI panel.

        Args:
            panel_name: Name of panel to capture (task_list, task_editor, runs, logs, all).

        Returns:
            Dictionary with file path(s) to saved screenshots.
        """
        from datetime import datetime
        from pathlib import Path

        # Create screenshots directory
        screenshots_dir = Path.home() / ".claude-scheduler" / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Map panel names to widgets
        panel_widgets: dict[str, QWidget] = {
            "task_list": self.task_list_panel,
            "task_editor": self.task_editor_panel,
            "runs": self.runs_panel,
            "logs": self.logs_panel,
            "window": self,
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if panel_name == "all":
            # Capture all panels
            paths: dict[str, str] = {}
            for name, widget in panel_widgets.items():
                pixmap = widget.grab()
                filename = f"screenshot_{name}_{timestamp}.png"
                filepath = screenshots_dir / filename
                pixmap.save(str(filepath), "PNG")
                paths[name] = str(filepath)
            return {
                "status": "success",
                "panel": "all",
                "paths": paths,
                "timestamp": timestamp,
                "directory": str(screenshots_dir),
            }
        elif panel_name in panel_widgets:
            # Capture single panel
            widget = panel_widgets[panel_name]
            pixmap = widget.grab()
            filename = f"screenshot_{panel_name}_{timestamp}.png"
            filepath = screenshots_dir / filename
            pixmap.save(str(filepath), "PNG")
            return {
                "status": "success",
                "panel": panel_name,
                "path": str(filepath),
                "timestamp": timestamp,
                "size": {"width": pixmap.width(), "height": pixmap.height()},
            }
        else:
            return {
                "status": "error",
                "error": f"Unknown panel: {panel_name}",
                "available_panels": list(panel_widgets.keys()) + ["all"],
            }

    # -------------------------------------------------------------------------
    # REST API Single Item Read Providers (for debug server)
    # -------------------------------------------------------------------------

    def _api_get_task(self, task_id: UUID) -> dict[str, object]:
        """Get a single task via REST API.

        Args:
            task_id: Task UUID to retrieve.

        Returns:
            Result dictionary with task data.
        """
        try:
            for task in self.tasks:
                if task.id == task_id:
                    return {"success": True, "task": task.to_dict()}
            return {"success": False, "error": f"Task not found: {task_id}"}
        except Exception as e:
            logger.exception("Failed to get task via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_get_run(self, run_id: UUID) -> dict[str, object]:
        """Get a single run via REST API.

        Args:
            run_id: Run UUID to retrieve.

        Returns:
            Result dictionary with run data.
        """
        try:
            for run in self.runs:
                if run.id == run_id:
                    return {"success": True, "run": run.to_dict()}
            return {"success": False, "error": f"Run not found: {run_id}"}
        except Exception as e:
            logger.exception("Failed to get run via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_get_run_logs(self, run_id: UUID) -> str | None:
        """Get run logs via REST API.

        Args:
            run_id: Run UUID to retrieve logs for.

        Returns:
            Log content string if found, None if not found or error.
        """
        try:
            # Find the run in self.runs
            found_run = None
            for run in self.runs:
                if run.id == run_id:
                    found_run = run
                    break

            if not found_run:
                logger.warning("Run not found: %s", run_id)
                return None

            # Log files are stored in ~/.claude-scheduler/logs/run_<uuid>.log
            log_file_path = Path.home() / ".claude-scheduler" / "logs" / f"run_{run_id}.log"

            if not log_file_path.exists():
                logger.warning("Log file not found: %s", log_file_path)
                return None

            # Read log file content
            try:
                with open(log_file_path, encoding="utf-8") as f:
                    logs_content = f.read()
                return logs_content
            except Exception as e:
                logger.exception("Failed to read log file %s: %s", log_file_path, e)
                return None

        except Exception as e:
            logger.exception("Failed to get run logs via API: %s", e)
            return None

    # -------------------------------------------------------------------------
    # REST API Write Providers (for debug server)
    # -------------------------------------------------------------------------

    def _api_create_task(self, data: dict[str, object]) -> dict[str, object]:
        """Create a new task via REST API.

        Args:
            data: Task data from request body.

        Returns:
            Result dictionary with success status and task data.
        """
        from datetime import time
        from typing import Any

        from claude_code_scheduler.models.enums import IntervalType, ScheduleType
        from claude_code_scheduler.models.task import (
            NotificationConfig,
            RetryConfig,
            ScheduleConfig,
            Task,
        )

        try:
            # Validate required fields
            name = data.get("name")
            command = data.get("command")
            job_id_str = data.get("job_id")

            if not name or not command:
                return {"success": False, "error": "Missing required fields: name, command"}

            # Validate job_id is required and must reference existing job
            if not job_id_str:
                return {
                    "success": False,
                    "error": "Missing required field: job_id. "
                    "Tasks must belong to a job. Create a job first with: "
                    "claude-code-scheduler cli jobs create --name <job-name>",
                }

            try:
                job_id = UUID(str(job_id_str))
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid job_id format: {job_id_str}. Must be a valid UUID.",
                }

            # Verify job exists
            job_exists = any(j.id == job_id for j in self.jobs)
            if not job_exists:
                return {
                    "success": False,
                    "error": f"Job not found: {job_id}. "
                    "List available jobs with: claude-code-scheduler cli jobs list",
                }

            # Validate profile is required and must reference existing profile
            profile_id_str = data.get("profile")
            if not profile_id_str:
                return {
                    "success": False,
                    "error": "Missing required field: profile. "
                    "Tasks must have a profile for environment configuration. "
                    "List available profiles with: claude-code-scheduler cli profiles list",
                }

            try:
                profile_id = UUID(str(profile_id_str))
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid profile format: {profile_id_str}. Must be a valid UUID.",
                }

            # Verify profile exists
            profile_exists = any(p.id == profile_id for p in self.profiles)
            if not profile_exists:
                return {
                    "success": False,
                    "error": f"Profile not found: {profile_id}. "
                    "List available profiles with: claude-code-scheduler cli profiles list",
                }

            # Build schedule from nested object or flat fields (backwards compatible)
            schedule_data = data.get("schedule", {})
            if isinstance(schedule_data, dict) and schedule_data:
                # New nested format
                schedule_type_str = str(schedule_data.get("schedule_type", "manual"))
                schedule_type = ScheduleType(schedule_type_str)
                calendar_time_str = schedule_data.get("calendar_time")
                schedule = ScheduleConfig(
                    schedule_type=schedule_type,
                    timezone=str(schedule_data.get("timezone", "Europe/Amsterdam")),
                    calendar_frequency=str(schedule_data.get("calendar_frequency"))
                    if schedule_data.get("calendar_frequency")
                    else None,
                    calendar_time=time.fromisoformat(str(calendar_time_str))
                    if calendar_time_str
                    else None,
                    calendar_days_of_week=schedule_data.get("calendar_days_of_week"),
                    calendar_day_of_month=int(str(schedule_data.get("calendar_day_of_month")))
                    if schedule_data.get("calendar_day_of_month")
                    else None,
                    interval_type=IntervalType(str(schedule_data.get("interval_type")))
                    if schedule_data.get("interval_type")
                    else None,
                    interval_preset=str(schedule_data.get("interval_preset"))
                    if schedule_data.get("interval_preset")
                    else None,
                    interval_value=int(str(schedule_data.get("interval_value")))
                    if schedule_data.get("interval_value")
                    else None,
                    interval_unit=str(schedule_data.get("interval_unit"))
                    if schedule_data.get("interval_unit")
                    else None,
                    interval_cron=str(schedule_data.get("interval_cron"))
                    if schedule_data.get("interval_cron")
                    else None,
                    watch_directory=str(schedule_data.get("watch_directory"))
                    if schedule_data.get("watch_directory")
                    else None,
                    watch_recursive=bool(schedule_data.get("watch_recursive", True)),
                    watch_debounce_seconds=int(str(schedule_data.get("watch_debounce_seconds", 5))),
                )
            else:
                # Default manual schedule
                schedule = ScheduleConfig(schedule_type=ScheduleType.MANUAL)

            # Build retry config
            retry_data = data.get("retry", {})
            if isinstance(retry_data, dict) and retry_data:
                retry = RetryConfig(
                    enabled=bool(retry_data.get("enabled", False)),
                    max_attempts=int(str(retry_data.get("max_attempts", 3))),
                    delay_seconds=int(str(retry_data.get("delay_seconds", 60))),
                    backoff_multiplier=float(str(retry_data.get("backoff_multiplier", 2.0))),
                )
            else:
                retry = RetryConfig()

            # Build notifications config
            notifications_data = data.get("notifications", {})
            if isinstance(notifications_data, dict) and notifications_data:
                notifications = NotificationConfig(
                    on_start=bool(notifications_data.get("on_start", False)),
                    on_end=bool(notifications_data.get("on_end", False)),
                    on_failure=bool(notifications_data.get("on_failure", False)),
                )
            else:
                notifications = NotificationConfig()

            # Parse tool lists
            allowed_tools = data.get("allowed_tools", [])
            if isinstance(allowed_tools, list):
                allowed_tools = [str(t) for t in allowed_tools]
            else:
                allowed_tools = []

            disallowed_tools = data.get("disallowed_tools", [])
            if isinstance(disallowed_tools, list):
                disallowed_tools = [str(t) for t in disallowed_tools]
            else:
                disallowed_tools = []

            # Create task with all fields
            # NOTE: working_directory is inherited from Job, not set on Task
            task = Task(
                name=str(name),
                job_id=job_id,
                model=str(data.get("model", "sonnet")),
                permissions=str(data.get("permissions", "bypass")),
                session_mode=str(data.get("session_mode", "new")),
                command_type=str(data.get("command_type", "prompt")),
                command=str(command),
                schedule=schedule,
                enabled=bool(data.get("enabled", False)),
                commit_on_success=bool(data.get("commit_on_success", True)),
                profile=str(data.get("profile")) if data.get("profile") else None,
                retry=retry,
                notifications=notifications,
                allowed_tools=allowed_tools,
                disallowed_tools=disallowed_tools,
            )

            # Add to tasks list and save
            self.tasks.append(task)
            self.storage.save_task(task)

            # Add task to job's task_order
            for job in self.jobs:
                if job.id == job_id:
                    if task.id not in job.task_order:
                        job.task_order.append(task.id)
                        self.storage.save_job(job)
                        logger.debug("Added task %s to job %s task_order", task.id, job.id)
                    break

            # Schedule if enabled
            if task.enabled:
                self._reschedule_task(task)

            # Emit signal for thread-safe UI refresh
            self._signal_bridge.state_changed.emit()

            logger.info("Task created via API: %s", task.name)

            # Return full task dict for response
            task_dict: dict[str, Any] = task.to_dict()
            return {"success": True, "task": task_dict}

        except ValueError as e:
            return {"success": False, "error": f"Invalid value: {e}"}
        except Exception as e:
            logger.exception("Failed to create task via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_update_task(self, task_id: UUID, data: dict[str, object]) -> dict[str, object]:
        """Update an existing task via REST API.

        Args:
            task_id: Task UUID to update.
            data: Fields to update.

        Returns:
            Result dictionary with success status.
        """
        from datetime import time
        from typing import Any

        from claude_code_scheduler.models.enums import IntervalType, ScheduleType
        from claude_code_scheduler.models.task import (
            NotificationConfig,
            RetryConfig,
            ScheduleConfig,
        )

        try:
            # Find the task
            task = None
            for t in self.tasks:
                if t.id == task_id:
                    task = t
                    break

            if not task:
                return {"success": False, "error": f"Task not found: {task_id}"}

            # Update simple fields if provided
            if "name" in data:
                task.name = str(data["name"])
            if "command" in data:
                task.command = str(data["command"])
            if "model" in data:
                task.model = str(data["model"])
            if "permissions" in data:
                task.permissions = str(data["permissions"])
            if "session_mode" in data:
                task.session_mode = str(data["session_mode"])
            # NOTE: working_directory is now on Job, not Task
            # Ignore working_directory in task update, use job_id instead
            if "command_type" in data:
                task.command_type = str(data["command_type"])
            if "enabled" in data:
                task.enabled = bool(data["enabled"])
            if "commit_on_success" in data:
                task.commit_on_success = bool(data["commit_on_success"])
            if "profile" in data:
                task.profile = str(data["profile"]) if data["profile"] else None

            # Update schedule if provided as nested object
            schedule_data = data.get("schedule")
            if isinstance(schedule_data, dict) and schedule_data:
                schedule_type_str = str(
                    schedule_data.get("schedule_type", task.schedule.schedule_type.value)
                )
                schedule_type = ScheduleType(schedule_type_str)
                calendar_time_str = schedule_data.get(
                    "calendar_time",
                    task.schedule.calendar_time.isoformat()
                    if task.schedule.calendar_time
                    else None,
                )
                task.schedule = ScheduleConfig(
                    schedule_type=schedule_type,
                    timezone=str(schedule_data.get("timezone", task.schedule.timezone)),
                    calendar_frequency=str(schedule_data.get("calendar_frequency"))
                    if schedule_data.get("calendar_frequency")
                    else task.schedule.calendar_frequency,
                    calendar_time=time.fromisoformat(str(calendar_time_str))
                    if calendar_time_str
                    else None,
                    calendar_days_of_week=schedule_data.get(
                        "calendar_days_of_week", task.schedule.calendar_days_of_week
                    ),
                    calendar_day_of_month=int(str(schedule_data.get("calendar_day_of_month")))
                    if schedule_data.get("calendar_day_of_month")
                    else task.schedule.calendar_day_of_month,
                    interval_type=IntervalType(str(schedule_data.get("interval_type")))
                    if schedule_data.get("interval_type")
                    else task.schedule.interval_type,
                    interval_preset=str(schedule_data.get("interval_preset"))
                    if schedule_data.get("interval_preset")
                    else task.schedule.interval_preset,
                    interval_value=int(str(schedule_data.get("interval_value")))
                    if schedule_data.get("interval_value")
                    else task.schedule.interval_value,
                    interval_unit=str(schedule_data.get("interval_unit"))
                    if schedule_data.get("interval_unit")
                    else task.schedule.interval_unit,
                    interval_cron=str(schedule_data.get("interval_cron"))
                    if schedule_data.get("interval_cron")
                    else task.schedule.interval_cron,
                    watch_directory=str(schedule_data.get("watch_directory"))
                    if schedule_data.get("watch_directory")
                    else task.schedule.watch_directory,
                    watch_recursive=bool(
                        schedule_data.get("watch_recursive", task.schedule.watch_recursive)
                    ),
                    watch_debounce_seconds=int(
                        str(
                            schedule_data.get(
                                "watch_debounce_seconds", task.schedule.watch_debounce_seconds
                            )
                        )
                    ),
                )

            # Update retry config if provided
            retry_data = data.get("retry")
            if isinstance(retry_data, dict) and retry_data:
                task.retry = RetryConfig(
                    enabled=bool(retry_data.get("enabled", task.retry.enabled)),
                    max_attempts=int(str(retry_data.get("max_attempts", task.retry.max_attempts))),
                    delay_seconds=int(
                        str(retry_data.get("delay_seconds", task.retry.delay_seconds))
                    ),
                    backoff_multiplier=float(
                        str(retry_data.get("backoff_multiplier", task.retry.backoff_multiplier))
                    ),
                )

            # Update notifications config if provided
            notifications_data = data.get("notifications")
            if isinstance(notifications_data, dict) and notifications_data:
                task.notifications = NotificationConfig(
                    on_start=bool(notifications_data.get("on_start", task.notifications.on_start)),
                    on_end=bool(notifications_data.get("on_end", task.notifications.on_end)),
                    on_failure=bool(
                        notifications_data.get("on_failure", task.notifications.on_failure)
                    ),
                )

            # Update tool lists if provided
            if "allowed_tools" in data:
                allowed_tools = data.get("allowed_tools", [])
                if isinstance(allowed_tools, list):
                    task.allowed_tools = [str(t) for t in allowed_tools]

            if "disallowed_tools" in data:
                disallowed_tools = data.get("disallowed_tools", [])
                if isinstance(disallowed_tools, list):
                    task.disallowed_tools = [str(t) for t in disallowed_tools]

            # Save and reschedule
            self.storage.save_task(task)
            self._reschedule_task(task)

            # Emit signal for thread-safe UI refresh
            self._signal_bridge.state_changed.emit()

            logger.info("Task updated via API: %s", task.name)

            # Return full task dict
            task_dict: dict[str, Any] = task.to_dict()
            return {"success": True, "task": task_dict}

        except ValueError as e:
            return {"success": False, "error": f"Invalid value: {e}"}
        except Exception as e:
            logger.exception("Failed to update task via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_delete_task(self, task_id: UUID) -> dict[str, object]:
        """Delete a task via REST API.

        Args:
            task_id: Task UUID to delete.

        Returns:
            Result dictionary with success status.
        """
        try:
            # Find and delete task
            for i, task in enumerate(self.tasks):
                if task.id == task_id:
                    self._scheduler.unschedule_task(task_id)
                    self._file_watcher.unwatch_task(task_id)
                    del self.tasks[i]
                    self.storage.delete_task(task_id)
                    # Emit signal for thread-safe UI refresh
                    self._signal_bridge.state_changed.emit()
                    logger.info("Task deleted via API: %s", task_id)
                    return {"success": True, "message": f"Task {task_id} deleted"}

            return {"success": False, "error": f"Task not found: {task_id}"}

        except Exception as e:
            logger.exception("Failed to delete task via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_run_task(self, task_id: UUID) -> dict[str, object]:
        """Run a task immediately via REST API.

        Uses Qt signal to marshal the call to the main thread, since APScheduler's
        QtScheduler requires job additions from the Qt thread.

        Args:
            task_id: Task UUID to run.

        Returns:
            Result dictionary with success status.
        """
        try:
            for task in self.tasks:
                if task.id == task_id:
                    # Emit signal to run task on main Qt thread
                    # Direct call to scheduler from HTTP thread doesn't work with QtScheduler
                    self._signal_bridge.api_run_task.emit(task_id)
                    logger.info("Task run requested via API: %s", task.name)
                    return {"success": True, "message": f"Task {task.name} started"}

            return {"success": False, "error": f"Task not found: {task_id}"}

        except Exception as e:
            logger.exception("Failed to run task via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_enable_task(self, task_id: UUID, enabled: bool) -> dict[str, object]:
        """Enable or disable a task via REST API.

        Args:
            task_id: Task UUID to enable/disable.
            enabled: True to enable, False to disable.

        Returns:
            Result dictionary with success status.
        """
        try:
            for task in self.tasks:
                if task.id == task_id:
                    task.enabled = enabled
                    self.storage.save_task(task)
                    self._reschedule_task(task)
                    # Emit signal for thread-safe UI refresh
                    self._signal_bridge.state_changed.emit()
                    action = "enabled" if enabled else "disabled"
                    logger.info("Task %s via API: %s", action, task.name)
                    return {"success": True, "message": f"Task {task.name} {action}"}

            return {"success": False, "error": f"Task not found: {task_id}"}

        except Exception as e:
            logger.exception("Failed to enable/disable task via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_stop_run(self, run_id: UUID) -> dict[str, object]:
        """Stop a running task via REST API.

        Args:
            run_id: Run UUID to stop.

        Returns:
            Result dictionary with success status.
        """
        try:
            stopped = self._scheduler.stop_run(run_id)

            if stopped:
                logger.info("Run stopped via API: %s", run_id)
                return {"success": True, "message": f"Run {run_id} stopped"}

            # Mark as failed if no process found
            from datetime import UTC, datetime

            from claude_code_scheduler.models.enums import RunStatus

            for i, run in enumerate(self.runs):
                if run.id == run_id:
                    run.status = RunStatus.FAILED
                    run.end_time = datetime.now(UTC)
                    run.errors = (run.errors or "") + "\n[FAILED] No running process found"
                    self.runs[i] = run
                    self.storage.save_run(run)
                    self.runs_panel.set_runs(self.runs)
                    logger.warning("Run marked as failed via API: %s", run_id)
                    return {"success": True, "message": f"Run {run_id} marked as failed"}

            return {"success": False, "error": f"Run not found: {run_id}"}

        except Exception as e:
            logger.exception("Failed to stop run via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_restart_run(self, run_id: UUID) -> dict[str, object]:
        """Restart a task from a run via REST API.

        Args:
            run_id: Run UUID to restart.

        Returns:
            Result dictionary with success status.
        """
        try:
            # Find the run
            run = None
            for r in self.runs:
                if r.id == run_id:
                    run = r
                    break

            if not run:
                return {"success": False, "error": f"Run not found: {run_id}"}

            # Find and run the task
            for task in self.tasks:
                if task.id == run.task_id:
                    self._scheduler.run_task_now(task)
                    logger.info("Task restarted via API: %s", task.name)
                    return {"success": True, "message": f"Task {task.name} restarted"}

            return {"success": False, "error": f"Task not found for run: {run_id}"}

        except Exception as e:
            logger.exception("Failed to restart run via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_delete_run(self, run_id: UUID) -> dict[str, object]:
        """Delete a run record via REST API.

        Args:
            run_id: Run UUID to delete.

        Returns:
            Result dictionary with success status.
        """
        try:
            # Check if run is currently running
            for run in self.runs:
                if run.id == run_id:
                    if run.status.value == "running":
                        return {
                            "success": False,
                            "error": "Cannot delete a running task. Stop it first.",
                        }
                    break

            # Remove from runs list
            original_count = len(self.runs)
            self.runs = [r for r in self.runs if r.id != run_id]

            if len(self.runs) == original_count:
                return {"success": False, "error": f"Run not found: {run_id}"}

            # Save and refresh
            self.storage.save_runs(self.runs)
            self.runs_panel.set_runs(self.runs)
            self.logs_panel.clear()

            logger.info("Run deleted via API: %s", run_id)
            return {"success": True, "message": f"Run {run_id} deleted"}

        except Exception as e:
            logger.exception("Failed to delete run via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_list_profiles(self) -> dict[str, object]:
        """List all profiles via REST API.

        Returns:
            Dictionary with list of profile objects.
        """
        try:

            def serialize_profile(profile: Profile) -> dict[str, object]:
                return {
                    "id": str(profile.id),
                    "name": profile.name,
                    "description": profile.description,
                    "env_vars": [ev.to_dict() for ev in profile.env_vars],
                    "created_at": profile.created_at.isoformat(),
                    "updated_at": profile.updated_at.isoformat(),
                }

            return {"profiles": [serialize_profile(p) for p in self.profiles]}
        except Exception as e:
            logger.exception("Failed to list profiles via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_get_profile(self, profile_id: UUID) -> dict[str, object]:
        """Get a single profile via REST API.

        Args:
            profile_id: Profile UUID to retrieve.

        Returns:
            Result dictionary with profile data.
        """
        try:
            for profile in self.profiles:
                if profile.id == profile_id:
                    return {
                        "success": True,
                        "profile": {
                            "id": str(profile.id),
                            "name": profile.name,
                            "description": profile.description,
                            "env_vars": [ev.to_dict() for ev in profile.env_vars],
                            "created_at": profile.created_at.isoformat(),
                            "updated_at": profile.updated_at.isoformat(),
                        },
                    }
            return {"success": False, "error": f"Profile not found: {profile_id}"}
        except Exception as e:
            logger.exception("Failed to get profile via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_create_profile(self, data: dict[str, object]) -> dict[str, object]:
        """Create a new profile via REST API.

        Args:
            data: Profile data with name, description, env_vars.

        Returns:
            Result dictionary with created profile.
        """
        from datetime import datetime

        from claude_code_scheduler.models.enums import EnvVarSource
        from claude_code_scheduler.models.profile import EnvVar

        try:
            # Validate required fields
            name = data.get("name")
            if not name:
                return {"success": False, "error": "Profile name is required"}

            # Parse env vars if provided
            env_vars: list[EnvVar] = []
            if "env_vars" in data and isinstance(data["env_vars"], list):
                for ev_data in data["env_vars"]:
                    if isinstance(ev_data, dict):
                        env_vars.append(
                            EnvVar(
                                name=str(ev_data.get("name", "")),
                                source=EnvVarSource(ev_data.get("source", "static")),
                                value=str(ev_data.get("value", "")),
                                config=ev_data.get("config"),
                            )
                        )

            # Create profile
            profile = Profile(
                name=str(name),
                description=str(data.get("description", "")),
                env_vars=env_vars,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # Add to list and save
            self.profiles.append(profile)
            self.storage.save_profiles(self.profiles)
            self.task_editor_panel.set_profiles(self.profiles)

            logger.info("Profile created via API: %s", profile.name)
            return {
                "success": True,
                "profile": {
                    "id": str(profile.id),
                    "name": profile.name,
                    "description": profile.description,
                    "env_vars": [ev.to_dict() for ev in profile.env_vars],
                    "created_at": profile.created_at.isoformat(),
                    "updated_at": profile.updated_at.isoformat(),
                },
            }
        except Exception as e:
            logger.exception("Failed to create profile via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_update_profile(self, profile_id: UUID, data: dict[str, object]) -> dict[str, object]:
        """Update a profile via REST API.

        Args:
            profile_id: Profile UUID to update.
            data: Partial update data.

        Returns:
            Result dictionary with updated profile.
        """
        from datetime import datetime

        from claude_code_scheduler.models.enums import EnvVarSource
        from claude_code_scheduler.models.profile import EnvVar

        try:
            # Find profile
            profile: Profile | None = None
            for p in self.profiles:
                if p.id == profile_id:
                    profile = p
                    break

            if not profile:
                return {"success": False, "error": f"Profile not found: {profile_id}"}

            # Apply updates
            if "name" in data:
                profile.name = str(data["name"])
            if "description" in data:
                profile.description = str(data["description"])
            if "env_vars" in data and isinstance(data["env_vars"], list):
                env_vars: list[EnvVar] = []
                for ev_data in data["env_vars"]:
                    if isinstance(ev_data, dict):
                        env_vars.append(
                            EnvVar(
                                name=str(ev_data.get("name", "")),
                                source=EnvVarSource(ev_data.get("source", "static")),
                                value=str(ev_data.get("value", "")),
                                config=ev_data.get("config"),
                            )
                        )
                profile.env_vars = env_vars

            profile.updated_at = datetime.now()

            # Save and refresh
            self.storage.save_profiles(self.profiles)
            self.task_editor_panel.set_profiles(self.profiles)

            logger.info("Profile updated via API: %s", profile.name)
            return {
                "success": True,
                "profile": {
                    "id": str(profile.id),
                    "name": profile.name,
                    "description": profile.description,
                    "env_vars": [ev.to_dict() for ev in profile.env_vars],
                    "created_at": profile.created_at.isoformat(),
                    "updated_at": profile.updated_at.isoformat(),
                },
            }
        except Exception as e:
            logger.exception("Failed to update profile via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_delete_profile(self, profile_id: UUID) -> dict[str, object]:
        """Delete a profile via REST API.

        Args:
            profile_id: Profile UUID to delete.

        Returns:
            Result dictionary with success status.
        """
        try:
            # Find and remove profile
            original_count = len(self.profiles)
            self.profiles = [p for p in self.profiles if p.id != profile_id]

            if len(self.profiles) == original_count:
                return {"success": False, "error": f"Profile not found: {profile_id}"}

            # Save and refresh
            self.storage.save_profiles(self.profiles)
            self.task_editor_panel.set_profiles(self.profiles)

            logger.info("Profile deleted via API: %s", profile_id)
            return {"success": True, "message": f"Profile {profile_id} deleted"}

        except Exception as e:
            logger.exception("Failed to delete profile via API: %s", e)
            return {"success": False, "error": str(e)}

    # Job API methods

    def _api_list_jobs(self) -> dict[str, object]:
        """List all jobs via REST API."""
        try:
            return {"jobs": [job.to_dict() for job in self.jobs]}
        except Exception as e:
            logger.exception("Failed to list jobs via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_get_job(self, job_id: UUID) -> dict[str, object]:
        """Get a single job via REST API."""
        try:
            for job in self.jobs:
                if job.id == job_id:
                    return {"success": True, "job": job.to_dict()}
            return {"success": False, "error": f"Job not found: {job_id}"}
        except Exception as e:
            logger.exception("Failed to get job via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_get_job_tasks(self, job_id: UUID) -> dict[str, object]:
        """Get tasks for a specific job via REST API."""
        try:
            # Verify job exists
            job_exists = any(j.id == job_id for j in self.jobs)
            if not job_exists:
                return {"success": False, "error": f"Job not found: {job_id}"}

            # Get tasks for this job
            job_tasks = [t for t in self.tasks if t.job_id == job_id]
            return {"tasks": [t.to_dict() for t in job_tasks]}
        except Exception as e:
            logger.exception("Failed to get job tasks via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_create_job(self, data: dict[str, object]) -> dict[str, object]:
        """Create a new job via REST API."""
        from datetime import datetime

        from claude_code_scheduler.models.job import JobWorkingDirectory

        try:
            name = data.get("name")
            if not name:
                return {"success": False, "error": "Job name is required"}

            # Validate profile if provided
            profile_id = data.get("profile")
            if profile_id is not None:
                if not isinstance(profile_id, str):
                    return {"success": False, "error": "Profile ID must be a string"}
                try:
                    profile_uuid = UUID(profile_id)
                    profile_exists = any(p.id == profile_uuid for p in self.profiles)
                    if not profile_exists:
                        return {"success": False, "error": f"Profile not found: {profile_id}"}
                except ValueError:
                    return {"success": False, "error": "Invalid profile UUID format"}

            # Parse working_directory if provided
            working_directory = JobWorkingDirectory()
            if "working_directory" in data:
                wd_data = data["working_directory"]
                if isinstance(wd_data, dict):
                    working_directory = JobWorkingDirectory.from_dict(wd_data)

            job = Job(
                name=str(name),
                description=str(data.get("description", "")),
                status=JobStatus.PENDING,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                working_directory=working_directory,
            )

            self.jobs.append(job)
            self.storage.save_jobs(self.jobs)
            # Emit signal for thread-safe UI refresh
            self._signal_bridge.state_changed.emit()

            logger.info("Job created via API: %s", job.name)
            return {"success": True, "job": job.to_dict()}
        except Exception as e:
            logger.exception("Failed to create job via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_update_job(self, job_id: UUID, data: dict[str, object]) -> dict[str, object]:
        """Update a job via REST API."""
        from datetime import datetime

        from claude_code_scheduler.models.job import JobWorkingDirectory

        try:
            for job in self.jobs:
                if job.id == job_id:
                    # Validate profile if provided
                    profile_id = data.get("profile")
                    if profile_id is not None:
                        if not isinstance(profile_id, str):
                            return {"success": False, "error": "Profile ID must be a string"}
                        try:
                            profile_uuid = UUID(profile_id)
                            profile_exists = any(p.id == profile_uuid for p in self.profiles)
                            if not profile_exists:
                                return {
                                    "success": False,
                                    "error": f"Profile not found: {profile_id}",
                                }
                        except ValueError:
                            return {"success": False, "error": "Invalid profile UUID format"}

                    if "name" in data:
                        job.name = str(data["name"])
                    if "description" in data:
                        job.description = str(data["description"])
                    if "status" in data:
                        job.status = JobStatus(str(data["status"]))
                    if "task_order" in data:
                        # Convert string UUIDs to UUID objects
                        task_order_raw = data["task_order"]
                        if isinstance(task_order_raw, list):
                            job.task_order = [UUID(str(tid)) for tid in task_order_raw]
                    if "working_directory" in data:
                        wd_data = data["working_directory"]
                        if isinstance(wd_data, dict):
                            job.working_directory = JobWorkingDirectory.from_dict(wd_data)
                    job.updated_at = datetime.now()

                    self.storage.save_jobs(self.jobs)
                    # Emit signal for thread-safe UI refresh
                    self._signal_bridge.state_changed.emit()
                    logger.info("Job updated via API: %s", job.name)
                    return {"success": True, "job": job.to_dict()}

            return {"success": False, "error": f"Job not found: {job_id}"}
        except Exception as e:
            logger.exception("Failed to update job via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_delete_job(self, job_id: UUID) -> dict[str, object]:
        """Delete a job via REST API (cascade deletes tasks and runs, keeps worktree)."""
        try:
            job_to_delete = next((j for j in self.jobs if j.id == job_id), None)

            if not job_to_delete:
                return {"success": False, "error": f"Job not found: {job_id}"}

            # Cascade delete: remove tasks and their runs
            tasks_to_delete = [t for t in self.tasks if t.job_id == job_id]
            task_ids = {t.id for t in tasks_to_delete}
            runs_to_delete = [r for r in self.runs if r.task_id in task_ids]

            # Remove runs and tasks
            self.runs = [r for r in self.runs if r.task_id not in task_ids]
            self.tasks = [t for t in self.tasks if t.job_id != job_id]

            # Delete the job (worktree is intentionally kept on disk)
            self.jobs = [j for j in self.jobs if j.id != job_id]

            # Save all changes
            self.storage.save_jobs(self.jobs)
            self.storage.save_tasks(self.tasks)
            self.storage.save_runs(self.runs)

            logger.info(
                "Job deleted via API: %s (deleted %d tasks, %d runs, kept worktree)",
                job_id,
                len(tasks_to_delete),
                len(runs_to_delete),
            )
            return {
                "success": True,
                "message": f"Job {job_id} deleted",
                "tasks_deleted": len(tasks_to_delete),
                "runs_deleted": len(runs_to_delete),
                "worktree_kept": job_to_delete.working_directory.use_git_worktree,
            }

        except Exception as e:
            logger.exception("Failed to delete job via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_run_job(self, job_id: UUID) -> dict[str, object]:
        """Run a job (start sequential task execution) via REST API.

        Uses Qt signal to marshal the call to the main thread, since APScheduler's
        QtScheduler requires job additions from the Qt thread.

        Args:
            job_id: Job UUID to run.

        Returns:
            Result dictionary with success status.
        """
        try:
            job = next((j for j in self.jobs if j.id == job_id), None)
            if not job:
                return {"success": False, "error": f"Job not found: {job_id}"}

            if not job.task_order:
                return {"success": False, "error": f"Job {job.name} has no tasks"}

            if self._sequential_scheduler.is_job_running(job_id):
                return {"success": False, "error": f"Job {job.name} is already running"}

            # Emit signal to run job on main Qt thread
            # Direct call to scheduler from HTTP thread doesn't work with QtScheduler
            self._signal_bridge.api_run_job.emit(job_id)
            logger.info("Job run requested via API: %s", job.name)
            return {
                "success": True,
                "message": f"Job {job.name} started",
                "job_id": str(job_id),
            }

        except Exception as e:
            logger.exception("Failed to run job via API: %s", e)
            return {"success": False, "error": str(e)}

    def _api_stop_job(self, job_id: UUID) -> dict[str, object]:
        """Stop a running job via REST API.

        Args:
            job_id: Job UUID to stop.

        Returns:
            Result dictionary with success status.
        """
        try:
            job = next((j for j in self.jobs if j.id == job_id), None)
            if not job:
                return {"success": False, "error": f"Job not found: {job_id}"}

            if not self._sequential_scheduler.is_job_running(job_id):
                return {"success": False, "error": f"Job {job.name} is not running"}

            # Stop the job sequence
            stopped = self._sequential_scheduler.stop_job(job_id, JobStatus.FAILED)
            if stopped:
                logger.info("Job stopped via API: %s", job.name)
                return {
                    "success": True,
                    "message": f"Job {job.name} stopped",
                    "job_id": str(job_id),
                }
            else:
                return {"success": False, "error": f"Failed to stop job {job.name}"}

        except Exception as e:
            logger.exception("Failed to stop job via API: %s", e)
            return {"success": False, "error": str(e)}

    def _resolve_profile(self, profile_id: str) -> Profile | None:
        """Resolve a profile by its ID string.

        Args:
            profile_id: The profile ID as string.

        Returns:
            Profile object or None if not found.
        """
        from uuid import UUID

        try:
            target_id = UUID(profile_id)
            for profile in self.profiles:
                if profile.id == target_id:
                    return profile
        except ValueError:
            logger.warning("Invalid profile ID format: %s", profile_id)
        return None

    def _resolve_task_by_id(self, task_id: UUID) -> Task | None:
        """Resolve a task by UUID.

        Args:
            task_id: The task UUID.

        Returns:
            Task object or None if not found.
        """
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def _resolve_job_by_id(self, job_id: UUID) -> Job | None:
        """Resolve a job by UUID.

        Args:
            job_id: The job UUID.

        Returns:
            Job object or None if not found.
        """
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None

    def _update_job_status(self, job_id: UUID, status: JobStatus) -> None:
        """Update job status and save.

        Args:
            job_id: The job UUID.
            status: New status.
        """
        for job in self.jobs:
            if job.id == job_id:
                job.status = status
                self.storage.save_jobs(self.jobs)
                self._refresh_ui()
                logger.info("Job %s status updated to %s", job.name, status.value)
                return

    def _on_job_sequence_started(self, job_id: UUID) -> None:
        """Handle job sequence started event."""
        job = self._resolve_job_by_id(job_id)
        if job:
            logger.info("Job sequence started: %s", job.name)

    def _on_job_sequence_progress(self, job_id: UUID, current: int, total: int) -> None:
        """Handle job sequence progress event."""
        job = self._resolve_job_by_id(job_id)
        if job:
            logger.info("Job %s progress: %d/%d", job.name, current, total)

    def _on_job_sequence_completed(self, job_id: UUID, status: JobStatus) -> None:
        """Handle job sequence completed event."""
        job = self._resolve_job_by_id(job_id)
        if job:
            logger.info("Job sequence completed: %s (status=%s)", job.name, status.value)

    def _on_task_saved(self, task: Task) -> None:
        """Handle task saved from editor."""
        logger.info("Task saved: %s", task.name)

        # Check if task exists
        found = False
        for i, t in enumerate(self.tasks):
            if t.id == task.id:
                self.tasks[i] = task
                found = True
                break

        if not found:
            self.tasks.append(task)

        # Save and refresh
        self.storage.save_task(task)
        self._refresh_ui()

        # Reschedule task (handles both new and updated tasks)
        self._reschedule_task(task)

        # Select the saved task
        self.task_list_panel.select_task(task.id)

    def _load_state(self) -> None:
        """Load application state from storage.

        Note: Settings are loaded in __init__ before scheduler creation.
        """
        logger.info("Loading application state...")
        self.tasks = self.storage.load_tasks()
        self.runs = self.storage.load_runs()
        self.profiles = self.storage.load_profiles()
        self.jobs = self.storage.load_jobs()
        logger.info(
            "Loaded %d tasks, %d runs, %d profiles, %d jobs",
            len(self.tasks),
            len(self.runs),
            len(self.profiles),
            len(self.jobs),
        )

    def _save_state(self) -> None:
        """Save application state to storage."""
        logger.info("Saving application state...")
        self.storage.save_tasks(self.tasks)
        self.storage.save_runs(self.runs)
        self.storage.save_profiles(self.profiles)
        self.storage.save_settings(self.settings)
        logger.info("State saved")

    def _save_window_geometry(self) -> None:
        """Save window geometry and splitter sizes to settings."""
        # Save window state
        self.settings.window_maximized = self.isMaximized()

        # Only save position/size if not maximized (to restore normal state)
        if not self.isMaximized():
            geometry = self.geometry()
            self.settings.window_x = geometry.x()
            self.settings.window_y = geometry.y()
            self.settings.window_width = geometry.width()
            self.settings.window_height = geometry.height()

        # Save splitter sizes
        self.settings.main_splitter_sizes = self.main_splitter.sizes()
        self.settings.right_splitter_sizes = self.right_splitter.sizes()

        self.storage.save_settings(self.settings)
        logger.debug("Window geometry saved")

    def closeEvent(self, event: QCloseEvent | None) -> None:  # noqa: N802
        """Handle window close event."""
        self._stop_services()
        self._save_state()
        self._save_window_geometry()
        if event:
            event.accept()

    def _start_services(self) -> None:
        """Start scheduler, file watcher, and debug server."""
        logger.info("Starting services...")
        self._scheduler.start()
        self._file_watcher.start()
        self._debug_server.start()

        # Schedule all enabled tasks
        for task in self.tasks:
            if task.enabled:
                if task.schedule.schedule_type == ScheduleType.FILE_WATCH:
                    self._file_watcher.watch_task(task)
                else:
                    self._scheduler.schedule_task(task)

        logger.info("Services started")

    def _stop_services(self) -> None:
        """Stop scheduler, file watcher, and debug server."""
        logger.info("Stopping services...")
        self._scheduler.stop()
        self._file_watcher.stop()
        self._debug_server.stop()
        logger.info("Services stopped")

    def _on_run_started(self, run: Run) -> None:
        """Handle run started callback from executor.

        Args:
            run: The run that started.
        """
        logger.info("Run started: %s (%s)", run.task_name, run.id)
        self.runs.insert(0, run)  # Add to front
        self.runs_panel.set_runs(self.runs)
        self.task_list_panel.set_runs(self.runs)  # Update task statistics
        self.runs_panel.select_run(run.id)
        self.logs_panel.show_run_logs(run)
        # Prepare live output tab
        self.logs_panel.start_live_output(run.task_name or "Unknown Task")

    def _on_output_received(self, run_id: UUID, line: str) -> None:
        """Handle streaming output from executor.

        Args:
            run_id: UUID of the run producing output.
            line: Line of output from the subprocess.
        """
        # Only append if this is the currently displayed run
        if self.logs_panel.current_run and self.logs_panel.current_run.id == run_id:
            self.logs_panel.append_live(line)

    def _on_run_completed(self, run: Run) -> None:
        """Handle run completed callback from executor.

        Args:
            run: The completed run.
        """
        logger.info("Run completed: %s (status=%s)", run.task_name, run.status.value)

        # Update the run in our list
        for i, r in enumerate(self.runs):
            if r.id == run.id:
                self.runs[i] = run
                break

        # Save and refresh UI
        self.storage.save_run(run)
        self.runs_panel.set_runs(self.runs)
        self.task_list_panel.set_runs(self.runs)  # Update task statistics
        self.logs_panel.show_run_logs(run)

        # Notify sequential scheduler of run completion
        self._sequential_scheduler.on_run_completed(run)

    def _on_file_watch_triggered(self, task: Task) -> None:
        """Handle file watch trigger.

        Args:
            task: The task to execute.
        """
        logger.info("File watch triggered for task: %s", task.name)
        self._scheduler.run_task_now(task)

    def _reschedule_task(self, task: Task) -> None:
        """Reschedule a task after it has been updated.

        Args:
            task: The updated task.
        """
        # Remove from both scheduler and file watcher
        self._scheduler.unschedule_task(task.id)
        self._file_watcher.unwatch_task(task.id)

        if not task.enabled:
            return

        # Re-add based on schedule type
        if task.schedule.schedule_type == ScheduleType.FILE_WATCH:
            self._file_watcher.watch_task(task)
        else:
            self._scheduler.schedule_task(task)
