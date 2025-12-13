"""ConfigStorage for Claude Code Scheduler.

This module handles persistent JSON file storage of all application data
in ~/.config/claude-code-scheduler/.

Key Components:
    - ConfigStorage: Main class for CRUD operations on all data types

Dependencies:
    - json: JSON file serialization
    - pathlib: File path handling
    - models.*: Data models for serialization

Related Modules:
    - models: All data models loaded/saved by ConfigStorage
    - services: Business logic that uses stored data
    - ui.main_window: Loads initial data via ConfigStorage

Calls:
    - Task.to_dict/from_dict: Task serialization
    - Run.to_dict/from_dict: Run serialization
    - Job.to_dict/from_dict: Job serialization
    - Profile.to_dict/from_dict: Profile serialization
    - Settings.to_dict/from_dict: Settings serialization

Called By:
    - MainWindow: Initial data loading
    - All panels: Data CRUD operations
    - TaskScheduler: Task loading for scheduling
    - CLI debug commands: Data inspection

Example:
    >>> from claude_code_scheduler.storage import ConfigStorage
    >>> storage = ConfigStorage()
    >>> tasks = storage.load_tasks()
    >>> storage.save_task(new_task)

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from claude_code_scheduler.logging_config import get_logger
from claude_code_scheduler.models.enums import ScheduleType
from claude_code_scheduler.models.job import Job
from claude_code_scheduler.models.profile import Profile
from claude_code_scheduler.models.run import Run
from claude_code_scheduler.models.settings import Settings
from claude_code_scheduler.models.task import ScheduleConfig, Task

logger = get_logger(__name__)


class ConfigStorage:
    """Persistent storage for application data."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize config storage.

        Args:
            config_dir: Optional custom config directory. Defaults to
                        ~/.config/claude-code-scheduler/
        """
        if config_dir is None:
            config_dir = Path.home() / ".config" / "claude-code-scheduler"

        self.config_dir = config_dir
        self.jobs_file = config_dir / "jobs.json"
        self.tasks_file = config_dir / "tasks.json"
        self.runs_file = config_dir / "runs.json"
        self.profiles_file = config_dir / "profiles.json"
        self.settings_file = config_dir / "settings.json"

        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Config directory: %s", self.config_dir)
        self._initialize_default_files()

    def _initialize_default_files(self) -> None:
        """Create default files if they don't exist."""
        if not self.jobs_file.exists():
            self._write_json(self.jobs_file, [])
        if not self.tasks_file.exists():
            # Create sample tasks on first launch
            sample_tasks = self._create_sample_tasks()
            self._write_json(self.tasks_file, [t.to_dict() for t in sample_tasks])
            logger.info("Created %d sample tasks", len(sample_tasks))
        if not self.runs_file.exists():
            self._write_json(self.runs_file, [])
        if not self.profiles_file.exists():
            self._write_json(self.profiles_file, [])
        if not self.settings_file.exists():
            self._write_json(self.settings_file, Settings().to_dict())

    def _create_sample_tasks(self) -> list[Task]:
        """Create sample tasks for first-time users."""
        from datetime import time

        return [
            Task(
                name="Daily Code Review",
                model="sonnet",
                prompt="Review recent git commits and summarize changes",
                # NOTE: working_directory is now on Job, not Task
                schedule=ScheduleConfig(
                    schedule_type=ScheduleType.CALENDAR,
                    calendar_frequency="daily",
                    calendar_time=time(9, 0),
                ),
                enabled=False,
            ),
            Task(
                name="Weekly Test Report",
                model="sonnet",
                prompt="Run tests and generate a summary report",
                # NOTE: working_directory is now on Job, not Task
                schedule=ScheduleConfig(
                    schedule_type=ScheduleType.CALENDAR,
                    calendar_frequency="weekly",
                    calendar_time=time(10, 0),
                    calendar_days_of_week=[0],  # Monday
                ),
                enabled=False,
            ),
            Task(
                name="On-Demand Analysis",
                model="opus",
                prompt="Analyze the codebase and suggest improvements",
                # NOTE: working_directory is now on Job, not Task
                schedule=ScheduleConfig(schedule_type=ScheduleType.MANUAL),
                enabled=True,
            ),
        ]

    def _read_json(self, file_path: Path) -> dict[str, Any] | list[Any]:
        """Read JSON file, return empty dict/list if not exists."""
        if not file_path.exists():
            result: dict[str, Any] | list[Any] = {} if "settings" in file_path.name else []
            return result

        try:
            with open(file_path, encoding="utf-8") as f:
                data: dict[str, Any] | list[Any] = json.load(f)
                return data
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read %s: %s", file_path, e)
            default: dict[str, Any] | list[Any] = {} if "settings" in file_path.name else []
            return default

    def _write_json(self, file_path: Path, data: dict[str, Any] | list[Any]) -> bool:
        """Write data to JSON file."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Saved %s", file_path)
            return True
        except OSError as e:
            logger.error("Failed to write %s: %s", file_path, e)
            return False

    # Tasks

    def load_tasks(self) -> list[Task]:
        """Load all tasks from storage."""
        data = self._read_json(self.tasks_file)
        if not isinstance(data, list):
            return []

        tasks = []
        for item in data:
            try:
                tasks.append(Task.from_dict(item))
            except (KeyError, ValueError) as e:
                logger.warning("Failed to load task: %s", e)
        logger.info("Loaded %d tasks", len(tasks))
        return tasks

    def save_tasks(self, tasks: list[Task]) -> bool:
        """Save all tasks to storage."""
        data = [task.to_dict() for task in tasks]
        return self._write_json(self.tasks_file, data)

    def get_task(self, task_id: UUID) -> Task | None:
        """Get a specific task by ID."""
        tasks = self.load_tasks()
        for task in tasks:
            if task.id == task_id:
                return task
        return None

    def save_task(self, task: Task) -> bool:
        """Save or update a single task."""
        tasks = self.load_tasks()

        # Find and update existing, or add new
        found = False
        for i, t in enumerate(tasks):
            if t.id == task.id:
                tasks[i] = task
                found = True
                break

        if not found:
            tasks.append(task)

        return self.save_tasks(tasks)

    def delete_task(self, task_id: UUID) -> bool:
        """Delete a task by ID."""
        tasks = self.load_tasks()
        original_count = len(tasks)
        tasks = [t for t in tasks if t.id != task_id]

        if len(tasks) < original_count:
            return self.save_tasks(tasks)
        return False

    def get_tasks_for_job(self, job_id: UUID) -> list[Task]:
        """Get all tasks belonging to a job."""
        tasks = self.load_tasks()
        return [t for t in tasks if t.job_id == job_id]

    # Jobs

    def load_jobs(self) -> list[Job]:
        """Load all jobs from storage."""
        data = self._read_json(self.jobs_file)
        if not isinstance(data, list):
            return []

        jobs = []
        for item in data:
            try:
                jobs.append(Job.from_dict(item))
            except (KeyError, ValueError) as e:
                logger.warning("Failed to load job: %s", e)
        logger.info("Loaded %d jobs", len(jobs))
        return jobs

    def save_jobs(self, jobs: list[Job]) -> bool:
        """Save all jobs to storage."""
        data = [job.to_dict() for job in jobs]
        return self._write_json(self.jobs_file, data)

    def get_job(self, job_id: UUID) -> Job | None:
        """Get a specific job by ID."""
        jobs = self.load_jobs()
        for job in jobs:
            if job.id == job_id:
                return job
        return None

    def save_job(self, job: Job) -> bool:
        """Save or update a single job."""
        jobs = self.load_jobs()

        found = False
        for i, j in enumerate(jobs):
            if j.id == job.id:
                jobs[i] = job
                found = True
                break

        if not found:
            jobs.append(job)

        return self.save_jobs(jobs)

    def delete_job(self, job_id: UUID, cascade: bool = True) -> bool:
        """Delete a job by ID.

        Args:
            job_id: The job ID to delete.
            cascade: If True, also delete all tasks and runs belonging to this job.

        Returns:
            True if job was deleted, False if not found.
        """
        jobs = self.load_jobs()
        original_count = len(jobs)
        jobs = [j for j in jobs if j.id != job_id]

        if len(jobs) < original_count:
            if cascade:
                # Delete all tasks belonging to this job (and their runs)
                tasks = self.get_tasks_for_job(job_id)
                for task in tasks:
                    self.delete_runs_for_task(task.id)
                    self.delete_task(task.id)
                logger.info("Cascade deleted %d tasks for job %s", len(tasks), job_id)
            return self.save_jobs(jobs)
        return False

    # Runs

    def load_runs(self) -> list[Run]:
        """Load all runs from storage."""
        data = self._read_json(self.runs_file)
        if not isinstance(data, list):
            return []

        runs = []
        for item in data:
            try:
                runs.append(Run.from_dict(item))
            except (KeyError, ValueError) as e:
                logger.warning("Failed to load run: %s", e)
        logger.info("Loaded %d runs", len(runs))
        return runs

    def save_runs(self, runs: list[Run]) -> bool:
        """Save all runs to storage."""
        data = [run.to_dict() for run in runs]
        return self._write_json(self.runs_file, data)

    def get_runs_for_task(self, task_id: UUID) -> list[Run]:
        """Get all runs for a specific task."""
        runs = self.load_runs()
        return [r for r in runs if r.task_id == task_id]

    def save_run(self, run: Run) -> bool:
        """Save or update a single run."""
        runs = self.load_runs()

        # Find and update existing, or add new
        found = False
        for i, r in enumerate(runs):
            if r.id == run.id:
                runs[i] = run
                found = True
                break

        if not found:
            runs.append(run)

        return self.save_runs(runs)

    def delete_runs_for_task(self, task_id: UUID) -> bool:
        """Delete all runs for a task."""
        runs = self.load_runs()
        runs = [r for r in runs if r.task_id != task_id]
        return self.save_runs(runs)

    def cleanup_old_runs(self, retention_count: int) -> int:
        """Remove old runs beyond retention count per task.

        Args:
            retention_count: Maximum runs to keep per task.

        Returns:
            Number of runs deleted.
        """
        runs = self.load_runs()
        original_count = len(runs)

        # Group by task
        runs_by_task: dict[UUID, list[Run]] = {}
        for run in runs:
            if run.task_id not in runs_by_task:
                runs_by_task[run.task_id] = []
            runs_by_task[run.task_id].append(run)

        # Keep only most recent N per task
        kept_runs = []
        for task_runs in runs_by_task.values():
            # Sort by scheduled_time descending
            task_runs.sort(key=lambda r: r.scheduled_time, reverse=True)
            kept_runs.extend(task_runs[:retention_count])

        if len(kept_runs) < original_count:
            self.save_runs(kept_runs)

        deleted = original_count - len(kept_runs)
        if deleted > 0:
            logger.info("Cleaned up %d old runs", deleted)
        return deleted

    # Profiles

    def load_profiles(self) -> list[Profile]:
        """Load all profiles from storage."""
        data = self._read_json(self.profiles_file)
        if not isinstance(data, list):
            return []

        profiles = []
        for item in data:
            try:
                profiles.append(Profile.from_dict(item))
            except (KeyError, ValueError) as e:
                logger.warning("Failed to load profile: %s", e)
        logger.info("Loaded %d profiles", len(profiles))
        return profiles

    def save_profiles(self, profiles: list[Profile]) -> bool:
        """Save all profiles to storage."""
        data = [profile.to_dict() for profile in profiles]
        return self._write_json(self.profiles_file, data)

    def get_profile(self, profile_id: UUID) -> Profile | None:
        """Get a specific profile by ID."""
        profiles = self.load_profiles()
        for profile in profiles:
            if profile.id == profile_id:
                return profile
        return None

    def save_profile(self, profile: Profile) -> bool:
        """Save or update a single profile."""
        profiles = self.load_profiles()

        found = False
        for i, p in enumerate(profiles):
            if p.id == profile.id:
                profiles[i] = profile
                found = True
                break

        if not found:
            profiles.append(profile)

        return self.save_profiles(profiles)

    def delete_profile(self, profile_id: UUID) -> bool:
        """Delete a profile by ID."""
        profiles = self.load_profiles()
        original_count = len(profiles)
        profiles = [p for p in profiles if p.id != profile_id]

        if len(profiles) < original_count:
            return self.save_profiles(profiles)
        return False

    # Settings

    def load_settings(self) -> Settings:
        """Load settings from storage."""
        data = self._read_json(self.settings_file)
        if not isinstance(data, dict):
            return Settings()

        try:
            return Settings.from_dict(data)
        except (KeyError, ValueError) as e:
            logger.warning("Failed to load settings: %s", e)
            return Settings()

    def save_settings(self, settings: Settings) -> bool:
        """Save settings to storage."""
        return self._write_json(self.settings_file, settings.to_dict())

    # Short ID resolution

    def resolve_task_id(self, short_id: str) -> UUID | None:
        """Resolve a short task ID (prefix) to a full UUID.

        Args:
            short_id: A short ID prefix (e.g., first 8 chars of UUID)

        Returns:
            Full UUID if exactly one match found, None otherwise
        """
        short_id_lower = short_id.lower()
        tasks = self.load_tasks()
        matches = [t for t in tasks if str(t.id).lower().startswith(short_id_lower)]

        if len(matches) == 1:
            return matches[0].id
        return None

    def resolve_job_id(self, short_id: str) -> UUID | None:
        """Resolve a short job ID (prefix) to a full UUID.

        Args:
            short_id: A short ID prefix (e.g., first 8 chars of UUID)

        Returns:
            Full UUID if exactly one match found, None otherwise
        """
        short_id_lower = short_id.lower()
        jobs = self.load_jobs()
        matches = [j for j in jobs if str(j.id).lower().startswith(short_id_lower)]

        if len(matches) == 1:
            return matches[0].id
        return None

    def resolve_run_id(self, short_id: str) -> UUID | None:
        """Resolve a short run ID (prefix) to a full UUID.

        Args:
            short_id: A short ID prefix (e.g., first 8 chars of UUID)

        Returns:
            Full UUID if exactly one match found, None otherwise
        """
        short_id_lower = short_id.lower()
        runs = self.load_runs()
        matches = [r for r in runs if str(r.id).lower().startswith(short_id_lower)]

        if len(matches) == 1:
            return matches[0].id
        return None
