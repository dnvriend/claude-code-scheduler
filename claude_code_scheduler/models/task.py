"""Task data model for Claude Code Scheduler.

This module contains the Task dataclass and related configuration models
for scheduled Claude Code CLI commands.

Key Components:
    - Task: Main dataclass for scheduled CLI tasks
    - ScheduleConfig: Scheduling configuration (calendar, interval, file watch)
    - RetryConfig: Retry behavior configuration
    - NotificationConfig: Notification preferences

Dependencies:
    - dataclasses: Python dataclass decorators
    - datetime: Time handling for schedule times
    - uuid: UUID generation for task IDs
    - models.enums: ScheduleType, IntervalType enums

Related Modules:
    - models.job: Parent container for tasks
    - models.run: Execution instances of tasks
    - services.executor: Executes tasks
    - services.scheduler: Schedules tasks
    - storage.config_storage: Persists tasks to JSON

Collaborators:
    - Job: Tasks belong to a Job (via job_id foreign key)
    - Profile: Tasks reference profiles for environment variables

Example:
    >>> from claude_code_scheduler.models.task import Task, ScheduleConfig
    >>> from claude_code_scheduler.models.enums import ScheduleType
    >>> schedule = ScheduleConfig(schedule_type=ScheduleType.CALENDAR)
    >>> task = Task(name="Daily Review", model="sonnet", schedule=schedule)

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any
from uuid import UUID, uuid4

from claude_code_scheduler.models.enums import IntervalType, ScheduleType


@dataclass
class RetryConfig:
    """Configuration for task retry behavior on failure."""

    enabled: bool = False
    max_attempts: int = 3
    delay_seconds: int = 60
    backoff_multiplier: float = 2.0  # 1.0 = fixed, 2.0 = exponential


@dataclass
class NotificationConfig:
    """Configuration for task notification preferences."""

    on_start: bool = False
    on_end: bool = True
    on_failure: bool = True


@dataclass
class ScheduleConfig:
    """Configuration for task scheduling."""

    schedule_type: ScheduleType = ScheduleType.MANUAL
    timezone: str = "Europe/Amsterdam"

    # Calendar fields
    calendar_frequency: str | None = None  # "daily" | "weekly" | "monthly"
    calendar_time: time | None = None  # e.g., 23:00
    calendar_days_of_week: list[int] | None = None  # For weekly: [0=Mon, 6=Sun]
    calendar_day_of_month: int | None = None  # For monthly: 1-31

    # Interval fields
    interval_type: IntervalType | None = None  # simple | custom | cron
    interval_preset: str | None = None  # "5min" | "15min" | "30min" | "1hour"
    interval_value: int | None = None  # Custom: number value
    interval_unit: str | None = None  # Custom: "minutes" | "hours" | "days"
    interval_cron: str | None = None  # Cron: "0 */2 * * *"

    # File watch fields
    watch_directory: str | None = None  # Directory to watch
    watch_recursive: bool | None = True  # Include subdirectories
    watch_debounce_seconds: int | None = 5  # Wait after last change

    # Sequential schedule fields (for SEQUENTIAL type)
    seq_max_retries: int = 0  # Max retry attempts on failure (0 = no retry)
    seq_retry_delay_seconds: int = 60  # Delay between retries


@dataclass
class Task:
    """A scheduled Claude Code CLI task."""

    id: UUID = field(default_factory=uuid4)
    job_id: UUID | None = None  # Foreign key to Job (nullable for backward compatibility)
    name: str = "Untitled Task"
    enabled: bool = True
    commit_on_success: bool = True  # Auto-commit changes when task succeeds
    model: str = "sonnet"  # opus | sonnet | haiku
    profile: str | None = None  # Profile ID (None = default/no profile)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    prompt_type: str = "prompt"  # "prompt" | "slash_command"
    prompt: str = ""  # The prompt text or slash command
    # NOTE: working_directory moved to Job.working_directory
    # Tasks inherit working directory from their parent Job
    permissions: str = "bypass"  # default | bypass | acceptEdits | plan
    session_mode: str = "new"  # "new" | "reuse" | "fork"
    last_session_id: UUID | None = None  # Session ID from last run
    allowed_tools: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)
    retry: RetryConfig = field(default_factory=RetryConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_run_status: str | None = None  # For "Recent:" indicator

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "job_id": str(self.job_id) if self.job_id else None,
            "name": self.name,
            "enabled": self.enabled,
            "commit_on_success": self.commit_on_success,
            "model": self.model,
            "profile": self.profile,
            "schedule": {
                "schedule_type": self.schedule.schedule_type.value,
                "timezone": self.schedule.timezone,
                "calendar_frequency": self.schedule.calendar_frequency,
                "calendar_time": (
                    self.schedule.calendar_time.isoformat() if self.schedule.calendar_time else None
                ),
                "calendar_days_of_week": self.schedule.calendar_days_of_week,
                "calendar_day_of_month": self.schedule.calendar_day_of_month,
                "interval_type": (
                    self.schedule.interval_type.value if self.schedule.interval_type else None
                ),
                "interval_preset": self.schedule.interval_preset,
                "interval_value": self.schedule.interval_value,
                "interval_unit": self.schedule.interval_unit,
                "interval_cron": self.schedule.interval_cron,
                "watch_directory": self.schedule.watch_directory,
                "watch_recursive": self.schedule.watch_recursive,
                "watch_debounce_seconds": self.schedule.watch_debounce_seconds,
                "seq_max_retries": self.schedule.seq_max_retries,
                "seq_retry_delay_seconds": self.schedule.seq_retry_delay_seconds,
            },
            "prompt_type": self.prompt_type,
            "prompt": self.prompt,
            "permissions": self.permissions,
            "session_mode": self.session_mode,
            "last_session_id": (str(self.last_session_id) if self.last_session_id else None),
            "allowed_tools": self.allowed_tools,
            "disallowed_tools": self.disallowed_tools,
            "retry": {
                "enabled": self.retry.enabled,
                "max_attempts": self.retry.max_attempts,
                "delay_seconds": self.retry.delay_seconds,
                "backoff_multiplier": self.retry.backoff_multiplier,
            },
            "notifications": {
                "on_start": self.notifications.on_start,
                "on_end": self.notifications.on_end,
                "on_failure": self.notifications.on_failure,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_run_status": self.last_run_status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Create task from dictionary."""
        schedule_data = data.get("schedule", {})
        schedule = ScheduleConfig(
            schedule_type=ScheduleType(schedule_data.get("schedule_type", "manual")),
            timezone=schedule_data.get("timezone", "Europe/Amsterdam"),
            calendar_frequency=schedule_data.get("calendar_frequency"),
            calendar_time=(
                time.fromisoformat(schedule_data["calendar_time"])
                if schedule_data.get("calendar_time")
                else None
            ),
            calendar_days_of_week=schedule_data.get("calendar_days_of_week"),
            calendar_day_of_month=schedule_data.get("calendar_day_of_month"),
            interval_type=(
                IntervalType(schedule_data["interval_type"])
                if schedule_data.get("interval_type")
                else None
            ),
            interval_preset=schedule_data.get("interval_preset"),
            interval_value=schedule_data.get("interval_value"),
            interval_unit=schedule_data.get("interval_unit"),
            interval_cron=schedule_data.get("interval_cron"),
            watch_directory=schedule_data.get("watch_directory"),
            watch_recursive=schedule_data.get("watch_recursive", True),
            watch_debounce_seconds=schedule_data.get("watch_debounce_seconds", 5),
            seq_max_retries=schedule_data.get("seq_max_retries", 0),
            seq_retry_delay_seconds=schedule_data.get("seq_retry_delay_seconds", 60),
        )

        retry_data = data.get("retry", {})
        retry = RetryConfig(
            enabled=retry_data.get("enabled", False),
            max_attempts=retry_data.get("max_attempts", 3),
            delay_seconds=retry_data.get("delay_seconds", 60),
            backoff_multiplier=retry_data.get("backoff_multiplier", 2.0),
        )

        notifications_data = data.get("notifications", {})
        notifications = NotificationConfig(
            on_start=notifications_data.get("on_start", False),
            on_end=notifications_data.get("on_end", True),
            on_failure=notifications_data.get("on_failure", True),
        )

        # Generate defaults for new tasks (id, timestamps)
        task_id = UUID(data["id"]) if "id" in data else uuid4()
        now = datetime.now()
        created_at = datetime.fromisoformat(data["created_at"]) if "created_at" in data else now
        updated_at = datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else now

        return cls(
            id=task_id,
            job_id=UUID(data["job_id"]) if data.get("job_id") else None,
            name=data.get("name", "Untitled Task"),
            enabled=data.get("enabled", True),
            commit_on_success=data.get("commit_on_success", True),
            model=data.get("model", "sonnet"),
            profile=data.get("profile"),
            schedule=schedule,
            # Support both old 'command' and new 'prompt' field names for backward compatibility
            prompt_type=data.get("prompt_type", data.get("command_type", "prompt")),
            prompt=data.get("prompt", data.get("command", "")),
            # NOTE: working_directory ignored - migrated to Job
            permissions=data.get("permissions", "bypass"),
            session_mode=data.get("session_mode", "new"),
            last_session_id=(
                UUID(data["last_session_id"]) if data.get("last_session_id") else None
            ),
            allowed_tools=data.get("allowed_tools", []),
            disallowed_tools=data.get("disallowed_tools", []),
            retry=retry,
            notifications=notifications,
            created_at=created_at,
            updated_at=updated_at,
            last_run_status=data.get("last_run_status"),
        )
