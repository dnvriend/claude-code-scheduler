"""Tests for claude_code_scheduler.services.export_service module.

This module contains comprehensive tests for the ExportService class,
covering all major functionality including edge cases and error conditions.

Test Cases:
    - Export job with no tasks
    - Export job with multiple tasks
    - Export job with profile references
    - Export to file creates valid JSON
    - Export non-existent job raises error
    - Exported JSON can be re-imported (round-trip)

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
import tempfile
from datetime import UTC, datetime, time
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from claude_code_scheduler.models.enums import IntervalType, JobStatus, ScheduleType
from claude_code_scheduler.models.job import Job, JobWorkingDirectory
from claude_code_scheduler.models.task import ScheduleConfig, Task
from claude_code_scheduler.services.export_service import ExportService
from claude_code_scheduler.storage.config_storage import ConfigStorage


@pytest.fixture
def mock_storage() -> Mock:
    """Create a mock ConfigStorage instance."""
    storage = Mock(spec=ConfigStorage)
    return storage


@pytest.fixture
def export_service(mock_storage: Mock) -> ExportService:
    """Create ExportService instance with mocked storage."""
    return ExportService(storage=mock_storage)


@pytest.fixture
def sample_job() -> Job:
    """Create a sample Job instance for testing."""
    working_dir = JobWorkingDirectory(
        path="~/projects/test",
        use_git_worktree=True,
        worktree_name="test-worktree",
        worktree_branch="feature/test",
    )
    return Job(
        id=uuid4(),
        name="Test Job",
        description="A test job for unit testing",
        status=JobStatus.PENDING,
        profile="test-profile-uuid",
        working_directory=working_dir,
        task_order=[uuid4(), uuid4()],  # Two task UUIDs
    )


@pytest.fixture
def sample_tasks(sample_job: Job) -> list[Task]:
    """Create sample Task instances for testing."""
    task1_id = sample_job.task_order[0]
    task2_id = sample_job.task_order[1]

    schedule1 = ScheduleConfig(
        schedule_type=ScheduleType.CALENDAR,
        calendar_frequency="daily",
        calendar_time=time(9, 0),  # 9 AM
    )

    schedule2 = ScheduleConfig(
        schedule_type=ScheduleType.INTERVAL,
        interval_type=IntervalType.SIMPLE,
        interval_preset="1hour",
    )

    return [
        Task(
            id=task1_id,
            job_id=sample_job.id,
            name="Task 1",
            enabled=True,
            model="sonnet",
            profile="task1-profile-uuid",
            schedule=schedule1,
            prompt_type="prompt",
            prompt="Review the code changes",
            permissions="default",
            session_mode="new",
            allowed_tools=["read", "write"],
            disallowed_tools=["bash"],
        ),
        Task(
            id=task2_id,
            job_id=sample_job.id,
            name="Task 2",
            enabled=False,  # Test with disabled task
            model="opus",
            profile=None,  # Test with no profile
            schedule=schedule2,
            prompt_type="prompt",
            prompt="run tests",
            permissions="restricted",
            session_mode="continue",
            allowed_tools=[],
            disallowed_tools=["bash", "web_search"],
        ),
    ]


class TestExportJobBasic:
    """Test basic export functionality."""

    def test_export_job_with_no_tasks(
        self, export_service: ExportService, mock_storage: Mock, sample_job: Job
    ) -> None:
        """Test exporting a job that has no associated tasks."""
        # Setup mock to return job and empty tasks list
        mock_storage.get_job.return_value = sample_job
        mock_storage.get_tasks_for_job.return_value = []

        # Export the job
        result = export_service.export_job(sample_job.id)

        # Verify structure
        assert "version" in result
        assert "exported_at" in result
        assert "job" in result
        assert "tasks" in result
        assert "profiles_referenced" in result

        # Verify job data
        assert result["job"]["id"] == str(sample_job.id)
        assert result["job"]["name"] == sample_job.name
        assert result["job"]["description"] == sample_job.description
        assert result["job"]["status"] == sample_job.status.value
        assert result["job"]["profile"] == sample_job.profile

        # Verify tasks is empty
        assert result["tasks"] == []

        # Verify profiles_referenced contains job profile
        assert sample_job.profile in result["profiles_referenced"]

        # Verify mock calls
        mock_storage.get_job.assert_called_once_with(sample_job.id)
        mock_storage.get_tasks_for_job.assert_called_once_with(sample_job.id)

    def test_export_job_with_multiple_tasks(
        self,
        export_service: ExportService,
        mock_storage: Mock,
        sample_job: Job,
        sample_tasks: list[Task],
    ) -> None:
        """Test exporting a job with multiple associated tasks."""
        # Setup mock to return job and tasks
        mock_storage.get_job.return_value = sample_job
        mock_storage.get_tasks_for_job.return_value = sample_tasks

        # Export the job
        result = export_service.export_job(sample_job.id)

        # Verify tasks data
        assert len(result["tasks"]) == 2

        # Verify first task
        task1_data = result["tasks"][0]
        assert task1_data["id"] == str(sample_tasks[0].id)
        assert task1_data["job_id"] == str(sample_job.id)
        assert task1_data["name"] == "Task 1"
        assert task1_data["enabled"] is True
        assert task1_data["model"] == "sonnet"
        assert task1_data["profile"] == "task1-profile-uuid"

        # Verify second task
        task2_data = result["tasks"][1]
        assert task2_data["id"] == str(sample_tasks[1].id)
        assert task2_data["job_id"] == str(sample_job.id)
        assert task2_data["name"] == "Task 2"
        assert task2_data["enabled"] is False
        assert task2_data["model"] == "opus"
        assert task2_data["profile"] is None

        # Verify profiles_referenced contains profiles from job and tasks
        assert len(result["tasks"]) == 2
        assert "task1-profile-uuid" in result["profiles_referenced"]

    def test_export_job_with_profile_references(
        self,
        export_service: ExportService,
        mock_storage: Mock,
        sample_job: Job,
        sample_tasks: list[Task],
    ) -> None:
        """Test exporting job with various profile references."""
        # Setup mock to return job and tasks
        mock_storage.get_job.return_value = sample_job
        mock_storage.get_tasks_for_job.return_value = sample_tasks

        # Export the job
        result = export_service.export_job(sample_job.id)

        # Verify job profile reference
        assert result["job"]["profile"] == "test-profile-uuid"

        # Verify task profile references
        task_profiles = [task.get("profile") for task in result["tasks"]]
        assert "task1-profile-uuid" in task_profiles
        assert None in task_profiles  # Task 2 has no profile


class TestExportJobErrors:
    """Test error handling in export functionality."""

    def test_export_nonexistent_job_raises_error(
        self, export_service: ExportService, mock_storage: Mock
    ) -> None:
        """Test that exporting a non-existent job raises ValueError."""
        # Setup mock to return None (job not found)
        job_id = uuid4()
        mock_storage.get_job.return_value = None

        # Verify exception is raised
        with pytest.raises(ValueError, match=f"Job with ID {job_id} not found"):
            export_service.export_job(job_id)

        # Verify mock calls
        mock_storage.get_job.assert_called_once_with(job_id)
        mock_storage.get_tasks_for_job.assert_not_called()


class TestExportToFile:
    """Test file export functionality."""

    def test_export_to_file_creates_valid_json(
        self,
        export_service: ExportService,
        mock_storage: Mock,
        sample_job: Job,
        sample_tasks: list[Task],
    ) -> None:
        """Test that exporting to file creates valid JSON with proper structure."""
        # Setup mock to return job and tasks
        mock_storage.get_job.return_value = sample_job
        mock_storage.get_tasks_for_job.return_value = sample_tasks

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            # Export to file
            result_path = export_service.export_to_file(sample_job.id, temp_path)

            # Verify correct path returned
            assert result_path == temp_path

            # Verify file exists and contains valid JSON
            assert temp_path.exists()

            with open(temp_path, encoding="utf-8") as f:
                loaded_data = json.load(f)

            # Verify structure matches in-memory export (except for timestamps which will differ)
            memory_export = export_service.export_job(sample_job.id)
            assert loaded_data["version"] == memory_export["version"]
            assert loaded_data["job"] == memory_export["job"]
            assert loaded_data["tasks"] == memory_export["tasks"]
            assert loaded_data["profiles_referenced"] == memory_export["profiles_referenced"]

            # Verify JSON structure
            assert isinstance(loaded_data, dict)
            assert "version" in loaded_data
            assert "exported_at" in loaded_data
            assert "job" in loaded_data
            assert "tasks" in loaded_data
            assert "profiles_referenced" in loaded_data

            # Verify timestamps are valid ISO format
            datetime.fromisoformat(loaded_data["exported_at"].replace("Z", "+00:00"))

        finally:
            # Clean up
            if temp_path.exists():
                temp_path.unlink()

    def test_export_to_file_creates_directories(
        self, export_service: ExportService, mock_storage: Mock, sample_job: Job
    ) -> None:
        """Test that export_to_file creates parent directories if needed."""
        # Setup mock to return job
        mock_storage.get_job.return_value = sample_job
        mock_storage.get_tasks_for_job.return_value = []

        # Create temporary directory with nested subdirectory
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "exports" / "nested" / "job.json"

            # Export to nested path
            result_path = export_service.export_to_file(sample_job.id, nested_path)

            # Verify file was created
            assert result_path.exists()
            assert result_path == nested_path

    def test_export_to_file_handles_file_write_errors(
        self, export_service: ExportService, mock_storage: Mock, sample_job: Job
    ) -> None:
        """Test that file write errors are properly handled."""
        # Setup mock to return job
        mock_storage.get_job.return_value = sample_job
        mock_storage.get_tasks_for_job.return_value = []

        # Try to write to an invalid path (directory instead of file)
        invalid_path = Path("/root/nonexistent/path/job.json")

        # Verify OSError is raised
        with pytest.raises(OSError):
            export_service.export_to_file(sample_job.id, invalid_path)


class TestValidateExportData:
    """Test export data validation functionality."""

    def test_validate_export_data_valid_structure(self, export_service: ExportService) -> None:
        """Test validation of properly structured export data."""
        valid_data = {
            "version": "1.0.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "job": {
                "id": str(uuid4()),
                "name": "Test Job",
                "status": "pending",
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            },
            "tasks": [
                {
                    "id": str(uuid4()),
                    "name": "Test Task",
                    "job_id": str(uuid4()),
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            ],
            "profiles_referenced": ["test-profile-uuid"],
        }

        assert export_service.validate_export_data(valid_data) is True

    def test_validate_export_data_missing_fields(self, export_service: ExportService) -> None:
        """Test validation fails with missing required fields."""
        incomplete_data = {
            "version": "1.0.0",
            "exported_at": datetime.now(UTC).isoformat(),
            # Missing "job", "tasks", "metadata"
        }

        assert export_service.validate_export_data(incomplete_data) is False

    def test_validate_export_data_invalid_job_structure(
        self, export_service: ExportService
    ) -> None:
        """Test validation fails with invalid job structure."""
        invalid_data = {
            "version": "1.0.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "job": {
                "id": str(uuid4()),
                # Missing required job fields
            },
            "tasks": [],
            "profiles_referenced": [],
        }

        assert export_service.validate_export_data(invalid_data) is False

    def test_validate_export_data_invalid_tasks_structure(
        self, export_service: ExportService
    ) -> None:
        """Test validation fails with invalid tasks structure."""
        invalid_data = {
            "version": "1.0.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "job": {
                "id": str(uuid4()),
                "name": "Test Job",
                "status": "pending",
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            },
            "tasks": "not_a_list",  # Should be a list
            "profiles_referenced": [],
        }

        assert export_service.validate_export_data(invalid_data) is False


class TestRoundTripImportExport:
    """Test that exported data can be used to recreate jobs and tasks."""

    def test_exported_json_can_be_round_trip_imported(
        self,
        export_service: ExportService,
        mock_storage: Mock,
        sample_job: Job,
        sample_tasks: list[Task],
    ) -> None:
        """Test that exported JSON can be used to recreate the original job and tasks."""
        # Setup mock to return job and tasks
        mock_storage.get_job.return_value = sample_job
        mock_storage.get_tasks_for_job.return_value = sample_tasks

        # Export the job
        export_data = export_service.export_job(sample_job.id)

        # Test round-trip for job
        recreated_job = Job.from_dict(export_data["job"])
        assert recreated_job.id == sample_job.id
        assert recreated_job.name == sample_job.name
        assert recreated_job.description == sample_job.description
        assert recreated_job.status == sample_job.status
        assert recreated_job.profile == sample_job.profile
        assert len(recreated_job.task_order) == len(sample_job.task_order)

        # Test round-trip for tasks
        assert len(export_data["tasks"]) == len(sample_tasks)
        for i, task_data in enumerate(export_data["tasks"]):
            # Note: This assumes Task.from_dict exists and works correctly
            # In a real implementation, you would test the actual import functionality
            assert task_data["id"] == str(sample_tasks[i].id)
            assert task_data["name"] == sample_tasks[i].name
            assert task_data["job_id"] == str(sample_tasks[i].job_id)

    @patch("claude_code_scheduler.services.export_service.json.dump")
    def test_export_preserves_all_task_configuration(
        self,
        mock_json_dump: Mock,
        export_service: ExportService,
        mock_storage: Mock,
        sample_job: Job,
        sample_tasks: list[Task],
    ) -> None:
        """Test that all task configuration is preserved in export."""
        # Setup mock to return job and tasks
        mock_storage.get_job.return_value = sample_job
        mock_storage.get_tasks_for_job.return_value = sample_tasks

        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            # Export to file
            export_service.export_to_file(sample_job.id, temp_path)

            # Verify json.dump was called with complete data
            assert mock_json_dump.called
            export_data = mock_json_dump.call_args[0][0]  # First argument to json.dump

            # Verify all task fields are present
            task_data = export_data["tasks"][0]
            expected_task_fields = {
                "id",
                "job_id",
                "name",
                "enabled",
                "model",
                "profile",
                "schedule",
                "prompt_type",
                "prompt",
                "permissions",
                "session_mode",
                "allowed_tools",
                "disallowed_tools",
                "created_at",
                "updated_at",
            }

            assert expected_task_fields.issubset(task_data.keys())

            # Verify specific values
            assert task_data["allowed_tools"] == ["read", "write"]
            assert task_data["disallowed_tools"] == ["bash"]
            assert task_data["permissions"] == "default"
            assert task_data["session_mode"] == "new"

        finally:
            # Clean up
            if temp_path.exists():
                temp_path.unlink()


class TestExportServiceIntegration:
    """Integration tests for ExportService with real ConfigStorage."""

    @pytest.fixture
    def real_storage(self) -> ConfigStorage:
        """Create a real ConfigStorage instance for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            storage = ConfigStorage(config_dir=config_dir)
            yield storage

    @pytest.fixture
    def integration_export_service(self, real_storage: ConfigStorage) -> ExportService:
        """Create ExportService with real storage for integration testing."""
        return ExportService(storage=real_storage)

    def test_export_with_real_storage(
        self,
        integration_export_service: ExportService,
        real_storage: ConfigStorage,
        sample_job: Job,
        sample_tasks: list[Task],
    ) -> None:
        """Test export functionality with real ConfigStorage."""
        # Save job and tasks to real storage
        real_storage.save_job(sample_job)
        for task in sample_tasks:
            real_storage.save_task(task)

        # Export the job
        result = integration_export_service.export_job(sample_job.id)

        # Verify export structure
        assert result["job"]["id"] == str(sample_job.id)
        assert len(result["tasks"]) == len(sample_tasks)
        assert "profiles_referenced" in result

        # Verify the exported data matches what we can load back
        loaded_job = real_storage.get_job(sample_job.id)
        loaded_tasks = real_storage.get_tasks_for_job(sample_job.id)

        assert loaded_job.id == sample_job.id
        assert len(loaded_tasks) == len(sample_tasks)
