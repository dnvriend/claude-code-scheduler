---
name: skill-claude-code-scheduler
description: Schedule and manage Claude Code sessions
---

# When to Use

- Schedule and automate Claude Code CLI sessions
- Manage jobs, tasks, runs, and profiles
- Implement redundant worker patterns for AI-assisted coding
- Interact with the scheduler's REST API
- Use agentic coding patterns (/plan, /orchestrate, /qc, /finalize)

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

# Run a job
curl -X POST http://127.0.0.1:5679/api/jobs/{id}/run
```

## Data Model

```
Job (1) → Task (many) → Run (many)
```

- **Job**: Container for related tasks
- **Task**: A scheduled Claude Code command
- **Run**: An execution record

## Key Settings

| Setting | Value |
|---------|-------|
| REST API URL | `http://127.0.0.1:5679` |
| ZAI Profile ID | `5270805b-3731-41da-8710-fe765f2e58be` |
| GUI Port | 5679 |
| Daemon Port | 8787 |

## Data Storage

```
~/.claude-scheduler/
├── jobs.json
├── tasks.json
├── runs.json
├── profiles.json
└── settings.json
```

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
    --name "My Task" --prompt "your prompt here" --zai --job <job-id>

# Use --bedrock for AWS Bedrock profile
claude-code-scheduler cli tasks create \
    --name "My Task" --prompt "your prompt here" --bedrock --job <job-id>
```

### Run Job
```bash
curl -X POST http://127.0.0.1:5679/api/jobs/{id}/run
```

### Agentic Patterns

| Command | Purpose |
|---------|---------|
| `/plan` | Interview user, create Job→Task breakdown |
| `/orchestrate` | Execute job with parallel workers |
| `/qc` | Quality check candidates |
| `/finalize` | Move winner, cleanup |
| `/retry-until-green` | Retry until QC passes |

## References

For detailed information, read these files:

- `{baseDir}/references/data-model.md` - Complete data model and field definitions
- `{baseDir}/references/cli-commands.md` - Full CLI command reference
- `{baseDir}/references/rest-api.md` - REST API endpoints and examples
- `{baseDir}/references/installation.md` - Installation, shell completion, prerequisites
- `{baseDir}/references/development.md` - Development workflow, code style, security
- `{baseDir}/references/troubleshooting.md` - Common issues and solutions
- `{baseDir}/references/aws-infrastructure.md` - AWS IaC with Pulumi
- `{baseDir}/references/distributed-nodes.md` - Worker nodes, SQS/SNS, monitoring
- `{baseDir}/references/agentic-patterns.md` - Redundant worker patterns (/plan, /orchestrate)
