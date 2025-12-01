"""Storage module for Claude Code Scheduler.

This package provides persistent JSON file storage for all application data
including tasks, runs, profiles, jobs, and settings.

Key Components:
    - ConfigStorage: Main storage class for all data persistence

Dependencies:
    - json: JSON file handling
    - pathlib: File path operations
    - models: Data models for serialization

Related Modules:
    - models: Data models that are persisted
    - services: Business logic that uses stored data
    - ui: GUI components that display stored data

Data Files:
    - ~/.config/claude-code-scheduler/tasks.json
    - ~/.config/claude-code-scheduler/runs.json
    - ~/.config/claude-code-scheduler/jobs.json
    - ~/.config/claude-code-scheduler/profiles.json
    - ~/.config/claude-code-scheduler/settings.json

Example:
    >>> from claude_code_scheduler.storage import ConfigStorage
    >>> storage = ConfigStorage()
    >>> tasks = storage.load_tasks()

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from claude_code_scheduler.storage.config_storage import ConfigStorage

__all__ = ["ConfigStorage"]
