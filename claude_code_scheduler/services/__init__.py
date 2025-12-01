"""Services for Claude Code Scheduler.

This package contains the business logic layer including task execution,
scheduling, file watching, and environment variable resolution.

Key Components:
    - TaskExecutor: Executes tasks via Claude Code CLI
    - TaskScheduler: APScheduler-based task scheduling
    - EnvVarResolver: Resolves environment variables from multiple sources
    - FileWatcher: File system monitoring for file-watch schedules

Dependencies:
    - apscheduler: Task scheduling engine
    - watchdog: File system monitoring
    - subprocess: CLI execution
    - boto3: AWS SDK for secrets/SSM resolution

Related Modules:
    - models: Data models used by services
    - storage: Persistence layer for service data
    - ui: GUI components that use services

Example:
    >>> from claude_code_scheduler.services import TaskExecutor, TaskScheduler
    >>> executor = TaskExecutor(mock_mode=True)
    >>> scheduler = TaskScheduler()

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from claude_code_scheduler.services.env_resolver import EnvVarResolver
from claude_code_scheduler.services.executor import TaskExecutor
from claude_code_scheduler.services.file_watcher import FileWatcher
from claude_code_scheduler.services.scheduler import TaskScheduler

__all__ = [
    "EnvVarResolver",
    "FileWatcher",
    "TaskExecutor",
    "TaskScheduler",
]
