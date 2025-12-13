"""CLI entry point for claude-code-scheduler.

This module provides the main command-line interface for the scheduler,
including the GUI launcher, debug commands, and REST API client commands.

Key Components:
    - main: Root CLI group with version and help options
    - gui_command: Launches the PyQt6 GUI application
    - debug_group: Inspection commands for tasks, runs, profiles, settings
    - cli_group: REST API client commands for remote control

Dependencies:
    - click: CLI framework with groups and subcommands
    - claude_code_scheduler.cli_*: Subcommand modules (jobs, tasks, runs, profiles)
    - claude_code_scheduler.storage: ConfigStorage for debug commands
    - claude_code_scheduler.logging_config: Multi-level verbosity logging

Related Modules:
    - cli_client: HTTP client for REST API communication
    - cli_jobs, cli_tasks, cli_runs, cli_profiles: Subcommand implementations
    - main: GUI entry point (launched by gui_command)

Example:
    >>> # Launch GUI
    >>> claude-code-scheduler gui -v
    >>> # List tasks via REST API
    >>> claude-code-scheduler cli tasks list
    >>> # Debug inspection
    >>> claude-code-scheduler debug all

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import sys

import click

from claude_code_scheduler._version import __version__
from claude_code_scheduler.cli_jobs import jobs
from claude_code_scheduler.cli_profiles import profiles
from claude_code_scheduler.cli_runs import runs
from claude_code_scheduler.cli_state import health, scheduler, state
from claude_code_scheduler.cli_tasks import tasks
from claude_code_scheduler.completion import completion_command
from claude_code_scheduler.logging_config import get_logger, setup_logging
from claude_code_scheduler.services.headless_server import HeadlessServer
from claude_code_scheduler.startup_banner import log_gui_banner
from claude_code_scheduler.storage import ConfigStorage

logger = get_logger(__name__)


@click.group(invoke_without_command=True)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Enable verbose output (use -v for INFO, -vv for DEBUG, -vvv for TRACE)",
)
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context, verbose: int) -> None:
    """Claude Code Scheduler - Schedule and manage Claude Code CLI sessions.

    Examples:

    \b
        # Launch the GUI application
        claude-code-scheduler gui

    \b
        # Show help
        claude-code-scheduler --help

    \b
        # Show version
        claude-code-scheduler --version
    """
    # Setup logging based on verbosity count
    setup_logging(verbose)

    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@click.command("gui")
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Enable verbose output for GUI logging",
)
@click.option(
    "--restport",
    default=5679,
    type=int,
    help="Port for debug REST API server (default: 5679)",
)
def gui_command(verbose: int, restport: int) -> None:
    """Launch the Claude Code Scheduler GUI application.

    Examples:

    \b
        # Launch GUI (warnings only)
        claude-code-scheduler gui

    \b
        # Launch with INFO logging
        claude-code-scheduler gui -v

    \b
        # Launch with DEBUG logging
        claude-code-scheduler gui -vv

    \b
        # Launch with TRACE logging (includes APScheduler)
        claude-code-scheduler gui -vvv

    \b
    For debugging, use the CLI debug commands:
        claude-code-scheduler debug all       # Full state dump
        claude-code-scheduler debug tasks     # List tasks
        claude-code-scheduler debug runs      # List runs
        claude-code-scheduler debug settings  # Show settings
    """
    setup_logging(verbose)
    log_gui_banner(verbose, restport)

    from claude_code_scheduler.main import main as gui_main

    sys.exit(gui_main(restport=restport))


@click.command("server")
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Enable verbose output for server logging",
)
@click.option(
    "--port",
    "-p",
    default=5679,
    type=int,
    help="Port for REST API server (default: 5679)",
)
@click.option(
    "--workers",
    "-w",
    type=int,
    help="Max parallel job workers (default: from settings, fallback 3)",
)
def server_command(verbose: int, port: int, workers: int | None) -> None:
    """Launch the Claude Code Scheduler headless server.

    The headless server runs without GUI and provides REST API for job management
    and execution. Jobs are executed in parallel using a thread pool.

    Examples:

    \b
        # Launch server with defaults
        claude-code-scheduler server

    \b
        # Launch with custom port and workers
        claude-code-scheduler server --port 8080 --workers 5

    \b
        # Launch with INFO logging
        claude-code-scheduler server -v

    \b
        # Launch with DEBUG logging
        claude-code-scheduler server -vv
    """
    setup_logging(verbose)

    # Load settings for defaults
    storage = ConfigStorage()
    settings = storage.load_settings()
    final_workers = workers if workers is not None else settings.max_concurrent_tasks

    # Print startup banner
    click.echo("=" * 60)
    click.echo("Claude Code Scheduler - Headless Server")
    click.echo("=" * 60)
    click.echo(f"REST API: http://127.0.0.1:{port}")
    click.echo(f"Workers: {final_workers}")
    click.echo("=" * 60)
    click.echo("Press Ctrl+C to stop")
    click.echo()

    # Create and start server
    try:
        server = HeadlessServer(port=port, workers=final_workers)
        server.start()
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Debug command group for inspection
@click.group("debug")
def debug_group() -> None:
    """Debug commands for inspecting scheduler state.

    Examples:

    \b
        # List recent runs
        claude-code-scheduler debug runs

    \b
        # Show log file for a run
        claude-code-scheduler debug log <run-id>

    \b
        # List tasks
        claude-code-scheduler debug tasks

    \b
        # Show settings
        claude-code-scheduler debug settings
    """


@debug_group.command("runs")
@click.option("--limit", "-n", default=10, help="Number of runs to show")
def debug_runs(limit: int) -> None:
    """List recent runs with status."""
    from claude_code_scheduler.storage import ConfigStorage

    storage = ConfigStorage()
    runs = storage.load_runs()

    if not runs:
        click.echo("No runs found.")
        return

    click.echo(f"Recent runs (showing {min(limit, len(runs))} of {len(runs)}):\n")
    for run in runs[:limit]:
        status_icon = {
            "upcoming": "⏳",
            "running": "🔄",
            "success": "✅",
            "failed": "❌",
            "cancelled": "⚪",
        }.get(run.status.value, "❓")
        click.echo(f"  {status_icon} {run.id}")
        click.echo(f"     Task: {run.task_name}")
        click.echo(f"     Status: {run.status.value}")
        click.echo(f"     Scheduled: {run.scheduled_time}")
        if run.start_time:
            click.echo(f"     Started: {run.start_time}")
        if run.end_time:
            click.echo(f"     Ended: {run.end_time}")
        if run.exit_code is not None:
            click.echo(f"     Exit code: {run.exit_code}")
        if run.errors:
            click.echo(f"     Errors: {run.errors[:100]}...")
        click.echo()


@debug_group.command("log")
@click.argument("run_id")
def debug_log(run_id: str) -> None:
    """Show log file contents for a run."""
    from pathlib import Path

    log_dir = Path.home() / ".claude-scheduler" / "logs"
    log_file = log_dir / f"run_{run_id}.log"

    if not log_file.exists():
        click.echo(f"Log file not found: {log_file}")
        click.echo("\nAvailable logs:")
        if log_dir.exists():
            for f in sorted(log_dir.glob("run_*.log"))[-10:]:
                click.echo(f"  {f.stem.replace('run_', '')}")
        return

    click.echo(f"=== Log: {log_file} ===\n")
    click.echo(log_file.read_text())


@debug_group.command("tasks")
def debug_tasks() -> None:
    """List all tasks with configuration."""
    from claude_code_scheduler.storage import ConfigStorage

    storage = ConfigStorage()
    tasks = storage.load_tasks()

    if not tasks:
        click.echo("No tasks found.")
        return

    click.echo(f"Tasks ({len(tasks)}):\n")
    for task in tasks:
        enabled_icon = "✅" if task.enabled else "⚪"
        click.echo(f"  {enabled_icon} {task.name}")
        click.echo(f"     ID: {task.id}")
        click.echo(f"     Model: {task.model}")
        click.echo(f"     Schedule: {task.schedule.schedule_type.value}")
        click.echo(f"     Job ID: {task.job_id or '(none)'}")
        click.echo(f"     Profile: {task.profile or '(none)'}")
        if task.prompt:
            prompt_preview = task.prompt[:60] + "..." if len(task.prompt) > 60 else task.prompt
            click.echo(f"     Prompt: {prompt_preview}")
        click.echo()


@debug_group.command("settings")
def debug_settings() -> None:
    """Show current settings."""
    from claude_code_scheduler.storage import ConfigStorage

    storage = ConfigStorage()
    settings = storage.load_settings()

    click.echo("Settings:\n")
    for key, value in settings.to_dict().items():
        click.echo(f"  {key}: {value}")


@debug_group.command("profiles")
def debug_profiles() -> None:
    """List all profiles with env vars."""
    from claude_code_scheduler.storage import ConfigStorage

    storage = ConfigStorage()
    profiles = storage.load_profiles()

    if not profiles:
        click.echo("No profiles found.")
        return

    click.echo(f"Profiles ({len(profiles)}):\n")
    for profile in profiles:
        click.echo(f"  {profile.name}")
        click.echo(f"     ID: {profile.id}")
        click.echo(f"     Description: {profile.description or '(none)'}")
        click.echo(f"     Env vars: {len(profile.env_vars)}")
        for env_var in profile.env_vars:
            click.echo(f"       - {env_var.name} ({env_var.source.value})")
        click.echo()


@debug_group.command("task")
@click.argument("task_id")
def debug_task(task_id: str) -> None:
    """Show full details for a specific task."""
    from claude_code_scheduler.storage import ConfigStorage

    storage = ConfigStorage()
    tasks = storage.load_tasks()

    task = None
    for t in tasks:
        if str(t.id) == task_id or t.name.lower() == task_id.lower():
            task = t
            break

    if not task:
        click.echo(f"Task not found: {task_id}")
        click.echo("\nAvailable tasks:")
        for t in tasks:
            click.echo(f"  {t.id} - {t.name}")
        return

    click.echo(f"=== Task: {task.name} ===\n")
    click.echo(f"ID: {task.id}")
    click.echo(f"Enabled: {task.enabled}")
    click.echo(f"Model: {task.model}")
    click.echo(f"Permissions: {task.permissions}")
    click.echo(f"Session mode: {task.session_mode}")
    click.echo(f"Job ID: {task.job_id or '(none)'}")
    click.echo(f"Profile: {task.profile or '(none)'}")
    click.echo(f"Last run status: {task.last_run_status or '(never run)'}")
    click.echo(f"\nPrompt:\n{task.prompt or '(no prompt)'}")
    click.echo("\nSchedule:")
    click.echo(f"  Type: {task.schedule.schedule_type.value}")
    if task.schedule.calendar_time:
        click.echo(f"  Time: {task.schedule.calendar_time}")
    if task.schedule.calendar_frequency:
        click.echo(f"  Frequency: {task.schedule.calendar_frequency}")
    if task.schedule.interval_value:
        click.echo(f"  Interval: {task.schedule.interval_value} {task.schedule.interval_unit}")
    if task.schedule.interval_cron:
        click.echo(f"  Cron: {task.schedule.interval_cron}")
    if task.schedule.watch_directory:
        click.echo(f"  Watch dir: {task.schedule.watch_directory}")
    click.echo(f"\nAllowed tools: {task.allowed_tools or '(all)'}")
    click.echo(f"Disallowed tools: {task.disallowed_tools or '(none)'}")


@debug_group.command("run")
@click.argument("run_id")
def debug_run(run_id: str) -> None:
    """Show full details for a specific run."""
    from claude_code_scheduler.storage import ConfigStorage

    storage = ConfigStorage()
    runs = storage.load_runs()

    run = None
    for r in runs:
        if str(r.id).startswith(run_id):
            run = r
            break

    if not run:
        click.echo(f"Run not found: {run_id}")
        return

    click.echo(f"=== Run: {run.id} ===\n")
    click.echo(f"Task: {run.task_name} ({run.task_id})")
    click.echo(f"Status: {run.status.value}")
    click.echo(f"Session ID: {run.session_id or '(none)'}")
    click.echo(f"Scheduled: {run.scheduled_time}")
    click.echo(f"Started: {run.start_time or '(not started)'}")
    click.echo(f"Ended: {run.end_time or '(not ended)'}")
    click.echo(f"Duration: {run.duration or '(unknown)'}")
    click.echo(f"Exit code: {run.exit_code}")
    click.echo(f"\nOutput:\n{run.output or '(no output)'}")
    click.echo(f"\nErrors:\n{run.errors or '(no errors)'}")
    click.echo(f"\nRaw output length: {len(run.raw_output) if run.raw_output else 0} chars")


@debug_group.command("logs")
@click.option("--limit", "-n", default=10, help="Number of logs to show")
def debug_logs(limit: int) -> None:
    """List available log files."""
    from pathlib import Path

    log_dir = Path.home() / ".claude-scheduler" / "logs"

    if not log_dir.exists():
        click.echo(f"Log directory not found: {log_dir}")
        return

    log_files = sorted(log_dir.glob("run_*.log"), key=lambda f: f.stat().st_mtime, reverse=True)

    if not log_files:
        click.echo("No log files found.")
        return

    click.echo(f"Log files (showing {min(limit, len(log_files))} of {len(log_files)}):\n")
    for log_file in log_files[:limit]:
        size = log_file.stat().st_size
        mtime = log_file.stat().st_mtime
        from datetime import datetime

        mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        run_id = log_file.stem.replace("run_", "")
        click.echo(f"  {run_id}")
        click.echo(f"     Size: {size} bytes")
        click.echo(f"     Modified: {mtime_str}")
        click.echo()


@debug_group.command("all")
def debug_all() -> None:
    """Show complete scheduler state (tasks, runs, profiles, settings)."""
    from pathlib import Path

    from claude_code_scheduler.storage import ConfigStorage

    storage = ConfigStorage()

    # Settings
    click.echo("=" * 60)
    click.echo("SETTINGS")
    click.echo("=" * 60)
    settings = storage.load_settings()
    for key, value in settings.to_dict().items():
        click.echo(f"  {key}: {value}")

    # Profiles
    click.echo("\n" + "=" * 60)
    click.echo("PROFILES")
    click.echo("=" * 60)
    profiles = storage.load_profiles()
    for profile in profiles:
        click.echo(f"\n  [{profile.name}] ({profile.id})")
        for env_var in profile.env_vars:
            click.echo(f"    - {env_var.name}: {env_var.source.value} = {env_var.value[:20]}...")

    # Tasks
    click.echo("\n" + "=" * 60)
    click.echo("TASKS")
    click.echo("=" * 60)
    tasks = storage.load_tasks()
    for task in tasks:
        enabled = "ON" if task.enabled else "OFF"
        click.echo(f"\n  [{enabled}] {task.name} ({task.id})")
        click.echo(f"    Model: {task.model}, Profile: {task.profile or 'none'}")
        click.echo(f"    Schedule: {task.schedule.schedule_type.value}")
        click.echo(f"    Job ID: {task.job_id or 'none'}")

    # Recent runs
    click.echo("\n" + "=" * 60)
    click.echo("RECENT RUNS (last 5)")
    click.echo("=" * 60)
    runs = storage.load_runs()
    for run in runs[:5]:
        status_icon = {"success": "✅", "failed": "❌", "running": "🔄"}.get(run.status.value, "⚪")
        click.echo(f"\n  {status_icon} {run.task_name}")
        click.echo(f"    ID: {run.id}")
        click.echo(f"    Status: {run.status.value}, Exit: {run.exit_code}")
        click.echo(f"    Time: {run.scheduled_time}")

    # Log files
    click.echo("\n" + "=" * 60)
    click.echo("LOG FILES")
    click.echo("=" * 60)
    log_dir = Path.home() / ".claude-scheduler" / "logs"
    if log_dir.exists():
        log_files = sorted(log_dir.glob("run_*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
        click.echo(f"  Directory: {log_dir}")
        click.echo(f"  Files: {len(log_files)}")
        if log_files:
            total_size = sum(f.stat().st_size for f in log_files)
            click.echo(f"  Total size: {total_size} bytes")
    else:
        click.echo("  No log directory")


@debug_group.command("options")
def debug_options() -> None:
    """Show available debug and development options."""
    click.echo("=== Debug Options ===\n")

    click.echo("CLI Debug Commands:")
    click.echo("  claude-code-scheduler debug all        # Complete state dump")
    click.echo("  claude-code-scheduler debug tasks      # List all tasks")
    click.echo("  claude-code-scheduler debug task <id>  # Full task details")
    click.echo("  claude-code-scheduler debug runs       # List recent runs")
    click.echo("  claude-code-scheduler debug run <id>   # Full run details")
    click.echo("  claude-code-scheduler debug logs       # List log files")
    click.echo("  claude-code-scheduler debug log <id>   # Show log contents")
    click.echo("  claude-code-scheduler debug profiles   # List profiles")
    click.echo("  claude-code-scheduler debug settings   # Show settings")

    click.echo("\nGUI Debug Options:")
    click.echo("  claude-code-scheduler gui -v           # INFO logging")
    click.echo("  claude-code-scheduler gui -vv          # DEBUG logging")
    click.echo("  claude-code-scheduler gui -vvv         # TRACE logging (all libs)")

    click.echo("\nDebug HTTP Server (auto-starts with GUI on port 5679):")
    click.echo("  curl http://127.0.0.1:5679/            # API docs")
    click.echo("  curl http://127.0.0.1:5679/api/state   # Full state")
    click.echo("  curl http://127.0.0.1:5679/api/runs    # Runs")
    click.echo("  curl http://127.0.0.1:5679/api/tasks   # Tasks")
    click.echo("  curl http://127.0.0.1:5679/api/health  # Health check")

    click.echo("\nLog Files:")
    click.echo("  Location: ~/.claude-scheduler/logs/")
    click.echo("  Format: run_<uuid>.log")

    click.echo("\nData Files:")
    click.echo("  ~/.claude-scheduler/tasks.json")
    click.echo("  ~/.claude-scheduler/runs.json")
    click.echo("  ~/.claude-scheduler/profiles.json")
    click.echo("  ~/.claude-scheduler/settings.json")

    click.echo("\nSettings for Debug:")
    click.echo("  mock_mode: true          # Simulate CLI (no real execution)")
    click.echo("  unmask_env_vars: true    # Show full env var values in logs")


@debug_group.command("env")
@click.argument("profile_name")
def debug_env(profile_name: str) -> None:
    """Resolve and show environment variables for a profile."""
    from claude_code_scheduler.services.env_resolver import EnvVarResolver
    from claude_code_scheduler.storage import ConfigStorage

    storage = ConfigStorage()
    profiles = storage.load_profiles()

    profile = None
    for p in profiles:
        if p.name.lower() == profile_name.lower() or str(p.id) == profile_name:
            profile = p
            break

    if not profile:
        click.echo(f"Profile not found: {profile_name}")
        click.echo("\nAvailable profiles:")
        for p in profiles:
            click.echo(f"  {p.name} ({p.id})")
        return

    click.echo(f"=== Resolving env vars for: {profile.name} ===\n")

    resolver = EnvVarResolver()
    for env_var in profile.env_vars:
        click.echo(f"{env_var.name}:")
        click.echo(f"  Source: {env_var.source.value}")
        click.echo(f"  Config: {env_var.value}")
        try:
            resolved = resolver.resolve_env_var(env_var)
            if resolved:
                # Mask for security
                masked = resolved[:8] + "****" if len(resolved) > 8 else "****"
                click.echo(f"  Resolved: {masked} ({len(resolved)} chars)")
            else:
                click.echo("  Resolved: (failed to resolve)")
        except Exception as e:
            click.echo(f"  Error: {e}")
        click.echo()


# CLI command group for API operations
@click.group("cli")
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Enable verbose output (use -v for INFO, -vv for DEBUG)",
)
@click.option(
    "--api-url",
    default="http://127.0.0.1:5679",
    help="Base URL of the scheduler API (default: http://127.0.0.1:5679)",
)
@click.pass_context
def cli_group(ctx: click.Context, verbose: int, api_url: str) -> None:
    """CLI commands for interacting with the scheduler REST API.

    These commands communicate with the running scheduler daemon via its HTTP API.
    Make sure the scheduler GUI is running before using these commands.

    Examples:

    \b
        # List all tasks
        claude-code-scheduler cli tasks list

    \b
        # Get task details
        claude-code-scheduler cli tasks get <task-id>

    \b
        # List recent runs
        claude-code-scheduler cli runs list

    \b
        # Stop a running task
        claude-code-scheduler cli runs stop <run-id>

    \b
        # List profiles
        claude-code-scheduler cli profiles list

    \b
        # Check scheduler health
        claude-code-scheduler cli health

    \b
        # Get full application state
        claude-code-scheduler cli state
    """
    setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url


# Add subgroups to cli
cli_group.add_command(jobs)
cli_group.add_command(tasks)
cli_group.add_command(runs)
cli_group.add_command(profiles)

# Add state commands directly to cli group
cli_group.add_command(state)
cli_group.add_command(health)
cli_group.add_command(scheduler)


# Add subcommands to main
main.add_command(completion_command)
main.add_command(gui_command)
main.add_command(server_command)
main.add_command(debug_group)
main.add_command(cli_group)


if __name__ == "__main__":
    main()
