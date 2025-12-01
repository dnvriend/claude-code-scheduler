# claude-code-scheduler

[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://github.com/python/mypy)
[![AI Generated](https://img.shields.io/badge/AI-Generated-blueviolet.svg)](https://www.anthropic.com/claude)
[![Built with Claude Code](https://img.shields.io/badge/Built_with-Claude_Code-5A67D8.svg)](https://www.anthropic.com/claude/code)

Claude Code Scheduler

## Table of Contents

- [About](#about)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [GUI Application](#gui-application)
- [Debug HTTP Server](#debug-http-server)
- [Debug CLI Commands](#debug-cli-commands)
- [Distributed Node Mode](#distributed-node-mode)
- [Multi-Level Verbosity Logging](#multi-level-verbosity-logging)
- [Shell Completion](#shell-completion)
- [Development](#development)
- [Testing](#testing)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

## About

`claude-code-scheduler` is a Python CLI tool built with modern tooling and best practices.

## Features

- ✅ Type-safe with mypy strict mode
- ✅ Linted with ruff
- ✅ Tested with pytest
- 📊 Multi-level verbosity logging (-v/-vv/-vvv)
- 🐚 Shell completion for bash, zsh, and fish
- 🔒 Security scanning with bandit, pip-audit, and gitleaks
- ✅ Modern Python tooling (uv, mise, click)

## Installation

### Prerequisites

- Python 3.14 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Install from source

```bash
# Clone the repository
git clone https://github.com/dnvriend/claude-code-scheduler.git
cd claude-code-scheduler

# Install globally with uv
uv tool install .
```

### Install with mise (recommended for development)

```bash
cd claude-code-scheduler
mise trust
mise install
uv sync
uv tool install .
```

### Verify installation

```bash
claude-code-scheduler --version
```

## Usage

### Basic Usage

```bash
# Show help
claude-code-scheduler --help

# Run the tool
claude-code-scheduler

# Run with verbose output
claude-code-scheduler -v      # INFO level
claude-code-scheduler -vv     # DEBUG level
claude-code-scheduler -vvv    # TRACE level (includes library internals)
```

## GUI Application

### Launch the GUI

```bash
# Standard launch
claude-code-scheduler gui

# With verbose logging
claude-code-scheduler gui -v      # INFO level
claude-code-scheduler gui -vv     # DEBUG level
claude-code-scheduler gui -vvv    # TRACE level (includes APScheduler)
```

## Debug HTTP Server

The GUI automatically starts a debug HTTP server on port 5679 for live runtime inspection:

```bash
# API documentation (self-describing)
curl http://127.0.0.1:5679/

# Full application state
curl http://127.0.0.1:5679/api/state

# List runs and tasks
curl http://127.0.0.1:5679/api/runs
curl http://127.0.0.1:5679/api/tasks
```

This RESTful API allows external tools to inspect the live running process.

## Debug CLI Commands

The scheduler includes debug commands for inspecting application state from files. These commands provide visibility into tasks, runs, profiles, settings, and logs without requiring the GUI - useful for troubleshooting or when working with Claude Code.

### State Inspection

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
claude-code-scheduler debug profiles           # List all profiles with env vars
claude-code-scheduler debug env <profile>      # Resolve and test env vars

# Settings
claude-code-scheduler debug settings           # Show current settings

# Help
claude-code-scheduler debug options            # Show all debug options
```

### Data File Locations

```
~/.claude-scheduler/
├── tasks.json       # Task configurations
├── runs.json        # Execution history
├── profiles.json    # Environment profiles
├── settings.json    # Application settings
└── logs/
    └── run_<uuid>.log   # Per-run output logs
```

## Distributed Node Mode

The scheduler supports distributed execution via worker nodes that run Claude Code tasks in isolated environments.

### Architecture

```
┌─────────────┐
│   Server    │ (GUI + Control Bus)
│ + Scheduler │
└──────┬──────┘
       │
       │ SNS/SQS
       │
┌──────┴──────────────────┐
│                         │
▼                         ▼
┌───────────┐      ┌───────────┐
│  Node 1   │      │  Node 2   │
│  (Worker) │      │  (Worker) │
└───────────┘      └───────────┘
```

### Node Command

Run a worker node that listens for tasks from the scheduler:

```bash
# Basic node execution
claude-code-scheduler node \
  --queue-url https://sqs.us-east-1.amazonaws.com/123/command-queue \
  --topic-arn arn:aws:sns:us-east-1:123:control-bus \
  --log-bucket my-log-bucket

# With custom node ID and name
claude-code-scheduler node \
  --queue-url <url> \
  --topic-arn <arn> \
  --log-bucket <bucket> \
  --node-id worker-01 \
  --node-name "Production Worker 1"

# With AWS profile and region
claude-code-scheduler node \
  --queue-url <url> \
  --topic-arn <arn> \
  --log-bucket <bucket> \
  --profile production \
  --region us-west-2

# With custom heartbeat interval (default: 30s)
claude-code-scheduler node \
  --queue-url <url> \
  --topic-arn <arn> \
  --log-bucket <bucket> \
  --heartbeat-interval 60

# Mock mode (simulate execution without running Claude CLI)
claude-code-scheduler node \
  --queue-url <url> \
  --topic-arn <arn> \
  --log-bucket <bucket> \
  --mock-mode

# With verbose logging
claude-code-scheduler node <options> -v      # INFO
claude-code-scheduler node <options> -vv     # DEBUG
claude-code-scheduler node <options> -vvv    # TRACE
```

### AWS Infrastructure Requirements

Nodes require the following AWS resources:

1. **SQS Queue** - Command queue for receiving tasks
2. **SNS Topic** - Control bus for publishing events
3. **S3 Bucket** - Storage for task output logs

### Node Lifecycle

1. **Initialization** - Node starts and validates configuration
2. **Registration** - Node registers with control bus (publishes `NodeRegistered` event)
3. **Idle** - Node waits for commands from the queue
4. **Task Execution** - Node receives and executes tasks
5. **Heartbeat** - Node sends periodic heartbeat events
6. **Shutdown** - Node deregisters gracefully on exit

### Node Events

Nodes publish the following events to the control bus:

- `NodeRegistered` - Node startup and registration
- `NodeDeregistered` - Node shutdown
- `NodeHeartbeat` - Periodic health check
- `TaskStarted` - Task execution began
- `TaskOutput` - Task output chunk
- `TaskCompleted` - Task finished successfully
- `TaskFailed` - Task encountered an error

### Environment Variables

Nodes support environment variable configuration:

```bash
# AWS credentials (if not using IAM roles)
export AWS_ACCESS_KEY_ID=<key>
export AWS_SECRET_ACCESS_KEY=<secret>
export AWS_REGION=us-east-1

# Node configuration
export CLAUDE_NODE_QUEUE_URL=<url>
export CLAUDE_NODE_TOPIC_ARN=<arn>
export CLAUDE_NODE_LOG_BUCKET=<bucket>
export CLAUDE_NODE_ID=worker-01
```

### Monitoring

Monitor node health via:

- **Heartbeat events** - Sent every 30 seconds (configurable)
- **AWS CloudWatch** - SQS metrics, SNS delivery stats
- **S3 logs** - Task execution logs in `s3://<bucket>/logs/<run-id>.log`

### Security Considerations

- Nodes require IAM permissions for SQS, SNS, and S3
- Use IAM roles for EC2 instances or ECS tasks
- Enable SQS encryption at rest
- Use VPC endpoints to avoid internet traffic
- Implement least-privilege IAM policies

## Multi-Level Verbosity Logging

The CLI supports progressive verbosity levels for debugging and troubleshooting. All logs output to stderr, keeping stdout clean for data piping.

### Logging Levels

| Flag | Level | Output | Use Case |
|------|-------|--------|----------|
| (none) | WARNING | Errors and warnings only | Production, quiet mode |
| `-v` | INFO | + High-level operations | Normal debugging |
| `-vv` | DEBUG | + Detailed info, full tracebacks | Development, troubleshooting |
| `-vvv` | TRACE | + Library internals | Deep debugging |

### Examples

```bash
# Quiet mode - only errors and warnings
claude-code-scheduler

# INFO - see operations and progress
claude-code-scheduler -v
# Output:
# [INFO] claude-code-scheduler started
# [INFO] claude-code-scheduler completed

# DEBUG - see detailed information
claude-code-scheduler -vv
# Output:
# [INFO] claude-code-scheduler started
# [DEBUG] Running with verbose level: 2
# [INFO] claude-code-scheduler completed

# TRACE - see library internals (configure in logging_config.py)
claude-code-scheduler -vvv
```

### Customizing Library Logging

To enable DEBUG logging for third-party libraries at TRACE level (-vvv), edit `claude_code_scheduler/logging_config.py`:

```python
# Configure dependent library loggers at TRACE level (-vvv)
if verbose_count >= 3:
    logging.getLogger("requests").setLevel(logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)
    # Add your project-specific library loggers here
```

## Shell Completion

The CLI provides native shell completion for bash, zsh, and fish shells.

### Supported Shells

| Shell | Version Requirement | Status |
|-------|-------------------|--------|
| **Bash** | ≥ 4.4 | ✅ Supported |
| **Zsh** | Any recent version | ✅ Supported |
| **Fish** | ≥ 3.0 | ✅ Supported |
| **PowerShell** | Any version | ❌ Not Supported |

### Installation

#### Quick Setup (Temporary)

```bash
# Bash - active for current session only
eval "$(claude-code-scheduler completion bash)"

# Zsh - active for current session only
eval "$(claude-code-scheduler completion zsh)"

# Fish - active for current session only
claude-code-scheduler completion fish | source
```

#### Permanent Setup (Recommended)

```bash
# Bash - add to ~/.bashrc
echo 'eval "$(claude-code-scheduler completion bash)"' >> ~/.bashrc
source ~/.bashrc

# Zsh - add to ~/.zshrc
echo 'eval "$(claude-code-scheduler completion zsh)"' >> ~/.zshrc
source ~/.zshrc

# Fish - save to completions directory
mkdir -p ~/.config/fish/completions
claude-code-scheduler completion fish > ~/.config/fish/completions/claude-code-scheduler.fish
```

#### File-based Installation (Better Performance)

For better shell startup performance, generate completion scripts to files:

```bash
# Bash
claude-code-scheduler completion bash > ~/.claude-code-scheduler-complete.bash
echo 'source ~/.claude-code-scheduler-complete.bash' >> ~/.bashrc

# Zsh
claude-code-scheduler completion zsh > ~/.claude-code-scheduler-complete.zsh
echo 'source ~/.claude-code-scheduler-complete.zsh' >> ~/.zshrc

# Fish (automatic loading from completions directory)
mkdir -p ~/.config/fish/completions
claude-code-scheduler completion fish > ~/.config/fish/completions/claude-code-scheduler.fish
```

### Usage

Once installed, completion works automatically:

```bash
# Tab completion for commands
claude-code-scheduler <TAB>
# Shows: completion

# Tab completion for options
claude-code-scheduler --<TAB>
# Shows: --verbose --version --help

# Tab completion for shell types
claude-code-scheduler completion <TAB>
# Shows: bash zsh fish
```

### Getting Help

```bash
# View completion installation instructions
claude-code-scheduler completion --help
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/dnvriend/claude-code-scheduler.git
cd claude-code-scheduler

# Install dependencies
make install

# Show available commands
make help
```

### Available Make Commands

```bash
make install                 # Install dependencies
make format                  # Format code with ruff
make lint                    # Run linting with ruff
make typecheck               # Run type checking with mypy
make test                    # Run tests with pytest
make security-bandit         # Python security linter
make security-pip-audit      # Dependency vulnerability scanner
make security-gitleaks       # Secret/API key detection
make security                # Run all security checks
make check                   # Run all checks (lint, typecheck, test, security)
make pipeline                # Run full pipeline (format, lint, typecheck, test, security, build, install-global)
make build                   # Build package
make run ARGS="..."          # Run claude-code-scheduler locally
make clean                   # Remove build artifacts
```

### Project Structure

```
claude-code-scheduler/
├── claude_code_scheduler/    # Main package
│   ├── __init__.py
│   ├── cli.py          # CLI entry point
│   └── utils.py        # Utility functions
├── tests/              # Test suite
│   ├── __init__.py
│   └── test_utils.py
├── pyproject.toml      # Project configuration
├── Makefile            # Development commands
├── README.md           # This file
├── LICENSE             # MIT License
└── CLAUDE.md           # Development documentation
```

## Testing

Run the test suite:

```bash
# Run all tests
make test

# Run tests with verbose output
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_utils.py

# Run with coverage
uv run pytest tests/ --cov=claude_code_scheduler
```

## Security

The project includes lightweight security tools providing 80%+ coverage with fast scan times:

### Security Tools

| Tool | Purpose | Speed | Coverage |
|------|---------|-------|----------|
| **bandit** | Python code security linting | ⚡⚡ Fast | SQL injection, hardcoded secrets, unsafe functions |
| **pip-audit** | Dependency vulnerability scanning | ⚡⚡ Fast | Known CVEs in dependencies |
| **gitleaks** | Secret and API key detection | ⚡⚡⚡ Very Fast | Secrets in code and git history |

### Running Security Scans

```bash
# Run all security checks (~5-8 seconds)
make security

# Or run individually
make security-bandit       # Python security linting
make security-pip-audit    # Dependency CVE scanning
make security-gitleaks     # Secret detection
```

### Prerequisites

gitleaks must be installed separately:

```bash
# macOS
brew install gitleaks

# Linux
# See: https://github.com/gitleaks/gitleaks#installation
```

Security checks run automatically in `make check` and `make pipeline`.

### What's Protected

- ✅ AWS credentials (AKIA*, ASIA*, etc.)
- ✅ GitHub tokens (ghp_*, gho_*, etc.)
- ✅ API keys and secrets
- ✅ Private keys
- ✅ Slack tokens
- ✅ 100+ other secret types

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run the full pipeline (`make pipeline`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Write docstrings for public functions
- Format code with `ruff`
- Pass all linting and type checks

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Dennis Vriend**

- GitHub: [@dnvriend](https://github.com/dnvriend)

## Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI framework
- Developed with [uv](https://github.com/astral-sh/uv) for fast Python tooling

---

**Generated with AI**

This project was generated using [Claude Code](https://www.anthropic.com/claude/code), an AI-powered development tool by [Anthropic](https://www.anthropic.com/). Claude Code assisted in creating the project structure, implementation, tests, documentation, and development tooling.

Made with ❤️ using Python 3.14
