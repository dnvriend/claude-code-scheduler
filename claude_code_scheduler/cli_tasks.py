"""
CLI commands for task management in Claude Code Scheduler.

Provides Click commands for creating, reading, updating, deleting, and managing
tasks through the REST API. Supports table output for listing and JSON output
for detailed operations.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import builtins
import json
from typing import Any, cast

import click
import tabulate

from .cli_client import SchedulerAPIError, SchedulerClient, api_url_option
from .logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def format_duration(seconds: float | None) -> str:
    """Format duration in seconds to human readable string."""
    if seconds is None:
        return "-"
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m{secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h{minutes}m"


def format_timestamp(timestamp: str | None) -> str:
    """Format ISO timestamp to readable string."""
    if not timestamp:
        return "-"
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return timestamp[:16] if timestamp else "-"


def format_task_table(
    tasks: builtins.list[dict[str, Any]],
    runs: builtins.list[dict[str, Any]] | None = None,
) -> str:
    """
    Format tasks as a table with run information.

    Args:
        tasks: List of task dictionaries
        runs: Optional list of run dictionaries to join with tasks

    Returns:
        Formatted table string
    """
    if not tasks:
        return "No tasks found."

    headers = ["Task ID", "Task Name", "Run ID", "Status", "Start Time", "Duration"]
    rows = []

    # Build task_id -> runs mapping
    runs_by_task: dict[str, builtins.list[dict[str, Any]]] = {}
    if runs:
        for run in runs:
            task_id = run.get("task_id", "")
            if task_id not in runs_by_task:
                runs_by_task[task_id] = []
            runs_by_task[task_id].append(run)

        # Sort runs by start_time (oldest first)
        for task_id in runs_by_task:
            runs_by_task[task_id].sort(
                key=lambda r: r.get("start_time") or r.get("scheduled_time") or ""
            )

    for task in tasks:
        task_id = task.get("id", "")
        task_name = (task.get("name") or "")[:25]
        task_runs = runs_by_task.get(task_id, [])

        if task_runs:
            # One row per run
            for run in task_runs:
                rows.append(
                    [
                        task_id[:8],
                        task_name,
                        (run.get("id") or "")[:8],
                        run.get("status", "-"),
                        format_timestamp(run.get("start_time")),
                        format_duration(run.get("duration")),
                    ]
                )
        else:
            # Task with no runs
            rows.append([task_id[:8], task_name, "-", "-", "-", "-"])

    return tabulate.tabulate(rows, headers=headers, tablefmt="grid")


@click.group()
def tasks() -> None:
    """Manage Claude Code Scheduler tasks."""
    pass


@tasks.command()
@api_url_option
@click.option("--table", "-t", "use_table", is_flag=True, help="Output as table")
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def list(api_url: str, use_table: bool, verbose: int) -> None:
    """List all tasks.

    Examples:

    \b
        # List all tasks as JSON (default)
        claude-code-scheduler cli tasks list

    \b
        # List tasks as table (joined with runs)
        claude-code-scheduler cli tasks list --table

    \b
    Output Format:
        JSON (default): Array of task objects with full details
        Table (--table): Task/Run table with one row per run (oldest first)
    """
    setup_logging(verbose)

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Fetching tasks from API")
            response = client.get("/api/tasks")

            if isinstance(response, dict) and "tasks" in response:
                tasks_list = cast(builtins.list[dict[str, Any]], response["tasks"])
            elif isinstance(response, builtins.list):
                tasks_list = cast(builtins.list[dict[str, Any]], response)
            else:
                click.echo(f"Unexpected response format: {response}")
                return

            if use_table:
                # Fetch runs to join with tasks
                logger.debug("Fetching runs from API for table join")
                runs_response = client.get("/api/runs")
                runs_list = runs_response.get("runs", [])

                table_output = format_task_table(tasks_list, runs_list)
                click.echo(table_output)
                if verbose:
                    click.echo(f"\nTotal tasks: {len(tasks_list)}, Total runs: {len(runs_list)}")
            else:
                click.echo(json.dumps(response, indent=2))

    except SchedulerAPIError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.ClickException(str(e))


@tasks.command()
@click.argument("task_id")
@api_url_option
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def get(task_id: str, api_url: str, verbose: int) -> None:
    """Get detailed information about a specific task.

    Args:
        task_id: ID of the task to retrieve

    Examples:

    \b
        # Get task details
        claude-code-scheduler tasks get 12345678-1234-1234-1234-123456789abc

    \b
        # Get task with custom API URL
        claude-code-scheduler tasks get task-id --api-url http://localhost:8080

    \b
    Output Format:
        Returns complete task configuration as JSON including:
        - id: Unique identifier
        - name: Task name
        - prompt: The prompt text for Claude Code
        - model: AI model
        - profile: Environment profile
        - enabled: Whether task is enabled
        - job_id: Associated job (working directory inherited from job)
        - permissions: Task permissions
        - created_at/updated_at: Timestamps
    """
    setup_logging(verbose)

    try:
        with SchedulerClient(api_url) as client:
            logger.debug(f"Fetching task {task_id} from API")
            response = client.get(f"/api/tasks/{task_id}")

            # Pretty print JSON
            click.echo(json.dumps(response, indent=2))

    except SchedulerAPIError as e:
        if e.status_code == 404:
            click.echo(f"Task '{task_id}' not found", err=True)
        else:
            click.echo(f"Error: {e}", err=True)
        raise click.ClickException(str(e))


# Well-known profile IDs for shortcuts
ZAI_PROFILE_ID = "5270805b-3731-41da-8710-fe765f2e58be"
BEDROCK_PROFILE_ID = "9e4eaa7d-ba4e-44c0-861a-712aa75382d1"


@tasks.command()
@click.option("--name", required=True, help="Task name")
@click.option("--prompt", required=True, help="The prompt text for Claude Code")
@click.option("--model", help="AI model to use (default: claude-3-5-sonnet-20241022)")
@click.option("--profile", help="Environment profile ID")
@click.option("--zai", "use_zai", is_flag=True, help="Use ZAI profile (shortcut)")
@click.option("--bedrock", "use_bedrock", is_flag=True, help="Use Bedrock profile (shortcut)")
@click.option("--job", "job_id", help="Job ID to assign task to (inherits working dir)")
@click.option("--permissions", help="Task permissions (comma-separated)")
@click.option("--enabled", is_flag=True, default=True, help="Enable task (default: enabled)")
@click.option(
    "--commit-on-success/--no-commit-on-success",
    default=True,
    help="Commit changes on successful execution (default: enabled)",
)
@api_url_option
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def create(
    name: str,
    prompt: str,
    model: str | None,
    profile: str | None,
    use_zai: bool,
    use_bedrock: bool,
    job_id: str | None,
    permissions: str | None,
    enabled: bool,
    commit_on_success: bool,
    api_url: str,
    verbose: int,
) -> None:
    """Create a new task.

    Working directory is inherited from the assigned Job. To set a working
    directory, first create a Job with the desired directory, then assign
    this task to that job.

    Examples:

    \b
        # Create task with ZAI profile shortcut (recommended)
        claude-code-scheduler tasks create \\
            --name "Code Review" \\
            --prompt "Review the code for security issues" \\
            --zai \\
            --job <job-id>

    \b
        # Create task with Bedrock profile
        claude-code-scheduler tasks create \\
            --name "Code Review" \\
            --prompt "Review the code" \\
            --bedrock \\
            --job <job-id>

    \b
        # Create task with explicit profile
        claude-code-scheduler tasks create \\
            --name "Daily Backup" \\
            --prompt "Create a backup of the database" \\
            --profile <profile-id>

    \b
        # Create task with all options
        claude-code-scheduler tasks create \\
            --name "Code Review" \\
            --prompt "Review code and fix issues" \\
            --model "claude-3-5-sonnet-20241022" \\
            --profile <profile-id> \\
            --job <job-id> \\
            --permissions "bypass" \\
            --enabled \\
            --commit-on-success

    \b
        # List available profiles
        claude-code-scheduler profiles list

    \b
    Output Format:
        Returns created task as JSON with all configuration details
        including the generated task ID.
    """
    setup_logging(verbose)

    # Resolve profile from shortcuts or explicit --profile
    resolved_profile: str | None = profile
    if use_zai and use_bedrock:
        click.echo("Error: Cannot use both --zai and --bedrock. Choose one.", err=True)
        raise click.ClickException("Conflicting profile options")
    elif use_zai:
        resolved_profile = ZAI_PROFILE_ID
        logger.debug("Using ZAI profile shortcut: %s", resolved_profile)
    elif use_bedrock:
        resolved_profile = BEDROCK_PROFILE_ID
        logger.debug("Using Bedrock profile shortcut: %s", resolved_profile)

    if not resolved_profile:
        click.echo("Error: Profile is required. Use --profile <id>, --zai, or --bedrock.", err=True)
        raise click.ClickException("Profile is required")

    # Build task data
    # NOTE: working_directory is inherited from Job, not set on Task
    task_data: dict[str, object] = {
        "name": name,
        "prompt": prompt,
        "enabled": enabled,
        "profile": resolved_profile,
        "commit_on_success": commit_on_success,
    }

    if model:
        task_data["model"] = model
    if job_id:
        task_data["job_id"] = job_id
    if permissions:
        task_data["permissions"] = [p.strip() for p in permissions.split(",")]

    try:
        with SchedulerClient(api_url) as client:
            logger.debug(f"Creating task '{name}'")
            response = client.post("/api/tasks", data=task_data)

            click.echo("Task created successfully!")
            click.echo(json.dumps(response, indent=2))

    except SchedulerAPIError as e:
        click.echo(f"Error creating task: {e}", err=True)
        raise click.ClickException(str(e))


@tasks.command()
@click.argument("task_id")
@click.option("--name", help="Update task name")
@click.option("--prompt", help="Update prompt text")
@click.option("--model", help="Update AI model")
@click.option("--profile", help="Update environment profile")
@click.option("--job", "job_id", help="Assign to job (use 'none' to unassign)")
@click.option("--permissions", help="Update permissions (comma-separated)")
@click.option("--enabled/--disabled", default=None, help="Enable or disable task")
@click.option(
    "--commit-on-success/--no-commit-on-success",
    default=None,
    help="Commit changes on successful execution",
)
@api_url_option
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def update(
    task_id: str,
    name: str | None,
    prompt: str | None,
    model: str | None,
    profile: str | None,
    job_id: str | None,
    permissions: str | None,
    enabled: bool | None,
    commit_on_success: bool | None,
    api_url: str,
    verbose: int,
) -> None:
    """Update an existing task.

    Working directory is inherited from the assigned Job. To change working
    directory, either assign the task to a different job or update the job's
    working directory.

    Args:
        task_id: ID of the task to update

    Examples:

    \b
        # Update task name only
        claude-code-scheduler tasks update task-id --name "New Name"

    \b
        # Update prompt text
        claude-code-scheduler tasks update task-id \\
            --prompt "New prompt for Claude Code"

    \b
        # Assign task to a job (inherits working directory)
        claude-code-scheduler tasks update task-id --job <job-id>

    \b
        # Unassign task from job
        claude-code-scheduler tasks update task-id --job none

    \b
        # Update multiple fields
        claude-code-scheduler tasks update task-id \\
            --prompt "New prompt text" \\
            --model "claude-3-5-sonnet-20241022" \\
            --enabled \\
            --commit-on-success

    \b
        # Disable task and disable auto-commit
        claude-code-scheduler tasks update task-id \\
            --disabled \\
            --no-commit-on-success

    \b
    Output Format:
        Returns updated task as JSON with all current configuration.
    """
    setup_logging(verbose)

    # Build update data with only provided fields
    # NOTE: working_directory is inherited from Job, not set on Task
    update_data: dict[str, Any] = {}

    if name is not None:
        update_data["name"] = name
    if prompt is not None:
        update_data["prompt"] = prompt
    if model is not None:
        update_data["model"] = model
    if profile is not None:
        update_data["profile"] = profile
    if job_id is not None:
        # Allow "none" to unassign from job
        update_data["job_id"] = None if job_id.lower() == "none" else job_id
    if permissions is not None:
        update_data["permissions"] = [p.strip() for p in permissions.split(",")]
    if enabled is not None:
        update_data["enabled"] = enabled
    if commit_on_success is not None:
        update_data["commit_on_success"] = commit_on_success

    if not update_data:
        click.echo("No updates specified. Use --help to see available options.")
        return

    try:
        with SchedulerClient(api_url) as client:
            logger.debug(f"Updating task {task_id}")
            response = client.put(f"/api/tasks/{task_id}", data=update_data)

            click.echo("Task updated successfully!")
            click.echo(json.dumps(response, indent=2))

    except SchedulerAPIError as e:
        if e.status_code == 404:
            click.echo(f"Task '{task_id}' not found", err=True)
        else:
            click.echo(f"Error updating task: {e}", err=True)
        raise click.ClickException(str(e))


@tasks.command()
@click.argument("task_id")
@api_url_option
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def delete(task_id: str, api_url: str, verbose: int) -> None:
    """Delete a task.

    Args:
        task_id: ID of the task to delete

    Examples:

    \b
        # Delete a task
        claude-code-scheduler tasks delete 12345678-1234-1234-1234-123456789abc

    \b
        # Delete with custom API URL
        claude-code-scheduler tasks delete task-id --api-url http://localhost:8080

    \b
    Output Format:
        Confirms deletion with success message.
    """
    setup_logging(verbose)

    try:
        with SchedulerClient(api_url) as client:
            logger.debug(f"Deleting task {task_id}")
            response = client.delete(f"/api/tasks/{task_id}")

            click.echo("Task deleted successfully!")
            if verbose and response:
                click.echo(json.dumps(response, indent=2))

    except SchedulerAPIError as e:
        if e.status_code == 404:
            click.echo(f"Task '{task_id}' not found", err=True)
        else:
            click.echo(f"Error deleting task: {e}", err=True)
        raise click.ClickException(str(e))


@tasks.command()
@click.argument("task_id")
@api_url_option
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def run(task_id: str, api_url: str, verbose: int) -> None:
    """Run a task immediately.

    Args:
        task_id: ID of the task to run

    Examples:

    \b
        # Run a task
        claude-code-scheduler tasks run 12345678-1234-1234-1234-123456789abc

    \b
        # Run with custom API URL
        claude-code-scheduler tasks run task-id --api-url http://localhost:8080

    \b
    Output Format:
        Returns run information as JSON including:
        - run_id: Unique identifier for the execution
        - task_id: ID of the executed task
        - status: Initial run status (usually "running")
        - started_at: Execution start timestamp
    """
    setup_logging(verbose)

    try:
        with SchedulerClient(api_url) as client:
            logger.debug(f"Running task {task_id}")
            response = client.post(f"/api/tasks/{task_id}/run")

            click.echo("Task started successfully!")
            click.echo(json.dumps(response, indent=2))

    except SchedulerAPIError as e:
        if e.status_code == 404:
            click.echo(f"Task '{task_id}' not found", err=True)
        else:
            click.echo(f"Error running task: {e}", err=True)
        raise click.ClickException(str(e))


@tasks.command()
@click.argument("task_id")
@api_url_option
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def enable(task_id: str, api_url: str, verbose: int) -> None:
    """Enable a task.

    Args:
        task_id: ID of the task to enable

    Examples:

    \b
        # Enable a task
        claude-code-scheduler tasks enable 12345678-1234-1234-1234-123456789abc

    \b
        # Enable with custom API URL
        claude-code-scheduler tasks enable task-id --api-url http://localhost:8080

    \b
    Output Format:
        Returns updated task as JSON showing enabled=true status.
    """
    setup_logging(verbose)

    try:
        with SchedulerClient(api_url) as client:
            logger.debug(f"Enabling task {task_id}")
            response = client.post(f"/api/tasks/{task_id}/enable")

            click.echo("Task enabled successfully!")
            click.echo(json.dumps(response, indent=2))

    except SchedulerAPIError as e:
        if e.status_code == 404:
            click.echo(f"Task '{task_id}' not found", err=True)
        else:
            click.echo(f"Error enabling task: {e}", err=True)
        raise click.ClickException(str(e))


@tasks.command()
@click.argument("task_id")
@api_url_option
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def disable(task_id: str, api_url: str, verbose: int) -> None:
    """Disable a task.

    Args:
        task_id: ID of the task to disable

    Examples:

    \b
        # Disable a task
        claude-code-scheduler tasks disable 12345678-1234-1234-1234-123456789abc

    \b
        # Disable with custom API URL
        claude-code-scheduler tasks disable task-id --api-url http://localhost:8080

    \b
    Output Format:
        Returns updated task as JSON showing enabled=false status.
    """
    setup_logging(verbose)

    try:
        with SchedulerClient(api_url) as client:
            logger.debug(f"Disabling task {task_id}")
            response = client.post(f"/api/tasks/{task_id}/disable")

            click.echo("Task disabled successfully!")
            click.echo(json.dumps(response, indent=2))

    except SchedulerAPIError as e:
        if e.status_code == 404:
            click.echo(f"Task '{task_id}' not found", err=True)
        else:
            click.echo(f"Error disabling task: {e}", err=True)
        raise click.ClickException(str(e))
