"""
CLI commands for managing runs in Claude Code Scheduler.

Provides commands for listing, viewing, stopping, restarting, and deleting runs
through the scheduler's REST API with proper error handling and JSON output.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import builtins
import json
from datetime import datetime
from typing import Any

import click
import tabulate

from .cli_client import SchedulerAPIError, SchedulerClient, api_url_option
from .logging_config import get_logger, setup_logging

logger = get_logger(__name__)


@click.group()
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
@api_url_option
@click.pass_context
def runs(ctx: click.Context, verbose: int, api_url: str) -> None:
    """
    Manage scheduler runs.

    Commands for interacting with run executions including listing, viewing details,
    stopping, restarting, and deleting runs through the REST API.

    Examples:

    \b
        # List recent runs
        claude-code-scheduler runs list

    \b
        # List more runs with verbose output
        claude-code-scheduler runs list -n 20 -v

    \b
        # Get full details for a specific run
        claude-code-scheduler runs get 12345678-1234-1234-1234-123456789abc

    \b
        # Stop a running run
        claude-code-scheduler runs stop 12345678-1234-1234-1234-123456789abc

    \b
        # Restart a completed run
        claude-code-scheduler runs restart 12345678-1234-1234-1234-123456789abc

    \b
        # Delete a run
        claude-code-scheduler runs delete 12345678-1234-1234-1234-123456789abc
    """
    setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url


def format_duration(seconds: float | None) -> str:
    """
    Format duration in seconds to human readable string.

    Args:
        seconds: Duration in seconds or None

    Returns:
        Formatted duration string
    """
    if seconds is None:
        return "-"

    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_timestamp(timestamp: str | None) -> str:
    """
    Format ISO timestamp to readable string.

    Args:
        timestamp: ISO timestamp string or None

    Returns:
        Formatted timestamp string
    """
    if not timestamp:
        return "-"

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return timestamp


def format_run_table(runs: builtins.list[dict[str, Any]]) -> str:
    """
    Format runs list as a table.

    Args:
        runs: List of run dictionaries

    Returns:
        Formatted table string
    """
    if not runs:
        return "No runs found."

    headers = ["ID", "Task Name", "Status", "Start Time", "Duration"]
    rows = []

    for run in runs:
        # Calculate duration if not provided
        duration = run.get("duration")
        if duration is None and run.get("start_time"):
            try:
                start = datetime.fromisoformat(run["start_time"].replace("Z", "+00:00"))
                if run.get("end_time"):
                    end = datetime.fromisoformat(run["end_time"].replace("Z", "+00:00"))
                    duration = (end - start).total_seconds()
                else:
                    # Run is still active
                    duration = (datetime.now().astimezone() - start).total_seconds()
            except (ValueError, TypeError):
                duration = None

        rows.append(
            [
                run.get("id", "-")[:8] + "..."
                if len(run.get("id", "")) > 8
                else run.get("id", "-"),
                run.get("task_name", "-"),
                run.get("status", "-"),
                format_timestamp(run.get("start_time")),
                format_duration(duration),
            ]
        )

    return tabulate.tabulate(rows, headers=headers, tablefmt="grid")


@runs.command()
@click.option("-n", "--limit", default=10, help="Maximum number of runs to list (default: 10)")
@click.pass_context
def list(ctx: click.Context, limit: int) -> None:
    """
    List recent runs.

    Retrieves a list of runs from the API and displays them in a table format
    with key information including ID, task name, status, start time, and duration.

    Examples:

    \b
        # List default number of runs (10)
        claude-code-scheduler runs list

    \b
        # List more runs
        claude-code-scheduler runs list -n 25

    \b
        # List runs from custom API URL
        claude-code-scheduler runs list --api-url http://localhost:8080
    """
    api_url = ctx.obj["api_url"]

    try:
        with SchedulerClient(api_url) as client:
            logger.debug(f"Fetching runs from API: {api_url}")
            response = client.get("/api/runs")

            runs_list = response.get("runs", [])
            if limit:
                runs_list = runs_list[:limit]

            if runs_list:
                click.echo(format_run_table(runs_list))
                click.echo(f"\nShowing {len(runs_list)} runs")
            else:
                click.echo("No runs found.")

    except SchedulerAPIError as e:
        logger.error(f"Failed to list runs: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.ClickException(str(e))


@runs.command()
@click.argument("run_id")
@click.pass_context
def get(ctx: click.Context, run_id: str) -> None:
    """
    Get full details for a specific run.

    Retrieves complete information about a single run including all configuration,
    execution details, and output logs in JSON format.

    Examples:

    \b
        # Get full details for a run
        claude-code-scheduler runs get 12345678-1234-1234-1234-123456789abc

    \b
        # Get run details from custom API URL
        claude-code-scheduler runs get abc123 --api-url http://localhost:8080
    """
    api_url = ctx.obj["api_url"]

    try:
        with SchedulerClient(api_url) as client:
            logger.debug(f"Fetching run details: {run_id}")
            response = client.get(f"/api/runs/{run_id}")

            # Output full JSON
            click.echo(json.dumps(response, indent=2))

    except SchedulerAPIError as e:
        logger.error(f"Failed to get run {run_id}: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.ClickException(str(e))


@runs.command()
@click.argument("run_id")
@click.pass_context
def stop(ctx: click.Context, run_id: str) -> None:
    """
    Stop a running run.

    Sends a stop signal to interrupt execution of a currently running run.
    The run will be marked as stopped and partial results may be available.

    Examples:

    \b
        # Stop a running run
        claude-code-scheduler runs stop 12345678-1234-1234-1234-123456789abc

    \b
        # Stop run from custom API URL
        claude-code-scheduler runs stop abc123 --api-url http://localhost:8080
    """
    api_url = ctx.obj["api_url"]

    try:
        with SchedulerClient(api_url) as client:
            logger.debug(f"Stopping run: {run_id}")
            response = client.post(f"/api/runs/{run_id}/stop")

            # Output response
            click.echo(json.dumps(response, indent=2))
            click.echo(f"Run {run_id} stop request sent.")

    except SchedulerAPIError as e:
        logger.error(f"Failed to stop run {run_id}: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.ClickException(str(e))


@runs.command()
@click.argument("run_id")
@click.pass_context
def restart(ctx: click.Context, run_id: str) -> None:
    """
    Restart a completed or failed run.

    Creates a new execution of a previously run task using the same configuration
    as the original run. Returns details of the new run instance.

    Examples:

    \b
        # Restart a failed run
        claude-code-scheduler runs restart 12345678-1234-1234-1234-123456789abc

    \b
        # Restart run from custom API URL
        claude-code-scheduler runs restart abc123 --api-url http://localhost:8080
    """
    api_url = ctx.obj["api_url"]

    try:
        with SchedulerClient(api_url) as client:
            logger.debug(f"Restarting run: {run_id}")
            response = client.post(f"/api/runs/{run_id}/restart")

            # Output response
            click.echo(json.dumps(response, indent=2))
            click.echo(f"Run {run_id} restart request sent.")

    except SchedulerAPIError as e:
        logger.error(f"Failed to restart run {run_id}: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.ClickException(str(e))


@runs.command()
@click.argument("run_id")
@click.option("-f", "--force", is_flag=True, help="Force delete without confirmation")
@click.pass_context
def delete(ctx: click.Context, run_id: str, force: bool) -> None:
    """
    Delete a run permanently.

    Removes a run from the system permanently. This action cannot be undone.
    All run data including logs and results will be deleted.

    Examples:

    \b
        # Delete a run (with confirmation)
        claude-code-scheduler runs delete 12345678-1234-1234-1234-123456789abc

    \b
        # Force delete without confirmation
        claude-code-scheduler runs delete abc123 -f

    \b
        # Delete run from custom API URL
        claude-code-scheduler runs delete abc123 --api-url http://localhost:8080
    """
    api_url = ctx.obj["api_url"]

    if not force:
        if not click.confirm(
            f"Are you sure you want to delete run {run_id}? This cannot be undone."
        ):
            click.echo("Delete cancelled.")
            return

    try:
        with SchedulerClient(api_url) as client:
            logger.debug(f"Deleting run: {run_id}")
            response = client.delete(f"/api/runs/{run_id}")

            # Output response
            click.echo(json.dumps(response, indent=2))
            click.echo(f"Run {run_id} deleted successfully.")

    except SchedulerAPIError as e:
        logger.error(f"Failed to delete run {run_id}: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.ClickException(str(e))
