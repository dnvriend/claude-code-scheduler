"""ExportService for Claude Code Scheduler.

This module provides job and task export functionality to JSON format
for backup, migration, or sharing purposes.

Key Components:
    - ExportService: Handles job and task data export with metadata

Dependencies:
    - json: JSON serialization
    - datetime: Timestamp generation
    - pathlib: File path handling
    - uuid: UUID handling
    - models.job: Job data model
    - models.task: Task data model
    - storage.config_storage: Data persistence

Related Modules:
    - storage.config_storage: Loads job and task data
    - models.job: Job serialization via to_dict()
    - models.task: Task serialization via to_dict()
    - _version: Version information for export metadata

Example:
    >>> from claude_code_scheduler.services.export_service import ExportService
    >>> from pathlib import Path
    >>> service = ExportService()
    >>> data = service.export_job(job_id)
    >>> output_path = service.export_to_file(job_id, Path("backup.json"))

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from claude_code_scheduler.logging_config import get_logger
from claude_code_scheduler.storage.config_storage import ConfigStorage

logger = get_logger(__name__)


class ExportService:
    """Service for exporting jobs and tasks to JSON format."""

    def __init__(self, storage: ConfigStorage | None = None) -> None:
        """Initialize export service.

        Args:
            storage: Optional storage instance. Defaults to new ConfigStorage.
        """
        self.storage = storage or ConfigStorage()

    def export_job(self, job_id: UUID, include_profiles: bool = False) -> dict[str, Any]:
        """Export job and its tasks to dictionary format.

        Args:
            job_id: UUID of the job to export.
            include_profiles: If True, include profile definitions (not implemented yet).

        Returns:
            Dictionary containing job data, tasks, and metadata in the format:
            {
                "version": "1.0",
                "exported_at": "2025-12-01T10:00:00Z",
                "job": {...},
                "tasks": [...],
                "profiles_referenced": [...]
            }

        Raises:
            ValueError: If job is not found.
        """
        logger.debug("Exporting job %s", job_id)

        # Load job and associated tasks
        job = self.storage.get_job(job_id)
        if not job:
            raise ValueError(f"Job with ID {job_id} not found")

        tasks = self.storage.get_tasks_for_job(job_id)

        # Collect referenced profile IDs from job and tasks
        profiles_referenced = set()
        if job.profile:
            profiles_referenced.add(job.profile)
        for task in tasks:
            if task.profile:
                profiles_referenced.add(task.profile)

        # Build export data structure
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "job": job.to_dict(),
            "tasks": [task.to_dict() for task in tasks],
            "profiles_referenced": sorted(list(profiles_referenced)),
        }

        logger.info(
            "Exported job '%s' with %d tasks",
            job.name,
            len(tasks),
        )
        return export_data

    def export_to_file(self, job_id: UUID, output_path: Path) -> Path:
        """Export job and tasks to JSON file.

        Args:
            job_id: UUID of the job to export.
            output_path: Path where JSON file will be written.

        Returns:
            Path to the written file.

        Raises:
            ValueError: If job is not found.
            OSError: If file cannot be written.
        """
        logger.debug("Exporting job %s to file %s", job_id, output_path)

        # Get export data
        export_data = self.export_job(job_id)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info("Export saved to %s", output_path)
            return output_path

        except OSError as e:
            logger.error("Failed to write export file %s: %s", output_path, e)
            raise

    def validate_export_data(self, export_data: dict[str, Any]) -> bool:
        """Validate export data structure and required fields.

        Args:
            export_data: Dictionary containing export data.

        Returns:
            True if valid, False otherwise.
        """
        required_fields = {"version", "exported_at", "job", "tasks", "profiles_referenced"}

        if not required_fields.issubset(export_data.keys()):
            logger.warning(
                "Export data missing required fields: %s", required_fields - export_data.keys()
            )
            return False

        # Validate job structure
        job_data = export_data["job"]
        job_fields = {"id", "name", "status", "created_at", "updated_at"}
        if not job_fields.issubset(job_data.keys()):
            logger.warning("Job data missing required fields: %s", job_fields - job_data.keys())
            return False

        # Validate tasks list
        tasks = export_data["tasks"]
        if not isinstance(tasks, list):
            logger.warning("Tasks field is not a list")
            return False

        # Validate each task structure
        task_fields = {"id", "name", "job_id", "created_at", "updated_at"}
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                logger.warning("Task %d is not a dictionary", i)
                return False
            if not task_fields.issubset(task.keys()):
                logger.warning("Task %d missing required fields: %s", i, task_fields - task.keys())
                return False

        # Validate profiles_referenced is a list
        if not isinstance(export_data["profiles_referenced"], list):
            logger.warning("profiles_referenced field is not a list")
            return False

        logger.debug("Export data validation passed")
        return True
