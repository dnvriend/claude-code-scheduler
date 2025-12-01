"""UI widgets for Claude Code Scheduler.

This package contains reusable UI components used across panels and dialogs,
including list items, schedule editors, and collapsible containers.

Key Components:
    - TaskItemWidget: Task list item display
    - RunItemWidget: Run history item display
    - JobItemWidget: Job list item display
    - ScheduleTypeSelector: Schedule type dropdown
    - CalendarSchedulePanel: Calendar schedule configuration
    - IntervalSchedulePanel: Interval schedule configuration
    - FileWatchSchedulePanel: File watch schedule configuration
    - AdvancedOptionsPanel: Advanced task options
    - CollapsibleWidget: Collapsible container widget
    - CommandTypeSelector: Command type selection

Dependencies:
    - PyQt6: Widget framework
    - models: Data models for display

Related Modules:
    - ui.panels: Panels that use these widgets
    - models: Data models rendered by widgets

Example:
    >>> from claude_code_scheduler.ui.widgets import TaskItemWidget
    >>> widget = TaskItemWidget(task)
    >>> widget.show()

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

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
from claude_code_scheduler.ui.widgets.job_item import JobItemWidget
from claude_code_scheduler.ui.widgets.run_item import RunItemWidget
from claude_code_scheduler.ui.widgets.schedule_type_selector import (
    ScheduleTypeSelector,
)
from claude_code_scheduler.ui.widgets.task_item import TaskItemWidget

__all__ = [
    "AdvancedOptionsPanel",
    "CalendarSchedulePanel",
    "CollapsibleWidget",
    "CommandTypeSelector",
    "FileWatchSchedulePanel",
    "IntervalSchedulePanel",
    "JobItemWidget",
    "RunItemWidget",
    "ScheduleTypeSelector",
    "TaskItemWidget",
]
