"""Enumeration types for Claude Code Scheduler.

This module contains all enum definitions used across data models,
providing type-safe constants for scheduling, status tracking, and configuration.

Key Components:
    - ScheduleType: Types of task scheduling (manual, interval, calendar, etc.)
    - IntervalType: Interval scheduling subtypes (simple, custom, cron)
    - RunStatus: Task execution status (upcoming, running, success, failed)
    - EnvVarSource: Environment variable resolution sources
    - JobStatus: Job execution status

Dependencies:
    - enum: Python standard library Enum

Related Modules:
    - models.task: Uses ScheduleType, IntervalType
    - models.run: Uses RunStatus
    - models.job: Uses JobStatus
    - models.profile: Uses EnvVarSource

Example:
    >>> from claude_code_scheduler.models.enums import ScheduleType, RunStatus
    >>> schedule = ScheduleType.CALENDAR
    >>> status = RunStatus.SUCCESS

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from enum import Enum


class ScheduleType(Enum):
    """Types of task scheduling."""

    MANUAL = "manual"
    INTERVAL = "interval"
    CALENDAR = "calendar"
    STARTUP = "startup"
    FILE_WATCH = "file_watch"
    SEQUENTIAL = "sequential"  # Runs as part of Job sequence, triggered by previous task


class IntervalType(Enum):
    """Types of interval scheduling."""

    SIMPLE = "simple"  # Preset intervals (5min, 15min, etc.)
    CUSTOM = "custom"  # Custom number + unit
    CRON = "cron"  # Cron expression


class RunStatus(Enum):
    """Status of a task run."""

    UPCOMING = "upcoming"  # Yellow badge - scheduled but not started
    RUNNING = "running"  # Orange/Yellow text - currently executing
    SUCCESS = "success"  # Green text - completed successfully
    FAILED = "failed"  # Red text - execution failed
    CANCELLED = "cancelled"  # Grey text - manually cancelled


class EnvVarSource(Enum):
    """Source types for resolving environment variable values."""

    STATIC = "static"  # Hardcoded value
    ENVIRONMENT = "env"  # Read from existing env var
    KEYCHAIN = "keychain"  # macOS Keychain lookup
    AWS_SECRETS_MANAGER = "aws_sm"  # AWS Secrets Manager
    AWS_SSM = "aws_ssm"  # AWS Systems Manager Parameter Store
    COMMAND = "command"  # Execute shell command
    UNSET = "unset"  # Remove/unset the environment variable


class JobStatus(Enum):
    """Status of a job (container for tasks)."""

    PENDING = "pending"  # Job created but no tasks started
    IN_PROGRESS = "in_progress"  # At least one task running
    COMPLETED = "completed"  # All tasks completed successfully
    FAILED = "failed"  # At least one task failed
