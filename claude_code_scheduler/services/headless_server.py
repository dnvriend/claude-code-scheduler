"""Headless Server for Claude Code Scheduler.

This module provides a headless HTTP server that combines the REST API
with parallel job execution capabilities. It runs without a GUI and
manages job scheduling through a thread pool.

Key Components:
    - HeadlessServer: Main server class with HTTP API and job execution
    - Uses DebugRequestHandler for REST API handling
    - ThreadPoolExecutor for parallel job execution
    - SequentialScheduler for task execution within jobs

Dependencies:
    - http.server: HTTP server functionality
    - concurrent.futures: Thread pool for parallel jobs
    - threading: Thread-safe operations
    - signal: Graceful shutdown handling

Related Modules:
    - services.debug_server: REST API handler
    - services.sequential_scheduler: Job task execution
    - services.executor: Task execution
    - storage.config_storage: Data persistence

Example:
    >>> from claude_code_scheduler.services.headless_server import HeadlessServer
    >>> server = HeadlessServer(port=5679, workers=3)
    >>> server.start()

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import signal
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer
from typing import Any
from uuid import UUID

from claude_code_scheduler.logging_config import get_logger
from claude_code_scheduler.models.enums import JobStatus
from claude_code_scheduler.models.job import Job
from claude_code_scheduler.models.task import Task
from claude_code_scheduler.services.debug_server import DebugRequestHandler
from claude_code_scheduler.services.executor import TaskExecutor
from claude_code_scheduler.services.sequential_scheduler import (
    SequentialScheduler,
    SequentialSchedulerConfig,
)
from claude_code_scheduler.storage.config_storage import ConfigStorage

logger = get_logger(__name__)


class HeadlessServer:
    """Headless HTTP server with parallel job execution.

    Provides REST API endpoints via DebugRequestHandler and executes
    jobs in parallel using a thread pool. Tasks within each job run
    sequentially via SequentialScheduler.
    """

    def __init__(
        self,
        port: int = 5679,
        workers: int | None = None,
        config_storage: ConfigStorage | None = None,
    ) -> None:
        """Initialize headless server.

        Args:
            port: Port for HTTP server.
            workers: Number of parallel job workers. If None, loads from settings.
            config_storage: Optional ConfigStorage instance. If None, creates default.
        """
        self.port = port
        self.storage = config_storage or ConfigStorage()

        # Load settings and determine worker count
        settings = self.storage.load_settings()
        self.workers = workers if workers is not None else settings.max_concurrent_tasks
        logger.info("Initializing headless server on port %d with %d workers", port, self.workers)

        # Thread pool for parallel job execution
        self._executor = ThreadPoolExecutor(max_workers=self.workers)

        # Track running jobs
        self._running_jobs: dict[UUID, threading.Event] = {}
        self._jobs_lock = threading.Lock()

        # Create task executor
        self._task_executor = TaskExecutor(
            on_run_started=self._on_run_started,
            on_run_completed=self._on_run_completed,
            mock_mode=settings.mock_mode,
            unmask_env_vars=settings.unmask_env_vars,
        )

        # Create sequential scheduler
        scheduler_config = SequentialSchedulerConfig(
            task_resolver=self._get_task,
            job_resolver=self._get_job,
            task_runner=self._run_task,
            job_status_updater=self._update_job_status,
        )
        self._sequential_scheduler = SequentialScheduler(config=scheduler_config)

        # HTTP server
        self._http_server: HTTPServer | None = None
        self._server_thread: threading.Thread | None = None

        # Shutdown flag
        self._shutdown_event = threading.Event()

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def start(self) -> None:
        """Start the HTTP server and begin accepting requests."""
        logger.info("Starting headless server on http://127.0.0.1:%d", self.port)

        # Configure request handler with providers
        self._configure_handlers()

        # Create HTTP server
        self._http_server = HTTPServer(("127.0.0.1", self.port), DebugRequestHandler)

        # Start server in main thread (blocking)
        logger.info("Server ready - accepting requests")
        try:
            self._http_server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the server and clean up resources."""
        logger.info("Stopping headless server")
        self._shutdown_event.set()

        # Shutdown HTTP server
        if self._http_server:
            self._http_server.shutdown()
            logger.info("HTTP server stopped")

        # Shutdown thread pool
        logger.info("Shutting down thread pool executor")
        self._executor.shutdown(wait=True)
        logger.info("Thread pool shutdown complete")

        logger.info("Headless server stopped")

    def run_job(self, job_id: UUID) -> dict[str, Any]:
        """Execute a job in the thread pool.

        Args:
            job_id: ID of the job to execute.

        Returns:
            Status dict with success/error information.
        """
        # Validate job exists
        job = self.storage.get_job(job_id)
        if not job:
            return {
                "success": False,
                "error": f"Job {job_id} not found",
                "error_code": "JOB_NOT_FOUND",
            }

        # Validate job has tasks in task_order
        if not job.task_order:
            tasks = self.storage.get_tasks_for_job(job_id)
            return {
                "success": False,
                "error": f"Job '{job.name}' has no tasks in task_order",
                "error_code": "NO_TASK_ORDER",
                "details": {
                    "job_id": str(job_id),
                    "job_name": job.name,
                    "tasks_in_job": len(tasks),
                    "task_order_count": 0,
                },
                "hints": [
                    "Create tasks: cli tasks create --job <job-id> --name <name> --prompt <prompt>",
                    "Tasks must be added to task_order for sequential execution",
                    "Set order: cli jobs set-order <job-id> <task-id-1> <task-id-2> ...",
                    "Task order determines execution sequence - first task runs first",
                ],
            }

        # Validate all tasks in task_order exist
        missing_tasks = []
        for task_id in job.task_order:
            task = self.storage.get_task(task_id)
            if not task:
                missing_tasks.append(str(task_id))

        if missing_tasks:
            return {
                "success": False,
                "error": f"Job '{job.name}' references {len(missing_tasks)} missing task(s)",
                "error_code": "MISSING_TASKS",
                "details": {
                    "job_id": str(job_id),
                    "job_name": job.name,
                    "missing_task_ids": missing_tasks,
                },
                "hints": [
                    "Some tasks in task_order were deleted or don't exist",
                    "Update task_order: cli jobs set-order <job-id> <valid-task-ids>",
                ],
            }

        with self._jobs_lock:
            if job_id in self._running_jobs:
                return {
                    "success": False,
                    "error": f"Job '{job.name}' is already running",
                    "error_code": "JOB_ALREADY_RUNNING",
                }

            # Create stop event for this job
            stop_event = threading.Event()
            self._running_jobs[job_id] = stop_event

        # Submit job to thread pool
        logger.info("Submitting job %s to thread pool", job_id)
        self._executor.submit(self._execute_job, job_id, stop_event)

        return {
            "success": True,
            "message": f"Job {job_id} submitted for execution",
        }

    def get_status(self) -> dict[str, Any]:
        """Get server status information.

        Returns:
            Status dict with server information.
        """
        with self._jobs_lock:
            running_jobs = list(self._running_jobs.keys())

        return {
            "status": "running",
            "port": self.port,
            "workers": self.workers,
            "running_jobs": [str(job_id) for job_id in running_jobs],
            "active_threads": threading.active_count(),
        }

    def _execute_job(self, job_id: UUID, stop_event: threading.Event) -> None:
        """Execute a job in a worker thread.

        Args:
            job_id: ID of the job to execute.
            stop_event: Event to signal job cancellation.
        """
        try:
            logger.info("Worker thread starting job %s", job_id)

            # Load job
            job = self.storage.get_job(job_id)
            if not job:
                logger.error("Job %s not found in storage", job_id)
                return

            # Log job details for debugging
            logger.debug(
                "Job details: name='%s', status=%s, task_order=%s, working_dir=%s",
                job.name,
                job.status.value,
                [str(t)[:8] for t in job.task_order],
                job.working_directory.path,
            )

            # Check prerequisites before starting
            if not job.task_order:
                logger.error(
                    "Job '%s' (%s) has no tasks in task_order. "
                    "Add tasks to the job and set the task order before running.",
                    job.name,
                    job_id,
                )
                return

            # Log task details
            tasks = self.storage.get_tasks_for_job(job_id)
            logger.info(
                "Job '%s' has %d tasks in order, %d tasks in storage",
                job.name,
                len(job.task_order),
                len(tasks),
            )
            for i, task_id in enumerate(job.task_order):
                task = self.storage.get_task(task_id)
                if task:
                    logger.debug(
                        "  Task %d: %s (%s) - %s",
                        i + 1,
                        task.name,
                        str(task_id)[:8],
                        "enabled" if task.enabled else "disabled",
                    )
                else:
                    logger.warning(
                        "  Task %d: %s NOT FOUND in storage",
                        i + 1,
                        str(task_id)[:8],
                    )

            # Start job execution via sequential scheduler
            success = self._sequential_scheduler.start_job(job)
            if not success:
                logger.error(
                    "Failed to start job '%s' (%s) - check logs above for details",
                    job.name,
                    job_id,
                )
                return

            logger.info("Job '%s' (%s) execution started", job.name, job_id)

        except Exception as e:
            logger.error("Error executing job %s: %s", job_id, e)
        finally:
            # Remove from running jobs
            with self._jobs_lock:
                self._running_jobs.pop(job_id, None)
            logger.info("Worker thread finished job %s", job_id)

    def _configure_handlers(self) -> None:
        """Configure HTTP request handlers with data providers."""
        # Job providers
        DebugRequestHandler.job_list_provider = self._api_job_list
        DebugRequestHandler.job_get_provider = self._api_job_get
        DebugRequestHandler.job_create_provider = self._api_job_create
        DebugRequestHandler.job_update_provider = self._api_job_update
        DebugRequestHandler.job_delete_provider = self._api_job_delete
        DebugRequestHandler.job_tasks_provider = self._api_job_tasks
        DebugRequestHandler.job_run_provider = self._api_job_run
        DebugRequestHandler.job_stop_provider = self._api_job_stop

        # Task providers
        DebugRequestHandler.task_get_provider = self._api_task_get
        DebugRequestHandler.task_create_provider = self._api_task_create
        DebugRequestHandler.task_update_provider = self._api_task_update
        DebugRequestHandler.task_delete_provider = self._api_task_delete
        DebugRequestHandler.task_run_provider = self._api_task_run

        # Run providers
        DebugRequestHandler.run_get_provider = self._api_run_get
        DebugRequestHandler.run_stop_provider = self._api_run_stop

        # Profile providers
        DebugRequestHandler.profile_list_provider = self._api_profile_list
        DebugRequestHandler.profile_get_provider = self._api_profile_get

        # State providers
        DebugRequestHandler.state_provider = self._api_state

        # Short ID resolvers (for prefix matching)
        DebugRequestHandler.task_id_resolver = self.storage.resolve_task_id
        DebugRequestHandler.job_id_resolver = self.storage.resolve_job_id
        DebugRequestHandler.run_id_resolver = self.storage.resolve_run_id

        # Set port on handler
        DebugRequestHandler.server_port = self.port

    # API Provider Methods - Jobs

    def _api_job_list(self) -> dict[str, Any]:
        """List all jobs."""
        jobs = self.storage.load_jobs()
        return {
            "jobs": [job.to_dict() for job in jobs],
            "count": len(jobs),
        }

    def _api_job_get(self, job_id: UUID) -> dict[str, Any]:
        """Get a single job."""
        job = self.storage.get_job(job_id)
        if not job:
            return {"success": False, "error": f"Job {job_id} not found"}
        return {"success": True, "job": job.to_dict()}

    def _api_job_create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new job."""
        try:
            job = Job.from_dict(data)
            self.storage.save_job(job)
            logger.info("Created job: %s", job.name)
            return {"success": True, "job": job.to_dict()}
        except Exception as e:
            logger.error("Failed to create job: %s", e)
            return {"success": False, "error": str(e)}

    def _api_job_update(self, job_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing job."""
        try:
            job = self.storage.get_job(job_id)
            if not job:
                return {"success": False, "error": f"Job {job_id} not found"}

            # Update job fields from data
            updated_job = Job.from_dict({**job.to_dict(), **data, "id": str(job_id)})
            self.storage.save_job(updated_job)
            logger.info("Updated job: %s", updated_job.name)
            return {"success": True, "job": updated_job.to_dict()}
        except Exception as e:
            logger.error("Failed to update job: %s", e)
            return {"success": False, "error": str(e)}

    def _api_job_delete(self, job_id: UUID) -> dict[str, Any]:
        """Delete a job."""
        try:
            success = self.storage.delete_job(job_id, cascade=True)
            if success:
                logger.info("Deleted job: %s", job_id)
                return {"success": True, "message": f"Job {job_id} deleted"}
            return {"success": False, "error": f"Job {job_id} not found"}
        except Exception as e:
            logger.error("Failed to delete job: %s", e)
            return {"success": False, "error": str(e)}

    def _api_job_tasks(self, job_id: UUID) -> dict[str, Any]:
        """List tasks for a job."""
        tasks = self.storage.get_tasks_for_job(job_id)
        return {
            "tasks": [task.to_dict() for task in tasks],
            "count": len(tasks),
        }

    def _api_job_run(self, job_id: UUID) -> dict[str, Any]:
        """Run a job."""
        return self.run_job(job_id)

    def _api_job_stop(self, job_id: UUID) -> dict[str, Any]:
        """Stop a running job."""
        with self._jobs_lock:
            stop_event = self._running_jobs.get(job_id)
            if not stop_event:
                return {
                    "success": False,
                    "error": f"Job {job_id} is not running",
                }
            stop_event.set()

        # Stop the job in the sequential scheduler
        self._sequential_scheduler.stop_job(job_id, JobStatus.FAILED)

        return {
            "success": True,
            "message": f"Job {job_id} stop requested",
        }

    # API Provider Methods - Tasks

    def _api_task_get(self, task_id: UUID) -> dict[str, Any]:
        """Get a single task."""
        task = self.storage.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        return {"success": True, "task": task.to_dict()}

    def _api_task_create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new task."""
        try:
            task = Task.from_dict(data)
            self.storage.save_task(task)
            logger.info("Created task: %s", task.name)
            return {"success": True, "task": task.to_dict()}
        except Exception as e:
            logger.error("Failed to create task: %s", e)
            return {"success": False, "error": str(e)}

    def _api_task_update(self, task_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing task."""
        try:
            task = self.storage.get_task(task_id)
            if not task:
                return {"success": False, "error": f"Task {task_id} not found"}

            # Update task fields from data
            updated_task = Task.from_dict({**task.to_dict(), **data, "id": str(task_id)})
            self.storage.save_task(updated_task)
            logger.info("Updated task: %s", updated_task.name)
            return {"success": True, "task": updated_task.to_dict()}
        except Exception as e:
            logger.error("Failed to update task: %s", e)
            return {"success": False, "error": str(e)}

    def _api_task_delete(self, task_id: UUID) -> dict[str, Any]:
        """Delete a task."""
        try:
            success = self.storage.delete_task(task_id)
            if success:
                logger.info("Deleted task: %s", task_id)
                return {"success": True, "message": f"Task {task_id} deleted"}
            return {"success": False, "error": f"Task {task_id} not found"}
        except Exception as e:
            logger.error("Failed to delete task: %s", e)
            return {"success": False, "error": str(e)}

    def _api_task_run(self, task_id: UUID) -> dict[str, Any]:
        """Run a task immediately."""
        try:
            task = self.storage.get_task(task_id)
            if not task:
                return {"success": False, "error": f"Task {task_id} not found"}

            # Execute task in thread pool
            self._executor.submit(self._run_single_task, task)

            return {
                "success": True,
                "message": f"Task {task_id} submitted for execution",
            }
        except Exception as e:
            logger.error("Failed to run task: %s", e)
            return {"success": False, "error": str(e)}

    # API Provider Methods - Runs

    def _api_run_get(self, run_id: UUID) -> dict[str, Any]:
        """Get a single run."""
        runs = self.storage.load_runs()
        run = next((r for r in runs if r.id == run_id), None)
        if not run:
            return {"success": False, "error": f"Run {run_id} not found"}
        return {"success": True, "run": run.to_dict()}

    def _api_run_stop(self, run_id: UUID) -> dict[str, Any]:
        """Stop a running task."""
        success = self._task_executor.stop_run(run_id)
        if success:
            return {"success": True, "message": f"Run {run_id} stopped"}
        return {"success": False, "error": f"Run {run_id} not found or not running"}

    # API Provider Methods - Profiles

    def _api_profile_list(self) -> dict[str, Any]:
        """List all profiles."""
        profiles = self.storage.load_profiles()
        return {
            "profiles": [profile.to_dict() for profile in profiles],
            "count": len(profiles),
        }

    def _api_profile_get(self, profile_id: UUID) -> dict[str, Any]:
        """Get a single profile."""
        profile = self.storage.get_profile(profile_id)
        if not profile:
            return {"success": False, "error": f"Profile {profile_id} not found"}
        return {"success": True, "profile": profile.to_dict()}

    # API Provider Methods - State

    def _api_state(self) -> dict[str, Any]:
        """Get full application state."""
        jobs = self.storage.load_jobs()
        tasks = self.storage.load_tasks()
        runs = self.storage.load_runs()
        profiles = self.storage.load_profiles()
        settings = self.storage.load_settings()

        with self._jobs_lock:
            running_jobs = list(self._running_jobs.keys())

        return {
            "jobs": [job.to_dict() for job in jobs],
            "tasks": [task.to_dict() for task in tasks],
            "runs": [run.to_dict() for run in runs],
            "profiles": [profile.to_dict() for profile in profiles],
            "settings": settings.to_dict(),
            "running_jobs": [str(job_id) for job_id in running_jobs],
            "server": {
                "port": self.port,
                "workers": self.workers,
                "active_threads": threading.active_count(),
            },
        }

    # Helper methods for sequential scheduler

    def _get_task(self, task_id: UUID) -> Task | None:
        """Resolve a task by ID."""
        return self.storage.get_task(task_id)

    def _get_job(self, job_id: UUID) -> Job | None:
        """Resolve a job by ID."""
        return self.storage.get_job(job_id)

    def _run_task(self, task: Task) -> None:
        """Run a single task."""
        # Get job for working directory
        job = self.storage.get_job(task.job_id) if task.job_id else None
        working_dir = job.working_directory.path if job else None

        # Get profile if specified
        profile = None
        if task.profile:
            profile = self.storage.get_profile(UUID(task.profile))
        elif job and job.profile:
            profile = self.storage.get_profile(UUID(job.profile))

        # Execute task
        self._task_executor.execute(task, profile, working_dir)

    def _run_single_task(self, task: Task) -> None:
        """Run a single task (for direct task execution)."""
        self._run_task(task)

    def _update_job_status(self, job_id: UUID, status: JobStatus) -> None:
        """Update job status."""
        job = self.storage.get_job(job_id)
        if job:
            job.status = status
            self.storage.save_job(job)

    def _on_run_started(self, run: Any) -> None:
        """Callback when a run starts."""
        self.storage.save_run(run)
        logger.info("Run started: %s for task %s", run.id, run.task_name)

    def _on_run_completed(self, run: Any) -> None:
        """Callback when a run completes."""
        self.storage.save_run(run)
        logger.info("Run completed: %s with status %s", run.id, run.status.value)

        # Notify sequential scheduler
        self._sequential_scheduler.on_run_completed(run)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals.

        Note: shutdown() must be called from a different thread than
        serve_forever(), so we spawn a thread to do it.
        """
        logger.info("Received signal %d, shutting down", signum)

        # Spawn thread to call shutdown - it must be called from a different
        # thread than serve_forever() to avoid deadlock
        def do_shutdown() -> None:
            self.stop()

        shutdown_thread = threading.Thread(target=do_shutdown, daemon=True)
        shutdown_thread.start()
