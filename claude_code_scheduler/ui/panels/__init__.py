"""UI panels for Claude Code Scheduler.

This package contains the main panel widgets that compose the 4-panel
layout of the application.

Key Components:
    - JobsPanel: Leftmost panel with job hierarchy (optional)
    - TaskListPanel: Left panel with task list and controls
    - TaskEditorPanel: Middle panel for task configuration
    - RunsPanel: Right-top panel with execution history
    - LogsPanel: Right-bottom panel with log output viewer

Dependencies:
    - PyQt6: Widget framework
    - models: Task, Run, Job, Profile data models
    - ui.widgets: Reusable UI components

Related Modules:
    - ui.main_window: Creates and arranges panels
    - ui.widgets: Shared widget components
    - services: Business logic for panel actions

Layout:
    MainWindow: [Jobs] | [Tasks] | [Editor] | [Runs/Logs]

Example:
    >>> from claude_code_scheduler.ui.panels import TaskListPanel, RunsPanel
    >>> task_panel = TaskListPanel()
    >>> runs_panel = RunsPanel()

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from claude_code_scheduler.ui.panels.jobs_panel import JobsPanel
from claude_code_scheduler.ui.panels.logs_panel import LogsPanel
from claude_code_scheduler.ui.panels.runs_panel import RunsPanel
from claude_code_scheduler.ui.panels.task_editor_panel import TaskEditorPanel
from claude_code_scheduler.ui.panels.task_list_panel import TaskListPanel

__all__ = ["JobsPanel", "TaskListPanel", "TaskEditorPanel", "RunsPanel", "LogsPanel"]
