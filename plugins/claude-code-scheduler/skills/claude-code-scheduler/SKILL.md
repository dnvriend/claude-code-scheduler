---
name: skill-claude-code-scheduler
description: Schedule and manage Claude Code sessions
---

# When to use
- When you need to schedule and automate Claude Code CLI sessions
- When you need to manage jobs, tasks, runs, and profiles
- When you need to implement redundant worker patterns for AI-assisted coding
- When you need to interact with the scheduler's REST API
- When you need guidance on agentic coding patterns (/plan, /orchestrate, /qc, /finalize)

# claude-code-scheduler Skill

## Purpose

This skill provides comprehensive guidance for `claude-code-scheduler`, a GUI application and CLI tool for scheduling and managing Claude Code CLI sessions. It implements **redundant worker patterns** for AI-assisted coding, where multiple workers execute tasks in parallel and the best result is selected.

**Key Capabilities:**
- Schedule Claude Code sessions (manual, interval, calendar, file-watch triggers)
- Manage jobs, tasks, runs, and environment profiles
- REST API for external control (port 5679)
- Agentic coding patterns with parallel workers and QC selection

## When to Use This Skill

**Use this skill when:**
- You need to schedule automated Claude Code CLI sessions
- You need to manage jobs (containers for related tasks)
- You need to interact with the scheduler REST API
- You need to use agentic coding patterns (/plan, /orchestrate, /qc)
- You need to configure environment profiles for different API backends

**Do NOT use this skill for:**
- Direct Claude Code CLI usage (not scheduling)
- General Python development questions
- Unrelated automation tasks

## Architecture

```
Data Model: Job (1) → Task (many) → Run (many)

User → /plan → Planner (Sonnet)
                    ↓
               job.json
                    ↓
       /orchestrate → Orchestrator (Sonnet)
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
Worker 1        Worker 2        Worker 3  (ZAI/GLM)
    ↓               ↓               ↓
candidates/     candidates/     candidates/
    └───────────────┼───────────────┘
                    ↓
              /qc → QC Agent (Sonnet)
                    ↓
            Score table + Winner
                    ↓
        /finalize → Move to final location
```

## CLI Tool: claude-code-scheduler

The `claude-code-scheduler` is a CLI and GUI application for scheduling Claude Code sessions with support for REST API control.

### Installation

```bash
# Clone and install
git clone https://github.com/dnvriend/claude-code-scheduler.git
cd claude-code-scheduler
uv tool install .
```

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager

### Quick Start

```bash
# Launch the GUI application
claude-code-scheduler gui

# Launch with verbose logging
claude-code-scheduler gui -vv

# List tasks via REST API (GUI must be running)
claude-code-scheduler cli tasks list

# Check scheduler health
claude-code-scheduler cli health
```

## Progressive Disclosure

<details>
<summary><strong>📖 Core Commands (Click to expand)</strong></summary>

### gui - Launch GUI Application

Launch the PyQt6-based GUI application with optional debug server.

**Usage:**
```bash
claude-code-scheduler gui [OPTIONS]
```

**Options:**
- `--restport PORT`: REST API port (default: 5679)
- `-v/-vv/-vvv`: Verbosity (INFO/DEBUG/TRACE)

**Examples:**
```bash
# Launch GUI
claude-code-scheduler gui

# Launch with DEBUG logging
claude-code-scheduler gui -vv

# Launch on custom port
claude-code-scheduler gui --restport 5680
```

---

### cli tasks - Task Management

Manage tasks via the REST API (requires GUI running).

**Usage:**
```bash
claude-code-scheduler cli tasks COMMAND [OPTIONS]
```

**Commands:**
- `list`: List all tasks
- `get <id>`: Get task details
- `create`: Create new task
- `update <id>`: Update task
- `delete <id>`: Delete task
- `run <id>`: Run task immediately
- `enable <id>`: Enable task
- `disable <id>`: Disable task

**Examples:**
```bash
# List all tasks
claude-code-scheduler cli tasks list

# List as table
claude-code-scheduler cli tasks list --output table

# Create a task
claude-code-scheduler cli tasks create --name "Daily Review" --command "Review code changes"

# Run a task now
claude-code-scheduler cli tasks run abc123

# Get task details
claude-code-scheduler cli tasks get abc123
```

---

### cli runs - Run Management

Manage task execution runs.

**Usage:**
```bash
claude-code-scheduler cli runs COMMAND [OPTIONS]
```

**Commands:**
- `list`: List recent runs
- `get <id>`: Get run details
- `stop <id>`: Stop running task
- `restart <id>`: Restart task
- `delete <id>`: Delete run record

**Examples:**
```bash
# List recent runs
claude-code-scheduler cli runs list

# List as table
claude-code-scheduler cli runs list --output table

# Stop a running task
claude-code-scheduler cli runs stop abc123

# Restart a task
claude-code-scheduler cli runs restart abc123
```

---

### cli jobs - Job Management

Manage jobs (containers for related tasks).

**Usage:**
```bash
claude-code-scheduler cli jobs COMMAND [OPTIONS]
```

**Commands:**
- `list`: List all jobs
- `get <id>`: Get job details
- `create`: Create new job
- `update <id>`: Update job
- `delete <id>`: Delete job
- `tasks <id>`: List tasks in job

**Examples:**
```bash
# List all jobs
claude-code-scheduler cli jobs list

# Create a job
claude-code-scheduler cli jobs create --name "Daily Maintenance"

# List tasks in a job
claude-code-scheduler cli jobs tasks abc123
```

---

### cli profiles - Profile Management

Manage environment profiles (API configurations).

**Usage:**
```bash
claude-code-scheduler cli profiles COMMAND [OPTIONS]
```

**Commands:**
- `list`: List all profiles
- `get <id>`: Get profile details
- `create`: Create new profile
- `update <id>`: Update profile
- `delete <id>`: Delete profile

**Examples:**
```bash
# List all profiles
claude-code-scheduler cli profiles list

# Create a profile
claude-code-scheduler cli profiles create --name "ZAI Production"
```

---

### cli state/health/scheduler - Status Commands

Check application and scheduler status.

**Examples:**
```bash
# Full application state
claude-code-scheduler cli state

# Health check
claude-code-scheduler cli health

# Scheduler status
claude-code-scheduler cli scheduler
```

---

### debug - Debug/Inspection Commands

Inspect application state without GUI.

**Usage:**
```bash
claude-code-scheduler debug COMMAND [OPTIONS]
```

**Commands:**
- `all`: Complete state dump
- `tasks`: List all tasks
- `task <id>`: Task details
- `runs`: List recent runs
- `run <id>`: Run details
- `logs`: List log files
- `log <run-id>`: Show log contents
- `profiles`: List profiles
- `env <profile>`: Resolve env vars
- `settings`: Show settings

**Examples:**
```bash
# Complete state dump
claude-code-scheduler debug all

# List tasks
claude-code-scheduler debug tasks

# Show recent runs
claude-code-scheduler debug runs -n 20

# View run log
claude-code-scheduler debug log abc123
```

---

### completion - Shell Completion

Generate shell completion scripts.

**Usage:**
```bash
claude-code-scheduler completion SHELL
```

**Examples:**
```bash
# Bash
eval "$(claude-code-scheduler completion bash)"

# Zsh
eval "$(claude-code-scheduler completion zsh)"

# Fish
claude-code-scheduler completion fish > ~/.config/fish/completions/claude-code-scheduler.fish
```

</details>

<details>
<summary><strong>🚀 Agentic Coding Patterns (Click to expand)</strong></summary>

### Slash Commands

The scheduler includes slash commands for agentic coding with redundant workers.

| Command | Purpose |
|---------|---------|
| `/plan` | Interview user, create Job→Task breakdown |
| `/orchestrate` | Execute job with parallel workers |
| `/qc` | Quality check candidates, build score table |
| `/finalize` | Move winner, cleanup |
| `/retry-until-green` | Retry single task until QC passes |
| `/cleanup` | Reset orchestration state |

---

### /plan [feature-description]

Interview user and create a Job→Task breakdown.

**Process:**
1. Asks clarifying questions (frontend/backend split, tech choices)
2. Identifies dependencies between tasks
3. Marks tasks as sequential or parallel
4. Creates `job.json` with full breakdown

**Example:**
```bash
/plan "Add user authentication with OAuth"
```

**Output:** `job.json`
```json
{
  "name": "Add OAuth Authentication",
  "tasks": [
    {
      "id": "1",
      "name": "Create auth models",
      "parallel_group": 1,
      "workers": 3
    },
    {
      "id": "2",
      "name": "Create auth endpoints",
      "depends_on": ["1"],
      "workers": 3
    }
  ]
}
```

---

### /orchestrate [job-file]

Execute the job with parallel workers.

**Process:**
1. Reads `job.json`
2. Creates `candidates/` directory
3. Spawns N workers per task (parallel)
4. Triggers `/qc` for each task
5. Selects winners

**Example:**
```bash
/orchestrate job.json
```

---

### /qc [candidates-dir]

Quality check candidate implementations.

**Process:**
1. Lists all worker directories
2. Runs `make lint` and `make typecheck`
3. Builds comparison table
4. Recommends winner

**Example:**
```bash
/qc candidates/task_1/
```

**Output:**
```
| Worker   | Lint | Type | LOC | Score |
|----------|------|------|-----|-------|
| worker_1 | PASS | PASS | 245 | 18    |
| worker_2 | FAIL | PASS | 312 | 10    |
| worker_3 | PASS | PASS | 198 | 19    | ← WINNER
```

---

### /finalize [winner] [destination]

Move winner to final location and cleanup.

**Example:**
```bash
/finalize candidates/task_1/worker_3 claude_code_scheduler/cli_tasks.py
```

---

### /retry-until-green [task-description]

Run a single task, retry until QC passes.

**Example:**
```bash
/retry-until-green "Create cli_tasks.py with CRUD operations" --output_path path/to/cli_tasks.py
```

---

### /cleanup

Remove all candidates and reset state.

**Example:**
```bash
/cleanup
```

</details>

<details>
<summary><strong>🔌 REST API (Click to expand)</strong></summary>

### REST API Endpoints

The GUI runs a debug HTTP server on port 5679.

**OpenAPI Spec:** `curl http://127.0.0.1:5679/api/openapi.json`

---

### Read Endpoints

```bash
# Health check
curl http://127.0.0.1:5679/api/health

# Full application state
curl http://127.0.0.1:5679/api/state

# Tasks
curl http://127.0.0.1:5679/api/tasks
curl http://127.0.0.1:5679/api/tasks/{id}

# Runs
curl http://127.0.0.1:5679/api/runs
curl http://127.0.0.1:5679/api/runs/{id}

# Profiles
curl http://127.0.0.1:5679/api/profiles

# Jobs
curl http://127.0.0.1:5679/api/jobs
curl http://127.0.0.1:5679/api/jobs/{id}/tasks

# Scheduler status
curl http://127.0.0.1:5679/api/scheduler
```

---

### Write Endpoints

```bash
# Create task
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"Test","command":"echo hi"}' \
  http://127.0.0.1:5679/api/tasks

# Update task
curl -X PUT -H "Content-Type: application/json" \
  -d '{"name":"Updated"}' \
  http://127.0.0.1:5679/api/tasks/{id}

# Delete task
curl -X DELETE http://127.0.0.1:5679/api/tasks/{id}

# Run task
curl -X POST http://127.0.0.1:5679/api/tasks/{id}/run

# Enable/disable task
curl -X POST http://127.0.0.1:5679/api/tasks/{id}/enable
curl -X POST http://127.0.0.1:5679/api/tasks/{id}/disable

# Stop/restart run
curl -X POST http://127.0.0.1:5679/api/runs/{id}/stop
curl -X POST http://127.0.0.1:5679/api/runs/{id}/restart
```

</details>

<details>
<summary><strong>⚙️ Advanced Features (Click to expand)</strong></summary>

### Multi-Level Verbosity Logging

| Flag | Level | Output | Use Case |
|------|-------|--------|----------|
| (none) | WARNING | Errors and warnings | Production |
| `-v` | INFO | + High-level operations | Normal debugging |
| `-vv` | DEBUG | + Detailed info | Development |
| `-vvv` | TRACE | + Library internals | Deep debugging |

**Examples:**
```bash
claude-code-scheduler gui -v    # INFO
claude-code-scheduler gui -vv   # DEBUG
claude-code-scheduler gui -vvv  # TRACE
```

---

### Environment Profiles

Profiles configure environment variables for different API backends.

**ZAI Profile Example:**
```json
{
  "name": "ZAI",
  "env_vars": [
    {"name": "ANTHROPIC_AUTH_TOKEN", "source": "keychain", "value": "zai-api-key"},
    {"name": "ANTHROPIC_BASE_URL", "source": "static", "value": "https://api.z.ai/api/anthropic"},
    {"name": "CLAUDE_CODE_USE_BEDROCK", "source": "static", "value": "0"}
  ]
}
```

**Important:** Set `CLAUDE_CODE_USE_BEDROCK=0` for Z.AI profiles to avoid auth conflicts.

---

### Data File Locations

```
~/.claude-scheduler/
├── jobs.json        # Job configurations
├── tasks.json       # Task configurations
├── runs.json        # Execution history
├── profiles.json    # Environment profiles
├── settings.json    # Application settings
└── logs/
    └── run_<uuid>.log   # Per-run output logs
```

---

### Pipeline Composition

```bash
# Get task IDs as JSON
claude-code-scheduler cli tasks list --output json | jq '.[].id'

# Check health and extract status
claude-code-scheduler cli health | jq '.status'

# List tasks in a job
claude-code-scheduler cli jobs tasks abc123 --output json | jq '.[].name'
```

</details>

<details>
<summary><strong>🔧 Troubleshooting (Click to expand)</strong></summary>

### Common Issues

**Issue: Workers not starting**
```bash
# Check scheduler is running
curl http://127.0.0.1:5679/api/health

# Check ZAI profile exists
curl http://127.0.0.1:5679/api/profiles
```

**Issue: Z.AI / GLM Profile not working**

Ensure `CLAUDE_CODE_USE_BEDROCK=0` is set in the profile. Bedrock env var overrides Z.AI auth.

**Issue: All candidates fail QC**
1. Review the prompt - is it clear enough?
2. Check CLAUDE.md conventions
3. Try `/retry-until-green` with more specific instructions

**Issue: Port already in use**
```bash
# Check what's using port 5679
lsof -i :5679

# Kill process
lsof -ti:5679 | xargs kill -9
```

**Issue: Command not found**
```bash
# Verify installation
claude-code-scheduler --version

# Reinstall
uv tool install . --reinstall
```

### Debug Mode

In GUI Settings or `settings.json`:
- `mock_mode: true` - Simulate execution (no real Claude calls)
- `unmask_env_vars: true` - Show full env var values in logs

### Getting Help

```bash
# Show help
claude-code-scheduler --help

# Command-specific help
claude-code-scheduler cli tasks --help
claude-code-scheduler debug --help
```

</details>

## Exit Codes

- `0`: Success
- `1`: Client error (invalid arguments, validation failed)
- `2`: Server error (API error, network issue)
- `3`: Network error (connection failed, timeout)

## Best Practices

1. **Clear task boundaries**: Define specific, focused tasks rather than broad ones
2. **Explicit output paths**: Tell workers exactly where to write files
3. **Include context**: Workers are isolated - provide reference files in prompts
4. **Use sequential when needed**: Mark dependent tasks with `depends_on`
5. **Automate QC**: Use lint/typecheck for objective quality assessment
6. **Start with `/plan`**: Let the planner interview you for complex features

## Resources

- **GitHub**: https://github.com/dnvriend/claude-code-scheduler
- **Data Location**: `~/.claude-scheduler/`
- **Default API Port**: 5679
