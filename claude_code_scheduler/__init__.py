"""Claude Code Scheduler - A GUI and CLI application for scheduling Claude Code sessions.

This package provides a comprehensive scheduling system for automating Claude Code CLI
sessions with support for multiple scheduling modes, environment profiles, and job
management.

Key Components:
    - cli: Main CLI entry point with debug and API commands
    - main: GUI entry point using PyQt6
    - models: Data models (Task, Run, Job, Profile, Settings)
    - services: Business logic (TaskExecutor, TaskScheduler, EnvVarResolver)
    - storage: JSON file persistence (ConfigStorage)
    - ui: PyQt6-based graphical interface

Dependencies:
    - click: CLI framework
    - PyQt6: GUI framework
    - apscheduler: Task scheduling engine
    - watchdog: File system monitoring

Example:
    >>> from claude_code_scheduler.models import Task, ScheduleConfig, ScheduleType
    >>> task = Task(name="Daily Review", model="sonnet")
    >>> task.schedule.schedule_type = ScheduleType.CALENDAR

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

__version__ = "0.1.0"
