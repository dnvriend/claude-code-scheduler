"""Job data model for Claude Code Scheduler.

This module contains the Job dataclass representing a container for
related tasks. The data hierarchy is: Job (1) → Task (many) → Run (many).

Key Components:
    - Job: Container for related tasks with shared configuration
    - JobWorkingDirectory: Working directory configuration with git worktree support

Dependencies:
    - dataclasses: Python dataclass decorators
    - datetime: Timestamp tracking
    - uuid: UUID generation
    - models.enums: JobStatus enum

Related Modules:
    - models.task: Tasks that belong to this job
    - services.sequential_scheduler: Executes jobs in task order
    - services.git_service: Creates git worktrees for job isolation
    - storage.config_storage: Persists jobs to JSON
    - ui.panels.jobs_panel: Displays jobs in GUI

Collaborators:
    - Task: Tasks belong to Jobs (task.job_id → job.id)
    - Profile: Jobs can override task profiles

Example:
    >>> from claude_code_scheduler.models.job import Job, JobWorkingDirectory
    >>> wd = JobWorkingDirectory(path="~/projects/myapp", use_git_worktree=True)
    >>> job = Job(name="Feature Development", working_directory=wd)

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from claude_code_scheduler.models.enums import JobStatus


@dataclass
class JobWorkingDirectory:
    """Working directory configuration for a Job.

    Supports two modes:
    1. Plain directory: All tasks run in the specified path
    2. Git worktree: Creates/uses a worktree in trees/ subdirectory for isolation

    The worktree mode is useful for parallel job execution or keeping the main
    working tree clean during automated tasks.
    """

    path: str = "~/projects"  # Base directory
    use_git_worktree: bool = False  # If True, create/use worktree for job execution
    worktree_name: str | None = None  # Worktree name (default: job-{job_id[:8]})
    worktree_branch: str | None = None  # Branch to checkout (existing or new)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": self.path,
            "use_git_worktree": self.use_git_worktree,
            "worktree_name": self.worktree_name,
            "worktree_branch": self.worktree_branch,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobWorkingDirectory:
        """Create from dictionary."""
        return cls(
            path=data.get("path", "~/projects"),
            use_git_worktree=data.get("use_git_worktree", False),
            worktree_name=data.get("worktree_name"),
            worktree_branch=data.get("worktree_branch"),
        )

    def get_resolved_path(self, job_id: UUID) -> str:
        """Get the actual working directory path.

        For plain directories, returns the path as-is (expanded).
        For worktrees, returns the path to the worktree inside trees/.
        """
        import os

        expanded_path = os.path.expanduser(self.path)

        if not self.use_git_worktree:
            return expanded_path

        # Worktree mode: return trees/{worktree_name}
        name = self.worktree_name or f"job-{str(job_id)[:8]}"
        return os.path.join(expanded_path, "trees", name)


@dataclass
class Job:
    """A job containing one or more related tasks."""

    id: UUID = field(default_factory=uuid4)
    name: str = "Untitled Job"
    description: str = ""
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Optional profile UUID - overrides task profiles when set
    profile: str | None = None

    # Working directory configuration (tasks inherit this)
    working_directory: JobWorkingDirectory = field(default_factory=JobWorkingDirectory)

    # Ordered list of task UUIDs for sequential execution
    task_order: list[UUID] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "profile": self.profile,
            "working_directory": self.working_directory.to_dict(),
            "task_order": [str(tid) for tid in self.task_order],
        }

    def get_working_directory_path(self) -> str:
        """Get the resolved working directory path for this job."""
        return self.working_directory.get_resolved_path(self.id)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        """Create job from dictionary."""
        task_order_raw = data.get("task_order", [])
        task_order = [UUID(tid) for tid in task_order_raw]

        # Parse working_directory - handle both old and new formats
        wd_data = data.get("working_directory")
        if wd_data and isinstance(wd_data, dict):
            working_directory = JobWorkingDirectory.from_dict(wd_data)
        else:
            working_directory = JobWorkingDirectory()

        return cls(
            id=UUID(data["id"]),
            name=data.get("name", "Untitled Job"),
            description=data.get("description", ""),
            status=JobStatus(data.get("status", "pending")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            profile=data.get("profile"),
            working_directory=working_directory,
            task_order=task_order,
        )
