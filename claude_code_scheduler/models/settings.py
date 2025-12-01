"""Settings data model for Claude Code Scheduler.

This module contains the Settings dataclass for application-wide
configuration including UI preferences, execution settings, and defaults.

Key Components:
    - Settings: Application configuration with all user preferences

Dependencies:
    - dataclasses: Python dataclass decorators

Related Modules:
    - storage.config_storage: Persists settings to JSON
    - ui.main_window: Applies settings to GUI
    - ui.dialogs.settings_dialog: Settings editing UI
    - services.executor: Uses mock_mode setting

Collaborators:
    - ConfigStorage: Loads and saves settings
    - MainWindow: Applies theme and window geometry
    - TaskExecutor: Uses mock_mode and unmask_env_vars

Example:
    >>> from claude_code_scheduler.models.settings import Settings
    >>> settings = Settings(theme="dark", mock_mode=False)
    >>> settings.to_dict()

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Settings:
    """Application-wide settings configuration."""

    # General
    launch_at_login: bool = False

    # Notifications
    notifications_enabled: bool = True
    notify_task_start: bool = False
    notify_task_end: bool = True
    notify_errors: bool = True

    # Appearance
    theme: str = "dark"  # "system" | "light" | "dark"
    compact_mode: bool = False
    show_token_usage: bool = True
    auto_scroll_logs: bool = True

    # UI State (panel visibility)
    show_jobs_panel: bool = True

    # Window geometry
    window_x: int | None = None
    window_y: int | None = None
    window_width: int = 1450
    window_height: int = 900
    window_maximized: bool = False

    # Panel sizes (splitter widths in pixels)
    main_splitter_sizes: list[int] | None = None  # [jobs, tasks, editor, right]
    right_splitter_sizes: list[int] | None = None  # [runs, logs]

    # Defaults
    default_working_directory: str = "~"
    default_model: str = "sonnet"  # opus | sonnet | haiku
    default_terminal: str = "iTerm2"

    # Data retention
    run_retention_count: int = 50
    log_retention_days: int = 30

    # Behavior
    close_to_menu_bar: bool = True
    run_in_background: bool = True

    # Execution
    max_concurrent_tasks: int = 3
    mock_mode: bool = True  # Use mock execution instead of real CLI
    claude_cli_path: str = ""  # Custom path to claude CLI (auto-detect if empty)

    # Debug
    unmask_env_vars: bool = False  # Show full env var values in debug logs

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary for JSON serialization."""
        return {
            "launch_at_login": self.launch_at_login,
            "notifications_enabled": self.notifications_enabled,
            "notify_task_start": self.notify_task_start,
            "notify_task_end": self.notify_task_end,
            "notify_errors": self.notify_errors,
            "theme": self.theme,
            "compact_mode": self.compact_mode,
            "show_token_usage": self.show_token_usage,
            "auto_scroll_logs": self.auto_scroll_logs,
            "show_jobs_panel": self.show_jobs_panel,
            "window_x": self.window_x,
            "window_y": self.window_y,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "window_maximized": self.window_maximized,
            "main_splitter_sizes": self.main_splitter_sizes,
            "right_splitter_sizes": self.right_splitter_sizes,
            "default_working_directory": self.default_working_directory,
            "default_model": self.default_model,
            "default_terminal": self.default_terminal,
            "run_retention_count": self.run_retention_count,
            "log_retention_days": self.log_retention_days,
            "close_to_menu_bar": self.close_to_menu_bar,
            "run_in_background": self.run_in_background,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "mock_mode": self.mock_mode,
            "claude_cli_path": self.claude_cli_path,
            "unmask_env_vars": self.unmask_env_vars,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        """Create settings from dictionary."""
        return cls(
            launch_at_login=data.get("launch_at_login", False),
            notifications_enabled=data.get("notifications_enabled", True),
            notify_task_start=data.get("notify_task_start", False),
            notify_task_end=data.get("notify_task_end", True),
            notify_errors=data.get("notify_errors", True),
            theme=data.get("theme", "dark"),
            compact_mode=data.get("compact_mode", False),
            show_token_usage=data.get("show_token_usage", True),
            auto_scroll_logs=data.get("auto_scroll_logs", True),
            show_jobs_panel=data.get("show_jobs_panel", True),
            window_x=data.get("window_x"),
            window_y=data.get("window_y"),
            window_width=data.get("window_width", 1450),
            window_height=data.get("window_height", 900),
            window_maximized=data.get("window_maximized", False),
            main_splitter_sizes=data.get("main_splitter_sizes"),
            right_splitter_sizes=data.get("right_splitter_sizes"),
            default_working_directory=data.get("default_working_directory", "~"),
            default_model=data.get("default_model", "sonnet"),
            default_terminal=data.get("default_terminal", "iTerm2"),
            run_retention_count=data.get("run_retention_count", 50),
            log_retention_days=data.get("log_retention_days", 30),
            close_to_menu_bar=data.get("close_to_menu_bar", True),
            run_in_background=data.get("run_in_background", True),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 3),
            mock_mode=data.get("mock_mode", True),
            claude_cli_path=data.get("claude_cli_path", ""),
            unmask_env_vars=data.get("unmask_env_vars", False),
        )
