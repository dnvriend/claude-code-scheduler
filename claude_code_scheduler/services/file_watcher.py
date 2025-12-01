"""File Watcher Service for Claude Code Scheduler.

This module monitors directories for file system changes and triggers
task execution using the watchdog library.

Key Components:
    - FileWatcher: Main watcher managing multiple directory observers
    - TaskFileEventHandler: Event handler with debouncing

Dependencies:
    - watchdog: File system monitoring library
    - pathlib: Path handling
    - models.task: Task data model
    - models.enums: ScheduleType enum

Related Modules:
    - services.scheduler: Integrates file watcher for FILE_WATCH schedules
    - models.task: ScheduleConfig with watch_directory field

Calls:
    - watchdog.Observer: File system observer
    - Task callback: Trigger task execution

Called By:
    - TaskScheduler: Manages file watchers for FILE_WATCH tasks

Example:
    >>> from claude_code_scheduler.services.file_watcher import FileWatcher
    >>> watcher = FileWatcher()
    >>> watcher.add_task(task, on_trigger_callback)

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import os
import time
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from claude_code_scheduler.logging_config import get_logger
from claude_code_scheduler.models.enums import ScheduleType
from claude_code_scheduler.models.task import Task

logger = get_logger(__name__)


class TaskFileEventHandler(FileSystemEventHandler):
    """Handles file system events and triggers task execution."""

    def __init__(
        self,
        task: Task,
        on_trigger: Callable[[Task], None],
        debounce_seconds: int = 5,
    ) -> None:
        """Initialize handler.

        Args:
            task: The task to execute on file changes.
            on_trigger: Callback to execute the task.
            debounce_seconds: Minimum seconds between triggers.
        """
        super().__init__()
        self.task = task
        self.on_trigger = on_trigger
        self.debounce_seconds = debounce_seconds
        self._last_trigger: float = 0

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle any file system event.

        Args:
            event: The file system event.
        """
        # Skip directory events and temporary files
        if event.is_directory:
            return

        src_path = str(event.src_path)
        if src_path.endswith((".tmp", ".swp", ".DS_Store", "~")):
            return

        # Debounce: skip if triggered recently
        now = time.time()
        if now - self._last_trigger < self.debounce_seconds:
            logger.debug("Debouncing file event for task: %s", self.task.name)
            return

        self._last_trigger = now
        logger.info(
            "File change detected for task %s: %s (%s)",
            self.task.name,
            src_path,
            event.event_type,
        )

        # Trigger task execution
        self.on_trigger(self.task)


class FileWatcher:
    """Monitors directories for file changes and triggers tasks."""

    def __init__(
        self,
        on_trigger: Callable[[Task], None],
    ) -> None:
        """Initialize file watcher.

        Args:
            on_trigger: Callback to execute when a watched task should run.
        """
        self.on_trigger = on_trigger
        self._observer = Observer()
        self._watches: dict[UUID, tuple[object, TaskFileEventHandler]] = {}

    def start(self) -> None:
        """Start the file watcher."""
        logger.info("Starting file watcher")
        self._observer.start()

    def stop(self) -> None:
        """Stop the file watcher."""
        logger.info("Stopping file watcher")
        self._observer.stop()
        self._observer.join(timeout=5)

    def watch_task(self, task: Task) -> None:
        """Start watching for a task's file watch configuration.

        Args:
            task: The task with FILE_WATCH schedule type.
        """
        if task.schedule.schedule_type != ScheduleType.FILE_WATCH:
            logger.warning("Task %s is not a file watch task", task.name)
            return

        if not task.enabled:
            logger.debug("Task %s is disabled, skipping watch", task.name)
            return

        # Remove existing watch if any
        self.unwatch_task(task.id)

        # Get watch configuration
        watch_dir = task.schedule.watch_directory or "~"
        watch_dir = os.path.expanduser(watch_dir)
        watch_dir = os.path.expandvars(watch_dir)

        if not Path(watch_dir).exists():
            logger.warning("Watch directory does not exist: %s", watch_dir)
            return

        recursive = (
            task.schedule.watch_recursive if task.schedule.watch_recursive is not None else True
        )
        debounce = task.schedule.watch_debounce_seconds or 5

        # Create handler and schedule watch
        handler = TaskFileEventHandler(
            task=task,
            on_trigger=self.on_trigger,
            debounce_seconds=debounce,
        )

        watch = self._observer.schedule(
            handler,
            watch_dir,
            recursive=recursive,
        )

        self._watches[task.id] = (watch, handler)
        logger.info(
            "Watching %s for task %s (recursive=%s, debounce=%ds)",
            watch_dir,
            task.name,
            recursive,
            debounce,
        )

    def unwatch_task(self, task_id: UUID) -> None:
        """Stop watching for a task.

        Args:
            task_id: ID of the task to stop watching.
        """
        if task_id in self._watches:
            watch, _ = self._watches[task_id]
            try:
                self._observer.unschedule(watch)  # type: ignore[arg-type]
                logger.debug("Unwatched task: %s", task_id)
            except Exception:  # nosec B110 - intentional cleanup
                pass
            del self._watches[task_id]

    def get_watched_tasks(self) -> list[UUID]:
        """Get list of currently watched task IDs.

        Returns:
            List of task UUIDs being watched.
        """
        return list(self._watches.keys())
