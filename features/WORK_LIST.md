# CLI Command Implementation Work Plan

## Objective
Create a `cli` command group that exposes all REST API operations as subcommands.

## API Operations to Expose

### Tasks (`cli tasks`)
| Subcommand | HTTP | Endpoint | Description |
|------------|------|----------|-------------|
| `list` | GET | /api/tasks | List all tasks |
| `get <id>` | GET | /api/tasks/{id} | Get task details |
| `create` | POST | /api/tasks | Create new task |
| `update <id>` | PUT | /api/tasks/{id} | Update task |
| `delete <id>` | DELETE | /api/tasks/{id} | Delete task |
| `run <id>` | POST | /api/tasks/{id}/run | Run task immediately |
| `enable <id>` | POST | /api/tasks/{id}/enable | Enable task |
| `disable <id>` | POST | /api/tasks/{id}/disable | Disable task |

### Runs (`cli runs`)
| Subcommand | HTTP | Endpoint | Description |
|------------|------|----------|-------------|
| `list` | GET | /api/runs | List all runs |
| `get <id>` | GET | /api/runs/{id} | Get run details |
| `stop <id>` | POST | /api/runs/{id}/stop | Stop running task |
| `restart <id>` | POST | /api/runs/{id}/restart | Restart run |
| `delete <id>` | DELETE | /api/runs/{id} | Delete run |

### Profiles (`cli profiles`)
| Subcommand | HTTP | Endpoint | Description |
|------------|------|----------|-------------|
| `list` | GET | /api/profiles | List all profiles |
| `get <id>` | GET | /api/profiles/{id} | Get profile details |
| `create` | POST | /api/profiles | Create new profile |
| `update <id>` | PUT | /api/profiles/{id} | Update profile |
| `delete <id>` | DELETE | /api/profiles/{id} | Delete profile |

### State (`cli` root level)
| Subcommand | HTTP | Endpoint | Description |
|------------|------|----------|-------------|
| `state` | GET | /api/state | Full application state |
| `health` | GET | /api/health | Health check |
| `scheduler` | GET | /api/scheduler | Scheduler status |

## Work Breakdown

### Phase 1: Foundation (Sequential)
| # | Task | Status | Worker |
|---|------|--------|--------|
| 1 | Create HTTP client module (`cli_client.py`) | pending | - |

### Phase 2: Command Groups (Parallel after Phase 1)
| # | Task | Status | Worker |
|---|------|--------|--------|
| 2a | Create tasks commands (`cli_tasks.py`) | pending | - |
| 2b | Create runs commands (`cli_runs.py`) | pending | - |
| 2c | Create profiles commands (`cli_profiles.py`) | pending | - |
| 2d | Create state commands (`cli_state.py`) | pending | - |

### Phase 3: Integration (Sequential after Phase 2)
| # | Task | Status | Worker |
|---|------|--------|--------|
| 3 | Integrate all into cli.py as `cli` group | pending | - |

### Phase 4: Quality Control (Sequential after Phase 3)
| # | Task | Status | Worker |
|---|------|--------|--------|
| 4 | QC review - lint, typecheck, test | pending | - |

## Worker Configuration
- **Profile**: ZAI (`5270805b-3731-41da-8710-fe765f2e58be`)
- **Working Directory**: `/Users/dennisvriend/projects/claude-code-scheduler`
- **Permissions**: bypass
- **Schedule**: immediate (single run)

## File Structure
```
claude_code_scheduler/
├── cli.py                 # Main CLI (add 'cli' group)
├── cli_client.py          # HTTP client for API calls (NEW)
├── cli_tasks.py           # Tasks subcommands (NEW)
├── cli_runs.py            # Runs subcommands (NEW)
├── cli_profiles.py        # Profiles subcommands (NEW)
└── cli_state.py           # State/health/scheduler (NEW)
```

## CLI Usage Examples
```bash
# Tasks
claude-code-scheduler cli tasks list
claude-code-scheduler cli tasks get <uuid>
claude-code-scheduler cli tasks create --name "Test" --command "echo hello"
claude-code-scheduler cli tasks run <uuid>

# Runs
claude-code-scheduler cli runs list
claude-code-scheduler cli runs get <uuid>
claude-code-scheduler cli runs stop <uuid>

# Profiles
claude-code-scheduler cli profiles list
claude-code-scheduler cli profiles get <uuid>

# State
claude-code-scheduler cli state
claude-code-scheduler cli health
claude-code-scheduler cli scheduler
```

## Progress Tracking
- [x] Phase 1 complete - cli_client.py created
- [x] Phase 2 complete - All CLI command modules created (tasks, runs, profiles, state)
- [x] Phase 3 complete - Integrated into cli.py as `cli` command group
- [x] Phase 4 complete (QC passed) - lint, typecheck, pipeline all green
