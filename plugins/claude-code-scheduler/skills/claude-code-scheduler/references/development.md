# Development Reference

## Technical Requirements

### Runtime
- Python 3.14+
- Installable globally with mise
- Cross-platform (macOS, Linux, Windows)

### Dependencies

**Runtime:**
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

**Development:**
- `ruff` - Linting and formatting
- `mypy` - Type checking
- `pytest` - Testing framework
- `bandit` - Security linting
- `pip-audit` - Dependency vulnerability scanning
- `gitleaks` - Secret detection

## Project Structure

```
claude-code-scheduler/
├── claude_code_scheduler/
│   ├── __init__.py
│   ├── _version.py           # Version info
│   ├── cli.py                # Main CLI entry point
│   ├── cli_client.py         # HTTP client for REST API
│   ├── cli_jobs.py           # CLI commands for jobs
│   ├── cli_profiles.py       # CLI commands for profiles
│   ├── cli_runs.py           # CLI commands for runs
│   ├── cli_state.py          # CLI commands for state/health
│   ├── cli_tasks.py          # CLI commands for tasks
│   ├── completion.py         # Shell completion command
│   ├── logging_config.py     # Multi-level verbosity logging
│   ├── main.py               # GUI entry point
│   ├── observability.py      # OpenTelemetry integration
│   ├── startup_banner.py     # CLI startup banner
│   ├── utils.py              # Utility functions
│   ├── models/
│   │   ├── enums.py          # Status enums
│   │   ├── job.py            # Job data model
│   │   ├── profile.py        # Profile data model
│   │   ├── run.py            # Run data model
│   │   ├── settings.py       # Application settings
│   │   └── task.py           # Task data model
│   ├── services/
│   │   ├── debug_server.py   # REST API HTTP server
│   │   ├── env_resolver.py   # Environment variable resolution
│   │   ├── executor.py       # Task execution engine
│   │   ├── export_service.py # Job export functionality
│   │   ├── file_watcher.py   # File system monitoring
│   │   └── scheduler.py      # APScheduler integration
│   ├── storage/
│   │   └── config_storage.py # JSON file persistence
│   └── ui/
│       ├── main_window.py    # Main application window
│       ├── theme.py          # UI theming
│       ├── dialogs/          # Modal dialogs
│       ├── panels/           # Main UI panels
│       └── widgets/          # Reusable widgets
├── tests/
│   └── test_*.py
├── pyproject.toml
├── Makefile
└── CLAUDE.md
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

## Security Tools

### bandit - Python Code Security
- Detects: SQL injection, hardcoded secrets, unsafe functions
- Speed: ~2-3 seconds

### pip-audit - Dependency Vulnerabilities
- Detects: Known CVEs in dependencies
- Speed: ~2-3 seconds

### gitleaks - Secret Detection
- Detects: AWS keys, GitHub tokens, API keys, private keys
- Speed: ~1 second
- Install: `brew install gitleaks` (macOS)

## Multi-Level Verbosity Logging

### Implementation Pattern

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

### Logging Levels

| Count | Level | Description |
|-------|-------|-------------|
| 0 | WARNING | Production/quiet mode |
| 1 (-v) | INFO | High-level operations |
| 2 (-vv) | DEBUG | Detailed debugging |
| 3+ (-vvv) | TRACE | Library internals |

### Best Practices

- Always log to stderr (keeps stdout clean for piping)
- Use structured messages: `logger.info("Found %d items", count)`
- Call `setup_logging()` first in every command
- Use `get_logger(__name__)` at module level

### Customizing Library Logging

```python
# In logging_config.py
if verbose_count >= 3:
    logging.getLogger("requests").setLevel(logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)
```

## Shell Completion

### Implementation

```python
from claude_code_scheduler.completion import completion_command

@click.group(invoke_without_command=True)
def main(ctx: click.Context):
    if ctx.invoked_subcommand is None:
        pass

main.add_command(completion_command)
```

### Supported Shells

- **Bash** (≥ 4.4) - Uses bash-completion
- **Zsh** (any recent) - Uses zsh completion system
- **Fish** (≥ 3.0) - Uses fish completion system
- **PowerShell** - Not supported by Click

### Installation Methods

```bash
# Temporary
eval "$(claude-code-scheduler completion bash)"

# Permanent (add to ~/.bashrc or ~/.zshrc)
eval "$(claude-code-scheduler completion bash)"

# File-based (recommended)
claude-code-scheduler completion bash > /etc/bash_completion.d/claude-code-scheduler
```

## Adding CLI Commands

```python
# 1. Create new command module
# claude_code_scheduler/cli_new.py

@click.group()
def new():
    """New command group."""
    pass

@new.command("subcommand")
def subcommand():
    """Subcommand description."""
    pass

# 2. Import and add to CLI group
# cli.py
from claude_code_scheduler.cli_new import new
cli.add_command(new)
```

## Installation Methods

### Global Installation (mise)

```bash
cd /path/to/claude-code-scheduler
mise use -g python@3.14
uv sync
uv tool install .
```

### Local Development

```bash
uv sync
uv run claude-code-scheduler [args]
```

## Creating Jobs with Tasks

When creating jobs with tasks, always end with:

1. Run linting and fix all issues
2. Run `make pipeline` and fix all issues
3. Update README.md with usage documentation

## Settings Reference

| Setting | Value |
|---------|-------|
| ZAI Profile ID | `5270805b-3731-41da-8710-fe765f2e58be` |
| Scheduler URL | `http://127.0.0.1:5679` |
| Worktree prefix | `feature-<kebabcase-slug>` |
| Job name format | `Feature: <kebabcase-slug>` |
| Task name format | `Task #: <kebabcase-slug>` |
| Task permission | `bypass` |
| Task schedule | `sequential` |
| Session mode | `new` |
