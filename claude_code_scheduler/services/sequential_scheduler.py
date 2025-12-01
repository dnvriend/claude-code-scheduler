"""Sequential Scheduler for Claude Code Scheduler.

This module manages sequential task execution within Jobs, observing run
completions and triggering subsequent tasks in the job's task_order sequence.

Key Components:
    - SequentialScheduler: Main scheduler for job task sequences
    - JobExecutionState: Tracks execution state of running job

Dependencies:
    - threading: Timer for retry delays
    - models.job: Job data model
    - models.task: Task data model
    - models.run: Run data model
    - models.enums: JobStatus, RunStatus
    - services.git_service: Git worktree creation

Related Modules:
    - services.scheduler: TaskScheduler that executes individual tasks
    - models.job: Job with task_order and working_directory
    - ui.main_window: Creates SequentialScheduler

Calls:
    - GitService: Create git worktrees for job isolation
    - TaskScheduler.run_task_now: Execute next task in sequence

Called By:
    - MainWindow: Creates instance and connects signals
    - RunsPanel: Start job button

Example:
    >>> from claude_code_scheduler.services.sequential_scheduler import SequentialScheduler
    >>> seq_scheduler = SequentialScheduler(task_scheduler, get_job, get_task, save_job)
    >>> seq_scheduler.start_job(job)

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from collections.abc import Callable
from dataclasses import dataclass
from threading import Timer
from uuid import UUID

from claude_code_scheduler.logging_config import get_logger
from claude_code_scheduler.models.enums import JobStatus, RunStatus
from claude_code_scheduler.models.job import Job
from claude_code_scheduler.models.run import Run
from claude_code_scheduler.models.task import Task
from claude_code_scheduler.services.git_service import GitService, GitServiceError

logger = get_logger(__name__)


@dataclass
class JobExecutionState:
    """Tracks the execution state of a running job sequence."""

    job_id: UUID
    task_order: list[UUID]
    current_index: int = 0
    retry_count: int = 0
    status: JobStatus = JobStatus.IN_PROGRESS

    @property
    def current_task_id(self) -> UUID | None:
        """Get the current task ID in the sequence."""
        if 0 <= self.current_index < len(self.task_order):
            return self.task_order[self.current_index]
        return None

    @property
    def total_tasks(self) -> int:
        """Get total number of tasks in sequence."""
        return len(self.task_order)

    @property
    def is_complete(self) -> bool:
        """Check if all tasks in sequence have completed."""
        return self.current_index >= len(self.task_order)


@dataclass
class SequentialSchedulerConfig:
    """Configuration for the sequential scheduler."""

    # Callbacks
    task_resolver: Callable[[UUID], Task | None] | None = None
    job_resolver: Callable[[UUID], Job | None] | None = None
    task_runner: Callable[[Task], None] | None = None
    job_status_updater: Callable[[UUID, JobStatus], None] | None = None

    # Event callbacks for UI updates
    on_job_started: Callable[[UUID], None] | None = None
    on_job_progress: Callable[[UUID, int, int], None] | None = None  # job_id, current, total
    on_job_completed: Callable[[UUID, JobStatus], None] | None = None


class SequentialScheduler:
    """Manages sequential task execution within Jobs.

    Observes run completion events and triggers the next task in sequence
    when the previous task completes successfully.
    """

    def __init__(self, config: SequentialSchedulerConfig | None = None) -> None:
        """Initialize the sequential scheduler.

        Args:
            config: Configuration with callbacks for task/job resolution and execution.
        """
        self.config = config or SequentialSchedulerConfig()

        # Track active job executions: job_id -> JobExecutionState
        self._active_jobs: dict[UUID, JobExecutionState] = {}

        # Track task -> job mapping for quick lookup on run completion
        self._task_to_job: dict[UUID, UUID] = {}

        # Pending retry timers
        self._retry_timers: dict[UUID, Timer] = {}

    def start_job(self, job: Job) -> bool:
        """Start sequential execution of a job.

        If the job's working_directory has use_git_worktree enabled, creates
        the worktree before starting task execution.

        Args:
            job: The job to execute.

        Returns:
            True if job was started, False if already running or no tasks.
        """
        if job.id in self._active_jobs:
            logger.warning("Job %s is already running", job.name)
            return False

        if not job.task_order:
            logger.warning("Job %s has no tasks in task_order", job.name)
            return False

        # Create worktree if configured
        if job.working_directory.use_git_worktree:
            if not self._setup_worktree(job):
                return False

        # Create execution state
        state = JobExecutionState(
            job_id=job.id,
            task_order=list(job.task_order),
        )
        self._active_jobs[job.id] = state

        # Build task -> job mapping
        for task_id in job.task_order:
            self._task_to_job[task_id] = job.id

        logger.info(
            "Starting job '%s' with %d tasks in sequence",
            job.name,
            len(job.task_order),
        )

        # Update job status
        if self.config.job_status_updater:
            self.config.job_status_updater(job.id, JobStatus.IN_PROGRESS)

        # Notify job started
        if self.config.on_job_started:
            self.config.on_job_started(job.id)

        # Start first task
        self._run_current_task(state)
        return True

    def _setup_worktree(self, job: Job) -> bool:
        """Set up git worktree for job isolation.

        Args:
            job: The job to set up worktree for.

        Returns:
            True if worktree was created or exists, False on error.
        """
        wd = job.working_directory
        worktree_name = wd.worktree_name or f"job-{str(job.id)[:8]}"

        logger.info("Setting up worktree '%s' for job '%s'", worktree_name, job.name)

        try:
            git_service = GitService(wd.path)

            # Ensure trees/ is in .gitignore
            git_service.ensure_trees_gitignored()

            # Create worktree with new branch based on selected branch
            worktree_path = git_service.create_worktree(
                name=worktree_name,
                base_branch=wd.worktree_branch,
            )

            logger.info("Worktree ready: %s", worktree_path)
            return True

        except GitServiceError as e:
            logger.error("Failed to create worktree: %s", e)
            return False

    def stop_job(self, job_id: UUID, status: JobStatus = JobStatus.FAILED) -> bool:
        """Stop a running job sequence.

        Args:
            job_id: ID of the job to stop.
            status: Final status to set (FAILED or CANCELLED).

        Returns:
            True if job was stopped, False if not running.
        """
        state = self._active_jobs.get(job_id)
        if not state:
            return False

        # Cancel any pending retry timer
        self._cancel_retry_timer(job_id)

        # Clean up
        self._cleanup_job(state, status)
        return True

    def on_run_completed(self, run: Run) -> None:
        """Handle run completion event (observer callback).

        This should be called when any task run completes.

        Args:
            run: The completed run.
        """
        # Check if this task is part of an active job sequence
        job_id = self._task_to_job.get(run.task_id)
        if not job_id:
            return

        state = self._active_jobs.get(job_id)
        if not state:
            return

        # Verify this is the current task in sequence
        if run.task_id != state.current_task_id:
            logger.warning(
                "Run completed for task %s but current task is %s",
                run.task_id,
                state.current_task_id,
            )
            return

        logger.info(
            "Task %d/%d completed with status: %s",
            state.current_index + 1,
            state.total_tasks,
            run.status.value,
        )

        if run.status == RunStatus.SUCCESS:
            self._handle_task_success(state)
        elif run.status == RunStatus.FAILED:
            self._handle_task_failure(state, run)
        elif run.status == RunStatus.CANCELLED:
            self._handle_task_cancelled(state)

    def get_job_state(self, job_id: UUID) -> JobExecutionState | None:
        """Get the execution state of a running job.

        Args:
            job_id: ID of the job.

        Returns:
            The job's execution state, or None if not running.
        """
        return self._active_jobs.get(job_id)

    def is_job_running(self, job_id: UUID) -> bool:
        """Check if a job is currently running.

        Args:
            job_id: ID of the job.

        Returns:
            True if job is running.
        """
        return job_id in self._active_jobs

    def _run_current_task(self, state: JobExecutionState) -> None:
        """Run the current task in the job sequence."""
        task_id = state.current_task_id
        if not task_id:
            logger.error("No current task to run for job %s", state.job_id)
            return

        task = self._resolve_task(task_id)
        if not task:
            logger.error("Task %s not found, stopping job", task_id)
            self._cleanup_job(state, JobStatus.FAILED)
            return

        # Emit progress event
        if self.config.on_job_progress:
            self.config.on_job_progress(
                state.job_id,
                state.current_index + 1,
                state.total_tasks,
            )

        # Run the task
        if self.config.task_runner:
            logger.info(
                "Running task %d/%d: %s",
                state.current_index + 1,
                state.total_tasks,
                task.name,
            )
            self.config.task_runner(task)
        else:
            logger.error("No task_runner configured")
            self._cleanup_job(state, JobStatus.FAILED)

    def _handle_task_success(self, state: JobExecutionState) -> None:
        """Handle successful task completion - advance to next task."""
        state.retry_count = 0  # Reset retry count
        state.current_index += 1

        if state.is_complete:
            # All tasks completed successfully
            logger.info("Job %s completed successfully", state.job_id)
            self._cleanup_job(state, JobStatus.COMPLETED)
        else:
            # Run next task
            self._run_current_task(state)

    def _handle_task_failure(self, state: JobExecutionState, run: Run) -> None:
        """Handle task failure - retry or fail job.

        Retry behavior is controlled by the task's retry config:
        - retry.enabled: Must be True for retries
        - retry.max_attempts: Maximum retry attempts
        - retry.delay_seconds: Delay between retries
        """
        task = self._resolve_task(run.task_id)
        if not task:
            self._cleanup_job(state, JobStatus.FAILED)
            return

        # Use task's retry config (from UI advanced options)
        retry_enabled = task.retry.enabled
        max_retries = task.retry.max_attempts if retry_enabled else 0
        retry_delay = task.retry.delay_seconds

        if retry_enabled and state.retry_count < max_retries:
            state.retry_count += 1
            logger.info(
                "Task failed, retrying (%d/%d) in %d seconds",
                state.retry_count,
                max_retries,
                retry_delay,
            )

            # Schedule retry after delay
            timer = Timer(retry_delay, self._retry_task, args=[state])
            timer.daemon = True
            timer.start()
            self._retry_timers[state.job_id] = timer
        else:
            logger.error(
                "Task failed after %d retries, stopping job",
                state.retry_count,
            )
            self._cleanup_job(state, JobStatus.FAILED)

    def _handle_task_cancelled(self, state: JobExecutionState) -> None:
        """Handle task cancellation - stop job sequence."""
        logger.info("Task cancelled, stopping job %s", state.job_id)
        self._cleanup_job(state, JobStatus.FAILED)

    def _retry_task(self, state: JobExecutionState) -> None:
        """Retry the current task after delay."""
        if state.job_id in self._retry_timers:
            del self._retry_timers[state.job_id]

        if state.job_id not in self._active_jobs:
            return  # Job was stopped

        logger.info("Retrying task (attempt %d)", state.retry_count + 1)
        self._run_current_task(state)

    def _cancel_retry_timer(self, job_id: UUID) -> None:
        """Cancel any pending retry timer for a job."""
        timer = self._retry_timers.pop(job_id, None)
        if timer:
            timer.cancel()

    def _cleanup_job(self, state: JobExecutionState, status: JobStatus) -> None:
        """Clean up after job completion or failure."""
        job_id = state.job_id

        # Remove task -> job mappings
        for task_id in state.task_order:
            self._task_to_job.pop(task_id, None)

        # Remove from active jobs
        self._active_jobs.pop(job_id, None)

        # Cancel retry timer
        self._cancel_retry_timer(job_id)

        # Update job status
        if self.config.job_status_updater:
            self.config.job_status_updater(job_id, status)

        # Notify completion
        if self.config.on_job_completed:
            self.config.on_job_completed(job_id, status)

        logger.info("Job %s finished with status: %s", job_id, status.value)

    def _resolve_task(self, task_id: UUID) -> Task | None:
        """Resolve a task by ID using the configured resolver."""
        if self.config.task_resolver:
            return self.config.task_resolver(task_id)
        return None
