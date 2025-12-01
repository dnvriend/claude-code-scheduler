# Job Story: Jobs as Task Container

## Overview

Add a new supertype `Job` that groups related tasks together. This creates a hierarchy:

```
Job (1) ──▶ Task (many) ──▶ Run (many)
```

## User Story

As a user, I want to organize my tasks into jobs so that I can:
- Group related tasks together (e.g., "Implement CLI feature")
- See progress at the job level
- Delete a job and have all its tasks/runs cascade delete
- Create a job first, then break it down into tasks

## Data Model Changes

### New: Job Model

```python
@dataclass
class Job:
    id: UUID
    name: str
    description: str
    status: JobStatus  # pending, in_progress, completed, failed
    created_at: datetime
    updated_at: datetime

class JobStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
```

### Modified: Task Model

```python
@dataclass
class Task:
    # Existing fields...
    job_id: UUID | None  # NEW: Foreign key to Job (nullable for migration)
```

### Relationships

- Job has many Tasks (1:N)
- Task has many Runs (1:N) - already exists
- Cascade delete: Job → Tasks → Runs

## Storage Changes

### New File: `~/.claude-scheduler/jobs.json`

```json
{
  "jobs": [
    {
      "id": "uuid",
      "name": "Implement CLI",
      "description": "Add CLI commands for API",
      "status": "in_progress",
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

### Modified: `tasks.json`

Tasks gain `job_id` field (nullable for backward compatibility).

## REST API Changes

### New Endpoints: Jobs CRUD

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | List all jobs |
| GET | `/api/jobs/{id}` | Get job with its tasks |
| POST | `/api/jobs` | Create new job |
| PUT | `/api/jobs/{id}` | Update job |
| DELETE | `/api/jobs/{id}` | Delete job (cascade to tasks/runs) |

### Modified Endpoints

| Method | Endpoint | Change |
|--------|----------|--------|
| POST | `/api/tasks` | Accept optional `job_id` |
| GET | `/api/tasks` | Include `job_id` in response |
| GET | `/api/jobs/{id}/tasks` | List tasks for a job |

## UI Changes

### New Panel: Jobs Panel (leftmost)

```
┌─────────────┬──────────────┬─────────────┬──────────┬──────────┐
│   JOBS      │    TASKS     │ TASK EDITOR │   RUNS   │   LOGS   │
│             │              │             │          │          │
│ + New Job   │ (filtered by │             │          │          │
│             │  selected    │             │          │          │
│ ▶ Job 1     │  job)        │             │          │          │
│   ├─ Task A │              │             │          │          │
│   └─ Task B │              │             │          │          │
│             │              │             │          │          │
│ ▶ Job 2     │              │             │          │          │
│   └─ Task C │              │             │          │          │
│             │              │             │          │          │
│ (Unassigned)│              │             │          │          │
│   └─ Task D │              │             │          │          │
└─────────────┴──────────────┴─────────────┴──────────┴──────────┘
```

### Behavior

1. Jobs panel shows tree: Job → Tasks
2. Selecting a job filters Tasks panel to show only that job's tasks
3. "(Unassigned)" section for tasks without a job
4. Delete job shows confirmation, cascades to tasks/runs
5. New task can be assigned to selected job

## CLI Changes

### New Commands

```bash
# Jobs CRUD
claude-code-scheduler cli jobs list
claude-code-scheduler cli jobs get <id>
claude-code-scheduler cli jobs create --name "Job Name" [--description "..."]
claude-code-scheduler cli jobs update <id> [--name] [--description] [--status]
claude-code-scheduler cli jobs delete <id> [--force]

# List tasks for a job
claude-code-scheduler cli jobs tasks <job-id>
```

### Modified Commands

```bash
# Tasks can now specify job
claude-code-scheduler cli tasks create --name "Task" --job <job-id> ...
```

## Cascade Delete Logic

```python
def delete_job(job_id: UUID) -> None:
    # 1. Find all tasks for this job
    tasks = [t for t in all_tasks if t.job_id == job_id]

    # 2. For each task, delete its runs
    for task in tasks:
        runs = [r for r in all_runs if r.task_id == task.id]
        for run in runs:
            delete_run(run.id)  # Also deletes log files
        delete_task(task.id)

    # 3. Delete the job
    jobs.remove(job_id)
```

## Migration Strategy

1. Add `job_id: UUID | None` to Task (nullable)
2. Existing tasks have `job_id = None` (shown as "Unassigned")
3. No data migration required - backward compatible

---

## Task Breakdown

### Phase 1: Data Model (Sequential)
| # | Task | Description | Depends |
|---|------|-------------|---------|
| 1.1 | Create Job model | `models/job.py` with Job dataclass and JobStatus enum | - |
| 1.2 | Update Task model | Add `job_id: UUID | None` field | 1.1 |
| 1.3 | Update storage | Add jobs.json handling in ConfigStorage | 1.2 |

### Phase 2: REST API (Parallel after Phase 1)
| # | Task | Description | Depends |
|---|------|-------------|---------|
| 2.1 | Jobs CRUD endpoints | Add to debug_server.py | 1.3 |
| 2.2 | Update tasks endpoints | Include job_id in task operations | 1.3 |
| 2.3 | Cascade delete logic | Implement in storage layer | 1.3 |

### Phase 3: CLI (Parallel after Phase 2)
| # | Task | Description | Depends |
|---|------|-------------|---------|
| 3.1 | Create cli_jobs.py | Jobs CLI commands | 2.1 |
| 3.2 | Update cli_tasks.py | Add --job option | 2.2 |
| 3.3 | Integrate into cli.py | Add jobs command group | 3.1 |

### Phase 4: UI (Parallel after Phase 2)
| # | Task | Description | Depends |
|---|------|-------------|---------|
| 4.1 | Create JobsPanel | New panel component | 2.1 |
| 4.2 | Update MainWindow | Add jobs panel, wire up | 4.1 |
| 4.3 | Update TaskListPanel | Filter by selected job | 4.2 |

### Phase 5: QC (Sequential after all)
| # | Task | Description | Depends |
|---|------|-------------|---------|
| 5.1 | Lint and typecheck | Fix all issues | 4.3 |
| 5.2 | Integration test | Manual testing | 5.1 |

---

## Worker Assignments

Using ZAI profile for parallel execution:

```
Phase 1: Sequential (model dependencies)
  Worker → 1.1, 1.2, 1.3

Phase 2: Parallel
  Worker A → 2.1 (Jobs CRUD)
  Worker B → 2.2 (Tasks update)
  Worker C → 2.3 (Cascade delete)

Phase 3: Parallel
  Worker D → 3.1 (cli_jobs.py)
  Worker E → 3.2 (cli_tasks.py update)

Phase 4: Sequential (UI dependencies)
  Worker → 4.1, 4.2, 4.3

Phase 5: QC
  Worker → 5.1, 5.2
```

## Acceptance Criteria

- [ ] Job CRUD works via API
- [ ] Job CRUD works via CLI
- [ ] Tasks can be assigned to jobs
- [ ] Jobs panel shows in UI
- [ ] Selecting job filters tasks
- [ ] Delete job cascades to tasks/runs
- [ ] Existing tasks work as "Unassigned"
- [ ] All lint/typecheck passes
