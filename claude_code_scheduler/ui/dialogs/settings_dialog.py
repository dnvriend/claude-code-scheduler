"""
Settings Dialog for Claude Code Scheduler.

Modal dialog for editing application settings.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from claude_code_scheduler.models.settings import Settings


class SettingsDialog(QDialog):
    """Dialog for editing application settings."""

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Tab widget for categories
        self.tab_widget = QTabWidget()

        # General tab
        general_tab = self._create_general_tab()
        self.tab_widget.addTab(general_tab, "General")

        # Notifications tab
        notifications_tab = self._create_notifications_tab()
        self.tab_widget.addTab(notifications_tab, "Notifications")

        # Appearance tab
        appearance_tab = self._create_appearance_tab()
        self.tab_widget.addTab(appearance_tab, "Appearance")

        # Defaults tab
        defaults_tab = self._create_defaults_tab()
        self.tab_widget.addTab(defaults_tab, "Defaults")

        # Data tab
        data_tab = self._create_data_tab()
        self.tab_widget.addTab(data_tab, "Data")

        layout.addWidget(self.tab_widget)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _create_general_tab(self) -> QWidget:
        """Create the General settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Startup group
        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout(startup_group)

        self.launch_at_login_cb = QCheckBox("Launch at login")
        startup_layout.addWidget(self.launch_at_login_cb)

        layout.addWidget(startup_group)

        # Behavior group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout(behavior_group)

        self.close_to_menu_bar_cb = QCheckBox("Close to menu bar (keep running)")
        behavior_layout.addWidget(self.close_to_menu_bar_cb)

        self.run_in_background_cb = QCheckBox("Run tasks in background")
        behavior_layout.addWidget(self.run_in_background_cb)

        layout.addWidget(behavior_group)

        # Execution group
        execution_group = QGroupBox("Execution")
        execution_layout = QFormLayout(execution_group)

        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 10)
        execution_layout.addRow("Max concurrent tasks:", self.max_concurrent_spin)

        self.mock_mode_cb = QCheckBox("Mock mode (simulate Claude CLI)")
        execution_layout.addRow("", self.mock_mode_cb)

        self.unmask_env_vars_cb = QCheckBox("Unmask env vars in debug logs")
        execution_layout.addRow("", self.unmask_env_vars_cb)

        self.claude_cli_path_edit = QLineEdit()
        self.claude_cli_path_edit.setPlaceholderText("Auto-detect")
        execution_layout.addRow("Claude CLI path:", self.claude_cli_path_edit)

        layout.addWidget(execution_group)

        layout.addStretch()
        return widget

    def _create_notifications_tab(self) -> QWidget:
        """Create the Notifications settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Enable notifications
        self.notifications_enabled_cb = QCheckBox("Enable notifications")
        layout.addWidget(self.notifications_enabled_cb)

        # Notification events group
        events_group = QGroupBox("Notify on")
        events_layout = QVBoxLayout(events_group)

        self.notify_task_start_cb = QCheckBox("Task start")
        events_layout.addWidget(self.notify_task_start_cb)

        self.notify_task_end_cb = QCheckBox("Task completion")
        events_layout.addWidget(self.notify_task_end_cb)

        self.notify_errors_cb = QCheckBox("Errors")
        events_layout.addWidget(self.notify_errors_cb)

        layout.addWidget(events_group)

        layout.addStretch()
        return widget

    def _create_appearance_tab(self) -> QWidget:
        """Create the Appearance settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        form = QFormLayout()
        form.setSpacing(12)

        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        form.addRow("Theme:", self.theme_combo)

        layout.addLayout(form)

        # Display options group
        display_group = QGroupBox("Display")
        display_layout = QVBoxLayout(display_group)

        self.compact_mode_cb = QCheckBox("Compact mode")
        display_layout.addWidget(self.compact_mode_cb)

        self.show_token_usage_cb = QCheckBox("Show token usage")
        display_layout.addWidget(self.show_token_usage_cb)

        self.auto_scroll_logs_cb = QCheckBox("Auto-scroll logs")
        display_layout.addWidget(self.auto_scroll_logs_cb)

        layout.addWidget(display_group)

        layout.addStretch()
        return widget

    def _create_defaults_tab(self) -> QWidget:
        """Create the Defaults settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        form = QFormLayout()
        form.setSpacing(12)

        # Working directory
        self.default_working_dir_edit = QLineEdit()
        self.default_working_dir_edit.setPlaceholderText("~")
        form.addRow("Working directory:", self.default_working_dir_edit)

        # Model
        self.default_model_combo = QComboBox()
        self.default_model_combo.addItems(["opus", "sonnet", "haiku"])
        form.addRow("Model:", self.default_model_combo)

        # Terminal
        self.default_terminal_combo = QComboBox()
        self.default_terminal_combo.addItems(["iTerm2", "Terminal.app", "Other"])
        form.addRow("Terminal:", self.default_terminal_combo)

        layout.addLayout(form)
        layout.addStretch()
        return widget

    def _create_data_tab(self) -> QWidget:
        """Create the Data retention settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Retention group
        retention_group = QGroupBox("Data Retention")
        retention_layout = QFormLayout(retention_group)

        self.run_retention_spin = QSpinBox()
        self.run_retention_spin.setRange(10, 500)
        self.run_retention_spin.setSuffix(" runs per task")
        retention_layout.addRow("Keep:", self.run_retention_spin)

        self.log_retention_spin = QSpinBox()
        self.log_retention_spin.setRange(1, 365)
        self.log_retention_spin.setSuffix(" days")
        retention_layout.addRow("Log retention:", self.log_retention_spin)

        layout.addWidget(retention_group)

        # Info label
        info_label = QLabel("Older runs and logs will be automatically deleted to save space.")
        info_label.setObjectName("helpLabel")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()
        return widget

    def _load_settings(self) -> None:
        """Load current settings into the UI."""
        # General
        self.launch_at_login_cb.setChecked(self.settings.launch_at_login)
        self.close_to_menu_bar_cb.setChecked(self.settings.close_to_menu_bar)
        self.run_in_background_cb.setChecked(self.settings.run_in_background)
        self.max_concurrent_spin.setValue(self.settings.max_concurrent_tasks)
        self.mock_mode_cb.setChecked(self.settings.mock_mode)
        self.unmask_env_vars_cb.setChecked(self.settings.unmask_env_vars)
        self.claude_cli_path_edit.setText(self.settings.claude_cli_path)

        # Notifications
        self.notifications_enabled_cb.setChecked(self.settings.notifications_enabled)
        self.notify_task_start_cb.setChecked(self.settings.notify_task_start)
        self.notify_task_end_cb.setChecked(self.settings.notify_task_end)
        self.notify_errors_cb.setChecked(self.settings.notify_errors)

        # Appearance
        theme_map = {"system": 0, "light": 1, "dark": 2}
        self.theme_combo.setCurrentIndex(theme_map.get(self.settings.theme, 2))
        self.compact_mode_cb.setChecked(self.settings.compact_mode)
        self.show_token_usage_cb.setChecked(self.settings.show_token_usage)
        self.auto_scroll_logs_cb.setChecked(self.settings.auto_scroll_logs)

        # Defaults
        self.default_working_dir_edit.setText(self.settings.default_working_directory)
        model_map = {"opus": 0, "sonnet": 1, "haiku": 2}
        self.default_model_combo.setCurrentIndex(model_map.get(self.settings.default_model, 1))
        terminal_map = {"iTerm2": 0, "Terminal.app": 1}
        self.default_terminal_combo.setCurrentIndex(
            terminal_map.get(self.settings.default_terminal, 0)
        )

        # Data
        self.run_retention_spin.setValue(self.settings.run_retention_count)
        self.log_retention_spin.setValue(self.settings.log_retention_days)

    def _on_accept(self) -> None:
        """Save settings and accept dialog."""
        # General
        self.settings.launch_at_login = self.launch_at_login_cb.isChecked()
        self.settings.close_to_menu_bar = self.close_to_menu_bar_cb.isChecked()
        self.settings.run_in_background = self.run_in_background_cb.isChecked()
        self.settings.max_concurrent_tasks = self.max_concurrent_spin.value()
        self.settings.mock_mode = self.mock_mode_cb.isChecked()
        self.settings.unmask_env_vars = self.unmask_env_vars_cb.isChecked()
        self.settings.claude_cli_path = self.claude_cli_path_edit.text()

        # Notifications
        self.settings.notifications_enabled = self.notifications_enabled_cb.isChecked()
        self.settings.notify_task_start = self.notify_task_start_cb.isChecked()
        self.settings.notify_task_end = self.notify_task_end_cb.isChecked()
        self.settings.notify_errors = self.notify_errors_cb.isChecked()

        # Appearance
        themes = ["system", "light", "dark"]
        self.settings.theme = themes[self.theme_combo.currentIndex()]
        self.settings.compact_mode = self.compact_mode_cb.isChecked()
        self.settings.show_token_usage = self.show_token_usage_cb.isChecked()
        self.settings.auto_scroll_logs = self.auto_scroll_logs_cb.isChecked()

        # Defaults
        self.settings.default_working_directory = self.default_working_dir_edit.text() or "~"
        models = ["opus", "sonnet", "haiku"]
        self.settings.default_model = models[self.default_model_combo.currentIndex()]
        terminals = ["iTerm2", "Terminal.app", "Other"]
        self.settings.default_terminal = terminals[self.default_terminal_combo.currentIndex()]

        # Data
        self.settings.run_retention_count = self.run_retention_spin.value()
        self.settings.log_retention_days = self.log_retention_spin.value()

        self.accept()

    def get_settings(self) -> Settings:
        """Get the modified settings."""
        return self.settings
