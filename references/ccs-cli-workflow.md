# Claude Code Scheduler CLI Workflow

## Command Overview

### Jobs

| Command | Description |
|---------|-------------|
| `jobs list` | List all jobs |
| `jobs get <id>` | Get job details |
| `jobs create` | Create a new job |
| `jobs update <id>` | Update a job |
| `jobs delete <id>` | Delete job (cascades tasks/runs) |
| `jobs run <id>` | Run all tasks in a job |
| `jobs stop <id>` | Stop a running job |
| `jobs tasks <id>` | List tasks for a job |
| `jobs set-order <id>` | Set task execution order |
| `jobs export <id>` | Export job to JSON |
| `jobs import <file>` | Import job from JSON |

### Tasks

| Command | Description |
|---------|-------------|
| `tasks list` | List all tasks |
| `tasks get <id>` | Get task details |
| `tasks create` | Create a new task |
| `tasks update <id>` | Update a task |
| `tasks delete <id>` | Delete a task |
| `tasks run <id>` | Run a task immediately |
| `tasks enable <id>` | Enable a task |
| `tasks disable <id>` | Disable a task |

### Runs

| Command | Description |
|---------|-------------|
| `runs list` | List recent runs |
| `runs get <id>` | Get run details |
| `runs stop <id>` | Stop a running task |
| `runs restart <id>` | Restart from a run |
| `runs delete <id>` | Delete run record |

### Profiles

| Command | Description |
|---------|-------------|
| `profiles list` | List all profiles |
| `profiles get <id>` | Get profile details |
| `profiles create` | Create a new profile |
| `profiles update <id>` | Update a profile |
| `profiles delete <id>` | Delete a profile |

### Utility

| Command | Description |
|---------|-------------|
| `health` | Check API health |
| `state` | Get aggregated state |
| `scheduler` | Show scheduled tasks |

---

## Shortcuts and Defaults

### Profile Shortcuts

Instead of looking up profile UUIDs, use shortcuts:

| Shortcut | Profile | UUID |
|----------|---------|------|
| `--zai` | ZAI (Z.AI API) | `5270805b-3731-41da-8710-fe765f2e58be` |
| `--bedrock` | AWS Bedrock | `9e4eaa7d-ba4e-44c0-861a-712aa75382d1` |

```bash
# Instead of:
claude-code-scheduler cli tasks create --profile 5270805b-3731-41da-8710-fe765f2e58be ...

# Use:
claude-code-scheduler cli tasks create --zai ...
```

### Task Defaults

| Field | Default | Description |
|-------|---------|-------------|
| `permissions` | `bypass` | Skip permission prompts |
| `session_mode` | `new` | Start fresh session |
| `model` | `sonnet` | Claude Sonnet model |
| `enabled` | `true` | Task is enabled |
| `commit_on_success` | `true` | Auto-commit on success |

### Job Defaults

| Field | Default | Description |
|-------|---------|-------------|
| `use_worktree` | `false` | Git worktree disabled |
| `worktree_branch` | `main` | Branch to create worktree from |
| `status` | `pending` | Initial job status |

---

## Workflow Examples

### 1. Basic Workflow: Create Job with Tasks

```bash
# Step 1: Create a job with working directory
claude-code-scheduler cli jobs create \
  --name "feature-auth" \
  --working-directory ~/projects/my-app \
  --use-worktree \
  --worktree-name "feature-auth" \
  --worktree-branch "main"

# Step 2: Create tasks (note the --zai shortcut and --prompt)
claude-code-scheduler cli tasks create \
  --name "implement-login" \
  --prompt "Implement user login with JWT authentication" \
  --zai \
  --job <job-id>

claude-code-scheduler cli tasks create \
  --name "add-tests" \
  --prompt "Add unit tests for the login functionality" \
  --zai \
  --job <job-id>

claude-code-scheduler cli tasks create \
  --name "run-pipeline" \
  --prompt "Run make pipeline and fix any issues" \
  --zai \
  --job <job-id>

# Step 3: Run the job
claude-code-scheduler cli jobs run <job-id>
```

### 2. Quick Task Creation

```bash
# Minimal task with ZAI profile
claude-code-scheduler cli tasks create \
  --name "code-review" \
  --prompt "Review code for security issues" \
  --zai \
  --job <job-id>

# Task with Bedrock profile
claude-code-scheduler cli tasks create \
  --name "refactor" \
  --prompt "Refactor the database module" \
  --bedrock \
  --job <job-id>
```

### 3. Update Task Prompt

```bash
claude-code-scheduler cli tasks update <task-id> \
  --prompt "Review code for security issues and performance bottlenecks"
```

### 4. Manage Task State

```bash
# Disable a task
claude-code-scheduler cli tasks disable <task-id>

# Enable a task
claude-code-scheduler cli tasks enable <task-id>

# Delete a task (removed from job's task_order automatically)
claude-code-scheduler cli tasks delete <task-id>
```

### 5. Export/Import Jobs

```bash
# Export job with all tasks
claude-code-scheduler cli jobs export <job-id> -o my-job.json

# Import job (creates new UUIDs)
claude-code-scheduler cli jobs import my-job.json
```

### 6. Monitor Runs

```bash
# List recent runs
claude-code-scheduler cli runs list

# Get run details
claude-code-scheduler cli runs get <run-id>

# Stop a running task
claude-code-scheduler cli runs stop <run-id>
```

### 7. Cleanup

```bash
# Delete job and all associated tasks/runs (cascade)
claude-code-scheduler cli jobs delete <job-id> --force

# Delete all jobs
claude-code-scheduler cli jobs list | jq -r '.jobs[].id' | \
  xargs -I {} claude-code-scheduler cli jobs delete {} --force
```

---

## Common Patterns

### Pattern 1: Feature Development Job

Standard structure for implementing a feature:

```bash
# Create job
claude-code-scheduler cli jobs create \
  --name "feature-<name>" \
  --working-directory ~/projects/<repo> \
  --use-worktree \
  --worktree-name "feature-<name>"

# Tasks follow this pattern:
# 1. Implementation task(s)
# 2. Test task
# 3. Pipeline task (lint, typecheck, test)
# 4. Documentation task (if needed)
```

### Pattern 2: Bug Fix Job

```bash
claude-code-scheduler cli jobs create \
  --name "fix-<issue>" \
  --working-directory ~/projects/<repo>

# Single task for simple fixes
claude-code-scheduler cli tasks create \
  --name "fix-and-test" \
  --prompt "Fix <issue description>. Run tests to verify." \
  --zai \
  --job <job-id>
```

### Pattern 3: Batch Operations

```bash
# List all task IDs for a job
claude-code-scheduler cli jobs tasks <job-id> | jq -r '.[].id'

# Disable all tasks in a job
claude-code-scheduler cli jobs tasks <job-id> | jq -r '.[].id' | \
  xargs -I {} claude-code-scheduler cli tasks disable {}
```

---

## Tips

1. **Use `--zai` by default** - It's the primary profile for most work
2. **Always assign tasks to jobs** - Tasks inherit working directory from jobs
3. **Use worktrees for isolation** - Prevents conflicts with your main branch
4. **End jobs with pipeline task** - Ensures code quality before completion
5. **Use `--force` for non-interactive scripts** - Skips confirmation prompts
6. **Check `task_order`** - Tasks run in this order for sequential execution
