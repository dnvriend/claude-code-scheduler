# Sequential Scheduler Implementation TODO

## Overview
Implement sequential task execution within Jobs - tasks run in order, each starting after the previous completes successfully.

## Data Model Changes

- [ ] Add `task_order: list[UUID]` field to Job model
- [ ] Update Job `to_dict()` and `from_dict()` serialization
- [ ] Add `ScheduleType.SEQUENTIAL` enum value to `enums.py`
  - Tasks with SEQUENTIAL schedule only run as part of a Job sequence
  - They don't run on their own schedule (no cron, no interval)
  - They wait to be triggered by the previous task's success
- [ ] Add retry configuration to Task or ScheduleConfig:
  - `max_retries: int = 0` - Maximum retry attempts on failure (0 = no retry)
  - `retry_delay_seconds: int = 60` - Delay between retries
  - `current_retry: int = 0` - Track current retry count (runtime state)
- [ ] Validation rules for SEQUENTIAL schedule:
  - Task MUST be assigned to a Job (`job_id` required)
  - Task MUST be in Job's `task_order` list
  - Cannot have interval/calendar/file_watch settings
- [ ] Update ScheduleTypeSelector widget (`schedule_type_selector.py`)
  - Add "Sequential" button to schedule type options
  - Button should be enabled/disabled based on task having a Job assigned
- [ ] Update TaskEditorPanel to handle SEQUENTIAL schedule
  - When SEQUENTIAL selected: hide interval/calendar/file_watch panels
  - Show retry configuration panel:
    - `max_retries` spinbox (0-10, default 0)
    - `retry_delay_seconds` spinbox (0-3600, default 60)
  - Disable SEQUENTIAL button when task has no Job assigned
  - Auto-switch away from SEQUENTIAL if Job is removed from task
- [ ] Update task schedule description for SEQUENTIAL: "Sequential (runs in job order)"
- [ ] Validation in TaskEditorPanel:
  - Cannot save SEQUENTIAL task without Job assignment
  - Show warning/error message if validation fails

## REST API

- [ ] Add `PUT /api/jobs/{id}/task-order` endpoint
  - Body: `["uuid1", "uuid2", "uuid3"]` (ordered list)
  - Validates all UUIDs belong to the job
  - Returns updated job
- [ ] Add `GET /api/jobs/{id}/task-order` endpoint
  - Returns current task order as list
- [ ] Update job GET to include `task_order` in response
- [ ] Update task PUT/POST to accept retry fields:
  - `max_retries: int`
  - `retry_delay_seconds: int`
- [ ] Validation on task save:
  - If `schedule_type == "sequential"` and `job_id` is null → 400 error
  - If `schedule_type == "sequential"` → clear interval/calendar/file_watch fields

## CLI Commands

- [ ] Add `claude-code-scheduler cli jobs reorder <job-id> <uuid1> <uuid2> ...`
- [ ] Update `claude-code-scheduler cli jobs get` to show task order
- [ ] Update `claude-code-scheduler cli tasks create` with sequential options:
  - `--schedule-type sequential` option
  - `--max-retries N` (default 0)
  - `--retry-delay N` (default 60 seconds)
  - `--job-id UUID` (required for sequential)
- [ ] Update `claude-code-scheduler cli tasks update` with same options
- [ ] CLI validation:
  - `--schedule-type sequential` requires `--job-id`
  - Error message: "Sequential schedule requires --job-id to be set"
  - `--max-retries` and `--retry-delay` only valid with `--schedule-type sequential`
  - Warn if used with other schedule types
- [ ] Update `claude-code-scheduler cli tasks get` to show:
  - Schedule type
  - Retry config (if sequential)
  - Position in job sequence (e.g., "Step 2/5 in Job 'Daily Maintenance'")

## UI - Drag and Drop

- [ ] Enable drag-drop on TaskListPanel when filtered by a Job
- [ ] Implement drag start (store dragged widget/index)
- [ ] Implement drag over (show placeholder hole, shift items)
- [ ] Implement drop (reorder list, save via API/storage)
- [ ] Visual feedback: ghost item while dragging, highlight drop zone
- [ ] Disable drag-drop when showing "All Tasks" (no job filter)

## Sequential Scheduler (Observer Pattern)

- [ ] Create `SequentialScheduler` service or extend `TaskScheduler`
- [ ] **Observable:** Run completion events from `TaskScheduler`
  - Already emits `run_completed` signal via `SchedulerSignalBridge`
- [ ] **Observer:** `SequentialScheduler` subscribes to run completions
  - On `RunStatus.SUCCESS`: check if task is in a Job sequence, start next
  - On `RunStatus.FAILED`:
    - If `current_retry < max_retries`: increment retry, wait `retry_delay_seconds`, retry task
    - Else: stop sequence, mark Job as failed
  - On `RunStatus.CANCELLED`: stop sequence, mark Job as cancelled
- [ ] Track active Job execution state:
  - `current_job_id: UUID | None`
  - `current_task_index: int`
- [ ] Add Job-level status tracking (pending, running, completed, failed)

## Visual Status Indicators

- [ ] Task status colors (already exist):
  - 🟡 Running (orange/yellow)
  - 🟢 Success (green)
  - 🔴 Failed (red)
  - ⚪ Pending/Idle (grey)
- [ ] Enhance TaskItemWidget to show "active in sequence" state
  - Highlight border or background when task is current in running Job
  - Show sequence position indicator (e.g., "2/5" or step number)
- [ ] Job status indicator in JobsPanel:
  - Show which Job is currently executing
  - Progress indicator (e.g., "Running task 2/5")
- [ ] Real-time updates via existing signal bridge:
  - `run_started` → highlight task as active
  - `run_completed` → update task status, advance to next
  - New signal: `job_progress(job_id, current_index, total)`

## Job Execution Flow

- [ ] Add "Run Job" action (menu + button)
- [ ] Starts first task in `task_order`
- [ ] Chain executions on success
- [ ] Update Job status throughout execution
- [ ] Emit signals/events for UI updates

## Testing

- [ ] Unit test: Job task_order serialization
- [ ] Unit test: Reorder API validation
- [ ] Unit test: Sequential scheduler next-task logic
- [ ] Integration test: Full job sequential execution

## Order of Implementation

1. Data model changes (Job.task_order)
2. REST API endpoints
3. Sequential scheduler logic
4. UI drag-and-drop
5. Job execution flow (Run Job action)
6. Testing
