"""Data models for Claude Code Scheduler.

This package contains all data models used throughout the application,
following a hierarchy: Job (1) → Task (many) → Run (many).

Key Components:
    - Task: Scheduled Claude Code CLI command with configuration
    - Run: Single execution instance of a task
    - Job: Container for related tasks
    - Profile: Environment variable configurations
    - Settings: Application settings
    - ScheduleConfig: Task scheduling configuration
    - RetryConfig: Task retry behavior configuration
    - NotificationConfig: Task notification preferences
    - EnvVar: Environment variable definition
    - JobWorkingDirectory: Job working directory configuration

Dependencies:
    - dataclasses: Python dataclass decorators
    - uuid: UUID generation
    - datetime: Time/date handling

Related Modules:
    - storage.config_storage: Persists models to JSON files
    - services.executor: Uses Task and Run models
    - services.scheduler: Uses Task and ScheduleConfig
    - ui.panels: Display models in GUI

Example:
    >>> from claude_code_scheduler.models import Task, Job, ScheduleType
    >>> task = Task(name="Daily Review", model="sonnet")
    >>> job = Job(name="Maintenance", task_order=[task.id])

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from claude_code_scheduler.models.enums import (
    EnvVarSource,
    IntervalType,
    JobStatus,
    RunStatus,
    ScheduleType,
)
from claude_code_scheduler.models.job import Job, JobWorkingDirectory
from claude_code_scheduler.models.profile import EnvVar, Profile
from claude_code_scheduler.models.run import Run
from claude_code_scheduler.models.settings import Settings
from claude_code_scheduler.models.task import (
    NotificationConfig,
    RetryConfig,
    ScheduleConfig,
    Task,
)

__all__ = [
    "EnvVarSource",
    "IntervalType",
    "JobStatus",
    "RunStatus",
    "ScheduleType",
    "EnvVar",
    "Job",
    "JobWorkingDirectory",
    "Profile",
    "Run",
    "Settings",
    "NotificationConfig",
    "RetryConfig",
    "ScheduleConfig",
    "Task",
]
