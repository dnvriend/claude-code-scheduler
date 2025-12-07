"""Import service for Claude Code Scheduler.

This module handles importing jobs and tasks from JSON files with validation
and conflict detection.

Key Components:
    - ImportService: Core import logic with validation
    - ImportResult: Result dataclass with success status and details

Dependencies:
    - dataclasses: Result dataclass
    - json: JSON file parsing
    - pathlib: File path handling
    - uuid: UUID handling and validation
    - typing: Type annotations
    - models.job: Job data model
    - models.task: Task data model
    - storage.config_storage: Persistent storage

Related Modules:
    - services.debug_server: REST API endpoint
    - cli_jobs: CLI import command

Collaborators:
    - ConfigStorage: Persists imported data
    - Job/Task Models: Data validation and conversion

Example:
    >>> from claude_code_scheduler.services.import_service import ImportService
    >>> service = ImportService()
    >>> result = service.import_job(Path("job.json"))
    >>> if result.success:
    ...     print(f"Imported {len(result.tasks)} tasks")

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from claude_code_scheduler.logging_config import get_logger
from claude_code_scheduler.models.job import Job
from claude_code_scheduler.models.task import Task
from claude_code_scheduler.storage.config_storage import ConfigStorage

logger = get_logger(__name__)


@dataclass
class ImportResult:
    """Result of an import operation with success status and details."""

    success: bool
    job: Job | None = None
    tasks: list[Task] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ImportService:
    """Service for importing jobs and tasks from JSON files."""

    def __init__(self, storage: ConfigStorage | None = None) -> None:
        """Initialize the import service.

        Args:
            storage: Optional custom storage instance. Defaults to creating new ConfigStorage.
        """
        self.storage = storage or ConfigStorage()
        self._supported_version = "1.0"

    def validate_import(self, data: dict[str, Any]) -> ImportResult:
        """Validate import data structure and references.

        Args:
            data: Parsed JSON data dictionary

        Returns:
            ImportResult with validation details
        """
        result = ImportResult(success=False)

        # Check version
        version = data.get("version")
        if not version:
            result.errors.append("Missing 'version' field")
            return result

        if version != self._supported_version:
            result.errors.append(
                f"Unsupported version: {version}. Supported: {self._supported_version}"
            )
            return result

        # Validate job structure
        job_data = data.get("job")
        if not job_data:
            result.errors.append("Missing 'job' field")
            return result

        try:
            # Check if job has required fields
            if "id" not in job_data:
                result.errors.append("Job missing required 'id' field")
                return result

            if "name" not in job_data:
                result.errors.append("Job missing required 'name' field")
                return result

            # Validate UUID format
            job_id_str = job_data["id"]
            try:
                job_id = UUID(job_id_str)
            except (ValueError, AttributeError):
                result.errors.append(f"Invalid job UUID format: {job_id_str}")
                return result

            # Check for UUID conflict
            existing_job = self.storage.get_job(job_id)
            if existing_job:
                result.errors.append(
                    f"Job with UUID {job_id} already exists: '{existing_job.name}'"
                )
                result.warnings.append("Use --force to overwrite existing job")

        except (KeyError, TypeError, AttributeError) as e:
            result.errors.append(f"Invalid job structure: {e}")
            return result

        # Validate tasks structure
        tasks_data = data.get("tasks", [])
        if not isinstance(tasks_data, list):
            result.errors.append("'tasks' must be a list")
            return result

        # Validate each task
        for i, task_data in enumerate(tasks_data):
            if not isinstance(task_data, dict):
                result.errors.append(f"Task {i} is not an object")
                continue

            # Check required fields
            required_fields = ["id", "name"]
            for required_field in required_fields:
                if required_field not in task_data:
                    result.errors.append(f"Task {i} missing required '{required_field}' field")

            # Validate task UUID format and check for conflicts
            if "id" in task_data:
                try:
                    task_uuid = UUID(task_data["id"])
                    # Check for task UUID conflict
                    existing_task = self.storage.get_task(task_uuid)
                    if existing_task:
                        result.errors.append(
                            f"Task with UUID {task_uuid} already exists: '{existing_task.name}'"
                        )
                        result.warnings.append("Use --force to overwrite existing tasks")
                except (ValueError, AttributeError):
                    result.errors.append(f"Task {i} has invalid UUID format: {task_data['id']}")

            # Check profile references - ERROR if profile not found
            profile_id = task_data.get("profile")
            if profile_id:
                try:
                    profile_uuid = UUID(profile_id) if "-" in profile_id else None
                    if profile_uuid:
                        profile = self.storage.get_profile(profile_uuid)
                        if not profile:
                            task_name = task_data.get("name", "Unknown")
                            result.errors.append(
                                f"Profile '{profile_id}' referenced by task "
                                f"'{task_name}' not found. Create the profile first."
                            )
                except (ValueError, AttributeError):
                    task_name = task_data.get("name", "Unknown")
                    result.errors.append(
                        f"Invalid profile ID format: {profile_id} in task '{task_name}'"
                    )

        # Check if job has required tasks order matching tasks
        job_task_order = job_data.get("task_order", [])
        if isinstance(job_task_order, list):
            imported_task_ids = {task.get("id") for task in tasks_data if task.get("id")}
            order_task_ids = set(job_task_order)

            # Tasks in order but not in tasks list
            missing_tasks = order_task_ids - imported_task_ids
            if missing_tasks:
                missing_count = len(missing_tasks)
                result.warnings.append(
                    f"Job task_order references {missing_count} task(s) not present in tasks list"
                )

            # Tasks in tasks but not in order
            extra_tasks = imported_task_ids - order_task_ids
            if extra_tasks:
                result.warnings.append(
                    f"{len(extra_tasks)} task(s) not referenced in job.task_order"
                )

        # Determine success based on errors
        result.success = len(result.errors) == 0
        return result

    def import_job(self, file_path: Path, force: bool = False) -> ImportResult:
        """Import job and tasks from JSON file.

        Args:
            file_path: Path to JSON file to import
            force: If True, overwrite existing job with same UUID

        Returns:
            ImportResult with import details
        """
        logger.info("Importing job from: %s (force=%s)", file_path, force)

        # Expand file path
        expanded_path = Path(os.path.expanduser(str(file_path)))

        # Check file exists
        if not expanded_path.exists():
            return ImportResult(success=False, errors=[f"File not found: {expanded_path}"])

        # Load and parse JSON
        try:
            with open(expanded_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return ImportResult(success=False, errors=[f"Invalid JSON: {e}"])
        except OSError as e:
            return ImportResult(success=False, errors=[f"Failed to read file: {e}"])

        # Validate import data
        validation_result = self.validate_import(data)

        # Separate conflict errors from other errors
        conflict_errors = [e for e in validation_result.errors if "already exists" in e]
        other_errors = [e for e in validation_result.errors if "already exists" not in e]

        # If force is not enabled and there are conflicts, return conflict errors
        if not force and conflict_errors:
            validation_result.errors = conflict_errors
            validation_result.success = False
            return validation_result

        # If there are non-conflict errors, always fail (force doesn't override these)
        if other_errors:
            validation_result.errors = other_errors
            validation_result.success = False
            return validation_result

        # Parse job and tasks
        try:
            job = Job.from_dict(data["job"])

            tasks = []
            for task_data in data.get("tasks", []):
                task = Task.from_dict(task_data)
                tasks.append(task)

            # Ensure tasks are linked to job
            for task in tasks:
                if task.job_id is None:
                    task.job_id = job.id

            # Save job and tasks
            job_saved = self.storage.save_job(job)
            if not job_saved:
                return ImportResult(success=False, errors=["Failed to save job to storage"])

            tasks_saved_count = 0
            for task in tasks:
                if self.storage.save_task(task):
                    tasks_saved_count += 1
                else:
                    logger.warning("Failed to save task: %s", task.name)

            if tasks_saved_count != len(tasks):
                validation_result.warnings.append(
                    f"Only {tasks_saved_count} of {len(tasks)} tasks saved successfully"
                )

            logger.info("Successfully imported job '%s' with %d tasks", job.name, len(tasks))

            return ImportResult(
                success=True, job=job, tasks=tasks, warnings=validation_result.warnings, errors=[]
            )

        except (KeyError, ValueError, TypeError) as e:
            return ImportResult(success=False, errors=[f"Failed to parse job/tasks data: {e}"])
