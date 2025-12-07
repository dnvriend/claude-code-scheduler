# CLI Commands Reference

## Main Commands

```bash
claude-code-scheduler gui              # Launch GUI application
claude-code-scheduler completion bash  # Generate shell completion
claude-code-scheduler debug <cmd>      # Debug/inspection commands
claude-code-scheduler cli <cmd>        # REST API client commands
```

## CLI Group (REST API Client)

Commands talk to the running GUI via REST API (default: http://127.0.0.1:5679).

### Tasks Management

```bash
# List all tasks
claude-code-scheduler cli tasks list
claude-code-scheduler cli tasks list --output table

# Get task details
claude-code-scheduler cli tasks get <id>

# Create task (use --zai or --bedrock shortcuts)
claude-code-scheduler cli tasks create --name "Test" --prompt "your prompt here" --zai
claude-code-scheduler cli tasks create --name "Task" --prompt "Review code" --bedrock --job <job-id>

# Update task
claude-code-scheduler cli tasks update <id> --name "Updated"

# Delete task
claude-code-scheduler cli tasks delete <id>

# Run task immediately
claude-code-scheduler cli tasks run <id>

# Enable/disable task
claude-code-scheduler cli tasks enable <id>
claude-code-scheduler cli tasks disable <id>
```

### Runs Management

```bash
# List recent runs
claude-code-scheduler cli runs list
claude-code-scheduler cli runs list --output table

# Get run details
claude-code-scheduler cli runs get <id>

# Stop running task
claude-code-scheduler cli runs stop <id>

# Restart task
claude-code-scheduler cli runs restart <id>

# Delete run record
claude-code-scheduler cli runs delete <id>
```

### Jobs Management

```bash
# List all jobs
claude-code-scheduler cli jobs list
claude-code-scheduler cli jobs list --output table

# Get job details
claude-code-scheduler cli jobs get <id>

# Create job
claude-code-scheduler cli jobs create --name "Daily Maintenance"
claude-code-scheduler cli jobs create --name "Feature" --description "Feature work" --working-directory ~/projects

# Update job
claude-code-scheduler cli jobs update <id> --name "Updated"

# Delete job
claude-code-scheduler cli jobs delete <id>

# List tasks in job
claude-code-scheduler cli jobs tasks <id>

# Export job
claude-code-scheduler cli jobs export <id> --out ~/exports/job.json

# Import job
claude-code-scheduler cli jobs import --input ~/exports/job.json
claude-code-scheduler cli jobs import --input ~/exports/job.json --force
```

### Profiles Management

```bash
# List all profiles
claude-code-scheduler cli profiles list

# Get profile details
claude-code-scheduler cli profiles get <id>

# Create profile
claude-code-scheduler cli profiles create --name "Production"

# Update profile
claude-code-scheduler cli profiles update <id> --name "Updated"

# Delete profile
claude-code-scheduler cli profiles delete <id>
```

### State and Health

```bash
# Full application state
claude-code-scheduler cli state

# Health check
claude-code-scheduler cli health

# Scheduler status
claude-code-scheduler cli scheduler
```

### Options

```bash
# Custom API URL
claude-code-scheduler cli --api-url http://127.0.0.1:5680 tasks list

# Verbose output
claude-code-scheduler cli -v tasks list
```

## Debug Commands

Inspect application state without requiring REST API.

```bash
# Complete state dump
claude-code-scheduler debug all

# Task inspection
claude-code-scheduler debug tasks
claude-code-scheduler debug task <id>

# Run inspection
claude-code-scheduler debug runs
claude-code-scheduler debug runs -n 20
claude-code-scheduler debug run <id>

# Log inspection
claude-code-scheduler debug logs
claude-code-scheduler debug log <run-id>

# Profile inspection
claude-code-scheduler debug profiles
claude-code-scheduler debug env <profile>

# Settings
claude-code-scheduler debug settings

# Help
claude-code-scheduler debug options
```

## GUI Command

```bash
# Launch GUI
claude-code-scheduler gui

# With verbose logging
claude-code-scheduler gui -v    # INFO
claude-code-scheduler gui -vv   # DEBUG
claude-code-scheduler gui -vvv  # TRACE

# Custom REST port
claude-code-scheduler gui --restport 5680
```

## Shell Completion

```bash
# Bash
eval "$(claude-code-scheduler completion bash)"

# Zsh
eval "$(claude-code-scheduler completion zsh)"

# Fish
claude-code-scheduler completion fish > ~/.config/fish/completions/claude-code-scheduler.fish
```

## Verbosity Levels

| Flag | Level | Description |
|------|-------|-------------|
| (none) | WARNING | Errors and warnings only |
| `-v` | INFO | High-level operations |
| `-vv` | DEBUG | Detailed debugging |
| `-vvv` | TRACE | Library internals |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Client error (invalid arguments) |
| 2 | Server error (API error) |
| 3 | Network error (connection failed) |

## Pipeline Examples

```bash
# Get task IDs
claude-code-scheduler cli tasks list --output json | jq '.[].id'

# Check health status
claude-code-scheduler cli health | jq '.status'

# List tasks in job
claude-code-scheduler cli jobs tasks abc123 --output json | jq '.[].name'

# Run all enabled tasks in a job
for id in $(claude-code-scheduler cli jobs tasks abc123 --output json | jq -r '.[].id'); do
  claude-code-scheduler cli tasks run $id
done
```
