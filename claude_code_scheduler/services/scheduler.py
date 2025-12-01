"""Task Scheduler for Claude Code Scheduler.

This module manages scheduled execution of tasks using APScheduler with
Qt integration for GUI thread safety.

Key Components:
    - TaskScheduler: Main scheduler with APScheduler backend

Dependencies:
    - apscheduler: Scheduling framework (QtScheduler, triggers)
    - models.task: Task and ScheduleConfig
    - models.run: Run records
    - services.executor: TaskExecutor for execution

Related Modules:
    - services.executor: Executes scheduled tasks
    - services.file_watcher: File-watch schedule integration
    - ui.main_window: Creates and manages scheduler

Calls:
    - TaskExecutor.execute: Execute task
    - APScheduler triggers: CronTrigger, IntervalTrigger, DateTrigger

Called By:
    - MainWindow: Creates scheduler instance
    - TaskListPanel: Triggers manual task runs

Example:
    >>> from claude_code_scheduler.services.scheduler import TaskScheduler
    >>> scheduler = TaskScheduler(mock_mode=True)
    >>> scheduler.add_task(task)
    >>> scheduler.start()

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from apscheduler.schedulers.qt import QtScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
from apscheduler.triggers.date import DateTrigger  # type: ignore[import-untyped]
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore[import-untyped]

from claude_code_scheduler.logging_config import get_logger
from claude_code_scheduler.models.enums import IntervalType, ScheduleType
from claude_code_scheduler.models.job import Job
from claude_code_scheduler.models.profile import Profile
from claude_code_scheduler.models.run import Run
from claude_code_scheduler.models.task import Task
from claude_code_scheduler.services.executor import TaskExecutor

logger = get_logger(__name__)


class TaskScheduler:
    """Manages task scheduling using APScheduler with Qt integration."""

    def __init__(
        self,
        on_run_started: Callable[[Run], None] | None = None,
        on_run_completed: Callable[[Run], None] | None = None,
        on_output: Callable[[UUID, str], None] | None = None,
        profile_resolver: Callable[[str], Profile | None] | None = None,
        job_resolver: Callable[[UUID], Job | None] | None = None,
        mock_mode: bool = True,
        unmask_env_vars: bool = False,
    ) -> None:
        """Initialize scheduler.

        Args:
            on_run_started: Callback when a run starts.
            on_run_completed: Callback when a run completes.
            on_output: Callback for streaming output (run_id, line).
            profile_resolver: Callback to resolve profile by ID string.
            job_resolver: Callback to resolve job by task's job_id (for working directory).
            mock_mode: If True, generate mock output instead of calling CLI.
            unmask_env_vars: If True, show full env var values in debug logs.
        """
        self.on_run_started = on_run_started
        self.on_run_completed = on_run_completed
        self.on_output = on_output
        self.profile_resolver = profile_resolver
        self.job_resolver = job_resolver
        self.mock_mode = mock_mode
        self.unmask_env_vars = unmask_env_vars

        # Initialize APScheduler with Qt backend for thread safety
        self._scheduler = QtScheduler()
        self._executor = TaskExecutor(
            on_run_started=on_run_started,
            on_run_completed=on_run_completed,
            on_output=on_output,
            mock_mode=mock_mode,
            unmask_env_vars=unmask_env_vars,
        )

        # Track scheduled jobs by task ID
        self._jobs: dict[UUID, str] = {}

    def start(self) -> None:
        """Start the scheduler."""
        logger.info("Starting task scheduler")
        self._scheduler.start()

    def stop(self) -> None:
        """Stop the scheduler."""
        logger.info("Stopping task scheduler")
        self._scheduler.shutdown(wait=False)

    def schedule_task(self, task: Task) -> None:
        """Schedule a task based on its configuration.

        Args:
            task: The task to schedule.
        """
        # Remove existing schedule if any
        self.unschedule_task(task.id)

        if not task.enabled:
            logger.debug("Task %s is disabled, skipping schedule", task.name)
            return

        schedule = task.schedule
        schedule_type = schedule.schedule_type

        if schedule_type == ScheduleType.MANUAL:
            # Manual tasks are not scheduled automatically
            logger.debug("Task %s is manual, no schedule created", task.name)
            return

        elif schedule_type == ScheduleType.STARTUP:
            # Run once at startup (immediately)
            self._schedule_once(task)

        elif schedule_type == ScheduleType.CALENDAR:
            self._schedule_calendar(task)

        elif schedule_type == ScheduleType.INTERVAL:
            self._schedule_interval(task)

        elif schedule_type == ScheduleType.FILE_WATCH:
            # File watch is handled separately by FileWatcher service
            logger.debug("Task %s uses file watch, handled by FileWatcher", task.name)
            return

        logger.info("Scheduled task: %s (%s)", task.name, schedule_type.value)

    def unschedule_task(self, task_id: UUID) -> None:
        """Remove a task from the schedule.

        Args:
            task_id: ID of the task to unschedule.
        """
        job_id = self._jobs.get(task_id)
        if job_id:
            try:
                self._scheduler.remove_job(job_id)
                logger.debug("Unscheduled task: %s", task_id)
            except Exception:  # nosec B110 - intentional cleanup
                pass
            del self._jobs[task_id]

    def run_task_now(self, task: Task) -> None:
        """Execute a task immediately.

        Args:
            task: The task to execute.
        """
        logger.info("Running task now: %s", task.name)
        # Schedule for immediate execution
        job = self._scheduler.add_job(
            self._execute_task,
            trigger=DateTrigger(run_date=datetime.now()),
            args=[task],
            id=f"immediate_{task.id}_{datetime.now().timestamp()}",
        )
        logger.debug("Scheduled immediate job: %s", job.id)

    def _execute_task(self, task: Task) -> None:
        """Execute a task (called by scheduler).

        Args:
            task: The task to execute.
        """
        # Look up profile - check job.profile first, then task.profile
        profile = None
        if task.job_id and self.job_resolver:
            job = self.job_resolver(task.job_id)
            if job and job.profile:
                # Job has profile set, use it (overrides task.profile)
                profile = self.profile_resolver(job.profile) if self.profile_resolver else None
                if profile:
                    logger.debug("Using job profile '%s' for task '%s'", profile.name, task.name)
                else:
                    logger.warning("Job profile %s not found for task %s", job.profile, task.name)
            else:
                # Job doesn't have profile, fall back to task.profile
                if task.profile and self.profile_resolver:
                    profile = self.profile_resolver(task.profile)
                    if profile:
                        logger.debug(
                            "Using task profile '%s' for task '%s'", profile.name, task.name
                        )
                    else:
                        logger.warning(
                            "Task profile %s not found for task %s", task.profile, task.name
                        )

        # Resolve working directory from job
        working_directory: str | None = None
        if task.job_id and self.job_resolver:
            job = self.job_resolver(task.job_id)
            if job:
                working_directory = job.get_working_directory_path()
                logger.debug(
                    "Using working directory '%s' from job '%s'",
                    working_directory,
                    job.name,
                )

        self._executor.execute(task, profile, working_directory)

    def _schedule_once(self, task: Task) -> None:
        """Schedule a task to run once (for startup tasks).

        Args:
            task: The task to schedule.
        """
        job = self._scheduler.add_job(
            self._execute_task,
            trigger=DateTrigger(run_date=datetime.now()),
            args=[task],
            id=f"startup_{task.id}",
        )
        self._jobs[task.id] = job.id

    def _schedule_calendar(self, task: Task) -> None:
        """Schedule a task with calendar-based trigger.

        Args:
            task: The task to schedule.
        """
        schedule = task.schedule
        freq = schedule.calendar_frequency or "daily"
        cal_time = schedule.calendar_time

        hour = cal_time.hour if cal_time else 0
        minute = cal_time.minute if cal_time else 0

        if freq == "daily":
            trigger = CronTrigger(hour=hour, minute=minute)

        elif freq == "weekly":
            days = schedule.calendar_days_of_week or [0]
            # APScheduler uses 0=Monday, same as our model
            day_of_week = ",".join(str(d) for d in days)
            trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)

        elif freq == "monthly":
            day = schedule.calendar_day_of_month or 1
            trigger = CronTrigger(day=day, hour=hour, minute=minute)

        else:
            logger.warning("Unknown calendar frequency: %s", freq)
            return

        job = self._scheduler.add_job(
            self._execute_task,
            trigger=trigger,
            args=[task],
            id=f"calendar_{task.id}",
        )
        self._jobs[task.id] = job.id

    def _schedule_interval(self, task: Task) -> None:
        """Schedule a task with interval-based trigger.

        Args:
            task: The task to schedule.
        """
        schedule = task.schedule
        interval_type = schedule.interval_type

        if interval_type == IntervalType.CRON:
            # Use cron expression
            cron_expr = schedule.interval_cron or "* * * * *"
            trigger = CronTrigger.from_crontab(cron_expr)

        elif interval_type == IntervalType.SIMPLE:
            # Use preset interval
            preset = schedule.interval_preset or "5 minutes"
            seconds = self._preset_to_seconds(preset)
            trigger = IntervalTrigger(seconds=seconds)

        else:
            # Custom interval
            value = schedule.interval_value or 1
            unit = schedule.interval_unit or "minutes"
            kwargs = {unit: value}
            trigger = IntervalTrigger(**kwargs)

        job = self._scheduler.add_job(
            self._execute_task,
            trigger=trigger,
            args=[task],
            id=f"interval_{task.id}",
        )
        self._jobs[task.id] = job.id

    def _preset_to_seconds(self, preset: str) -> int:
        """Convert preset string to seconds.

        Args:
            preset: Preset string like "5 minutes" or "1 hour".

        Returns:
            Number of seconds.
        """
        presets = {
            "5 minutes": 300,
            "15 minutes": 900,
            "30 minutes": 1800,
            "1 hour": 3600,
            "2 hours": 7200,
            "4 hours": 14400,
            "12 hours": 43200,
            "24 hours": 86400,
        }
        return presets.get(preset, 300)  # Default to 5 minutes

    def get_scheduled_tasks(self) -> list[UUID]:
        """Get list of currently scheduled task IDs.

        Returns:
            List of task UUIDs that are scheduled.
        """
        return list(self._jobs.keys())

    def stop_run(self, run_id: UUID) -> bool:
        """Stop a running task by its run ID.

        Args:
            run_id: UUID of the run to stop.

        Returns:
            True if the process was stopped, False if not found or already stopped.
        """
        logger.info("Stopping run: %s", run_id)
        return self._executor.stop_run(run_id)
