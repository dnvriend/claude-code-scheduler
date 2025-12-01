# TODO - Claude Code Scheduler

## Session Memory

**Last session:** 2025-11-29
**Focus:** Job Working Directory with Git Worktree + UI Improvements

### What was done this session:
1. Implemented Job Working Directory with git worktree isolation
2. Added GitService for branch listing and worktree creation
3. Job editor dialog with Browse button for directory selection
4. REST API working_directory handling for job create/update
5. Unicode status indicators for task/run widgets (○●◐✗◌)
6. Play/stop button toggle on task widget based on run state
7. Observer pattern fix: task widget updates on run start/complete
8. Job deletion cascade (tasks + runs) while keeping worktree

### Current state:
- Jobs can have isolated git worktrees for task execution
- Task widgets show running state with ◐ icon and ⏹ stop button
- Sequential job execution works with worktree isolation

---

## Sequential Job Execution Feature

### Completed

| Component | Status | Notes |
|-----------|--------|-------|
| **Data Model** | | |
| Job model with task_order | ✅ | `models/job.py` |
| JobStatus enum | ✅ | pending, in_progress, completed, failed |
| Job persistence (jobs.json) | ✅ | `storage/config_storage.py` |
| JobWorkingDirectory model | ✅ | path, use_git_worktree, worktree_name, worktree_branch |
| **Sequential Scheduler** | | |
| SequentialScheduler service | ✅ | `services/sequential_scheduler.py` |
| Task chaining (next on success) | ✅ | Observer pattern |
| Job status updates | ✅ | Via callback |
| Progress callbacks | ✅ | on_job_progress |
| Thread-safe API calls | ✅ | Qt signal bridge |
| **Git Worktree Support** | | |
| GitService | ✅ | `services/git_service.py` |
| Branch listing | ✅ | list_branches() |
| Worktree creation | ✅ | create_worktree() |
| Worktree in executor | ✅ | Sibling directory pattern |
| **REST API** | | |
| GET /api/jobs | ✅ | List all jobs |
| GET /api/jobs/{id} | ✅ | Get single job |
| POST /api/jobs | ✅ | Create job (with working_directory) |
| PUT /api/jobs/{id} | ✅ | Update job (with working_directory) |
| DELETE /api/jobs/{id} | ✅ | Cascade delete (tasks + runs, keep worktree) |
| GET /api/jobs/{id}/tasks | ✅ | List tasks in job |
| POST /api/jobs/{id}/run | ✅ | Start sequential execution |
| POST /api/jobs/{id}/stop | ✅ | Stop running job |
| **CLI** | | |
| jobs list | ✅ | --output json/table |
| jobs get | ✅ | |
| jobs create | ✅ | --name, --description |
| jobs update | ✅ | --name, --description, --status |
| jobs delete | ✅ | --force, cascade delete |
| jobs run | ✅ | Start sequential execution |
| jobs tasks | ✅ | List tasks in job |
| **UI - Jobs Panel** | | |
| Jobs panel | ✅ | Left panel with job list |
| Job item widget | ✅ | Status icon, name, task count |
| Run/Stop button on job items | ✅ | ▶/⏹ toggle |
| Job selection filters tasks | ✅ | Click job → filter task list |
| Drag-and-drop task reorder | ✅ | Only when job selected |
| Jobs panel minimum width | ✅ | 180px minimum |
| Show/hide jobs panel | ✅ | View menu toggle |
| **UI - Job Editor** | | |
| Job editor dialog | ✅ | Name, description, working directory |
| Browse button for directory | ✅ | QFileDialog |
| Git worktree checkbox | ✅ | Toggle worktree options |
| Branch dropdown | ✅ | Auto-populated from git repo |
| **UI - Task Widget** | | |
| Unicode status icon | ✅ | ○ disabled, ● enabled, ◐ running, ✗ failed |
| Clickable icon to toggle | ✅ | Click to enable/disable |
| Play/stop button toggle | ✅ | ▶ when idle, ⏹ when running |
| Observer update on run | ✅ | Status icon + button update |
| **UI - Run Widget** | | |
| Unicode status indicator | ✅ | ○ upcoming, ◐ running, ● success, ✗ failed, ◌ cancelled |
| Stop/restart/delete buttons | ✅ | Context-aware visibility |
| **Retry Logic** | | |
| Retry on task failure | ✅ | Wired to task.retry config |
| max_retries config | ✅ | Uses task.retry.max_attempts |
| retry_delay_seconds | ✅ | Uses task.retry.delay_seconds |

### Not Implemented

| Component | Priority | Notes |
|-----------|----------|-------|
| **Retry Logic** | | |
| Exponential backoff | Low | backoff_multiplier exists but not wired |
| **Stop/Cancel** | | |
| Cancel queued tasks | Low | Stop job stops current, doesn't cancel queue |

---

## Backlog

### REST API Improvements
- [ ] Add GET /api/runs/{id}/logs endpoint

### UI Improvements
- [ ] Add "Duplicate Job" action

### CLI Improvements
- [ ] Add `jobs set-order <id> <task-ids...>` command

### Job-level Config
- [ ] Job-level profile override (inherit or override task profiles)

---

## Completed (Archive)

### Job Working Directory - DONE (2025-11-29)
- Job owns working_directory (removed from Task)
- Git worktree support with sibling directory pattern
- Worktree creation on job start
- Branch selection in job editor

### UI Widget Improvements - DONE (2025-11-29)
- Unicode status indicators (consistent across task/run/job widgets)
- Play/stop button toggle on task widget
- Observer pattern for run state updates

### REST API Run Tracking Bug - FIXED (2025-11-29)
- **Root cause:** API calls from HTTP thread, QtScheduler needs Qt main thread
- **Fix:** Added `api_run_task` and `api_run_job` signals to SchedulerSignalBridge

### REST API Observer/Observable Bug - FIXED
- Added `state_changed` signal for thread-safe UI refresh

### Codebase cleanup - DONE
- Removed distributed components (daemon, server, node, messaging)
- GUI runs standalone with REST API on port 5679

---

## Scripts

- `./scripts/run.sh` - Run GUI with TRACE logging to `./logs/scheduler.log`

## Quick Reference

```bash
# Run GUI
claude-code-scheduler gui

# CLI jobs commands
claude-code-scheduler cli jobs list
claude-code-scheduler cli jobs create --name "My Job"
claude-code-scheduler cli jobs run <job-id>

# REST API
curl http://127.0.0.1:5679/api/jobs
curl -X POST http://127.0.0.1:5679/api/jobs/<id>/run
```
