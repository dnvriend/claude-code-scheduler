"""
Task Editor Panel - Middle panel for viewing and editing task details.

Supports two modes:
- View mode: Read-only display of task details
- Edit mode: Full form for creating/editing tasks

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from datetime import time
from uuid import UUID

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from claude_code_scheduler.models.enums import ScheduleType
from claude_code_scheduler.models.job import Job
from claude_code_scheduler.models.profile import Profile
from claude_code_scheduler.models.task import ScheduleConfig, Task
from claude_code_scheduler.ui.widgets.advanced_options_panel import (
    AdvancedOptionsPanel,
)
from claude_code_scheduler.ui.widgets.calendar_schedule_panel import (
    CalendarSchedulePanel,
)
from claude_code_scheduler.ui.widgets.collapsible_widget import CollapsibleWidget
from claude_code_scheduler.ui.widgets.command_type_selector import (
    CommandTypeSelector,
)
from claude_code_scheduler.ui.widgets.file_watch_schedule_panel import (
    FileWatchSchedulePanel,
)
from claude_code_scheduler.ui.widgets.interval_schedule_panel import (
    IntervalSchedulePanel,
)
from claude_code_scheduler.ui.widgets.schedule_type_selector import (
    ScheduleTypeSelector,
)


class TaskEditorPanel(QFrame):
    """Middle panel for viewing and editing task configuration."""

    # Signals
    task_saved = pyqtSignal(Task)
    task_cancelled = pyqtSignal()
    edit_requested = pyqtSignal(UUID)
    manage_profiles_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("taskEditorPanel")
        self.current_task: Task | None = None
        self.edit_mode = False
        self.profiles: list[Profile] = []
        self.jobs: list[Job] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel layout."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header
        self.header = self._create_header()
        self.main_layout.addWidget(self.header)

        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Content container
        self.content_container = QWidget()
        self.content_container.setObjectName("taskEditorContent")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(16)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state placeholder
        self.empty_state = self._create_empty_state()
        self.content_layout.addWidget(self.empty_state)

        # View mode container
        self.view_container = self._create_view_mode()
        self.view_container.hide()
        self.content_layout.addWidget(self.view_container)

        # Edit mode container
        self.edit_container = self._create_edit_mode()
        self.edit_container.hide()
        self.content_layout.addWidget(self.edit_container)

        scroll_area.setWidget(self.content_container)
        self.main_layout.addWidget(scroll_area, 1)

    def _create_header(self) -> QWidget:
        """Create the panel header."""
        header = QWidget()
        header.setObjectName("panelHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 16, 16, 16)

        self.title_label = QLabel("Task")
        self.title_label.setObjectName("panelTitle")
        layout.addWidget(self.title_label)

        layout.addStretch()

        # Action buttons
        self.header_actions = QWidget()
        self.header_actions_layout = QHBoxLayout(self.header_actions)
        self.header_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.header_actions_layout.setSpacing(8)

        # Edit button (view mode)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("secondaryButton")
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        self.edit_btn.hide()
        self.header_actions_layout.addWidget(self.edit_btn)

        # Save button (edit mode)
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.save_btn.hide()
        self.header_actions_layout.addWidget(self.save_btn)

        # Cancel button (edit mode)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        self.cancel_btn.hide()
        self.header_actions_layout.addWidget(self.cancel_btn)

        layout.addWidget(self.header_actions)

        return header

    def _create_empty_state(self) -> QWidget:
        """Create the empty state widget shown when no task is selected."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("Select a task to view details\nor create a new task")
        label.setObjectName("emptyStateLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        return widget

    def _create_view_mode(self) -> QWidget:
        """Create the view mode container with read-only fields."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Name section
        name_section = self._create_section("Name")
        self.view_name = QLabel()
        self.view_name.setObjectName("viewValue")
        name_section.section_layout.addWidget(self.view_name)  # type: ignore[attr-defined]
        layout.addWidget(name_section)

        # Model section
        model_section = self._create_section("Model")
        self.view_model = QLabel()
        self.view_model.setObjectName("modelBadge")
        model_section.section_layout.addWidget(self.view_model)  # type: ignore[attr-defined]
        layout.addWidget(model_section)

        # Profile section
        profile_section = self._create_section("Profile")
        self.view_profile = QLabel()
        self.view_profile.setObjectName("viewValue")
        profile_section.section_layout.addWidget(self.view_profile)  # type: ignore[attr-defined]
        layout.addWidget(profile_section)

        # Schedule section
        schedule_section = self._create_section("Schedule")
        self.view_schedule = QLabel()
        self.view_schedule.setObjectName("viewValue")
        schedule_section.section_layout.addWidget(self.view_schedule)  # type: ignore[attr-defined]
        layout.addWidget(schedule_section)

        # Prompt section
        prompt_section = self._create_section("Prompt")
        self.view_prompt = QLabel()
        self.view_prompt.setObjectName("viewValue")
        self.view_prompt.setWordWrap(True)
        prompt_section.section_layout.addWidget(self.view_prompt)  # type: ignore[attr-defined]
        layout.addWidget(prompt_section)

        # Working Directory section
        wd_section = self._create_section("Working Directory")
        self.view_working_dir = QLabel()
        self.view_working_dir.setObjectName("viewValue")
        wd_section.section_layout.addWidget(self.view_working_dir)  # type: ignore[attr-defined]
        layout.addWidget(wd_section)

        # Permissions section
        perms_section = self._create_section("Permissions")
        self.view_permissions = QLabel()
        self.view_permissions.setObjectName("viewValue")
        perms_section.section_layout.addWidget(self.view_permissions)  # type: ignore[attr-defined]
        layout.addWidget(perms_section)

        # Session section
        session_section = self._create_section("Session Mode")
        self.view_session = QLabel()
        self.view_session.setObjectName("viewValue")
        session_section.section_layout.addWidget(self.view_session)  # type: ignore[attr-defined]
        layout.addWidget(session_section)

        # Git section
        git_section = self._create_section("Git")
        self.view_commit_on_success = QLabel()
        self.view_commit_on_success.setObjectName("viewValue")
        git_section.section_layout.addWidget(self.view_commit_on_success)  # type: ignore[attr-defined]
        layout.addWidget(git_section)

        layout.addStretch()
        return widget

    def _create_section(self, title: str) -> QWidget:
        """Create a labeled section widget."""
        widget = QWidget()
        section_layout = QVBoxLayout(widget)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(4)

        label = QLabel(title)
        label.setObjectName("sectionLabel")
        section_layout.addWidget(label)

        # Store layout reference for adding content
        widget.section_layout = section_layout  # type: ignore[attr-defined]

        return widget

    def _create_edit_mode(self) -> QWidget:
        """Create the edit mode container with form fields."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Form layout for fields - use VBox with label above field for full width
        # Name field
        name_label = QLabel("Task Name")
        name_label.setObjectName("fieldLabel")
        layout.addWidget(name_label)
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Enter task name")
        layout.addWidget(self.edit_name)

        # Model and Permissions row (side by side)
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        model_container = QVBoxLayout()
        model_label = QLabel("Model")
        model_label.setObjectName("fieldLabel")
        model_container.addWidget(model_label)
        self.edit_model = QComboBox()
        self.edit_model.addItems(["opus", "sonnet", "haiku"])
        model_container.addWidget(self.edit_model)
        row1.addLayout(model_container)

        perms_container = QVBoxLayout()
        perms_label = QLabel("Permissions")
        perms_label.setObjectName("fieldLabel")
        perms_container.addWidget(perms_label)
        self.edit_permissions = QComboBox()
        self.edit_permissions.addItems(["default", "bypass", "acceptEdits", "plan"])
        perms_container.addWidget(self.edit_permissions)
        row1.addLayout(perms_container)

        layout.addLayout(row1)

        # Profile row (selector + manage button)
        profile_row = QHBoxLayout()
        profile_row.setSpacing(8)

        profile_container = QVBoxLayout()
        profile_label = QLabel("Profile")
        profile_label.setObjectName("fieldLabel")
        profile_container.addWidget(profile_label)
        self.edit_profile = QComboBox()
        self.edit_profile.addItem("(None)", None)  # Default option
        profile_container.addWidget(self.edit_profile)
        profile_row.addLayout(profile_container, 1)

        manage_btn_container = QVBoxLayout()
        manage_btn_spacer = QLabel("")  # Align with combobox
        manage_btn_spacer.setObjectName("fieldLabel")
        manage_btn_container.addWidget(manage_btn_spacer)
        self.manage_profiles_btn = QPushButton("Manage...")
        self.manage_profiles_btn.setObjectName("secondaryButton")
        self.manage_profiles_btn.clicked.connect(self.manage_profiles_requested.emit)
        manage_btn_container.addWidget(self.manage_profiles_btn)
        profile_row.addLayout(manage_btn_container)

        layout.addLayout(profile_row)

        # Job field (assign task to a job)
        job_label = QLabel("Job")
        job_label.setObjectName("fieldLabel")
        layout.addWidget(job_label)
        self.edit_job = QComboBox()
        self.edit_job.addItem("(None)", None)  # Default option - unassigned
        self.edit_job.currentIndexChanged.connect(self._on_job_changed)
        layout.addWidget(self.edit_job)

        # Session field
        session_label = QLabel("Session Mode")
        session_label.setObjectName("fieldLabel")
        layout.addWidget(session_label)
        self.edit_session = QComboBox()
        self.edit_session.addItems(["new", "reuse", "fork"])
        layout.addWidget(self.edit_session)

        # Working directory (read-only - inherited from Job)
        wd_label = QLabel("Working Directory (from Job)")
        wd_label.setObjectName("fieldLabel")
        layout.addWidget(wd_label)
        self.edit_working_dir_display = QLabel("(select a job)")
        self.edit_working_dir_display.setObjectName("viewValue")
        layout.addWidget(self.edit_working_dir_display)

        # Command type selector (Claude Prompt vs Existing Command)
        self.command_type_selector = CommandTypeSelector()
        self.command_type_selector.command_type_changed.connect(self._on_command_type_changed)
        layout.addWidget(self.command_type_selector)

        # Stacked widget for command input (switches based on command type)
        self.command_stack = QStackedWidget()

        # Index 0: Prompt text area (for Claude Prompt)
        self.edit_prompt = QPlainTextEdit()
        self.edit_prompt.setPlaceholderText("Enter the prompt for Claude...")
        self.edit_prompt.setMinimumHeight(120)
        self.edit_prompt.setMaximumHeight(150)
        self.command_stack.addWidget(self.edit_prompt)

        # Index 1: Command line edit (for Existing Command / slash command)
        # Wrap in a container with top alignment to prevent stretching
        slash_container = QWidget()
        slash_layout = QVBoxLayout(slash_container)
        slash_layout.setContentsMargins(0, 0, 0, 0)
        slash_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.edit_slash_command = QLineEdit()
        self.edit_slash_command.setPlaceholderText("/commit, /review-pr, /my-custom-command...")
        self.edit_slash_command.setFixedHeight(40)
        slash_layout.addWidget(self.edit_slash_command)
        slash_layout.addStretch()
        self.command_stack.addWidget(slash_container)

        layout.addWidget(self.command_stack)

        # Schedule section
        schedule_label = QLabel("Schedule:")
        schedule_label.setObjectName("sectionLabel")
        layout.addWidget(schedule_label)

        # Schedule type selector
        self.schedule_type_selector = ScheduleTypeSelector()
        self.schedule_type_selector.schedule_type_changed.connect(self._on_schedule_type_changed)
        layout.addWidget(self.schedule_type_selector)

        # Stacked widget for schedule panels
        self.schedule_stack = QStackedWidget()

        # Empty panel for Manual/Startup (no config needed)
        empty_panel = QWidget()
        empty_layout = QVBoxLayout(empty_panel)
        empty_label = QLabel("No additional configuration needed.")
        empty_label.setObjectName("helpLabel")
        empty_layout.addWidget(empty_label)
        empty_layout.addStretch()
        self.schedule_stack.addWidget(empty_panel)  # Index 0: Manual/Startup

        # Calendar panel
        self.calendar_panel = CalendarSchedulePanel()
        self.schedule_stack.addWidget(self.calendar_panel)  # Index 1: Calendar

        # Interval panel
        self.interval_panel = IntervalSchedulePanel()
        self.schedule_stack.addWidget(self.interval_panel)  # Index 2: Interval

        # File watch panel
        self.file_watch_panel = FileWatchSchedulePanel()
        self.schedule_stack.addWidget(self.file_watch_panel)  # Index 3: File Watch

        layout.addWidget(self.schedule_stack)

        # Separator line
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setObjectName("sectionSeparator")
        layout.addWidget(separator1)

        # Advanced Options section (collapsible)
        self.advanced_collapsible = CollapsibleWidget("Advanced Options", collapsed=True)
        self.advanced_options_panel = AdvancedOptionsPanel()
        self.advanced_collapsible.set_content_widget(self.advanced_options_panel)
        layout.addWidget(self.advanced_collapsible)

        # Separator line
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setObjectName("sectionSeparator")
        layout.addWidget(separator2)

        # Task Notifications section (always visible)
        notif_label = QLabel("Task Notifications")
        notif_label.setObjectName("sectionLabel")
        layout.addWidget(notif_label)

        self.notify_start_cb = QCheckBox("Notify on start")
        layout.addWidget(self.notify_start_cb)

        self.notify_end_cb = QCheckBox("Notify on completion")
        self.notify_end_cb.setChecked(True)
        layout.addWidget(self.notify_end_cb)

        self.notify_failure_cb = QCheckBox("Notify on failure")
        self.notify_failure_cb.setChecked(True)
        layout.addWidget(self.notify_failure_cb)

        # Git section
        git_label = QLabel("Git")
        git_label.setObjectName("sectionLabel")
        layout.addWidget(git_label)

        self.commit_on_success_cb = QCheckBox("Commit on success")
        self.commit_on_success_cb.setChecked(True)
        layout.addWidget(self.commit_on_success_cb)

        layout.addStretch()
        return widget

    def _on_schedule_type_changed(self, schedule_type: ScheduleType) -> None:
        """Handle schedule type change."""
        if schedule_type in (ScheduleType.MANUAL, ScheduleType.STARTUP, ScheduleType.SEQUENTIAL):
            self.schedule_stack.setCurrentIndex(0)  # Empty/minimal panel
        elif schedule_type == ScheduleType.CALENDAR:
            self.schedule_stack.setCurrentIndex(1)
        elif schedule_type == ScheduleType.INTERVAL:
            self.schedule_stack.setCurrentIndex(2)
        elif schedule_type == ScheduleType.FILE_WATCH:
            self.schedule_stack.setCurrentIndex(3)

    def _on_job_changed(self, index: int) -> None:
        """Handle job selection change - enable/disable Sequential schedule option."""
        job_id_str = self.edit_job.currentData()
        has_job = job_id_str is not None
        self.schedule_type_selector.set_has_job(has_job)

        # Update working directory display based on selected job
        job_id = UUID(job_id_str) if job_id_str else None
        self._update_working_dir_display(job_id)

    def _on_command_type_changed(self, command_type: str) -> None:
        """Handle command type change - switch between prompt and slash command input."""
        if command_type == "prompt":
            self.command_stack.setCurrentIndex(0)  # Show prompt text area
        else:
            self.command_stack.setCurrentIndex(1)  # Show slash command line edit

    def show_task(self, task: Task) -> None:
        """Show a task in view mode."""
        self.current_task = task
        self.edit_mode = False

        # Update header
        self.title_label.setText(task.name)
        self.edit_btn.show()
        self.save_btn.hide()
        self.cancel_btn.hide()

        # Update view fields
        self.view_name.setText(task.name)
        self.view_model.setText(task.model.capitalize())
        self.view_model.setProperty("model", task.model)
        self.view_profile.setText(self._get_profile_name(task.profile))
        self.view_schedule.setText(self._get_schedule_text(task))
        self.view_prompt.setText(task.prompt or "(no prompt)")
        self.view_working_dir.setText(self._get_working_dir_text(task))
        self.view_permissions.setText(task.permissions)
        self.view_session.setText(task.session_mode)
        self.view_commit_on_success.setText("Yes" if task.commit_on_success else "No")

        # Show view mode
        self.empty_state.hide()
        self.edit_container.hide()
        self.view_container.show()

    def show_edit(self, task: Task | None = None) -> None:
        """Show edit mode for a task (or new task if None)."""
        self.current_task = task
        self.edit_mode = True

        if task:
            self.title_label.setText(f"Edit: {task.name}")
            self.edit_name.setText(task.name)
            self.edit_model.setCurrentText(task.model)
            self.edit_permissions.setCurrentText(task.permissions)
            self._select_profile_by_id(task.profile)
            self._select_job_by_id(str(task.job_id) if task.job_id else None)
            self.schedule_type_selector.set_has_job(task.job_id is not None)
            self.edit_session.setCurrentText(task.session_mode)
            self._update_working_dir_display(task.job_id)

            # Set prompt type and content
            self.command_type_selector.set_command_type(task.prompt_type)
            self._on_command_type_changed(task.prompt_type)
            # Load prompt into the appropriate field
            if task.prompt_type == "prompt":
                self.edit_prompt.setPlainText(task.prompt)
                self.edit_slash_command.clear()
            else:
                self.edit_slash_command.setText(task.prompt)
                self.edit_prompt.clear()

            # Set schedule type and panel config
            self.schedule_type_selector.set_schedule_type(task.schedule.schedule_type)
            self._on_schedule_type_changed(task.schedule.schedule_type)

            # Populate schedule panels based on type
            if task.schedule.schedule_type == ScheduleType.CALENDAR:
                self.calendar_panel.set_config(task.schedule)
            elif task.schedule.schedule_type == ScheduleType.INTERVAL:
                self.interval_panel.set_config(task.schedule)
            elif task.schedule.schedule_type == ScheduleType.FILE_WATCH:
                self.file_watch_panel.set_config(task.schedule)

            # Populate advanced options
            self.advanced_options_panel.set_retry_config(task.retry)
            self.advanced_options_panel.set_allowed_tools(task.allowed_tools)
            self.advanced_options_panel.set_disallowed_tools(task.disallowed_tools)

            # Populate notification options
            self.notify_start_cb.setChecked(task.notifications.on_start)
            self.notify_end_cb.setChecked(task.notifications.on_end)
            self.notify_failure_cb.setChecked(task.notifications.on_failure)

            # Populate Git options
            self.commit_on_success_cb.setChecked(task.commit_on_success)
        else:
            self.title_label.setText("New Task")
            self.edit_name.clear()
            self.edit_model.setCurrentText("sonnet")
            self.edit_permissions.setCurrentText("default")
            self.edit_profile.setCurrentIndex(0)  # (None)
            self.edit_job.setCurrentIndex(0)  # (None)
            self.schedule_type_selector.set_has_job(False)
            self.edit_session.setCurrentText("new")
            self._update_working_dir_display(None)

            # Reset command type to prompt and clear both fields
            self.command_type_selector.set_command_type("prompt")
            self._on_command_type_changed("prompt")
            self.edit_prompt.clear()
            self.edit_slash_command.clear()

            # Reset schedule to default (Manual)
            self.schedule_type_selector.set_schedule_type(ScheduleType.MANUAL)
            self._on_schedule_type_changed(ScheduleType.MANUAL)

            # Reset advanced options to defaults
            from claude_code_scheduler.models.task import RetryConfig

            self.advanced_options_panel.set_retry_config(RetryConfig())
            self.advanced_options_panel.set_allowed_tools([])
            self.advanced_options_panel.set_disallowed_tools([])

            # Reset notification options to defaults
            self.notify_start_cb.setChecked(False)
            self.notify_end_cb.setChecked(True)
            self.notify_failure_cb.setChecked(True)

            # Reset Git options to defaults
            self.commit_on_success_cb.setChecked(True)

        # Update header buttons
        self.edit_btn.hide()
        self.save_btn.show()
        self.cancel_btn.show()

        # Show edit mode
        self.empty_state.hide()
        self.view_container.hide()
        self.edit_container.show()

    def clear(self) -> None:
        """Clear the panel and show empty state."""
        self.current_task = None
        self.edit_mode = False
        self.title_label.setText("Task")

        self.edit_btn.hide()
        self.save_btn.hide()
        self.cancel_btn.hide()

        self.view_container.hide()
        self.edit_container.hide()
        self.empty_state.show()

    def _get_schedule_text(self, task: Task) -> str:
        """Get human-readable schedule description."""
        sched = task.schedule
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

        return "Unknown schedule"

    def _get_working_dir_text(self, task: Task) -> str:
        """Get working directory display text (from parent Job)."""
        if task.job_id:
            job = next((j for j in self.jobs if j.id == task.job_id), None)
            if job:
                wd = job.get_working_directory_path()
                if job.working_directory.use_git_worktree:
                    return f"{wd} (worktree)"
                return wd
        return "(no job selected)"

    def _update_working_dir_display(self, job_id: UUID | None) -> None:
        """Update the working directory display based on selected job."""
        if job_id:
            job = next((j for j in self.jobs if j.id == job_id), None)
            if job:
                wd = job.get_working_directory_path()
                if job.working_directory.use_git_worktree:
                    self.edit_working_dir_display.setText(f"{wd} (worktree)")
                else:
                    self.edit_working_dir_display.setText(wd)
                return
        self.edit_working_dir_display.setText("(select a job)")

    def _on_edit_clicked(self) -> None:
        """Handle edit button click."""
        if self.current_task:
            self.show_edit(self.current_task)
            self.edit_requested.emit(self.current_task.id)

    def _on_save_clicked(self) -> None:
        """Handle save button click."""
        from claude_code_scheduler.models.task import NotificationConfig

        # Build schedule config from panels
        schedule = self._build_schedule_config()

        # Get advanced options from panel
        retry_config = self.advanced_options_panel.get_retry_config()
        allowed_tools = self.advanced_options_panel.get_allowed_tools()
        disallowed_tools = self.advanced_options_panel.get_disallowed_tools()

        # Get notification config from checkboxes
        notification_config = NotificationConfig(
            on_start=self.notify_start_cb.isChecked(),
            on_end=self.notify_end_cb.isChecked(),
            on_failure=self.notify_failure_cb.isChecked(),
        )

        # Get command type
        command_type = self.command_type_selector.get_command_type()

        # Get command from the appropriate field based on command type
        if command_type == "prompt":
            command_value = self.edit_prompt.toPlainText()
        else:
            command_value = self.edit_slash_command.text()

        # Get selected profile ID and job ID
        profile_id = self._get_selected_profile_id()
        job_id = self._get_selected_job_id()

        if self.current_task:
            # Update existing task
            self.current_task.name = self.edit_name.text()
            self.current_task.model = self.edit_model.currentText()
            self.current_task.permissions = self.edit_permissions.currentText()
            self.current_task.profile = profile_id
            self.current_task.job_id = job_id
            self.current_task.session_mode = self.edit_session.currentText()
            # NOTE: working_directory now inherited from Job
            self.current_task.prompt_type = command_type
            self.current_task.prompt = command_value
            self.current_task.schedule = schedule
            self.current_task.retry = retry_config
            self.current_task.notifications = notification_config
            self.current_task.allowed_tools = allowed_tools
            self.current_task.disallowed_tools = disallowed_tools
            self.current_task.commit_on_success = self.commit_on_success_cb.isChecked()
            self.task_saved.emit(self.current_task)
            self.show_task(self.current_task)
        else:
            # Create new task
            # NOTE: working_directory is inherited from Job, not set on Task
            new_task = Task(
                name=self.edit_name.text() or "Untitled Task",
                model=self.edit_model.currentText(),
                permissions=self.edit_permissions.currentText(),
                profile=profile_id,
                job_id=job_id,
                session_mode=self.edit_session.currentText(),
                prompt_type=command_type,
                prompt=command_value,
                schedule=schedule,
                retry=retry_config,
                notifications=notification_config,
                allowed_tools=allowed_tools,
                disallowed_tools=disallowed_tools,
                commit_on_success=self.commit_on_success_cb.isChecked(),
            )
            self.task_saved.emit(new_task)
            self.show_task(new_task)

    def _build_schedule_config(self) -> ScheduleConfig:
        """Build ScheduleConfig from the current panel state."""
        schedule_type = self.schedule_type_selector.get_schedule_type()
        config = ScheduleConfig(schedule_type=schedule_type)

        if schedule_type == ScheduleType.CALENDAR:
            panel_config = self.calendar_panel.get_config()
            config.calendar_frequency = str(panel_config.get("calendar_frequency", "daily"))
            cal_time = panel_config.get("calendar_time")
            if isinstance(cal_time, time):
                config.calendar_time = cal_time
            config.calendar_days_of_week = panel_config.get("calendar_days_of_week")  # type: ignore[assignment]
            config.calendar_day_of_month = panel_config.get("calendar_day_of_month")  # type: ignore[assignment]

        elif schedule_type == ScheduleType.INTERVAL:
            panel_config = self.interval_panel.get_config()
            config.interval_type = panel_config.get("interval_type")  # type: ignore[assignment]
            config.interval_preset = panel_config.get("interval_preset")  # type: ignore[assignment]
            config.interval_value = panel_config.get("interval_value")  # type: ignore[assignment]
            config.interval_unit = panel_config.get("interval_unit")  # type: ignore[assignment]
            config.interval_cron = panel_config.get("interval_cron")  # type: ignore[assignment]

        elif schedule_type == ScheduleType.FILE_WATCH:
            panel_config = self.file_watch_panel.get_config()
            config.watch_directory = str(panel_config.get("watch_directory", "~"))
            config.watch_recursive = bool(panel_config.get("watch_recursive", True))
            debounce_val = panel_config.get("watch_debounce_seconds", 5)
            config.watch_debounce_seconds = (
                int(str(debounce_val)) if debounce_val is not None else 5
            )

        return config

    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        if self.current_task:
            self.show_task(self.current_task)
        else:
            self.clear()
        self.task_cancelled.emit()

    # Profile helper methods

    def set_profiles(self, profiles: list[Profile]) -> None:
        """Set available profiles for the selector.

        Args:
            profiles: List of Profile objects to populate the dropdown.
        """
        self.profiles = profiles
        self.edit_profile.clear()
        self.edit_profile.addItem("(None)", None)
        for profile in profiles:
            self.edit_profile.addItem(profile.name, str(profile.id))

    def set_jobs(self, jobs: list[Job]) -> None:
        """Set available jobs for the selector.

        Args:
            jobs: List of Job objects to populate the dropdown.
        """
        self.jobs = jobs
        self.edit_job.clear()
        self.edit_job.addItem("(None)", None)
        for job in jobs:
            self.edit_job.addItem(job.name, str(job.id))

    def _get_profile_name(self, profile_id: str | None) -> str:
        """Get profile name by ID.

        Args:
            profile_id: The profile ID string or None.

        Returns:
            The profile name or "(None)" if not found.
        """
        if not profile_id:
            return "(None)"
        for profile in self.profiles:
            if str(profile.id) == profile_id:
                return profile.name
        return "(Unknown)"

    def _select_profile_by_id(self, profile_id: str | None) -> None:
        """Select a profile in the combo box by ID.

        Args:
            profile_id: The profile ID string or None.
        """
        if not profile_id:
            self.edit_profile.setCurrentIndex(0)
            return
        for i in range(self.edit_profile.count()):
            if self.edit_profile.itemData(i) == profile_id:
                self.edit_profile.setCurrentIndex(i)
                return
        # Profile not found, select None
        self.edit_profile.setCurrentIndex(0)

    def _get_selected_profile_id(self) -> str | None:
        """Get the currently selected profile ID.

        Returns:
            The profile ID string or None if "(None)" is selected.
        """
        data = self.edit_profile.currentData()
        return data if data else None

    # Job helper methods

    def _select_job_by_id(self, job_id: str | None) -> None:
        """Select a job in the combo box by ID.

        Args:
            job_id: The job ID string or None.
        """
        if not job_id:
            self.edit_job.setCurrentIndex(0)
            return
        for i in range(self.edit_job.count()):
            if self.edit_job.itemData(i) == job_id:
                self.edit_job.setCurrentIndex(i)
                return
        # Job not found, select None
        self.edit_job.setCurrentIndex(0)

    def _get_selected_job_id(self) -> UUID | None:
        """Get the currently selected job ID.

        Returns:
            The job UUID or None if "(None)" is selected.
        """
        data = self.edit_job.currentData()
        if data:
            return UUID(data)
        return None
