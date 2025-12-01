# Feature: Import Job and Tasks

## Overview

Import a job with all associated tasks from a JSON file. Handles UUID conflicts, validates profile references, and provides clear error messages.

## Data Model

See `export-job-and-tasks.md` for the expected JSON structure.

## Implementation Tasks

### Task 1: Create Import Service

**File:** `claude_code_scheduler/services/import_service.py`

**Description:** Core import logic with validation and conflict detection.

**Implementation:**
- Create `ImportService` class
- Create `ImportResult` dataclass:
  ```python
  @dataclass
  class ImportResult:
      success: bool
      job: Job | None
      tasks: list[Task]
      warnings: list[str]
      errors: list[str]
  ```
- Method `validate_import(data: dict) -> ImportResult`:
  - Check version compatibility
  - Validate job structure
  - Validate tasks structure
  - Check for UUID conflicts (job already exists)
  - Check profile references exist
  - Return validation result with warnings/errors
- Method `import_job(file_path: Path, force: bool = False) -> ImportResult`:
  - Load and parse JSON file
  - Call `validate_import()`
  - If validation fails and not force, return errors
  - If job UUID exists and not force, return conflict error
  - Save job and tasks to storage
  - Return result with created entities

**Validation Rules:**
- Job UUID must not exist (unless `force=True` to overwrite)
- All profile IDs referenced must exist (warning if not)
- JSON must have valid version field
- All required fields must be present

**Tests:** `tests/test_import_service.py`

---

### Task 2: Add REST API Import Endpoint

**File:** `claude_code_scheduler/services/debug_server.py`

**Description:** Add REST endpoint for job import.

**Endpoints:**
- `POST /api/jobs/import` - Import job from file path
  - Body: `{"file_path": "/path/to/file.json", "force": false}`

**Response Format (Success):**
```json
{
  "status": "success",
  "job": { ... },
  "tasks_imported": 5,
  "warnings": ["Profile 'abc-123' not found, tasks will use default"]
}
```

**Error Responses:**
- 400: Invalid JSON / validation failed
- 409: Job UUID already exists (conflict)
- 404: File not found
- 422: Profile not found (with details)

**Error Response Format:**
```json
{
  "status": "error",
  "error_code": "JOB_EXISTS",
  "message": "Job with UUID abc-123 already exists",
  "details": { "existing_job_name": "My Job" }
}
```

**Implementation:**
- Add `_api_import_job()` method in `DebugRequestHandler`
- Wire up routes in `_route_request()`
- Use `ImportService` for import logic

---

### Task 3: Add CLI Import Command

**File:** `claude_code_scheduler/cli_jobs.py`

**Description:** Add `job import` subcommand to CLI.

**Command:**
```bash
claude-code-scheduler cli jobs import --input <path> [--force]
```

**Arguments:**
- `--input` / `-i`: Input file path (required)
- `--force` / `-f`: Overwrite existing job if UUID conflict

**Implementation:**
- Add `import_job` command to jobs group
- Use `SchedulerClient` to call REST API
- Handle file path expansion (`~`, env vars)
- Display warnings prominently
- Exit with non-zero code on error

**Output Examples:**
```
# Success
Imported job "Daily Maintenance" (abc-123)
  - 5 tasks imported
  - Warning: Profile 'prod-profile' not found

# Conflict error
Error: Job with UUID abc-123 already exists ("Daily Maintenance")
Use --force to overwrite existing job.

# Profile error
Error: Profile 'missing-profile' referenced by task "Build" not found.
Available profiles: default, development, production
```

**Examples in Help:**
```
Examples:

\b
    # Import job from file
    claude-code-scheduler cli jobs import --input ~/exports/my-job.json

\b
    # Force overwrite existing job
    claude-code-scheduler cli jobs import -i ./backup.json --force

\b
    # Import with verbose output
    claude-code-scheduler cli jobs import -i ./job.json -v
```

---

### Task 4: Add GUI Import Menu Item

**File:** `claude_code_scheduler/ui/main_window.py`

**Description:** Add "Import Job..." menu item under Job menu.

**Implementation:**
- Add `_import_job_action` to Job menu
- Connect to `_on_import_job()` slot
- Slot implementation:
  1. Show `QFileDialog.getOpenFileName()` with `.json` filter
  2. Call import service validation
  3. If warnings, show confirmation dialog
  4. If conflict, show overwrite confirmation
  5. Perform import
  6. Refresh jobs panel
  7. Show success/error message box

**Menu Location:** Job → Import Job... (Ctrl+I)

---

### Task 5: Create Import Warning Dialog

**File:** `claude_code_scheduler/ui/dialogs/import_warning_dialog.py`

**Description:** Dialog showing import validation warnings before proceeding.

**Features:**
- Show file path being imported
- List all warnings (missing profiles, etc.)
- Show conflict info if job exists
- Buttons: "Import Anyway", "Cancel"
- Checkbox: "Overwrite existing job" (if conflict)

**Implementation:**
- Create `ImportWarningDialog(QDialog)`
- Accept `ImportResult` in constructor
- Display warnings in scrollable list
- Return tuple of (proceed: bool, force: bool)

---

### Task 6: Add Tests

**File:** `tests/test_import_service.py`

**Test Cases:**
1. Import valid job with tasks
2. Import job with missing profile (warning)
3. Import with UUID conflict (error without force)
4. Import with UUID conflict and force (overwrites)
5. Import invalid JSON (error)
6. Import file not found (error)
7. Import with version mismatch (error/warning)
8. Round-trip: export then import produces identical data

---

## Acceptance Criteria

- [ ] Import validates JSON structure before importing
- [ ] Missing profiles generate warnings, not blocking errors
- [ ] UUID conflicts are detected and reported
- [ ] `--force` flag allows overwriting existing jobs
- [ ] GUI shows warning dialog before import
- [ ] CLI displays clear error messages with suggestions
- [ ] REST API returns appropriate HTTP status codes
- [ ] Unit tests pass

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_JSON` | 400 | JSON parsing failed |
| `INVALID_SCHEMA` | 400 | Required fields missing |
| `VERSION_MISMATCH` | 400 | Unsupported export version |
| `JOB_EXISTS` | 409 | Job UUID already exists |
| `PROFILE_NOT_FOUND` | 422 | Referenced profile missing |
| `FILE_NOT_FOUND` | 404 | Import file does not exist |

## Dependencies

- Existing `ConfigStorage` class
- Existing `Job` and `Task` models with `from_dict()` methods
- `ExportService` (for round-trip testing)
- `QFileDialog` for GUI file selection

## Notes

- Import preserves original UUIDs (for migration scenarios)
- Import does NOT create missing profiles (only warns)
- Tasks are linked to job via `job_id` field
- Import atomic: all or nothing (rollback on partial failure)
