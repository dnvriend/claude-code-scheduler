"""Tests for claude_code_scheduler.services.import_service module.

This module contains comprehensive tests for the ImportService class,
covering all major functionality including edge cases and error conditions.

Test Cases:
    - Import valid job with tasks
    - Import job with missing profile (warning)
    - Import with UUID conflict (error without force)
    - Import with UUID conflict and force (overwrites)
    - Import invalid JSON (error)
    - Import file not found (error)
    - Round-trip: export then import produces identical data

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
from claude_code_scheduler.models.profile import Profile
from claude_code_scheduler.models.task import ScheduleConfig, Task
from claude_code_scheduler.services.export_service import ExportService
from claude_code_scheduler.services.import_service import ImportService
from claude_code_scheduler.storage.config_storage import ConfigStorage


@pytest.fixture
def mock_storage() -> Mock:
    """Create a mock ConfigStorage instance."""
    storage = Mock(spec=ConfigStorage)
    return storage


@pytest.fixture
def import_service(mock_storage: Mock) -> ImportService:
    """Create ImportService instance with mocked storage."""
    return ImportService(storage=mock_storage)


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
        profile=str(uuid4()),  # Use valid UUID format
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
            profile=str(uuid4()),  # Use valid UUID format
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


@pytest.fixture
def sample_profile() -> Profile:
    """Create a sample Profile instance for testing."""
    from claude_code_scheduler.models.enums import EnvVarSource
    from claude_code_scheduler.models.profile import EnvVar

    return Profile(
        id=uuid4(),
        name="Test Profile",
        description="A test profile",
        env_vars=[
            EnvVar(name="AWS_PROFILE", source=EnvVarSource.STATIC, value="default"),
            EnvVar(name="AWS_REGION", source=EnvVarSource.STATIC, value="us-east-1"),
        ],
    )


@pytest.fixture
def valid_import_data(sample_job: Job, sample_tasks: list[Task]) -> dict:
    """Create valid import data dictionary."""
    return {
        "version": "1.0",
        "exported_at": datetime.now(UTC).isoformat(),
        "job": sample_job.to_dict(),
        "tasks": [task.to_dict() for task in sample_tasks],
        "metadata": {
            "total_tasks": len(sample_tasks),
            "enabled_tasks": sum(1 for task in sample_tasks if task.enabled),
            "job_status": sample_job.status.value,
        },
    }


@pytest.fixture
def import_file_with_valid_data(valid_import_data: dict) -> Path:
    """Create a temporary file with valid import data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
        json.dump(valid_import_data, temp_file, indent=2)
        return Path(temp_file.name)


class TestImportValidation:
    """Test import validation functionality."""

    def test_validate_valid_import_data(
        self,
        import_service: ImportService,
        mock_storage: Mock,
        valid_import_data: dict,
        sample_profile: Profile,
    ) -> None:
        """Test validation of valid import data."""
        # Setup mock to return None (no existing job or task), but profile exists
        mock_storage.get_job.return_value = None
        mock_storage.get_task.return_value = None
        mock_storage.get_profile.return_value = sample_profile  # Profile must exist

        result = import_service.validate_import(valid_import_data)

        assert result.success is True
        assert len(result.errors) == 0
        # May have warnings for task order mismatches, but that's ok for validation
        assert "Job with UUID" not in " ".join(result.errors)

    def test_validate_missing_version_field(self, import_service: ImportService) -> None:
        """Test validation fails when version field is missing."""
        data = {
            "job": {"id": str(uuid4()), "name": "Test Job"},
            "tasks": [],
        }

        result = import_service.validate_import(data)

        assert result.success is False
        assert "Missing 'version' field" in result.errors

    def test_validate_unsupported_version(self, import_service: ImportService) -> None:
        """Test validation fails with unsupported version."""
        data = {
            "version": "2.0",
            "job": {"id": str(uuid4()), "name": "Test Job"},
            "tasks": [],
        }

        result = import_service.validate_import(data)

        assert result.success is False
        assert "Unsupported version: 2.0" in result.errors[0]

    def test_validate_missing_job_field(self, import_service: ImportService) -> None:
        """Test validation fails when job field is missing."""
        data = {
            "version": "1.0",
            "tasks": [],
        }

        result = import_service.validate_import(data)

        assert result.success is False
        assert "Missing 'job' field" in result.errors

    def test_validate_job_missing_required_fields(self, import_service: ImportService) -> None:
        """Test validation fails when job missing required fields."""
        data = {
            "version": "1.0",
            "job": {"name": "Test Job"},  # Missing 'id' field
            "tasks": [],
        }

        result = import_service.validate_import(data)

        assert result.success is False
        assert "Job missing required 'id' field" in result.errors

    def test_validate_invalid_job_uuid_format(self, import_service: ImportService) -> None:
        """Test validation fails with invalid job UUID format."""
        data = {
            "version": "1.0",
            "job": {"id": "invalid-uuid", "name": "Test Job"},
            "tasks": [],
        }

        result = import_service.validate_import(data)

        assert result.success is False
        assert "Invalid job UUID format: invalid-uuid" in result.errors

    def test_validate_tasks_not_a_list(self, import_service: ImportService) -> None:
        """Test validation fails when tasks is not a list."""
        data = {
            "version": "1.0",
            "job": {"id": str(uuid4()), "name": "Test Job"},
            "tasks": "not_a_list",
        }

        result = import_service.validate_import(data)

        assert result.success is False
        assert "'tasks' must be a list" in result.errors

    def test_validate_task_missing_required_fields(self, import_service: ImportService) -> None:
        """Test validation fails when task missing required fields."""
        data = {
            "version": "1.0",
            "job": {"id": str(uuid4()), "name": "Test Job"},
            "tasks": [{"id": str(uuid4())}],  # Missing 'name' field
        }

        result = import_service.validate_import(data)

        assert result.success is False
        assert "Task 0 missing required 'name' field" in result.errors

    def test_validate_task_invalid_uuid_format(self, import_service: ImportService) -> None:
        """Test validation fails with invalid task UUID format."""
        data = {
            "version": "1.0",
            "job": {"id": str(uuid4()), "name": "Test Job"},
            "tasks": [{"id": "invalid-uuid", "name": "Test Task"}],
        }

        result = import_service.validate_import(data)

        assert result.success is False
        assert "Task 0 has invalid UUID format: invalid-uuid" in result.errors


class TestImportUUIDConflicts:
    """Test UUID conflict detection and resolution."""

    def test_validate_detects_existing_job(
        self, import_service: ImportService, mock_storage: Mock, sample_job: Job
    ) -> None:
        """Test validation detects existing job UUID conflict."""
        # Setup mock to return existing job
        mock_storage.get_job.return_value = sample_job

        data = {
            "version": "1.0",
            "job": sample_job.to_dict(),
            "tasks": [],
        }

        result = import_service.validate_import(data)

        assert result.success is False  # Should fail due to conflict
        assert f"Job with UUID {sample_job.id} already exists" in result.errors[0]
        assert "Use --force to overwrite existing job" in result.warnings[0]

        mock_storage.get_job.assert_called_once_with(sample_job.id)

    def test_validate_with_nonexistent_job_uuid(
        self, import_service: ImportService, mock_storage: Mock, sample_job: Job
    ) -> None:
        """Test validation passes when job UUID doesn't exist."""
        # Setup mock to return None (job not found)
        mock_storage.get_job.return_value = None

        data = {
            "version": "1.0",
            "job": sample_job.to_dict(),
            "tasks": [],
        }

        result = import_service.validate_import(data)

        assert result.success is True
        assert len(result.errors) == 0

        mock_storage.get_job.assert_called_once_with(sample_job.id)


class TestImportProfileReferences:
    """Test profile reference validation."""

    def test_validate_missing_profile_reference_error(
        self, import_service: ImportService, mock_storage: Mock, sample_job: Job
    ) -> None:
        """Test validation errors about missing profile references."""
        # Setup mock to return None for missing profile
        mock_storage.get_job.return_value = None
        mock_storage.get_task.return_value = None
        mock_storage.get_profile.return_value = None

        missing_profile_id = str(uuid4())  # Use valid UUID format
        data = {
            "version": "1.0",
            "job": sample_job.to_dict(),
            "tasks": [
                {
                    "id": str(uuid4()),
                    "name": "Test Task",
                    "profile": missing_profile_id,
                }
            ],
        }

        result = import_service.validate_import(data)

        assert result.success is False  # Missing profiles are now errors
        # Check that one of the errors mentions the missing profile
        assert any(
            f"Profile '{missing_profile_id}'" in error and "not found" in error
            for error in result.errors
        )

        mock_storage.get_profile.assert_called_once()

    def test_validate_existing_profile_reference(
        self,
        import_service: ImportService,
        mock_storage: Mock,
        sample_job: Job,
        sample_profile: Profile,
    ) -> None:
        """Test validation passes with existing profile references."""
        # Setup mock to return existing profile
        mock_storage.get_job.return_value = None
        mock_storage.get_task.return_value = None
        mock_storage.get_profile.return_value = sample_profile

        # Create simple job without task_order to avoid order warnings
        simple_job = Job(
            id=uuid4(),
            name="Simple Test Job",
            description="A simple job for testing",
            status=JobStatus.PENDING,
            profile=None,
            working_directory=JobWorkingDirectory(
                path="~/test",
                use_git_worktree=False,
                worktree_name="",
                worktree_branch="",
            ),
            task_order=[],  # Empty task order
        )

        data = {
            "version": "1.0",
            "job": simple_job.to_dict(),
            "tasks": [
                {
                    "id": str(uuid4()),
                    "name": "Test Task",
                    "profile": str(sample_profile.id),
                }
            ],
        }

        result = import_service.validate_import(data)

        assert result.success is True
        assert len(result.errors) == 0

        mock_storage.get_profile.assert_called_once_with(sample_profile.id)


class TestImportFromFile:
    """Test file import functionality."""

    def test_import_valid_job_with_tasks(
        self,
        import_service: ImportService,
        mock_storage: Mock,
        valid_import_data: dict,
        import_file_with_valid_data: Path,
        sample_profile: Profile,
    ) -> None:
        """Test importing a valid job with tasks succeeds."""
        # Setup mocks
        mock_storage.get_job.return_value = None  # No existing job
        mock_storage.get_task.return_value = None  # No existing task
        mock_storage.get_profile.return_value = sample_profile  # Profile exists
        mock_storage.save_job.return_value = True
        mock_storage.save_task.return_value = True

        result = import_service.import_job(import_file_with_valid_data)

        assert result.success is True
        assert result.job is not None
        assert len(result.tasks) == 2
        assert len(result.errors) == 0

        # Verify job was saved
        mock_storage.save_job.assert_called_once()

        # Verify tasks were saved
        assert mock_storage.save_task.call_count == 2

    def test_import_with_missing_profile_error(
        self,
        import_service: ImportService,
        mock_storage: Mock,
        import_file_with_valid_data: Path,
    ) -> None:
        """Test importing job with missing profile generates error."""
        # Setup mocks - missing profile
        mock_storage.get_job.return_value = None
        mock_storage.get_task.return_value = None
        mock_storage.save_job.return_value = True
        mock_storage.save_task.return_value = True
        mock_storage.get_profile.return_value = None

        result = import_service.import_job(import_file_with_valid_data)

        # Missing profiles are now errors, not warnings
        assert result.success is False
        # Check for "not found" or "Invalid profile" in errors
        assert any("not found" in error or "Invalid profile" in error for error in result.errors)

    def test_import_file_not_found_error(self, import_service: ImportService) -> None:
        """Test importing non-existent file returns error."""
        nonexistent_path = Path("/nonexistent/path/file.json")

        result = import_service.import_job(nonexistent_path)

        assert result.success is False
        assert "File not found" in result.errors[0]

    def test_import_invalid_json_error(
        self, import_service: ImportService, mock_storage: Mock
    ) -> None:
        """Test importing invalid JSON returns error."""
        # Create temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            temp_file.write("{ invalid json content")
            invalid_json_path = Path(temp_file.name)

        try:
            result = import_service.import_job(invalid_json_path)

            assert result.success is False
            assert "Invalid JSON" in result.errors[0]

        finally:
            if invalid_json_path.exists():
                invalid_json_path.unlink()

    def test_import_uuid_conflict_without_force_error(
        self,
        import_service: ImportService,
        mock_storage: Mock,
        sample_job: Job,
        valid_import_data: dict,
    ) -> None:
        """Test importing with UUID conflict fails without force flag."""
        # Create temporary file with conflicting job data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            json.dump(valid_import_data, temp_file, indent=2)
            conflict_file_path = Path(temp_file.name)

        try:
            # Setup mock to return existing job (conflict)
            mock_storage.get_job.return_value = sample_job

            result = import_service.import_job(conflict_file_path, force=False)

            assert result.success is False
            assert f"Job with UUID {sample_job.id} already exists" in result.errors[0]
            assert "Use --force to overwrite existing job" in result.warnings[0]

        finally:
            if conflict_file_path.exists():
                conflict_file_path.unlink()

    def test_import_uuid_conflict_with_force_overwrites(
        self,
        import_service: ImportService,
        mock_storage: Mock,
        sample_job: Job,
        sample_profile: Profile,
        valid_import_data: dict,
    ) -> None:
        """Test importing with UUID conflict succeeds with force flag."""
        # Create temporary file with conflicting job data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            json.dump(valid_import_data, temp_file, indent=2)
            conflict_file_path = Path(temp_file.name)

        try:
            # Setup mocks
            mock_storage.get_job.return_value = sample_job  # Existing job
            mock_storage.get_task.return_value = sample_job  # Existing tasks (conflict)
            mock_storage.get_profile.return_value = sample_profile  # Profile exists
            mock_storage.save_job.return_value = True
            mock_storage.save_task.return_value = True

            result = import_service.import_job(conflict_file_path, force=True)

            assert result.success is True
            assert result.job is not None
            assert len(result.tasks) == 2

            # Verify job was saved (overwritten)
            mock_storage.save_job.assert_called_once()

        finally:
            if conflict_file_path.exists():
                conflict_file_path.unlink()


class TestRoundTripImportExport:
    """Test round-trip export then import functionality."""

    def test_round_trip_export_then_import_produces_identical_data(
        self,
        import_service: ImportService,
        mock_storage: Mock,
        sample_job: Job,
        sample_tasks: list[Task],
    ) -> None:
        """Test that exported data can be imported to produce identical job and tasks."""
        # Create import data manually with compatible version
        export_data = {
            "version": "1.0",  # Use compatible version
            "exported_at": datetime.now(UTC).isoformat(),
            "job": sample_job.to_dict(),
            "tasks": [task.to_dict() for task in sample_tasks],
            "metadata": {
                "total_tasks": len(sample_tasks),
                "enabled_tasks": sum(1 for task in sample_tasks if task.enabled),
            },
        }

        # Setup import mocks - no existing job/task, profile exists (use Mock profile)
        mock_storage.get_job.return_value = None
        mock_storage.get_task.return_value = None
        # Profile must exist for validation to pass - create a mock profile
        mock_profile = Mock()
        mock_profile.id = uuid4()
        mock_storage.get_profile.return_value = mock_profile
        mock_storage.save_job.return_value = True
        mock_storage.save_task.return_value = True

        # Create temporary file with export data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            json.dump(export_data, temp_file, indent=2)
            export_file_path = Path(temp_file.name)

        try:
            # Import the exported data
            import_result = import_service.import_job(export_file_path)

            assert import_result.success is True
            assert import_result.job is not None
            assert len(import_result.tasks) == len(sample_tasks)

            # Compare job data
            imported_job = import_result.job
            assert imported_job.id == sample_job.id
            assert imported_job.name == sample_job.name
            assert imported_job.description == sample_job.description
            assert imported_job.status == sample_job.status
            assert imported_job.profile == sample_job.profile

            # Compare tasks data
            for i, imported_task in enumerate(import_result.tasks):
                original_task = sample_tasks[i]
                assert imported_task.id == original_task.id
                assert imported_task.name == original_task.name
                assert imported_task.prompt == original_task.prompt
                assert imported_task.enabled == original_task.enabled

        finally:
            if export_file_path.exists():
                export_file_path.unlink()


class TestImportServiceIntegration:
    """Integration tests for ImportService with real ConfigStorage."""

    @pytest.fixture
    def real_storage(self) -> ConfigStorage:
        """Create a real ConfigStorage instance for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            storage = ConfigStorage(config_dir=config_dir)
            yield storage

    @pytest.fixture
    def integration_import_service(self, real_storage: ConfigStorage) -> ImportService:
        """Create ImportService with real storage for integration testing."""
        return ImportService(storage=real_storage)

    def test_import_with_real_storage(
        self,
        integration_import_service: ImportService,
        real_storage: ConfigStorage,
        sample_job: Job,
        sample_profile: Profile,
    ) -> None:
        """Test import functionality with real ConfigStorage."""
        # First save the profile so it can be referenced
        real_storage.save_profiles([sample_profile])

        # Create tasks without profile references for simpler test
        task1 = Task(
            id=uuid4(),
            job_id=sample_job.id,
            name="Task 1",
            enabled=True,
            model="sonnet",
            profile=None,  # No profile reference
            prompt_type="prompt",
            prompt="Test command",
        )
        task2 = Task(
            id=uuid4(),
            job_id=sample_job.id,
            name="Task 2",
            enabled=False,
            model="opus",
            profile=None,  # No profile reference
            prompt_type="prompt",
            prompt="run tests",
        )
        sample_tasks_no_profile = [task1, task2]

        # Create import data
        valid_import_data = {
            "version": "1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "job": sample_job.to_dict(),
            "tasks": [task.to_dict() for task in sample_tasks_no_profile],
            "metadata": {
                "total_tasks": len(sample_tasks_no_profile),
                "enabled_tasks": sum(1 for task in sample_tasks_no_profile if task.enabled),
            },
        }

        # Create temporary file with import data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            json.dump(valid_import_data, temp_file, indent=2)
            import_file_path = Path(temp_file.name)

        try:
            # Import the job
            result = integration_import_service.import_job(import_file_path)

            assert result.success is True
            assert result.job is not None
            assert len(result.tasks) == len(sample_tasks_no_profile)

            # Verify data was saved to storage
            loaded_job = real_storage.get_job(sample_job.id)
            assert loaded_job is not None
            assert loaded_job.name == sample_job.name

            loaded_tasks = real_storage.get_tasks_for_job(sample_job.id)
            assert len(loaded_tasks) == len(sample_tasks_no_profile)

        finally:
            if import_file_path.exists():
                import_file_path.unlink()


class TestImportPathHandling:
    """Test file path handling and expansion."""

    def test_import_expands_tilde_path(
        self,
        import_service: ImportService,
        mock_storage: Mock,
        valid_import_data: dict,
        sample_profile: Profile,
    ) -> None:
        """Test that import expands tilde (~) in file paths."""
        # Create temporary file with import data
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "job.json"
            with open(temp_path, "w") as f:
                json.dump(valid_import_data, f)

            # Mock the storage methods
            mock_storage.get_job.return_value = None
            mock_storage.get_task.return_value = None
            mock_storage.get_profile.return_value = sample_profile
            mock_storage.save_job.return_value = True
            mock_storage.save_task.return_value = True

            # Mock expanduser to return our temp path
            with patch("os.path.expanduser") as mock_expanduser:
                mock_expanduser.return_value = str(temp_path)

                # Use path with tilde
                tilde_path = Path("~/job.json")
                result = import_service.import_job(tilde_path)

                assert result.success is True
                mock_expanduser.assert_called_once_with("~/job.json")

    def test_import_handles_file_read_errors(
        self, import_service: ImportService, mock_storage: Mock
    ) -> None:
        """Test that file read errors are properly handled."""
        # Create file but make it unreadable
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            temp_file.write(b'{"test": "data"}')
            temp_path = Path(temp_file.name)

        try:
            # Mock file open to raise OSError
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                result = import_service.import_job(temp_path)

                assert result.success is False
                assert "Failed to read file" in result.errors[0]

        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestImportErrorConditions:
    """Test various error conditions during import."""

    def test_import_handles_storage_save_job_failure(
        self,
        import_service: ImportService,
        mock_storage: Mock,
        import_file_with_valid_data: Path,
        sample_profile: Profile,
    ) -> None:
        """Test handling of storage save_job failure."""
        # Setup mocks
        mock_storage.get_job.return_value = None
        mock_storage.get_task.return_value = None
        mock_storage.get_profile.return_value = sample_profile  # Profile exists
        mock_storage.save_job.return_value = False  # Save failed

        result = import_service.import_job(import_file_with_valid_data)

        assert result.success is False
        assert "Failed to save job to storage" in result.errors[0]

    def test_import_handles_partial_task_save_failure(
        self,
        import_service: ImportService,
        mock_storage: Mock,
        import_file_with_valid_data: Path,
        sample_profile: Profile,
    ) -> None:
        """Test handling of partial task save failures."""
        # Setup mocks - profile must exist for validation to pass
        mock_storage.get_job.return_value = None
        mock_storage.get_task.return_value = None
        mock_storage.save_job.return_value = True
        mock_storage.get_profile.return_value = sample_profile  # Profile exists

        # First task saves successfully, second fails
        mock_storage.save_task.side_effect = [True, False]

        result = import_service.import_job(import_file_with_valid_data)

        assert result.success is True  # Import succeeds with warning
        # Check for the partial save warning among any other warnings
        assert any("Only 1 of 2 tasks saved successfully" in warning for warning in result.warnings)

    def test_import_handles_parse_errors(
        self, import_service: ImportService, mock_storage: Mock
    ) -> None:
        """Test handling of data parsing errors."""
        # Create data that will fail Job.from_dict() - invalid UUID format
        invalid_data = {
            "version": "1.0",
            "job": {
                "id": "not-a-valid-uuid",  # Invalid UUID format
                "name": "Test Job",
            },
            "tasks": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            json.dump(invalid_data, temp_file)
            temp_path = Path(temp_file.name)

        try:
            mock_storage.get_job.return_value = None
            result = import_service.import_job(temp_path)

            assert result.success is False
            assert "Invalid job UUID format" in result.errors[0]

        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestImportJobTaskOrderValidation:
    """Test validation of job task_order consistency."""

    def test_validate_task_order_mismatch_warnings(
        self, import_service: ImportService, mock_storage: Mock, sample_job: Job
    ) -> None:
        """Test validation warns about task order mismatches."""
        # Setup mocks
        mock_storage.get_job.return_value = None
        mock_storage.get_task.return_value = None

        # Create data with task_order mismatch
        task_id1 = uuid4()
        task_id2 = uuid4()
        task_id3 = uuid4()  # Extra task in order

        data = {
            "version": "1.0",
            "job": {
                "id": str(sample_job.id),
                "name": "Test Job",
                "task_order": [str(task_id1), str(task_id2), str(task_id3)],  # 3 tasks in order
            },
            "tasks": [
                {"id": str(task_id1), "name": "Task 1"},
                {"id": str(task_id2), "name": "Task 2"},
                # Missing task_id3 in tasks list
            ],
        }

        result = import_service.validate_import(data)

        assert result.success is True  # Still succeeds, just with warnings
        assert "Job task_order references 1 task(s) not present in tasks list" in result.warnings[0]

    def test_validate_extra_tasks_not_in_order_warnings(
        self, import_service: ImportService, mock_storage: Mock, sample_job: Job
    ) -> None:
        """Test validation warns about extra tasks not in order."""
        # Setup mocks
        mock_storage.get_job.return_value = None
        mock_storage.get_task.return_value = None

        # Create data with extra tasks
        task_id1 = uuid4()
        task_id2 = uuid4()
        task_id3 = uuid4()  # Extra task

        data = {
            "version": "1.0",
            "job": {
                "id": str(sample_job.id),
                "name": "Test Job",
                "task_order": [str(task_id1), str(task_id2)],  # Only 2 tasks in order
            },
            "tasks": [
                {"id": str(task_id1), "name": "Task 1"},
                {"id": str(task_id2), "name": "Task 2"},
                {"id": str(task_id3), "name": "Task 3"},  # Extra task
            ],
        }

        result = import_service.validate_import(data)

        assert result.success is True  # Still succeeds, just with warnings
        assert "1 task(s) not referenced in job.task_order" in result.warnings[0]
