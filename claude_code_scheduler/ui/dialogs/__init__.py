"""Dialog windows for Claude Code Scheduler.

This package contains modal dialog windows for application settings,
profile editing, job configuration, and user confirmations.

Key Components:
    - SettingsDialog: Application settings configuration
    - ProfileEditorDialog: Environment profile editing
    - JobEditorDialog: Job creation and editing

Dependencies:
    - PyQt6: Dialog framework (QDialog, QFormLayout)
    - models: Settings, Profile, Job data models
    - storage: Data persistence

Related Modules:
    - ui.main_window: Opens dialogs from menu/toolbar
    - models: Data models edited by dialogs

Called By:
    - MainWindow: Menu actions and toolbar buttons

Example:
    >>> from claude_code_scheduler.ui.dialogs import SettingsDialog
    >>> dialog = SettingsDialog(parent=main_window)
    >>> dialog.exec()

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from claude_code_scheduler.ui.dialogs.settings_dialog import SettingsDialog

__all__ = ["SettingsDialog"]
