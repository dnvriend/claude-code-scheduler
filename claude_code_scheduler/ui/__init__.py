"""UI package for Claude Code Scheduler.

This package contains all PyQt6 widgets, panels, dialogs, and theming
for the graphical user interface.

Key Components:
    - MainWindow: Main application window with 4-panel layout
    - panels: TaskListPanel, TaskEditorPanel, RunsPanel, LogsPanel, JobsPanel
    - dialogs: SettingsDialog, ProfileEditorDialog, JobEditorDialog
    - widgets: Reusable UI components

Dependencies:
    - PyQt6: GUI framework
    - models: Data models for display
    - services: Business logic integration
    - storage: Data persistence

Related Modules:
    - main: Creates QApplication and MainWindow
    - cli: gui_command launches the UI

Example:
    >>> from claude_code_scheduler.ui import MainWindow
    >>> window = MainWindow(restport=5679)
    >>> window.show()

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from claude_code_scheduler.ui.main_window import MainWindow

__all__ = ["MainWindow"]
