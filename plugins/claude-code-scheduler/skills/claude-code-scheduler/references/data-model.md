# Data Model Reference

## Hierarchy

```
Job (1) → Task (many) → Run (many)
```

## Job

Container for related tasks (e.g., "Daily Maintenance").

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| name | string | Job name |
| description | string | Job description |
| status | JobStatus | pending, in_progress, completed, failed |
| profile | UUID | Optional profile ID |
| working_directory | JobWorkingDirectory | Working directory config |
| task_order | list[UUID] | Ordered list of task IDs |
| created_at | datetime | Creation timestamp |
| updated_at | datetime | Last update timestamp |

### JobWorkingDirectory

| Field | Type | Description |
|-------|------|-------------|
| path | string | Directory path |
| use_git_worktree | bool | Use git worktree isolation |
| worktree_name | string | Worktree name |
| worktree_branch | string | Branch to checkout |

## Task

A scheduled Claude Code command with configuration.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| job_id | UUID | Parent job ID |
| name | string | Task name |
| enabled | bool | Task is enabled |
| model | string | Model (sonnet, opus, haiku) |
| profile | UUID | Environment profile ID |
| schedule | ScheduleConfig | Scheduling configuration |
| command_type | string | prompt, slash_command, file |
| command | string | The command/prompt to execute |
| permissions | string | default, bypass |
| session_mode | string | new, continue, resume |
| allowed_tools | list[string] | Allowed tool names |
| disallowed_tools | list[string] | Disallowed tool names |
| retry | RetryConfig | Retry configuration |
| notifications | NotificationConfig | Notification settings |
| created_at | datetime | Creation timestamp |
| updated_at | datetime | Last update timestamp |
| last_run_status | RunStatus | Last run status |

### ScheduleConfig

| Field | Type | Description |
|-------|------|-------------|
| type | ScheduleType | manual, interval, calendar, file_watch, sequential |
| interval_value | int | Interval value (for interval type) |
| interval_type | IntervalType | minutes, hours, days |
| cron_expression | string | Cron expression (for calendar type) |
| watch_path | string | Path to watch (for file_watch type) |
| watch_patterns | list[string] | File patterns to watch |
| timezone | string | Timezone for scheduling |

### RetryConfig

| Field | Type | Description |
|-------|------|-------------|
| max_retries | int | Maximum retry attempts |
| retry_delay | int | Delay between retries (seconds) |

## Run

An execution record of a task.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| task_id | UUID | Parent task ID |
| task_name | string | Task name (snapshot) |
| status | RunStatus | upcoming, running, success, failed, cancelled |
| scheduled_time | datetime | Scheduled start time |
| start_time | datetime | Actual start time |
| end_time | datetime | End time |
| duration | float | Duration in seconds |
| session_id | string | Claude session ID |
| output | string | Processed output |
| raw_output | string | Raw command output |
| errors | list[string] | Error messages |
| exit_code | int | Process exit code |

## Profile

Environment variable configuration.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| name | string | Profile name |
| description | string | Profile description |
| env_vars | list[EnvVar] | Environment variables |
| created_at | datetime | Creation timestamp |
| updated_at | datetime | Last update timestamp |

### EnvVar

| Field | Type | Description |
|-------|------|-------------|
| name | string | Variable name |
| source | EnvVarSource | static, environment, keychain, aws_secrets_manager, aws_ssm, command, unset |
| value | string | Value or reference |
| config | dict | Source-specific config |

## Enums

### JobStatus
- `pending`
- `in_progress`
- `completed`
- `failed`

### RunStatus
- `upcoming`
- `running`
- `success`
- `failed`
- `cancelled`

### ScheduleType
- `manual`
- `interval`
- `calendar`
- `file_watch`
- `sequential`

### IntervalType
- `minutes`
- `hours`
- `days`

### EnvVarSource
- `static` - Fixed value
- `environment` - From shell environment
- `keychain` - macOS Keychain
- `aws_secrets_manager` - AWS Secrets Manager
- `aws_ssm` - AWS SSM Parameter Store
- `command` - Output from shell command
- `unset` - Unset the variable

## Data Storage

Files are stored in `~/.claude-scheduler/`:

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

## Serialization

All models implement `to_dict()` and `from_dict()` for JSON serialization:

```python
# Export
job_dict = job.to_dict()
json_string = json.dumps(job_dict, indent=2)

# Import
job_dict = json.loads(json_string)
job = Job.from_dict(job_dict)
```
