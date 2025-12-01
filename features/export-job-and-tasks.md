# Feature: Export Job and Tasks

## Overview

Export a job with all associated tasks and configuration to a JSON file for backup, sharing, or migration purposes.

## Data Model

The export file structure:

```json
{
  "version": "1.0",
  "exported_at": "2025-12-01T10:00:00Z",
  "job": {
    "id": "uuid-string",
    "name": "Job Name",
    "description": "...",
    "status": "pending",
    "profile": "profile-uuid-or-null",
    "working_directory": { ... },
    "task_order": ["task-uuid-1", "task-uuid-2"],
    "created_at": "...",
    "updated_at": "..."
  },
  "tasks": [
    {
      "id": "task-uuid-1",
      "job_id": "job-uuid",
      "name": "Task 1",
      "enabled": true,
      "model": "sonnet",
      "profile": "profile-uuid-or-null",
      "schedule": { ... },
      "command_type": "prompt",
      "command": "...",
      "permissions": "default",
      "session_mode": "new",
      "allowed_tools": [],
      "disallowed_tools": [],
      "retry": { ... },
      "notifications": { ... },
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "profiles_referenced": ["profile-uuid-1", "profile-uuid-2"]
}
```

## Implementation Tasks

### Task 1: Create Export Service

**File:** `claude_code_scheduler/services/export_service.py`

**Description:** Core export logic that gathers job and tasks data and serializes to JSON.

**Implementation:**
- Create `ExportService` class
- Method `export_job(job_id: UUID, include_profiles: bool = False) -> dict`
  - Load job by ID from storage
  - Load all tasks with matching `job_id`
  - Collect referenced profile IDs
  - Return structured export dict with version and timestamp
- Method `export_to_file(job_id: UUID, output_path: Path) -> Path`
  - Call `export_job()`
  - Write JSON to file with 2-space indent
  - Return resolved output path
- Validation:
  - Raise `ValueError` if job not found
  - Log warnings for orphaned task references

**Tests:** `tests/test_export_service.py`

---

### Task 2: Add REST API Export Endpoint

**File:** `claude_code_scheduler/services/debug_server.py`

**Description:** Add REST endpoint for job export.

**Endpoints:**
- `GET /api/jobs/{id}/export` - Export job with tasks as JSON response
- `POST /api/jobs/{id}/export` - Export job to file path (body: `{"output_path": "/path/to/file.json"}`)

**Response Format:**
```json
{
  "status": "success",
  "export": { ... },
  "output_path": "/path/to/exported.json"  // Only for POST
}
```

**Error Responses:**
- 404: Job not found
- 400: Invalid output path (POST)
- 500: Export failed

**Implementation:**
- Add `_api_export_job()` method in `DebugRequestHandler`
- Wire up routes in `_route_request()`
- Use `ExportService` for export logic

---

### Task 3: Add CLI Export Command

**File:** `claude_code_scheduler/cli_jobs.py`

**Description:** Add `job export` subcommand to CLI.

**Command:**
```bash
claude-code-scheduler cli jobs export <job-id> --out <path>
```

**Arguments:**
- `job-id` (positional): UUID of job to export
- `--out` / `-o`: Output file path (required)

**Implementation:**
- Add `export_job` command to jobs group
- Use `SchedulerClient` to call REST API
- Handle file path expansion (`~`, env vars)
- Pretty-print success/error messages

**Examples in Help:**
```
Examples:

\b
    # Export job to file
    claude-code-scheduler cli jobs export abc-123 --out ~/exports/my-job.json

\b
    # Export with verbose output
    claude-code-scheduler cli jobs export abc-123 -o ./backup.json -v
```

---

### Task 4: Add GUI Export Menu Item

**File:** `claude_code_scheduler/ui/main_window.py`

**Description:** Add "Export Job..." menu item under Job menu.

**Implementation:**
- Add `_export_job_action` to Job menu
- Connect to `_on_export_job()` slot
- Slot implementation:
  1. Get currently selected job from jobs panel
  2. Show `QFileDialog.getSaveFileName()` with `.json` filter
  3. Call export service
  4. Show success/error message box

**Menu Location:** Job → Export Job... (Ctrl+E)

---

### Task 5: Add GUI Context Menu Export

**File:** `claude_code_scheduler/ui/panels/jobs_panel.py`

**Description:** Add "Export" option to job item context menu (right-click).

**Implementation:**
- Add context menu to `JobItemWidget`
- Add "Export..." action
- Emit `export_job_requested(job_id: UUID)` signal
- Connect signal in `MainWindow` to `_on_export_job()` slot

---

### Task 6: Add Tests

**File:** `tests/test_export_service.py`

**Test Cases:**
1. Export job with no tasks
2. Export job with multiple tasks
3. Export job with profile references
4. Export to file creates valid JSON
5. Export non-existent job raises error
6. Exported JSON can be re-imported (round-trip)

---

## Acceptance Criteria

- [ ] Export produces valid JSON with version and timestamp
- [ ] All task configuration is preserved in export
- [ ] Profile IDs are listed for reference
- [ ] GUI shows file save dialog with `.json` filter
- [ ] CLI supports `--out` flag with path expansion
- [ ] REST API returns proper error codes
- [ ] Unit tests pass

## Dependencies

- Existing `ConfigStorage` class
- Existing `Job` and `Task` models with `to_dict()` methods
- `QFileDialog` for GUI file selection

## Notes

- Export does NOT include profile definitions (only references)
- Export does NOT include run history
- File format version allows future schema migrations
