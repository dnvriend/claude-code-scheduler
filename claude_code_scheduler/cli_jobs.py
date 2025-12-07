"""
CLI commands for managing jobs in the Claude Code Scheduler.

A Job is a container for related Tasks, creating a hierarchy:
Job (1) → Task (many) → Run (many)

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import builtins
import json
import os
import sys

import click
from tabulate import tabulate

from .cli_client import SchedulerAPIError, SchedulerClient, api_url_option
from .logging_config import get_logger, setup_logging

logger = get_logger(__name__)


@click.group()
@click.option("-v", "--verbose", count=True, help="Enable verbose output (use -v, -vv, -vvv)")
@click.pass_context
def jobs(ctx: click.Context, verbose: int) -> None:
    """Manage jobs in Claude Code Scheduler.

    Jobs are containers for related tasks. A job groups multiple tasks together
    and provides cascade delete (deleting a job removes all its tasks and runs).
    """
    setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@jobs.command("list")
@api_url_option
@click.option(
    "--output",
    default="json",
    type=click.Choice(["json", "table"]),
    help="Output format (default: json)",
)
@click.pass_context
def list_jobs(ctx: click.Context, api_url: str, output: str) -> None:
    """List all jobs.

    Retrieves and displays all configured jobs with their basic information.

    Examples:

    \b
        # List jobs as JSON (default)
        claude-code-scheduler cli jobs list

    \b
        # List jobs as table
        claude-code-scheduler cli jobs list --output table

    \b
    Output Format:
        JSON: Array of job objects with id, name, description, status fields
        Table: Formatted table showing id, name, status, description columns
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Fetching jobs from %s", api_url)
            response = client.get("/api/jobs")

            if output == "table":
                jobs_list: builtins.list[dict[str, str]] = response.get("jobs", [])
                if not jobs_list:
                    click.echo("No jobs found.")
                    return

                table_data = []
                for job in jobs_list:
                    table_data.append(
                        [
                            job.get("id", "")[:8] + "...",
                            job.get("name", ""),
                            job.get("status", ""),
                            job.get("description", "")[:40],
                        ]
                    )

                headers = ["ID", "Name", "Status", "Description"]
                click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
            else:
                click.echo(json.dumps(response, indent=2))

            logger.info("Retrieved %d jobs", len(response.get("jobs", [])))

    except SchedulerAPIError as e:
        logger.error("Failed to list jobs: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@jobs.command()
@api_url_option
@click.argument("job_id")
@click.pass_context
def get(ctx: click.Context, api_url: str, job_id: str) -> None:
    """Get detailed information about a specific job.

    Retrieves complete job information including status and timestamps.

    Examples:

    \b
        # Get job details
        claude-code-scheduler cli jobs get <job-id>

    \b
    Output Format:
        Returns JSON with complete job object
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Fetching job %s from %s", job_id, api_url)
            response = client.get(f"/api/jobs/{job_id}")
            click.echo(json.dumps(response, indent=2))
            logger.info("Retrieved job: %s", job_id)

    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Job not found: %s", job_id)
        else:
            logger.error("Failed to get job: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@jobs.command()
@api_url_option
@click.option("--name", required=True, help="Job name (required)")
@click.option("--description", default="", help="Job description")
@click.option(
    "--working-directory",
    default="~/projects",
    help="Working directory for all tasks in this job",
)
@click.option(
    "--use-worktree",
    is_flag=True,
    default=False,
    help="Use git worktree for isolation",
)
@click.option(
    "--worktree-name",
    default=None,
    help="Name for the worktree (default: job-{id[:8]})",
)
@click.option(
    "--worktree-branch",
    default=None,
    help="Branch to checkout in worktree",
)
@click.pass_context
def create(
    ctx: click.Context,
    api_url: str,
    name: str,
    description: str,
    working_directory: str,
    use_worktree: bool,
    worktree_name: str | None,
    worktree_branch: str | None,
) -> None:
    """Create a new job.

    Creates a new job with the specified name and optional description.
    Tasks can be assigned to this job after creation.

    Examples:

    \b
        # Create basic job
        claude-code-scheduler cli jobs create --name "Feature Implementation"

    \b
        # Create job with description
        claude-code-scheduler cli jobs create --name "Feature Implementation" \\
            --description "Tasks for implementing the new feature"

    \b
        # Create job with custom working directory
        claude-code-scheduler cli jobs create --name "My Job" \\
            --working-directory ~/projects/my-repo

    \b
        # Create job with git worktree
        claude-code-scheduler cli jobs create --name "Feature Branch" \\
            --working-directory ~/projects/my-repo \\
            --use-worktree --worktree-branch feature-auth

    \b
    Output Format:
        Returns JSON with the created job object including generated id
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    job_data: dict[str, object] = {
        "name": name,
        "description": description,
        "working_directory": {
            "path": working_directory,
            "use_git_worktree": use_worktree,
            "worktree_name": worktree_name,
            "worktree_branch": worktree_branch,
        },
    }

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Creating job: %s", name)
            response = client.post("/api/jobs", data=job_data)
            click.echo(json.dumps(response, indent=2))
            logger.info("Created job: %s", name)

    except SchedulerAPIError as e:
        logger.error("Failed to create job: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@jobs.command()
@api_url_option
@click.argument("job_id")
@click.option("--name", help="New job name")
@click.option("--description", help="New job description")
@click.option(
    "--status",
    type=click.Choice(["pending", "in_progress", "completed", "failed"]),
    help="New job status",
)
@click.option("--working-directory", help="Working directory for tasks")
@click.option("--use-worktree/--no-worktree", default=None, help="Use git worktree")
@click.option("--worktree-name", help="Worktree name")
@click.option("--worktree-branch", help="Worktree branch")
@click.pass_context
def update(
    ctx: click.Context,
    api_url: str,
    job_id: str,
    name: str | None,
    description: str | None,
    status: str | None,
    working_directory: str | None,
    use_worktree: bool | None,
    worktree_name: str | None,
    worktree_branch: str | None,
) -> None:
    """Update an existing job.

    Updates job metadata. Only specified fields are modified.

    Examples:

    \b
        # Update job name
        claude-code-scheduler cli jobs update <job-id> --name "New Name"

    \b
        # Update job status
        claude-code-scheduler cli jobs update <job-id> --status completed

    \b
        # Update multiple fields
        claude-code-scheduler cli jobs update <job-id> \\
            --name "Updated Job" --description "New description"

    \b
        # Update working directory
        claude-code-scheduler cli jobs update <job-id> \\
            --working-directory ~/projects/other-repo

    \b
        # Enable worktree mode
        claude-code-scheduler cli jobs update <job-id> \\
            --use-worktree --worktree-branch feature-x

    \b
    Output Format:
        Returns JSON with the updated job object
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    update_data: dict[str, object] = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if status is not None:
        update_data["status"] = status

    # Handle working directory updates
    wd_update: dict[str, object] = {}
    if working_directory is not None:
        wd_update["path"] = working_directory
    if use_worktree is not None:
        wd_update["use_git_worktree"] = use_worktree
    if worktree_name is not None:
        wd_update["worktree_name"] = worktree_name
    if worktree_branch is not None:
        wd_update["worktree_branch"] = worktree_branch
    if wd_update:
        update_data["working_directory"] = wd_update

    if not update_data:
        logger.warning("No updates specified")
        click.echo("No updates specified. Use --name, --description, or --status.", err=True)
        return

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Updating job: %s", job_id)
            response = client.put(f"/api/jobs/{job_id}", data=update_data)
            click.echo(json.dumps(response, indent=2))
            logger.info("Updated job: %s", job_id)

    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Job not found: %s", job_id)
        else:
            logger.error("Failed to update job: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@jobs.command()
@api_url_option
@click.argument("job_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete(ctx: click.Context, api_url: str, job_id: str, force: bool) -> None:
    """Delete a job and all its tasks/runs (cascade delete).

    Permanently removes a job along with all associated tasks and their runs.
    This action cannot be undone.

    Examples:

    \b
        # Delete with confirmation
        claude-code-scheduler cli jobs delete <job-id>

    \b
        # Delete without confirmation
        claude-code-scheduler cli jobs delete <job-id> --force

    \b
    Output Format:
        Returns JSON with deletion confirmation message
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    if not force:
        click.echo(f"Are you sure you want to delete job '{job_id}'?", err=True)
        click.echo("WARNING: This will also delete ALL tasks and runs in this job!", err=True)
        if not click.confirm("This action cannot be undone. Continue?"):
            click.echo("Deletion cancelled.", err=True)
            return

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Deleting job: %s", job_id)
            response = client.delete(f"/api/jobs/{job_id}")
            click.echo(json.dumps(response, indent=2))
            logger.info("Deleted job: %s", job_id)

    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Job not found: %s", job_id)
        else:
            logger.error("Failed to delete job: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@jobs.command()
@api_url_option
@click.argument("job_id")
@click.pass_context
def run(ctx: click.Context, api_url: str, job_id: str) -> None:
    """Run a job (start sequential task execution).

    Starts the sequential execution of all tasks in the job's task_order.
    Tasks are executed one at a time, waiting for each to complete before
    starting the next.

    Examples:

    \b
        # Start job execution
        claude-code-scheduler cli jobs run <job-id>

    \b
    Output Format:
        Returns JSON with success status and message
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Starting job %s", job_id)
            response = client.post(f"/api/jobs/{job_id}/run")
            click.echo(json.dumps(response, indent=2))
            logger.info("Started job: %s", job_id)

    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Job not found: %s", job_id)
        else:
            logger.error("Failed to run job: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@jobs.command()
@api_url_option
@click.argument("job_id")
@click.pass_context
def stop(ctx: click.Context, api_url: str, job_id: str) -> None:
    """Stop a running job.

    Stops the sequential execution of a job that is currently running.
    The job status will be set to 'failed' and no further tasks will execute.

    Examples:

    \b
        # Stop a running job
        claude-code-scheduler cli jobs stop <job-id>

    \b
    Output Format:
        Returns JSON with success status and message
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Stopping job %s", job_id)
            response = client.post(f"/api/jobs/{job_id}/stop")
            click.echo(json.dumps(response, indent=2))
            logger.info("Stopped job: %s", job_id)

    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Job not found: %s", job_id)
        else:
            logger.error("Failed to stop job: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@jobs.command("set-order")
@api_url_option
@click.argument("job_id", type=click.UUID)
@click.argument("task_ids", nargs=-1, type=click.UUID)
@click.pass_context
def set_order(ctx: click.Context, api_url: str, job_id: str, task_ids: tuple[str, ...]) -> None:
    """Set the task order for a job.

    Updates the task_order field for a job, specifying the sequence in which
    tasks should be executed. Tasks must belong to the job.

    Examples:

    \b
        # Set single task order
        claude-code-scheduler cli jobs set-order <job-id> <task-id>

    \b
        # Set multiple task order
        claude-code-scheduler cli jobs set-order <job-id> \\
            <task-id-1> <task-id-2> <task-id-3>

    \b
        # Reorder tasks in a specific sequence
        claude-code-scheduler cli jobs set-order <job-id> \\
            abc12345-def67-ghi89-jkl01-mno23-pqr45 \\
            stu67-vwx89-yza01-bcd23-efg45-hij67 \\
            klm89-nop01-qrs23-tuv45-wxy67-zab89

    \b
    Output Format:
        Returns JSON with the updated job object including new task_order
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    if not task_ids:
        logger.error("At least one task ID must be provided")
        click.echo("Error: At least one task ID must be provided.", err=True)
        sys.exit(1)

    # Convert UUID objects to strings for the API
    task_ids_str = [str(task_id) for task_id in task_ids]

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Setting task order for job %s: %s", job_id, task_ids_str)
            response = client.put(f"/api/jobs/{job_id}", data={"task_order": task_ids_str})
            click.echo(json.dumps(response, indent=2))
            logger.info("Updated task order for job: %s", job_id)

    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Job not found: %s", job_id)
        else:
            logger.error("Failed to set task order: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@jobs.command("export")
@api_url_option
@click.argument("job_id")
@click.option(
    "--out",
    "-o",
    required=True,
    help="Output file path for the export (required)",
)
@click.pass_context
def export_job(ctx: click.Context, api_url: str, job_id: str, out: str) -> None:
    """Export a job with all associated tasks and configuration to JSON.

    Creates a complete export of a job including all its tasks and configuration
    for backup, sharing, or migration purposes.

    Examples:

    \b
        # Export job to file
        claude-code-scheduler cli jobs export abc-123 --out ~/exports/my-job.json

    \b
        # Export with verbose output
        claude-code-scheduler cli jobs export abc-123 -o ./backup.json -v

    \b
        # Export to relative path
        claude-code-scheduler cli jobs export <job-id> --out ./job-export.json

    \b
    Output Format:
        Returns JSON with export status and file path:
        {"status": "success", "output_path": "/path/to/export.json", "export": {...}}
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    # Expand the output path (handles ~, environment variables, etc.)
    expanded_output_path = os.path.expanduser(out)
    logger.debug("Expanded output path: %s -> %s", out, expanded_output_path)

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Exporting job %s to %s", job_id, expanded_output_path)

            # Call the export API endpoint with output path
            request_data = {"output_path": expanded_output_path}
            response = client.post(f"/api/jobs/{job_id}/export", data=request_data)

            # Display the response
            click.echo(json.dumps(response, indent=2))

            # Extract output path from response for logging
            if response.get("status") == "success":
                output_path = response.get("output_path", expanded_output_path)
                logger.info("Job exported successfully: %s -> %s", job_id, output_path)
            else:
                logger.warning("Export response indicated issues: %s", response)

    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Job not found: %s", job_id)
        else:
            logger.error("Failed to export job: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@jobs.command("tasks")
@api_url_option
@click.argument("job_id")
@click.option(
    "--output",
    default="json",
    type=click.Choice(["json", "table"]),
    help="Output format (default: json)",
)
@click.pass_context
def list_tasks(ctx: click.Context, api_url: str, job_id: str, output: str) -> None:
    """List all tasks belonging to a job.

    Retrieves tasks that are assigned to the specified job.

    Examples:

    \b
        # List tasks for a job as JSON
        claude-code-scheduler cli jobs tasks <job-id>

    \b
        # List tasks as table
        claude-code-scheduler cli jobs tasks <job-id> --output table

    \b
    Output Format:
        JSON: Array of task objects belonging to this job
        Table: Formatted table showing task id, name, status, model
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Fetching tasks for job %s from %s", job_id, api_url)
            response = client.get(f"/api/jobs/{job_id}/tasks")

            if output == "table":
                tasks_list: builtins.list[dict[str, str]] = response.get("tasks", [])
                if not tasks_list:
                    click.echo("No tasks found for this job.")
                    return

                table_data = []
                for task in tasks_list:
                    table_data.append(
                        [
                            task.get("id", "")[:8] + "...",
                            task.get("name", ""),
                            "enabled" if task.get("enabled") else "disabled",
                            task.get("model", ""),
                        ]
                    )

                headers = ["ID", "Name", "Status", "Model"]
                click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
            else:
                click.echo(json.dumps(response, indent=2))

            logger.info("Retrieved %d tasks for job %s", len(response.get("tasks", [])), job_id)

    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Job not found: %s", job_id)
        else:
            logger.error("Failed to list tasks for job: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


@jobs.command("import")
@api_url_option
@click.option(
    "--input",
    "-i",
    required=True,
    help="Input file path for the JSON export to import (required)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing job if UUID conflict",
)
@click.pass_context
def import_job(ctx: click.Context, api_url: str, input: str, force: bool) -> None:
    """Import a job with all associated tasks from a JSON file.

    Imports a complete job with all its tasks from a previously exported JSON file.
    Handles UUID conflicts, validates profile references, and provides clear error messages.

    Examples:

    \b
        # Import job from file
        claude-code-scheduler cli jobs import --input ~/exports/my-job.json

    \b
        # Force overwrite existing job
        claude-code-scheduler cli jobs import -i ./backup.json --force

    \b
        # Import with verbose output
        claude-code-scheduler cli jobs import -i ./job.json -v

    \b
        # Import from relative path
        claude-code-scheduler cli jobs import --input ./exports/daily-maintenance.json

    \b
    Output Format:
        Returns JSON with import status and details:
        {"status": "success", "job": {...}, "tasks_imported": 5, "warnings": [...]}

    Error Responses:
        • Job UUID already exists: Use --force to overwrite
        • Profile not found: Warning shown, import continues
        • File not found: Check the input path
        • Invalid JSON: Verify export file format
    """
    _verbose = ctx.obj.get("verbose", 0)  # noqa: F841

    # Expand the input path (handles ~, environment variables, etc.)
    expanded_input_path = os.path.expanduser(input)
    expanded_input_path = os.path.expandvars(expanded_input_path)
    logger.debug("Expanded input path: %s -> %s", input, expanded_input_path)

    try:
        with SchedulerClient(api_url) as client:
            logger.debug("Importing job from %s (force=%s)", expanded_input_path, force)

            # Call the import API endpoint with file path and force flag
            request_data = {"file_path": expanded_input_path, "force": force}
            response = client.post("/api/jobs/import", data=request_data)

            # Check response status and display appropriate output
            if response.get("status") == "success":
                job_data = response.get("job", {})
                job_name = job_data.get("name", "Unknown")
                job_id = job_data.get("id", "unknown")
                tasks_count = response.get("tasks_imported", 0)
                warnings = response.get("warnings", [])

                # Display success message
                click.echo(f'Imported job "{job_name}" ({job_id[:8]}...)')
                click.echo(f"  - {tasks_count} tasks imported")

                # Display warnings prominently if any
                if warnings:
                    click.echo("\n⚠️  Warnings:", err=True)
                    for warning in warnings:
                        click.echo(f"  • {warning}", err=True)

                # Display full response in verbose mode
                if _verbose >= 2:
                    click.echo("\nFull response:")
                    click.echo(json.dumps(response, indent=2))
                elif _verbose >= 1:
                    click.echo(f"\nImport completed successfully. Warnings: {len(warnings)}")

                logger.info(
                    "Imported job %s with %d tasks from %s",
                    job_name,
                    tasks_count,
                    expanded_input_path,
                )

            else:
                # Display error response
                error_message = response.get("message", "Unknown error")
                error_code = response.get("error_code", "UNKNOWN")
                details = response.get("details", {})

                click.echo(f"Error: {error_message}", err=True)

                # Show additional details for specific error codes
                if error_code == "JOB_EXISTS":
                    existing_name = details.get("existing_job_name", "Unknown")
                    click.echo(f'  Existing job: "{existing_name}"', err=True)
                    click.echo("  Use --force to overwrite existing job.", err=True)
                elif error_code == "PROFILE_NOT_FOUND":
                    available_profiles = details.get("available_profiles", [])
                    if available_profiles:
                        click.echo(
                            f"  Available profiles: {', '.join(available_profiles)}", err=True
                        )
                elif error_code == "INVALID_SCHEMA":
                    missing_fields = details.get("missing_fields", [])
                    if missing_fields:
                        click.echo(
                            f"  Missing required fields: {', '.join(missing_fields)}", err=True
                        )

                # Display full response in verbose mode
                if _verbose >= 2:
                    click.echo("\nFull error response:")
                    click.echo(json.dumps(response, indent=2), err=True)

                logger.error("Import failed: %s", error_message)
                sys.exit(1)

    except SchedulerAPIError as e:
        if e.status_code == 404:
            logger.error("Import endpoint not found or file not found: %s", e)
            click.echo("Error: Import service not available or file not found.", err=True)
        elif e.status_code == 400:
            logger.error("Invalid request or malformed JSON: %s", e)
            click.echo("Error: Invalid JSON format in export file.", err=True)
        elif e.status_code == 409:
            logger.error("Job UUID conflict: %s", e)
            click.echo("Error: Job already exists. Use --force to overwrite.", err=True)
        elif e.status_code == 422:
            logger.error("Validation error: %s", e)
            click.echo("Error: Profile references are invalid.", err=True)
        else:
            logger.error("Import API error: %s", e)
            click.echo(f"Error: Failed to import job (HTTP {e.status_code}).", err=True)

        # Display full error in verbose mode
        if _verbose >= 2 and hasattr(e, "response") and e.response:
            try:
                error_data = json.loads(e.response)
                click.echo("\nFull error response:")
                click.echo(json.dumps(error_data, indent=2), err=True)
            except (json.JSONDecodeError, AttributeError):
                click.echo(f"\nRaw error response: {e.response}", err=True)

        sys.exit(1)

    except FileNotFoundError:
        logger.error("Import file not found: %s", expanded_input_path)
        click.echo(f"Error: Import file not found: {expanded_input_path}", err=True)
        click.echo("Check that the file path is correct and the file exists.", err=True)
        sys.exit(1)

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in import file: %s", e)
        click.echo("Error: Invalid JSON format in export file.", err=True)
        click.echo(f"JSON parsing error: {str(e)}", err=True)
        sys.exit(1)

    except Exception as e:
        logger.error("Unexpected import error: %s", e)
        click.echo(f"Error: Unexpected error during import: {str(e)}", err=True)
        sys.exit(1)
