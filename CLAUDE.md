# claude-code-scheduler - Project Specification

## Goal

Claude Code Scheduler

## What is claude-code-scheduler?

`claude-code-scheduler` is a GUI application and CLI tool for scheduling and managing Claude Code CLI sessions. It provides a PyQt6-based GUI with a REST API for external control.

## Data Model Hierarchy

```
Job (1) → Task (many) → Run (many)
```

- **Job**: Container for related tasks (e.g., "Daily Maintenance")
- **Task**: A scheduled Claude Code command with configuration
- **Run**: An execution record of a task

## Technical Requirements

### Runtime

- Python 3.14+
- Installable globally with mise
- Cross-platform (macOS, Linux, Windows)

### Dependencies

- `click` - CLI framework
- `PyQt6` - GUI framework
- `apscheduler` - Task scheduling
- `watchdog` - File system monitoring
- `croniter` - Cron expression parsing
- `pydantic` - Data validation
- `boto3` - AWS SDK (for distributed mode)
- `aiohttp` / `httpx` - HTTP client
- `tabulate` - CLI table output
- `opentelemetry-*` - Observability

### Development Dependencies

- `ruff` - Linting and formatting
- `mypy` - Type checking
- `pytest` - Testing framework
- `bandit` - Security linting
- `pip-audit` - Dependency vulnerability scanning
- `gitleaks` - Secret detection (requires separate installation)

## CLI Arguments

```bash
claude-code-scheduler [OPTIONS]
```

### Options

- `-v, --verbose` - Enable verbose output (count flag: -v, -vv, -vvv)
  - `-v` (count=1): INFO level logging
  - `-vv` (count=2): DEBUG level logging
  - `-vvv` (count=3+): TRACE level (includes library internals)
- `--help` / `-h` - Show help message
- `--version` - Show version

## Project Structure

```
claude-code-scheduler/
├── claude_code_scheduler/
│   ├── __init__.py
│   ├── _version.py           # Version info
│   ├── cli.py                # Main CLI entry point (group with subcommands)
│   ├── cli_client.py         # HTTP client for REST API
│   ├── cli_jobs.py           # CLI commands for jobs
│   ├── cli_profiles.py       # CLI commands for profiles
│   ├── cli_runs.py           # CLI commands for runs
│   ├── cli_state.py          # CLI commands for state/health/scheduler
│   ├── cli_tasks.py          # CLI commands for tasks
│   ├── completion.py         # Shell completion command
│   ├── logging_config.py     # Multi-level verbosity logging
│   ├── main.py               # GUI entry point
│   ├── observability.py      # OpenTelemetry integration
│   ├── startup_banner.py     # CLI startup banner
│   ├── utils.py              # Utility functions
│   ├── models/
│   │   ├── __init__.py
│   │   ├── enums.py          # Status enums (RunStatus, JobStatus, etc.)
│   │   ├── job.py            # Job data model
│   │   ├── profile.py        # Profile data model (env var configs)
│   │   ├── run.py            # Run data model (execution records)
│   │   ├── settings.py       # Application settings model
│   │   └── task.py           # Task data model
│   ├── services/
│   │   ├── __init__.py
│   │   ├── debug_server.py   # REST API HTTP server
│   │   ├── env_resolver.py   # Environment variable resolution
│   │   ├── executor.py       # Task execution engine
│   │   ├── file_watcher.py   # File system monitoring
│   │   └── scheduler.py      # APScheduler integration
│   ├── storage/
│   │   ├── __init__.py
│   │   └── config_storage.py # JSON file persistence
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py    # Main application window
│       ├── theme.py          # UI theming
│       ├── dialogs/
│       │   ├── __init__.py
│       │   ├── job_editor_dialog.py
│       │   ├── profile_editor_dialog.py
│       │   └── settings_dialog.py
│       ├── panels/
│       │   ├── __init__.py
│       │   ├── jobs_panel.py       # Jobs list panel
│       │   ├── logs_panel.py       # Log viewer panel
│       │   ├── runs_panel.py       # Runs list panel
│       │   ├── task_editor_panel.py # Task configuration
│       │   └── task_list_panel.py  # Task list panel
│       └── widgets/
│           ├── __init__.py
│           ├── advanced_options_panel.py
│           ├── calendar_schedule_panel.py
│           ├── collapsible_widget.py
│           ├── command_type_selector.py
│           ├── file_watch_schedule_panel.py
│           ├── interval_schedule_panel.py
│           ├── job_item.py
│           ├── run_item.py
│           ├── schedule_type_selector.py
│           └── task_item.py
├── tests/
│   ├── __init__.py
│   └── test_*.py
├── pyproject.toml        # Project configuration
├── README.md             # User documentation
├── CLAUDE.md             # This file
├── Makefile              # Development commands
├── LICENSE               # MIT License
├── .mise.toml            # mise configuration
├── .gitleaks.toml        # Gitleaks configuration
└── .gitignore
```

## Code Style

- Type hints for all functions
- Docstrings for all public functions
- Follow PEP 8 via ruff
- 100 character line length
- Strict mypy checking

## Development Workflow

```bash
# Install dependencies
make install

# Run linting
make lint

# Format code
make format

# Type check
make typecheck

# Run tests
make test

# Security scanning
make security-bandit       # Python security linting
make security-pip-audit    # Dependency CVE scanning
make security-gitleaks     # Secret detection
make security              # Run all security checks

# Run all checks (includes security)
make check

# Full pipeline (includes security)
make pipeline
```

## Security

The template includes three lightweight security tools:

1. **bandit** - Python code security linting
   - Detects: SQL injection, hardcoded secrets, unsafe functions
   - Speed: ~2-3 seconds

2. **pip-audit** - Dependency vulnerability scanning
   - Detects: Known CVEs in dependencies
   - Speed: ~2-3 seconds

3. **gitleaks** - Secret and API key detection
   - Detects: AWS keys, GitHub tokens, API keys, private keys
   - Speed: ~1 second
   - Requires: `brew install gitleaks` (macOS)

All security checks run automatically in `make check` and `make pipeline`.

## Multi-Level Verbosity Logging

The template includes a centralized logging system with progressive verbosity levels.

### Implementation Pattern

1. **logging_config.py** - Centralized logging configuration
   - `setup_logging(verbose_count)` - Configure logging based on -v count
   - `get_logger(name)` - Get logger instance for module
   - Maps verbosity to Python logging levels (WARNING/INFO/DEBUG)

2. **CLI Integration** - Add to every CLI command
   ```python
   from claude_code_scheduler.logging_config import get_logger, setup_logging

   logger = get_logger(__name__)

   @click.command()
   @click.option("-v", "--verbose", count=True, help="...")
   def command(verbose: int):
       setup_logging(verbose)  # First thing in command
       logger.info("Operation started")
       logger.debug("Detailed info")
   ```

3. **Logging Levels**
   - **0 (no -v)**: WARNING only - production/quiet mode
   - **1 (-v)**: INFO - high-level operations
   - **2 (-vv)**: DEBUG - detailed debugging
   - **3+ (-vvv)**: TRACE - enable library internals

4. **Best Practices**
   - Always log to stderr (keeps stdout clean for piping)
   - Use structured messages with placeholders: `logger.info("Found %d items", count)`
   - Call `setup_logging()` first in every command
   - Use `get_logger(__name__)` at module level
   - For TRACE level, enable third-party library loggers in `logging_config.py`

5. **Customizing Library Logging**
   Edit `logging_config.py` to add project-specific libraries:
   ```python
   if verbose_count >= 3:
       logging.getLogger("requests").setLevel(logging.DEBUG)
       logging.getLogger("urllib3").setLevel(logging.DEBUG)
   ```

## Shell Completion

The template includes shell completion for bash, zsh, and fish following the Click Shell Completion Pattern.

### Implementation

1. **completion.py** - Separate module for completion command
   - Uses Click's `BashComplete`, `ZshComplete`, `FishComplete` classes
   - Generates shell-specific completion scripts
   - Includes installation instructions in help text

2. **CLI Integration** - Added as subcommand
   ```python
   from claude_code_scheduler.completion import completion_command

   @click.group(invoke_without_command=True)
   def main(ctx: click.Context):
       # Default behavior when no subcommand
       if ctx.invoked_subcommand is None:
           # Main command logic here
           pass

   # Add completion subcommand
   main.add_command(completion_command)
   ```

3. **Usage Pattern** - User-friendly command
   ```bash
   # Generate completion script
   claude-code-scheduler completion bash
   claude-code-scheduler completion zsh
   claude-code-scheduler completion fish

   # Install (eval or save to file)
   eval "$(claude-code-scheduler completion bash)"
   ```

4. **Supported Shells**
   - **Bash** (≥ 4.4) - Uses bash-completion
   - **Zsh** (any recent) - Uses zsh completion system
   - **Fish** (≥ 3.0) - Uses fish completion system
   - **PowerShell** - Not supported by Click

5. **Installation Methods**
   - **Temporary**: `eval "$(claude-code-scheduler completion bash)"`
   - **Permanent**: Add eval to ~/.bashrc or ~/.zshrc
   - **File-based** (recommended): Save to dedicated completion file

### Adding More Commands

The CLI uses `@click.group()` for extensibility. To add new commands:

1. Create new command module in `claude_code_scheduler/`
2. Import and add to CLI group:
   ```python
   from claude_code_scheduler.new_command import new_command
   main.add_command(new_command)
   ```

3. Completion will automatically work for new commands and their options

## Port Administration

See [PORTS.md](PORTS.md) for complete port allocation and administration.

**Quick Reference:**
- **Port 5679**: GUI debug server (`claude-code-scheduler gui --restport 5679`)
- **Port 8787**: Daemon HTTP API (`claude-code-scheduler daemon --api-port 8787`)

**Check port conflicts:**
```bash
lsof -i :8787  # Check daemon port
lsof -i :5679  # Check GUI debug port

# Kill processes using ports
lsof -ti:8787 | xargs kill -9
lsof -ti:5679 | xargs kill -9
```

**Reserved port ranges:** 5679-5689, 8787-8797 (for multi-environment testing)

## CLI Commands

The CLI is organized into command groups for managing different resources via the REST API.

### Main Commands

```bash
claude-code-scheduler gui              # Launch the GUI application
claude-code-scheduler completion bash  # Generate shell completion
claude-code-scheduler debug <cmd>      # Debug/inspection commands (see below)
claude-code-scheduler cli <cmd>        # REST API client commands (see below)
```

### CLI Group (REST API Client)

These commands talk to the running GUI via its REST API (default: http://127.0.0.1:5679).

```bash
# Tasks management
claude-code-scheduler cli tasks list              # List all tasks
claude-code-scheduler cli tasks list --output table
claude-code-scheduler cli tasks get <id>          # Get task details
claude-code-scheduler cli tasks create --name "Test" --command "echo hi"
claude-code-scheduler cli tasks update <id> --name "Updated"
claude-code-scheduler cli tasks delete <id>
claude-code-scheduler cli tasks run <id>          # Run task now
claude-code-scheduler cli tasks enable <id>
claude-code-scheduler cli tasks disable <id>

# Runs management
claude-code-scheduler cli runs list               # List recent runs
claude-code-scheduler cli runs list --output table
claude-code-scheduler cli runs get <id>           # Get run details
claude-code-scheduler cli runs stop <id>          # Stop running task
claude-code-scheduler cli runs restart <id>       # Restart task
claude-code-scheduler cli runs delete <id>        # Delete run record

# Profiles management
claude-code-scheduler cli profiles list           # List all profiles
claude-code-scheduler cli profiles get <id>       # Get profile details
claude-code-scheduler cli profiles create --name "Production"
claude-code-scheduler cli profiles update <id> --name "Updated"
claude-code-scheduler cli profiles delete <id>

# Jobs management
claude-code-scheduler cli jobs list               # List all jobs
claude-code-scheduler cli jobs list --output table
claude-code-scheduler cli jobs get <id>           # Get job details
claude-code-scheduler cli jobs create --name "Daily Maintenance"
claude-code-scheduler cli jobs update <id> --name "Updated"
claude-code-scheduler cli jobs delete <id>
claude-code-scheduler cli jobs tasks <id>         # List tasks in job

# State and health
claude-code-scheduler cli state                   # Full application state
claude-code-scheduler cli health                  # Health check
claude-code-scheduler cli scheduler               # Scheduler status

# Options
claude-code-scheduler cli --api-url http://127.0.0.1:5679 tasks list
claude-code-scheduler cli -v tasks list           # Verbose output
```

## Debug CLI Commands

The scheduler includes comprehensive debug commands for inspecting application state. These commands provide visibility into tasks, runs, profiles, settings, and log files without requiring the GUI.

### Available Commands

```bash
# Complete state dump (tasks, runs, profiles, settings, logs)
claude-code-scheduler debug all

# Task inspection
claude-code-scheduler debug tasks              # List all tasks
claude-code-scheduler debug task <id>          # Full details for specific task

# Run inspection
claude-code-scheduler debug runs               # List recent runs (default: 10)
claude-code-scheduler debug runs -n 20         # List more runs
claude-code-scheduler debug run <id>           # Full details for specific run

# Log inspection
claude-code-scheduler debug logs               # List available log files
claude-code-scheduler debug log <run-id>       # Show log file contents

# Profile inspection
claude-code-scheduler debug profiles           # List all profiles
claude-code-scheduler debug env <profile>      # Resolve and test env vars

# Settings
claude-code-scheduler debug settings           # Show current settings

# Help
claude-code-scheduler debug options            # Show all debug options
```

### GUI Debug Options

```bash
# Launch GUI with verbose logging
claude-code-scheduler gui -v                   # INFO logging
claude-code-scheduler gui -vv                  # DEBUG logging
claude-code-scheduler gui -vvv                 # TRACE logging (all libs)
```

### Debug HTTP Server (REST API)

The GUI automatically starts a debug HTTP server on port 5679. This REST API allows external tools (like Claude Code) to control the live running process.

**OpenAPI Spec:** `curl http://127.0.0.1:5679/api/openapi.json`

#### Read Endpoints

```bash
# API documentation (self-describing)
curl http://127.0.0.1:5679/

# Full application state
curl http://127.0.0.1:5679/api/state

# Health check
curl http://127.0.0.1:5679/api/health

# Tasks
curl http://127.0.0.1:5679/api/tasks           # List all
curl http://127.0.0.1:5679/api/tasks/{id}      # Get single

# Runs
curl http://127.0.0.1:5679/api/runs            # List all
curl http://127.0.0.1:5679/api/runs/{id}       # Get single

# Profiles
curl http://127.0.0.1:5679/api/profiles        # List all
curl http://127.0.0.1:5679/api/profiles/{id}   # Get single

# Jobs
curl http://127.0.0.1:5679/api/jobs            # List all
curl http://127.0.0.1:5679/api/jobs/{id}       # Get single
curl http://127.0.0.1:5679/api/jobs/{id}/tasks # List tasks in job

# Scheduler status
curl http://127.0.0.1:5679/api/scheduler

# UI inspection
curl http://127.0.0.1:5679/api/ui
curl http://127.0.0.1:5679/api/ui/analysis
curl http://127.0.0.1:5679/api/ui/screenshot/task_list
```

#### Write Endpoints

```bash
# Tasks - CRUD
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"Test","command":"echo hi"}' \
  http://127.0.0.1:5679/api/tasks

curl -X PUT -H "Content-Type: application/json" \
  -d '{"name":"Updated"}' \
  http://127.0.0.1:5679/api/tasks/{id}

curl -X DELETE http://127.0.0.1:5679/api/tasks/{id}

# Task actions
curl -X POST http://127.0.0.1:5679/api/tasks/{id}/run
curl -X POST http://127.0.0.1:5679/api/tasks/{id}/enable
curl -X POST http://127.0.0.1:5679/api/tasks/{id}/disable

# Run actions
curl -X POST http://127.0.0.1:5679/api/runs/{id}/stop
curl -X POST http://127.0.0.1:5679/api/runs/{id}/restart
curl -X DELETE http://127.0.0.1:5679/api/runs/{id}

# Profiles - CRUD
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"Production"}' \
  http://127.0.0.1:5679/api/profiles

curl -X PUT -H "Content-Type: application/json" \
  -d '{"name":"Updated"}' \
  http://127.0.0.1:5679/api/profiles/{id}

curl -X DELETE http://127.0.0.1:5679/api/profiles/{id}

# Jobs - CRUD
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"Daily Maintenance"}' \
  http://127.0.0.1:5679/api/jobs

curl -X PUT -H "Content-Type: application/json" \
  -d '{"name":"Updated"}' \
  http://127.0.0.1:5679/api/jobs/{id}

curl -X DELETE http://127.0.0.1:5679/api/jobs/{id}
```

### Data File Locations

```
~/.claude-scheduler/
├── jobs.json        # Job configurations (containers for tasks)
├── tasks.json       # Task configurations
├── runs.json        # Execution history
├── profiles.json    # Environment profiles
├── settings.json    # Application settings
└── logs/
    └── run_<uuid>.log   # Per-run output logs
```

### Debug Settings

In the GUI Settings dialog or `settings.json`:
- `mock_mode: true` - Simulate CLI execution (no real Claude calls)
- `unmask_env_vars: true` - Show full env var values in debug logs

## Troubleshooting

### Z.AI / GLM Profile Not Working

**Symptom:** Task fails with "Invalid API Key format" or authentication errors when using Z.AI profile.

**Cause:** `CLAUDE_CODE_USE_BEDROCK=1` is set in the shell environment, which overrides the Z.AI authentication.

**Solution:** Ensure the Z.AI profile sets `CLAUDE_CODE_USE_BEDROCK=0` (or unsets it entirely).

**Key env vars for Z.AI:**
```bash
ANTHROPIC_AUTH_TOKEN=<z.ai-token>
ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
CLAUDE_CODE_USE_BEDROCK=0  # Must be 0 for Z.AI!
```

### Empty Env Vars Breaking Auth

**Symptom:** Authentication fails even though profile has correct values.

**Cause:** Empty env vars (e.g., `ANTHROPIC_API_KEY=`) override valid auth tokens.

**Solution:** The scheduler now skips empty values automatically. Check logs for `ENV SKIP:` warnings.

## AWS Infrastructure

The project includes Pulumi IaC in `claude-code-scheduler-iac/` for deploying distributed architecture.

### Deployed Resources

```yaml
region              : "eu-central-1"
command_topic_arn   : "arn:aws:sns:eu-central-1:862378407079:claude-code-scheduler-iac-claude-code-scheduler-command-topic"
control_bus_arn     : "arn:aws:sns:eu-central-1:862378407079:claude-code-scheduler-iac-claude-code-scheduler-control-bus"
server_queue_url    : "https://sqs.eu-central-1.amazonaws.com/862378407079/claude-code-scheduler-iac-claude-code-scheduler-server-queue"
node_queue_url      : "https://sqs.eu-central-1.amazonaws.com/862378407079/claude-code-scheduler-iac-claude-code-scheduler-node-queue"
log_bucket_name     : "claude-code-scheduler-iac-claude-code-scheduler-logs"
instance_id         : "i-0c5604d825c172a85"
instance_private_ip : "172.31.20.208"
instance_public_ip  : "35.156.62.7"
```

### Usage with Deployed Infrastructure

```bash
# Start daemon (server/coordinator)
claude-code-scheduler daemon \
  --command-topic arn:aws:sns:eu-central-1:862378407079:claude-code-scheduler-iac-claude-code-scheduler-command-topic \
  --server-queue https://sqs.eu-central-1.amazonaws.com/862378407079/claude-code-scheduler-iac-claude-code-scheduler-server-queue \
  --s3-bucket claude-code-scheduler-iac-claude-code-scheduler-logs

# Start node (worker)
claude-code-scheduler node \
  --command-queue https://sqs.eu-central-1.amazonaws.com/862378407079/claude-code-scheduler-iac-claude-code-scheduler-node-queue \
  --control-bus arn:aws:sns:eu-central-1:862378407079:claude-code-scheduler-iac-claude-code-scheduler-control-bus \
  --s3-bucket claude-code-scheduler-iac-claude-code-scheduler-logs

# CLI commands (talk to daemon)
claude-code-scheduler cli nodes list
claude-code-scheduler cli stats
```

## Installation Methods

### Global installation with mise

```bash
cd /path/to/claude-code-scheduler
mise use -g python@3.14
uv sync
uv tool install .
```

After installation, `claude-code-scheduler` command is available globally.

### Local development

```bash
uv sync
uv run claude-code-scheduler [args]
```
- always do a `make pipeline` and fix issues at the end of making code changes

## Agentic Coding Patterns

See [HOW_TO_USE.md](HOW_TO_USE.md) for comprehensive documentation on the redundant worker patterns.

### Quick Reference

```bash
# Plan a feature (interview + Job→Task breakdown)
/plan "Add dark mode toggle"

# Execute with parallel workers
/orchestrate job.json

# Quality check candidates
/qc candidates/task_1/

# Select winner and cleanup
/finalize candidates/task_1/worker_3 path/to/output.py

# Retry until QC passes
/retry-until-green "Create cli_jobs.py..." --output_path path/to/cli_jobs.py

# Cleanup failed orchestration
/cleanup
```

### Directory Structure

```
.claude/
├── commands/           # Slash commands
│   ├── plan.md         # /plan - Create Job→Task breakdown
│   ├── orchestrate.md  # /orchestrate - Run parallel workers
│   ├── qc.md           # /qc - Quality check candidates
│   ├── finalize.md     # /finalize - Select winner, cleanup
│   ├── retry-until-green.md  # /retry-until-green - Retry until pass
│   └── cleanup.md      # /cleanup - Reset state
└── agents/             # Agent configurations
    ├── planner.md      # Strategic planning (Sonnet)
    ├── worker.md       # Implementation (ZAI/GLM)
    └── qc.md           # Quality control (Sonnet)
```

### Key Concepts

- **Job**: Container for related tasks
- **Task**: A single implementation unit
- **Worker**: An AI agent executing a task (3 workers per task by default)
- **Candidate**: Output from a worker (candidates/ directory)
- **QC**: Quality control (lint, typecheck, scoring)

### When to Use

| Pattern | Use Case |
|---------|----------|
| `/plan` + `/orchestrate` | Complex features with multiple files |
| `/retry-until-green` | Single file with clear success criteria |
| `/qc` + `/finalize` | Manual candidate selection |

## Settings

- ZAI Profile ID: `5270805b-3731-41da-8710-fe765f2e58be`
- branch to make a git worktree from: `main`
- scheduler url: `http://127.0.0.1:5679`
- Worktree name start with the name `feature-<kebabcase-slug>`
- Job name format: `Feature: <kebabcase-slug>`
- Tasks name format: `Task #: <kebabcase-slug>`
- Task permission: `bypass`
- Task schedule: `sequential`
- Session mode: `new`

# Creating Jobs with Tasks
When you create a list of tasks, always end with the following tasks:

1. Run linting and fix all issues
2. Run `make pipeline` and fix all issues
3. Update README.md with usage documentation

