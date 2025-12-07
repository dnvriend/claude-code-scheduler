# claude-code-scheduler

<p align="center">
  <img src=".github/assets/logo.png" alt="Claude Code Scheduler Logo" width="256">
</p>

[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://github.com/python/mypy)
[![Built with Claude Code](https://img.shields.io/badge/Built_with-Claude_Code-5A67D8.svg)](https://www.anthropic.com/claude/code)

A GUI application and CLI tool that provides scheduling and management for Claude Code CLI sessions with REST API control.

## Features

- **Scheduling**: Manual, interval, calendar, and file-watch triggers
- **Data Model**: Job → Task → Run hierarchy for organized workflows
- **REST API**: External control via HTTP (port 5679)
- **Profiles**: Environment configurations for AWS Bedrock, Z.AI, Anthropic API
- **CLI**: Full management via command line with agent-friendly help
- **Export/Import**: Backup and share job configurations

## Quick Start

```bash
# Install
git clone https://github.com/dnvriend/claude-code-scheduler.git
cd claude-code-scheduler
uv tool install .

# Launch GUI
claude-code-scheduler gui

# Check health
curl http://127.0.0.1:5679/api/health
```

## Data Model

```
Job (1) → Task (many) → Run (many)
```

- **Job**: Container for related tasks with working directory
- **Task**: A Claude Code prompt with profile and schedule
- **Run**: Execution record with status and output

## CLI Commands

```bash
# Jobs
claude-code-scheduler cli jobs list              # List all jobs
claude-code-scheduler cli jobs create --name "Feature" --working-directory ~/projects/repo
claude-code-scheduler cli jobs run <job-id>      # Start sequential execution
claude-code-scheduler cli jobs export <job-id> -o backup.json
claude-code-scheduler cli jobs import -i backup.json

# Tasks (use --zai or --bedrock shortcuts)
claude-code-scheduler cli tasks create \
    --name "Code Review" \
    --prompt "Review code for issues" \
    --zai \
    --job <job-id>

claude-code-scheduler cli tasks list
claude-code-scheduler cli tasks run <task-id>

# Runs
claude-code-scheduler cli runs list
claude-code-scheduler cli runs stop <run-id>

# Profiles
claude-code-scheduler cli profiles list
claude-code-scheduler cli profiles get <profile-id>
```

### Profile Shortcuts

| Shortcut | Profile | Description |
|----------|---------|-------------|
| `--zai` | Z.AI API | Z.AI Claude API access |
| `--bedrock` | AWS Bedrock | AWS Bedrock Claude access |

## Debug Commands

```bash
# File-based inspection (no GUI required)
claude-code-scheduler debug all       # Complete state dump
claude-code-scheduler debug tasks     # List all tasks
claude-code-scheduler debug runs      # Recent runs
claude-code-scheduler debug settings  # Current settings
```

## REST API

```bash
# Health check
curl http://127.0.0.1:5679/api/health

# List resources
curl http://127.0.0.1:5679/api/jobs
curl http://127.0.0.1:5679/api/tasks
curl http://127.0.0.1:5679/api/runs

# Create task
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"Test","prompt":"echo hi","profile":"<profile-id>"}' \
  http://127.0.0.1:5679/api/tasks

# Run job
curl -X POST http://127.0.0.1:5679/api/jobs/{id}/run
```

## Development

```bash
make install    # Install dependencies
make test       # Run tests
make lint       # Run linting
make typecheck  # Type checking
make pipeline   # Full CI pipeline
```

## Data Files

```
~/.claude-scheduler/
├── jobs.json        # Job configurations
├── tasks.json       # Task configurations
├── runs.json        # Execution history
├── profiles.json    # Environment profiles
├── settings.json    # Application settings
└── logs/            # Per-run output logs
```

## License

MIT License - see [LICENSE](LICENSE)

## Author

**Dennis Vriend** - [@dnvriend](https://github.com/dnvriend)

---

Built with [Claude Code](https://www.anthropic.com/claude/code)
