"""
CLI commands for managing profiles in the Claude Code Scheduler.

Provides a command-line interface for creating, reading, updating, and deleting
profile configurations through the scheduler's REST API.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
import sys

import click
from tabulate import tabulate

from .cli_client import SchedulerAPIError, SchedulerClient, api_url_option
from .logging_config import get_logger, setup_logging

logger = get_logger(__name__)


@click.group()
@click.option("-v", "--verbose", count=True, help="Enable verbose output (use -v, -vv, -vvv)")
@click.pass_context
def profiles(ctx: click.Context, verbose: int) -> None:
    """Manage profile configurations for Claude Code Scheduler.

    Profiles contain environment variable configurations for different Claude Code
    execution environments (AWS Bedrock, Anthropic API, Z.AI, etc.).
    """
    setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@profiles.command()
@api_url_option
@click.option(
    "--output",
    default="json",
    type=click.Choice(["json", "table"]),
    help="Output format (default: json)",
)
@click.pass_context
def list(ctx: click.Context, api_url: str, output: str) -> None:
    """List all profiles.

    Retrieves and displays all configured profiles with their basic information.

    Examples:

    \b
        # List profiles as JSON (default)
        claude-code-scheduler profiles list

    \b
        # List profiles as table
        claude-code-scheduler profiles list --output table

    \b
        # List with custom API URL
        claude-code-scheduler profiles list --api-url http://localhost:8080

    \b
    Output Format:
        JSON: Array of profile objects with id, name, description fields
        Table: Formatted table showing id, name, description columns
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Fetching profiles from %s", api_url)
            response = client.get("/api/profiles")

            if output == "table":
                if not response.get("profiles"):
                    click.echo("No profiles found.")
                    return

                # Format as table
                table_data = []
                for profile in response["profiles"]:
                    table_data.append(
                        [
                            profile.get("id", ""),
                            profile.get("name", ""),
                            profile.get("description", ""),
                        ]
                    )

                headers = ["ID", "Name", "Description"]
                click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
            else:
                # JSON output
                click.echo(json.dumps(response, indent=2))

            logger.info("Retrieved %d profiles", len(response.get("profiles", [])))

    except SchedulerAPIError as e:
        logger.error("Failed to list profiles: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@profiles.command()
@api_url_option
@click.argument("profile_id")
@click.option(
    "--output",
    default="json",
    type=click.Choice(["json", "env"]),
    help="Output format (default: json)",
)
@click.pass_context
def get(ctx: click.Context, api_url: str, profile_id: str, output: str) -> None:
    """Get detailed information about a specific profile.

    Retrieves complete profile configuration including environment variables.

    Examples:

    \b
        # Get profile details as JSON
        claude-code-scheduler profiles get my-profile

    \b
        # Get profile as environment variables
        claude-code-scheduler profiles get my-profile --output env

    \b
    Output Format:
        JSON: Complete profile object with all fields including env_vars
        env: Environment variable assignments (KEY=value format)
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Fetching profile %s from %s", profile_id, api_url)
            response = client.get(f"/api/profiles/{profile_id}")

            if output == "env":
                # Output as environment variables
                # Response is {"success": true, "profile": {..., "env_vars": [...]}}
                profile_data = response.get("profile", response)
                env_vars = profile_data.get("env_vars", [])
                for env_var in env_vars:
                    name = env_var.get("name", "")
                    value = env_var.get("value", "")
                    # Skip empty values
                    if name and value:
                        click.echo(f"{name}={value}")
            else:
                # JSON output
                click.echo(json.dumps(response, indent=2))

            logger.info("Retrieved profile: %s", profile_id)

    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Profile not found: %s", profile_id)
        else:
            logger.error("Failed to get profile: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@profiles.command()
@api_url_option
@click.option("--name", required=True, help="Profile name (required)")
@click.option("--description", help="Profile description")
@click.pass_context
def create(ctx: click.Context, api_url: str, name: str, description: str | None) -> None:
    """Create a new profile.

    Creates a new profile with the specified name and optional description.
    Environment variables can be added later using the update command.

    Examples:

    \b
        # Create basic profile
        claude-code-scheduler profiles create --name my-profile

    \b
        # Create profile with description
        claude-code-scheduler profiles create --name "AWS Bedrock" \\
            --description "Profile for AWS Bedrock Claude access"

    \b
    Output Format:
        Returns JSON with the created profile object including generated id
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    profile_data = {"name": name, "description": description}

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Creating profile: %s", name)
            response = client.post("/api/profiles", data=profile_data)
            click.echo(json.dumps(response, indent=2))
            logger.info("Created profile: %s (ID: %s)", name, response.get("id"))

    except SchedulerAPIError as e:
        logger.error("Failed to create profile: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@profiles.command()
@api_url_option
@click.argument("profile_id")
@click.option("--name", help="New profile name")
@click.option("--description", help="New profile description")
@click.option(
    "--env",
    "env_vars",
    multiple=True,
    help="Set environment variable (format: KEY=VALUE, can be used multiple times)",
)
@click.option(
    "--unset-env",
    "unset_env_vars",
    multiple=True,
    help="Remove environment variable (can be used multiple times)",
)
@click.pass_context
def update(
    ctx: click.Context,
    api_url: str,
    profile_id: str,
    name: str | None,
    description: str | None,
    env_vars: tuple[str, ...],
    unset_env_vars: tuple[str, ...],
) -> None:
    """Update an existing profile.

    Updates profile metadata and environment variables. Only specified fields
    are modified - other fields remain unchanged.

    Examples:

    \b
        # Update profile name
        claude-code-scheduler profiles update my-profile --name "New Name"

    \b
        # Update description
        claude-code-scheduler profiles update my-profile --description "Updated description"

    \b
        # Set environment variables
        claude-code-scheduler profiles update my-profile \\
            --env AWS_REGION=us-east-1 \\
            --env CLAUDE_MODEL=claude-3-sonnet

    \b
        # Remove environment variables
        claude-code-scheduler profiles update my-profile --unset-env OLD_VAR

    \b
    Output Format:
        Returns JSON with the updated profile object
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    # First get current profile to preserve existing data
    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Fetching current profile: %s", profile_id)
            current_profile = client.get(f"/api/profiles/{profile_id}")
    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Profile not found: %s", profile_id)
        else:
            logger.error("Failed to fetch current profile: %s", e)
        sys.exit(1)

    # Prepare update data
    update_data = {}

    if name is not None:
        update_data["name"] = name

    if description is not None:
        update_data["description"] = description

    # Handle environment variables
    current_env_vars = current_profile.get("env_vars", {}).copy()

    # Parse and set new environment variables
    for env_var in env_vars:
        if "=" not in env_var:
            logger.error("Invalid environment variable format: %s (use KEY=VALUE)", env_var)
            sys.exit(1)
        key, value = env_var.split("=", 1)
        current_env_vars[key] = value
        logger.debug("Setting env var: %s", key)

    # Unset specified environment variables
    for env_var in unset_env_vars:
        if env_var in current_env_vars:
            del current_env_vars[env_var]
            logger.debug("Unsetting env var: %s", env_var)

    update_data["env_vars"] = current_env_vars

    if not update_data:
        logger.warning("No updates specified")
        return

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Updating profile: %s", profile_id)
            response = client.put(f"/api/profiles/{profile_id}", data=update_data)
            click.echo(json.dumps(response, indent=2))
            logger.info("Updated profile: %s", profile_id)

    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Profile not found: %s", profile_id)
        else:
            logger.error("Failed to update profile: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@profiles.command()
@api_url_option
@click.argument("profile_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete(ctx: click.Context, api_url: str, profile_id: str, force: bool) -> None:
    """Delete a profile.

    Permanently removes a profile and all its configuration. This action
    cannot be undone.

    Examples:

    \b
        # Delete with confirmation
        claude-code-scheduler profiles delete my-profile

    \b
        # Delete without confirmation
        claude-code-scheduler profiles delete my-profile --force

    \b
    Output Format:
        Returns JSON with deletion confirmation message
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    if not force:
        click.echo(f"Are you sure you want to delete profile '{profile_id}'?", err=True)
        if not click.confirm("This action cannot be undone. Continue?"):
            click.echo("Deletion cancelled.", err=True)
            return

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Deleting profile: %s", profile_id)
            response = client.delete(f"/api/profiles/{profile_id}")
            click.echo(json.dumps(response, indent=2))
            logger.info("Deleted profile: %s", profile_id)

    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Profile not found: %s", profile_id)
        else:
            logger.error("Failed to delete profile: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)
