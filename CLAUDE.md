# claude-code-scheduler

GUI application and CLI tool for scheduling and managing Claude Code CLI sessions.

## Quick Start

```bash
# Launch GUI
claude-code-scheduler gui

# Check health
curl http://127.0.0.1:5679/api/health

# List jobs
claude-code-scheduler cli jobs list
```

## Data Model

```
Job (1) → Task (many) → Run (many)
```

## Key Settings

| Setting | Value |
|---------|-------|
| REST API URL | `http://127.0.0.1:5679` |
| ZAI Profile ID | `5270805b-3731-41da-8710-fe765f2e58be` |
| Bedrock Profile ID | `9e4eaa7d-ba4e-44c0-861a-712aa75382d1` |
| GUI Port | 5679 |
| Daemon Port | 8787 |

## Profile Shortcuts

| CLI Flag | Profile | UUID |
|----------|---------|------|
| `--zai` | Z.AI API | `5270805b-3731-41da-8710-fe765f2e58be` |
| `--bedrock` | AWS Bedrock | `9e4eaa7d-ba4e-44c0-861a-712aa75382d1` |

## Common Operations

### Create Job
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"My Job","profile":"5270805b-3731-41da-8710-fe765f2e58be"}' \
  http://127.0.0.1:5679/api/jobs
```

### Create Task
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"job_id":"<uuid>","name":"My Task","prompt":"your prompt here","model":"sonnet"}' \
  http://127.0.0.1:5679/api/tasks
```

### Create Task via CLI (with profile shortcuts)
```bash
# Use --zai for Z.AI profile
claude-code-scheduler cli tasks create \
    --name "My Task" \
    --prompt "your prompt here" \
    --zai \
    --job <job-id>

# Use --bedrock for AWS Bedrock profile
claude-code-scheduler cli tasks create \
    --name "My Task" \
    --prompt "your prompt here" \
    --bedrock \
    --job <job-id>
```

### Run Job
```bash
curl -X POST http://127.0.0.1:5679/api/jobs/{id}/run
```

## Agentic Patterns

| Command | Purpose |
|---------|---------|
| `/plan` | Interview user, create Job→Task breakdown |
| `/orchestrate` | Execute job with parallel workers |
| `/qc` | Quality check candidates |
| `/finalize` | Move winner, cleanup |

## Development

```bash
make install    # Install dependencies
make lint       # Run linting
make typecheck  # Type check
make test       # Run tests
make pipeline   # Full pipeline
```

## Creating Jobs with Tasks

When you create a list of tasks, always end with:
1. Run linting and fix all issues
2. Run `make pipeline` and fix all issues
3. Update README.md with usage documentation

## Job/Task Naming Conventions

- Worktree name: `feature-<kebabcase-slug>`
- Job name format: `Feature: <kebabcase-slug>`
- Tasks name format: `Task #: <kebabcase-slug>`
- Task permission: `bypass`
- Task schedule: `sequential`
- Session mode: `new`

## Detailed References

For comprehensive documentation, see the skill references:

- `plugins/claude-code-scheduler/skills/claude-code-scheduler/references/data-model.md`
- `plugins/claude-code-scheduler/skills/claude-code-scheduler/references/cli-commands.md`
- `plugins/claude-code-scheduler/skills/claude-code-scheduler/references/rest-api.md`
- `plugins/claude-code-scheduler/skills/claude-code-scheduler/references/installation.md`
- `plugins/claude-code-scheduler/skills/claude-code-scheduler/references/development.md`
- `plugins/claude-code-scheduler/skills/claude-code-scheduler/references/troubleshooting.md`
- `plugins/claude-code-scheduler/skills/claude-code-scheduler/references/aws-infrastructure.md`
- `plugins/claude-code-scheduler/skills/claude-code-scheduler/references/distributed-nodes.md`
- `plugins/claude-code-scheduler/skills/claude-code-scheduler/references/agentic-patterns.md`

