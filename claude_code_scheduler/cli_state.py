"""
CLI commands for interacting with the Claude Code Scheduler state and health API endpoints.

Provides commands to retrieve application state, health status, and scheduler information
from the running daemon's HTTP API.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
import sys
from typing import Any

import click

from .cli_client import SchedulerAPIError, SchedulerClient, api_url_option
from .logging_config import get_logger, setup_logging


def output_json(data: dict[str, Any], pretty: bool = True) -> None:
    """
    Output JSON data to stdout.

    Args:
        data: Dictionary to output as JSON
        pretty: Whether to format with indentation (default: True)
    """
    if pretty:
        json.dump(data, sys.stdout, indent=2, sort_keys=True)
    else:
        json.dump(data, sys.stdout)
    sys.stdout.write("\n")


@click.command()
@api_url_option
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def state(api_url: str, verbose: int) -> None:
    """Get full application state from the scheduler.

    Retrieves the complete application state including tasks, runs, profiles,
    and settings from the running scheduler daemon.

    Examples:

    \b
        # Get full application state
        claude-code-scheduler cli state

    \b
        # Connect to different API URL
        claude-code-scheduler cli state --api-url http://192.168.1.100:5679

    \b
    Output Format:
        Returns JSON with the complete application state structure.
    """
    setup_logging(verbose)
    logger = get_logger(__name__)

    try:
        with SchedulerClient(base_url=api_url) as client:
            if verbose:
                click.echo(f"Connecting to scheduler at {api_url}", err=True)

            state_data = client.get("/api/state")
            output_json(state_data)

            if verbose:
                logger.info("Successfully retrieved application state")

    except SchedulerAPIError as e:
        click.echo(f"Error retrieving state: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@click.command()
@api_url_option
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def health(api_url: str, verbose: int) -> None:
    """Get health status from the scheduler.

    Retrieves the health status of the running scheduler daemon, including
    uptime, version information, and system status.

    Examples:

    \b
        # Check scheduler health
        claude-code-scheduler cli health

    \b
        # Connect to different API URL with verbose output
        claude-code-scheduler cli health --api-url http://192.168.1.100:5679 -v

    \b
    Output Format:
        Returns JSON with health information:
        {"status": "healthy", "uptime": "2h 30m", "version": "1.0.0"}
    """
    setup_logging(verbose)
    logger = get_logger(__name__)

    try:
        with SchedulerClient(base_url=api_url) as client:
            if verbose:
                click.echo(f"Connecting to scheduler at {api_url}", err=True)

            health_data = client.get("/api/health")
            output_json(health_data)

            if verbose:
                logger.info("Successfully retrieved health status")

    except SchedulerAPIError as e:
        click.echo(f"Error retrieving health: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@click.command()
@api_url_option
@click.option("-v", "--verbose", count=True, help="Enable verbose output")
def scheduler(api_url: str, verbose: int) -> None:
    """Get scheduler status and information.

    Retrieves detailed scheduler status including running tasks, queue information,
    and scheduler configuration from the running daemon.

    Examples:

    \b
        # Get scheduler status
        claude-code-scheduler cli scheduler

    \b
        # Connect to different API URL with verbose output
        claude-code-scheduler cli scheduler --api-url http://192.168.1.100:5679 -v

    \b
    Output Format:
        Returns JSON with scheduler status:
        {"status": "running", "active_tasks": 2, "queued_tasks": 0}
    """
    setup_logging(verbose)
    logger = get_logger(__name__)

    try:
        with SchedulerClient(base_url=api_url) as client:
            if verbose:
                click.echo(f"Connecting to scheduler at {api_url}", err=True)

            scheduler_data = client.get("/api/scheduler")
            output_json(scheduler_data)

            if verbose:
                logger.info("Successfully retrieved scheduler status")

    except SchedulerAPIError as e:
        click.echo(f"Error retrieving scheduler status: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


# Export commands for import in cli.py
__all__ = ["state", "health", "scheduler"]
