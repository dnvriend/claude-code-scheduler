"""Run data model for Claude Code Scheduler.

This module contains the Run dataclass representing a single execution
instance of a scheduled task.

Key Components:
    - Run: Execution record with status, output, and timing information

Dependencies:
    - dataclasses: Python dataclass decorators
    - datetime: Time tracking for execution timing
    - uuid: UUID for run and task identification
    - models.enums: RunStatus enum

Related Modules:
    - models.task: Task that this run executes
    - services.executor: Creates and updates Run instances
    - storage.config_storage: Persists runs to JSON
    - ui.panels.runs_panel: Displays runs in GUI

Collaborators:
    - Task: Run belongs to a Task (via task_id foreign key)
    - TaskExecutor: Creates Run instances during execution

Example:
    >>> from claude_code_scheduler.models.run import Run
    >>> from claude_code_scheduler.models.enums import RunStatus
    >>> run = Run(task_name="Daily Review", status=RunStatus.RUNNING)

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from claude_code_scheduler.models.enums import RunStatus


@dataclass
class Run:
    """A single execution instance of a scheduled task."""

    id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    task_name: str = ""  # Denormalized for display
    status: RunStatus = RunStatus.UPCOMING
    scheduled_time: datetime = field(default_factory=datetime.now)
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration: timedelta | None = None
    session_id: UUID | None = None  # The session ID used for this run
    output: str = ""  # Formatted output
    raw_output: str = ""  # Raw CLI output (JSONL)
    errors: str = ""  # stderr content
    exit_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert run to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id),
            "task_name": self.task_name,
            "status": self.status.value,
            "scheduled_time": self.scheduled_time.isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration.total_seconds() if self.duration else None,
            "session_id": str(self.session_id) if self.session_id else None,
            "output": self.output,
            "raw_output": self.raw_output,
            "errors": self.errors,
            "exit_code": self.exit_code,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Run:
        """Create run from dictionary."""
        duration = None
        if data.get("duration") is not None:
            duration = timedelta(seconds=data["duration"])

        return cls(
            id=UUID(data["id"]),
            task_id=UUID(data["task_id"]),
            task_name=data.get("task_name", ""),
            status=RunStatus(data.get("status", "upcoming")),
            scheduled_time=datetime.fromisoformat(data["scheduled_time"]),
            start_time=(
                datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None
            ),
            end_time=(datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None),
            duration=duration,
            session_id=UUID(data["session_id"]) if data.get("session_id") else None,
            output=data.get("output", ""),
            raw_output=data.get("raw_output", ""),
            errors=data.get("errors", ""),
            exit_code=data.get("exit_code"),
        )
