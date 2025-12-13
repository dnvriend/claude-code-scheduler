"""Debug HTTP Server for runtime inspection and control.

This module provides a REST API HTTP server for inspecting and controlling
the running GUI application. Enables external tools like Claude Code to
query and control the live scheduler process.

Key Components:
    - DebugServer: HTTP server running in background thread
    - DebugRequestHandler: Request handler with CRUD endpoints

Dependencies:
    - http.server: Python standard library HTTP server
    - json: JSON request/response handling
    - threading: Background server thread

Related Modules:
    - cli_client: SchedulerClient that communicates with this server
    - ui.main_window: Creates and starts the debug server
    - storage.config_storage: Server reads/writes via callbacks

API Endpoints:
    Read:
        - GET /api/health - Health check
        - GET /api/state - Full application state
        - GET /api/tasks - List tasks
        - GET /api/runs - List runs
        - GET /api/profiles - List profiles
        - GET /api/jobs - List jobs
        - GET /api/jobs/{id}/export - Export job and tasks as JSON
        - GET /api/scheduler - Scheduler status
    Write:
        - POST /api/tasks - Create task
        - PUT /api/tasks/{id} - Update task
        - DELETE /api/tasks/{id} - Delete task
        - POST /api/tasks/{id}/run - Run task now
        - POST /api/runs/{id}/stop - Stop running task
        - POST /api/jobs/{id}/export - Export job and tasks to file
        - POST /api/jobs/import - Import job from file

Called By:
    - MainWindow.__init__: Creates and starts server
    - CLI cli_* commands: Via SchedulerClient HTTP calls

Example:
    >>> server = DebugServer(port=5679, state_callback=get_state)
    >>> server.start()
    >>> # API available at http://127.0.0.1:5679/api/

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from uuid import UUID

from claude_code_scheduler.logging_config import get_logger

logger = get_logger(__name__)

# Default port for debug server
DEFAULT_DEBUG_PORT = 5679


class DebugRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for debug endpoints."""

    # Class-level providers (set by DebugServer)
    # Read providers
    state_provider: Callable[[], dict[str, Any]] | None = None
    ui_state_provider: Callable[[], dict[str, Any]] | None = None
    ui_analysis_provider: Callable[[], dict[str, Any]] | None = None
    screenshot_provider: Callable[[str], dict[str, Any]] | None = None
    # Read providers for single items
    task_get_provider: Callable[[UUID], dict[str, Any]] | None = None
    run_get_provider: Callable[[UUID], dict[str, Any]] | None = None
    run_logs_provider: Callable[[UUID], str | None] | None = None
    # Write providers (action callbacks)
    task_create_provider: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    task_update_provider: Callable[[UUID, dict[str, Any]], dict[str, Any]] | None = None
    task_delete_provider: Callable[[UUID], dict[str, Any]] | None = None
    task_run_provider: Callable[[UUID], dict[str, Any]] | None = None
    task_enable_provider: Callable[[UUID, bool], dict[str, Any]] | None = None
    run_stop_provider: Callable[[UUID], dict[str, Any]] | None = None
    run_restart_provider: Callable[[UUID], dict[str, Any]] | None = None
    run_delete_provider: Callable[[UUID], dict[str, Any]] | None = None
    # Profile providers
    profile_list_provider: Callable[[], dict[str, Any]] | None = None
    profile_get_provider: Callable[[UUID], dict[str, Any]] | None = None
    profile_create_provider: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    profile_update_provider: Callable[[UUID, dict[str, Any]], dict[str, Any]] | None = None
    profile_delete_provider: Callable[[UUID], dict[str, Any]] | None = None
    # Job providers
    job_list_provider: Callable[[], dict[str, Any]] | None = None
    job_get_provider: Callable[[UUID], dict[str, Any]] | None = None
    job_create_provider: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    job_update_provider: Callable[[UUID, dict[str, Any]], dict[str, Any]] | None = None
    job_delete_provider: Callable[[UUID], dict[str, Any]] | None = None
    job_tasks_provider: Callable[[UUID], dict[str, Any]] | None = None
    job_run_provider: Callable[[UUID], dict[str, Any]] | None = None
    job_stop_provider: Callable[[UUID], dict[str, Any]] | None = None
    job_export_provider: Callable[[UUID], dict[str, Any]] | None = None
    job_export_file_provider: Callable[[UUID, str], dict[str, Any]] | None = None
    job_import_provider: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    # Short ID resolvers (for prefix matching)
    task_id_resolver: Callable[[str], UUID | None] | None = None
    job_id_resolver: Callable[[str], UUID | None] | None = None
    run_id_resolver: Callable[[str], UUID | None] | None = None
    server_port: int = DEFAULT_DEBUG_PORT

    def log_message(self, format: str, *args: Any) -> None:
        """Override to use our logger instead of stderr."""
        logger.debug("Debug server: %s", format % args)

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests."""
        if self.path == "/api/openapi.json":
            self._send_json(self._get_openapi_spec())
        elif self.path == "/api/state":
            self._send_json(self._get_full_state())
        elif self.path == "/api/runs":
            self._send_json(self._get_runs())
        # GET /api/runs/{id} - Get single run
        elif self.path.startswith("/api/runs/"):
            if self.path.endswith("/logs"):
                run_id = self._extract_run_id("/logs")
                if run_id:
                    self._handle_run_get_logs(run_id)
            else:
                run_id = self._extract_run_id("")
                if run_id:
                    self._handle_run_get(run_id)
        elif self.path == "/api/tasks":
            self._send_json(self._get_tasks())
        # GET /api/tasks/{id} - Get single task
        elif self.path.startswith("/api/tasks/"):
            task_id = self._extract_task_id("")
            if task_id:
                self._handle_task_get(task_id)
        elif self.path == "/api/scheduler":
            self._send_json(self._get_scheduler())
        elif self.path == "/api/ui":
            self._send_json(self._get_ui_state())
        elif self.path == "/api/ui/analysis":
            self._send_json(self._get_ui_analysis())
        elif self.path.startswith("/api/ui/screenshot"):
            self._send_json(self._get_screenshot())
        elif self.path == "/api/health":
            self._send_json({"status": "ok", "message": "Debug server running"})
        # GET /api/profiles - List all profiles
        elif self.path == "/api/profiles":
            self._handle_profile_list()
        # GET /api/profiles/{id} - Get single profile
        elif self.path.startswith("/api/profiles/"):
            profile_id = self._extract_profile_id("")
            if profile_id:
                self._handle_profile_get(profile_id)
        # GET /api/jobs - List all jobs
        elif self.path == "/api/jobs":
            self._handle_job_list()
        # GET /api/jobs/{id}/tasks - List tasks for a job
        elif self.path.startswith("/api/jobs/") and self.path.endswith("/tasks"):
            job_id = self._extract_job_id("/tasks")
            if job_id:
                self._handle_job_tasks(job_id)
        # GET /api/jobs/{id}/task-order - Get task order for a job
        elif self.path.startswith("/api/jobs/") and self.path.endswith("/task-order"):
            job_id = self._extract_job_id("/task-order")
            if job_id:
                self._handle_job_task_order_get(job_id)
        # GET /api/jobs/{id}/export - Export job and tasks as JSON
        elif self.path.startswith("/api/jobs/") and self.path.endswith("/export"):
            job_id = self._extract_job_id("/export")
            if job_id:
                self._handle_job_export(job_id)
        # GET /api/jobs/{id} - Get single job
        elif self.path.startswith("/api/jobs/"):
            job_id = self._extract_job_id("")
            if job_id:
                self._handle_job_get(job_id)
        elif self.path == "/":
            self._send_help()
        else:
            self._send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests."""
        # POST /api/tasks - Create task
        if self.path == "/api/tasks":
            self._handle_task_create()
        # POST /api/tasks/{id}/run - Run task now
        elif self.path.startswith("/api/tasks/") and self.path.endswith("/run"):
            task_id = self._extract_task_id("/run")
            if task_id:
                self._handle_task_run(task_id)
        # POST /api/tasks/{id}/enable - Enable task
        elif self.path.startswith("/api/tasks/") and self.path.endswith("/enable"):
            task_id = self._extract_task_id("/enable")
            if task_id:
                self._handle_task_enable(task_id, enabled=True)
        # POST /api/tasks/{id}/disable - Disable task
        elif self.path.startswith("/api/tasks/") and self.path.endswith("/disable"):
            task_id = self._extract_task_id("/disable")
            if task_id:
                self._handle_task_enable(task_id, enabled=False)
        # POST /api/runs/{id}/stop - Stop run
        elif self.path.startswith("/api/runs/") and self.path.endswith("/stop"):
            run_id = self._extract_run_id("/stop")
            if run_id:
                self._handle_run_stop(run_id)
        # POST /api/runs/{id}/restart - Restart run
        elif self.path.startswith("/api/runs/") and self.path.endswith("/restart"):
            run_id = self._extract_run_id("/restart")
            if run_id:
                self._handle_run_restart(run_id)
        # POST /api/profiles - Create profile
        elif self.path == "/api/profiles":
            self._handle_profile_create()
        # POST /api/jobs - Create job
        elif self.path == "/api/jobs":
            self._handle_job_create()
        # POST /api/jobs/import - Import job from file
        elif self.path == "/api/jobs/import":
            self._handle_job_import()
        # POST /api/jobs/{id}/export - Export job and tasks to file
        elif self.path.startswith("/api/jobs/") and self.path.endswith("/export"):
            job_id = self._extract_job_id("/export")
            if job_id:
                self._handle_job_export_file(job_id)
        # POST /api/jobs/{id}/run - Run job (start sequential execution)
        elif self.path.startswith("/api/jobs/") and self.path.endswith("/run"):
            job_id = self._extract_job_id("/run")
            if job_id:
                self._handle_job_run(job_id)
        # POST /api/jobs/{id}/stop - Stop running job
        elif self.path.startswith("/api/jobs/") and self.path.endswith("/stop"):
            job_id = self._extract_job_id("/stop")
            if job_id:
                self._handle_job_stop(job_id)
        else:
            self._send_error(404, "Not found")

    def do_PUT(self) -> None:  # noqa: N802
        """Handle PUT requests."""
        # PUT /api/tasks/{id} - Update task
        if self.path.startswith("/api/tasks/"):
            task_id = self._extract_task_id("")
            if task_id:
                self._handle_task_update(task_id)
        # PUT /api/profiles/{id} - Update profile
        elif self.path.startswith("/api/profiles/"):
            profile_id = self._extract_profile_id("")
            if profile_id:
                self._handle_profile_update(profile_id)
        # PUT /api/jobs/{id}/task-order - Update task order for job
        elif self.path.startswith("/api/jobs/") and self.path.endswith("/task-order"):
            job_id = self._extract_job_id("/task-order")
            if job_id:
                self._handle_job_task_order_update(job_id)
        # PUT /api/jobs/{id} - Update job
        elif self.path.startswith("/api/jobs/"):
            job_id = self._extract_job_id("")
            if job_id:
                self._handle_job_update(job_id)
        else:
            self._send_error(404, "Not found")

    def do_DELETE(self) -> None:  # noqa: N802
        """Handle DELETE requests."""
        # DELETE /api/tasks/{id} - Delete task
        if self.path.startswith("/api/tasks/"):
            task_id = self._extract_task_id("")
            if task_id:
                self._handle_task_delete(task_id)
        # DELETE /api/runs/{id} - Delete run
        elif self.path.startswith("/api/runs/"):
            run_id = self._extract_run_id("")
            if run_id:
                self._handle_run_delete(run_id)
        # DELETE /api/profiles/{id} - Delete profile
        elif self.path.startswith("/api/profiles/"):
            profile_id = self._extract_profile_id("")
            if profile_id:
                self._handle_profile_delete(profile_id)
        # DELETE /api/jobs/{id} - Delete job
        elif self.path.startswith("/api/jobs/"):
            job_id = self._extract_job_id("")
            if job_id:
                self._handle_job_delete(job_id)
        else:
            self._send_error(404, "Not found")

    def _extract_task_id(self, suffix: str) -> UUID | None:
        """Extract task ID from path like /api/tasks/{id}{suffix}.

        Supports both full UUIDs and short ID prefixes (e.g., first 8 chars).
        """
        path = self.path
        if suffix:
            path = path.removesuffix(suffix)
        task_id_str = path.replace("/api/tasks/", "")

        # Try parsing as full UUID first
        try:
            return UUID(task_id_str)
        except ValueError:
            pass

        # Try resolving as short ID prefix
        if self.task_id_resolver:
            resolved = self.task_id_resolver(task_id_str)
            if resolved:
                return resolved

        self._send_error(400, f"Invalid or ambiguous task ID: {task_id_str}")
        return None

    def _extract_run_id(self, suffix: str) -> UUID | None:
        """Extract run ID from path like /api/runs/{id}{suffix}.

        Supports both full UUIDs and short ID prefixes (e.g., first 8 chars).
        """
        path = self.path
        if suffix:
            path = path.removesuffix(suffix)
        run_id_str = path.replace("/api/runs/", "")

        # Try parsing as full UUID first
        try:
            return UUID(run_id_str)
        except ValueError:
            pass

        # Try resolving as short ID prefix
        if self.run_id_resolver:
            resolved = self.run_id_resolver(run_id_str)
            if resolved:
                return resolved

        self._send_error(400, f"Invalid or ambiguous run ID: {run_id_str}")
        return None

    def _extract_profile_id(self, suffix: str) -> UUID | None:
        """Extract profile ID from path like /api/profiles/{id}{suffix}."""
        try:
            path = self.path
            if suffix:
                path = path.removesuffix(suffix)
            profile_id_str = path.replace("/api/profiles/", "")
            return UUID(profile_id_str)
        except ValueError:
            self._send_error(400, f"Invalid profile ID: {self.path}")
            return None

    def _extract_job_id(self, suffix: str) -> UUID | None:
        """Extract job ID from path like /api/jobs/{id}{suffix}.

        Supports both full UUIDs and short ID prefixes (e.g., first 8 chars).
        """
        path = self.path
        if suffix:
            path = path.removesuffix(suffix)
        job_id_str = path.replace("/api/jobs/", "")

        # Try parsing as full UUID first
        try:
            return UUID(job_id_str)
        except ValueError:
            pass

        # Try resolving as short ID prefix
        if self.job_id_resolver:
            resolved = self.job_id_resolver(job_id_str)
            if resolved:
                return resolved

        self._send_error(400, f"Invalid or ambiguous job ID: {job_id_str}")
        return None

    def _read_json_body(self) -> dict[str, Any] | None:
        """Read and parse JSON body from request."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        try:
            body = self.rfile.read(content_length)
            result: dict[str, Any] = json.loads(body.decode("utf-8"))
            return result
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self._send_error(400, f"Invalid JSON body: {e}")
            return None

    def _handle_task_get(self, task_id: UUID) -> None:
        """Handle GET /api/tasks/{id} - get single task."""
        if not self.task_get_provider:
            self._send_error(501, "Task retrieval not available")
            return
        result = self.task_get_provider(task_id)
        self._send_json(result)

    def _handle_run_get(self, run_id: UUID) -> None:
        """Handle GET /api/runs/{id} - get single run."""
        if not self.run_get_provider:
            self._send_error(501, "Run retrieval not available")
            return
        result = self.run_get_provider(run_id)
        self._send_json(result)

    def _handle_run_get_logs(self, run_id: UUID) -> None:
        """Handle GET /api/runs/{id}/logs - get log content for a run."""
        if not self.run_logs_provider:
            self._send_error(501, "Run logs retrieval not available")
            return

        try:
            content = self.run_logs_provider(run_id)
            if content is not None:
                self._send_json({"logs": content})
            else:
                self._send_error(404, f"No logs found for run {run_id}")
        except Exception as e:
            logger.error("Error retrieving logs for run %s: %s", run_id, e)
            self._send_error(500, f"Error retrieving logs: {str(e)}")

    def _handle_task_create(self) -> None:
        """Handle POST /api/tasks - create new task."""
        if not self.task_create_provider:
            self._send_error(501, "Task creation not available")
            return
        body = self._read_json_body()
        if body is None:
            return
        result = self.task_create_provider(body)
        self._send_json(result)

    def _handle_task_update(self, task_id: UUID) -> None:
        """Handle PUT /api/tasks/{id} - update task."""
        if not self.task_update_provider:
            self._send_error(501, "Task update not available")
            return
        body = self._read_json_body()
        if body is None:
            return
        result = self.task_update_provider(task_id, body)
        self._send_json(result)

    def _handle_task_delete(self, task_id: UUID) -> None:
        """Handle DELETE /api/tasks/{id} - delete task."""
        if not self.task_delete_provider:
            self._send_error(501, "Task deletion not available")
            return
        result = self.task_delete_provider(task_id)
        self._send_json(result)

    def _handle_task_run(self, task_id: UUID) -> None:
        """Handle POST /api/tasks/{id}/run - run task now."""
        if not self.task_run_provider:
            self._send_error(501, "Task execution not available")
            return
        result = self.task_run_provider(task_id)
        self._send_json(result)

    def _handle_task_enable(self, task_id: UUID, enabled: bool) -> None:
        """Handle POST /api/tasks/{id}/enable or /disable."""
        if not self.task_enable_provider:
            self._send_error(501, "Task enable/disable not available")
            return
        result = self.task_enable_provider(task_id, enabled)
        self._send_json(result)

    def _handle_run_stop(self, run_id: UUID) -> None:
        """Handle POST /api/runs/{id}/stop - stop running task."""
        if not self.run_stop_provider:
            self._send_error(501, "Run stop not available")
            return
        result = self.run_stop_provider(run_id)
        self._send_json(result)

    def _handle_run_restart(self, run_id: UUID) -> None:
        """Handle POST /api/runs/{id}/restart - restart task."""
        if not self.run_restart_provider:
            self._send_error(501, "Run restart not available")
            return
        result = self.run_restart_provider(run_id)
        self._send_json(result)

    def _handle_run_delete(self, run_id: UUID) -> None:
        """Handle DELETE /api/runs/{id} - delete run record."""
        if not self.run_delete_provider:
            self._send_error(501, "Run deletion not available")
            return
        result = self.run_delete_provider(run_id)
        self._send_json(result)

    def _handle_profile_list(self) -> None:
        """Handle GET /api/profiles - list all profiles."""
        if not self.profile_list_provider:
            self._send_error(501, "Profile listing not available")
            return
        result = self.profile_list_provider()
        self._send_json(result)

    def _handle_profile_get(self, profile_id: UUID) -> None:
        """Handle GET /api/profiles/{id} - get single profile."""
        if not self.profile_get_provider:
            self._send_error(501, "Profile retrieval not available")
            return
        result = self.profile_get_provider(profile_id)
        self._send_json(result)

    def _handle_profile_create(self) -> None:
        """Handle POST /api/profiles - create new profile."""
        if not self.profile_create_provider:
            self._send_error(501, "Profile creation not available")
            return
        body = self._read_json_body()
        if body is None:
            return
        result = self.profile_create_provider(body)
        self._send_json(result)

    def _handle_profile_update(self, profile_id: UUID) -> None:
        """Handle PUT /api/profiles/{id} - update profile."""
        if not self.profile_update_provider:
            self._send_error(501, "Profile update not available")
            return
        body = self._read_json_body()
        if body is None:
            return
        result = self.profile_update_provider(profile_id, body)
        self._send_json(result)

    def _handle_profile_delete(self, profile_id: UUID) -> None:
        """Handle DELETE /api/profiles/{id} - delete profile."""
        if not self.profile_delete_provider:
            self._send_error(501, "Profile deletion not available")
            return
        result = self.profile_delete_provider(profile_id)
        self._send_json(result)

    def _handle_job_list(self) -> None:
        """Handle GET /api/jobs - list all jobs."""
        if not self.job_list_provider:
            self._send_error(501, "Job listing not available")
            return
        result = self.job_list_provider()
        self._send_json(result)

    def _handle_job_get(self, job_id: UUID) -> None:
        """Handle GET /api/jobs/{id} - get single job."""
        if not self.job_get_provider:
            self._send_error(501, "Job retrieval not available")
            return
        result = self.job_get_provider(job_id)
        self._send_json(result)

    def _handle_job_tasks(self, job_id: UUID) -> None:
        """Handle GET /api/jobs/{id}/tasks - list tasks for a job."""
        if not self.job_tasks_provider:
            self._send_error(501, "Job tasks listing not available")
            return
        result = self.job_tasks_provider(job_id)
        self._send_json(result)

    def _handle_job_task_order_get(self, job_id: UUID) -> None:
        """Handle GET /api/jobs/{id}/task-order - get task order for a job."""
        if not self.job_get_provider:
            self._send_error(501, "Job get not available")
            return
        result = self.job_get_provider(job_id)
        if result and "error" not in result:
            # Return just the task_order array
            task_order = result.get("task_order", [])
            self._send_json({"task_order": task_order})
        else:
            self._send_json(result)

    def _handle_job_task_order_update(self, job_id: UUID) -> None:
        """Handle PUT /api/jobs/{id}/task-order - update task order for a job."""
        if not self.job_update_provider or not self.job_get_provider:
            self._send_error(501, "Job update not available")
            return

        body = self._read_json_body()
        if body is None:
            return

        # Accept either {"task_order": [...]} or just [...]
        if isinstance(body, list):
            task_order = body
        else:
            task_order = body.get("task_order", [])

        # Validate all items are strings (UUIDs)
        if not all(isinstance(item, str) for item in task_order):
            self._send_error(400, "task_order must be a list of UUID strings")
            return

        # Update the job with new task_order
        result = self.job_update_provider(job_id, {"task_order": task_order})
        self._send_json(result)

    def _handle_job_create(self) -> None:
        """Handle POST /api/jobs - create new job."""
        if not self.job_create_provider:
            self._send_error(501, "Job creation not available")
            return
        body = self._read_json_body()
        if body is None:
            return
        result = self.job_create_provider(body)
        self._send_json(result)

    def _handle_job_update(self, job_id: UUID) -> None:
        """Handle PUT /api/jobs/{id} - update job."""
        if not self.job_update_provider:
            self._send_error(501, "Job update not available")
            return
        body = self._read_json_body()
        if body is None:
            return
        result = self.job_update_provider(job_id, body)
        self._send_json(result)

    def _handle_job_delete(self, job_id: UUID) -> None:
        """Handle DELETE /api/jobs/{id} - delete job."""
        if not self.job_delete_provider:
            self._send_error(501, "Job deletion not available")
            return
        result = self.job_delete_provider(job_id)
        self._send_json(result)

    def _handle_job_run(self, job_id: UUID) -> None:
        """Handle POST /api/jobs/{id}/run - run job (start sequential execution)."""
        if not self.job_run_provider:
            self._send_error(501, "Job run not available")
            return
        result = self.job_run_provider(job_id)
        self._send_json(result)

    def _handle_job_stop(self, job_id: UUID) -> None:
        """Handle POST /api/jobs/{id}/stop - stop a running job."""
        if not self.job_stop_provider:
            self._send_error(501, "Job stop not available")
            return
        result = self.job_stop_provider(job_id)
        self._send_json(result)

    def _handle_job_export(self, job_id: UUID) -> None:
        """Handle GET /api/jobs/{id}/export - export job and tasks as JSON."""
        if not self.job_export_provider:
            self._send_error(501, "Job export not available")
            return
        result = self.job_export_provider(job_id)
        self._send_json(result)

    def _handle_job_export_file(self, job_id: UUID) -> None:
        """Handle POST /api/jobs/{id}/export - export job and tasks to file."""
        if not self.job_export_file_provider:
            self._send_error(501, "Job export to file not available")
            return

        body = self._read_json_body()
        if body is None:
            return

        output_path = body.get("output_path")
        if not output_path:
            self._send_error(400, "output_path is required in request body")
            return

        if not isinstance(output_path, str):
            self._send_error(400, "output_path must be a string")
            return

        result = self.job_export_file_provider(job_id, output_path)
        self._send_json(result)

    def _handle_job_import(self) -> None:
        """Handle POST /api/jobs/import - import job from file."""
        if not self.job_import_provider:
            self._send_error(501, "Job import not available")
            return

        body = self._read_json_body()
        if body is None:
            return

        file_path = body.get("file_path")
        if not file_path:
            self._send_error(400, "file_path is required in request body")
            return

        if not isinstance(file_path, str):
            self._send_error(400, "file_path must be a string")
            return

        force = body.get("force", False)
        if not isinstance(force, bool):
            self._send_error(400, "force must be a boolean")
            return

        result = self.job_import_provider({"file_path": file_path, "force": force})

        # Handle different HTTP status codes based on result
        if not result.get("success", False):
            error_code = result.get("error_code", "UNKNOWN_ERROR")
            message = result.get("message", "Import failed")

            if error_code == "FILE_NOT_FOUND":
                self._send_error(404, message)
            elif error_code == "JOB_EXISTS":
                self._send_error(409, message)
            elif error_code in ["INVALID_JSON", "INVALID_SCHEMA", "VERSION_MISMATCH"]:
                self._send_error(400, message)
            elif error_code == "PROFILE_NOT_FOUND":
                self._send_error(422, message)
            else:
                self._send_error(500, message)
        else:
            self._send_json(result)

    def _get_openapi_spec(self) -> dict[str, Any]:
        """Get OpenAPI 3.0 specification for this API."""
        return {
            "openapi": "3.0.3",
            "info": {
                "title": "Claude Code Scheduler GUI API",
                "description": (
                    "REST API for inspecting and controlling the Claude Code Scheduler "
                    "GUI application. This API allows external tools to manage tasks, "
                    "runs, and inspect application state."
                ),
                "version": "2.0.0",
                "contact": {"name": "Claude Code Scheduler"},
            },
            "servers": [
                {"url": f"http://127.0.0.1:{self.server_port}", "description": "Local GUI server"}
            ],
            "tags": [
                {"name": "health", "description": "Health check endpoints"},
                {"name": "tasks", "description": "Task management operations"},
                {"name": "runs", "description": "Run management operations"},
                {"name": "jobs", "description": "Job management operations"},
                {"name": "profiles", "description": "Profile management operations"},
                {"name": "state", "description": "Application state inspection"},
                {"name": "ui", "description": "UI inspection and screenshots"},
            ],
            "paths": {
                "/api/health": {
                    "get": {
                        "tags": ["health"],
                        "summary": "Health check",
                        "description": "Verify the debug server is running",
                        "operationId": "getHealth",
                        "responses": {
                            "200": {
                                "description": "Server is healthy",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/HealthResponse"}
                                    }
                                },
                            }
                        },
                    }
                },
                "/api/openapi.json": {
                    "get": {
                        "tags": ["health"],
                        "summary": "OpenAPI specification",
                        "description": "Get the OpenAPI 3.0 specification for this API",
                        "operationId": "getOpenApiSpec",
                        "responses": {
                            "200": {
                                "description": "OpenAPI specification",
                                "content": {"application/json": {"schema": {"type": "object"}}},
                            }
                        },
                    }
                },
                "/api/state": {
                    "get": {
                        "tags": ["state"],
                        "summary": "Get full application state",
                        "description": (
                            "Returns complete state including tasks, runs, profiles, "
                            "settings, and scheduler info"
                        ),
                        "operationId": "getState",
                        "responses": {
                            "200": {
                                "description": "Full application state",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ApplicationState"}
                                    }
                                },
                            }
                        },
                    }
                },
                "/api/tasks": {
                    "get": {
                        "tags": ["tasks"],
                        "summary": "List all tasks",
                        "description": "Get a list of all configured tasks",
                        "operationId": "listTasks",
                        "responses": {
                            "200": {
                                "description": "List of tasks",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/TaskList"}
                                    }
                                },
                            }
                        },
                    },
                    "post": {
                        "tags": ["tasks"],
                        "summary": "Create a new task",
                        "description": "Create a new scheduled task",
                        "operationId": "createTask",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TaskCreate"}
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Task created successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/TaskResponse"}
                                    }
                                },
                            },
                            "400": {
                                "description": "Invalid request",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                },
                "/api/tasks/{taskId}": {
                    "get": {
                        "tags": ["tasks"],
                        "summary": "Get a task",
                        "description": "Get a single task by ID with full details",
                        "operationId": "getTask",
                        "parameters": [
                            {
                                "name": "taskId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Task UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Task details",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/TaskResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Task not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                    "put": {
                        "tags": ["tasks"],
                        "summary": "Update a task",
                        "description": "Update an existing task. Partial updates supported.",
                        "operationId": "updateTask",
                        "parameters": [
                            {
                                "name": "taskId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Task UUID",
                            }
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TaskUpdate"}
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Task updated successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/TaskResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Task not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                    "delete": {
                        "tags": ["tasks"],
                        "summary": "Delete a task",
                        "description": "Delete a task and unschedule it",
                        "operationId": "deleteTask",
                        "parameters": [
                            {
                                "name": "taskId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Task UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Task deleted successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Task not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                },
                "/api/tasks/{taskId}/run": {
                    "post": {
                        "tags": ["tasks"],
                        "summary": "Run a task immediately",
                        "description": "Execute a task now, regardless of its schedule",
                        "operationId": "runTask",
                        "parameters": [
                            {
                                "name": "taskId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Task UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Task started successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Task not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    }
                },
                "/api/tasks/{taskId}/enable": {
                    "post": {
                        "tags": ["tasks"],
                        "summary": "Enable a task",
                        "description": "Enable a task so it will run on schedule",
                        "operationId": "enableTask",
                        "parameters": [
                            {
                                "name": "taskId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Task UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Task enabled successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Task not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    }
                },
                "/api/tasks/{taskId}/disable": {
                    "post": {
                        "tags": ["tasks"],
                        "summary": "Disable a task",
                        "description": "Disable a task so it will not run on schedule",
                        "operationId": "disableTask",
                        "parameters": [
                            {
                                "name": "taskId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Task UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Task disabled successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Task not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    }
                },
                "/api/runs": {
                    "get": {
                        "tags": ["runs"],
                        "summary": "List all runs",
                        "description": "Get a list of all task execution runs",
                        "operationId": "listRuns",
                        "responses": {
                            "200": {
                                "description": "List of runs",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/RunList"}
                                    }
                                },
                            }
                        },
                    }
                },
                "/api/runs/{runId}/stop": {
                    "post": {
                        "tags": ["runs"],
                        "summary": "Stop a running task",
                        "description": "Stop a currently running task execution",
                        "operationId": "stopRun",
                        "parameters": [
                            {
                                "name": "runId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Run UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Run stopped successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Run not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    }
                },
                "/api/runs/{runId}/restart": {
                    "post": {
                        "tags": ["runs"],
                        "summary": "Restart a task from a run",
                        "description": "Re-execute the task associated with this run",
                        "operationId": "restartRun",
                        "parameters": [
                            {
                                "name": "runId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Run UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Task restarted successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Run or task not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    }
                },
                "/api/runs/{runId}": {
                    "get": {
                        "tags": ["runs"],
                        "summary": "Get a run",
                        "description": "Get a single run by ID with full details",
                        "operationId": "getRun",
                        "parameters": [
                            {
                                "name": "runId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Run UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Run details",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/RunResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Run not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                    "delete": {
                        "tags": ["runs"],
                        "summary": "Delete a run record",
                        "description": "Delete a run record. Cannot delete running tasks.",
                        "operationId": "deleteRun",
                        "parameters": [
                            {
                                "name": "runId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Run UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Run deleted successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                    }
                                },
                            },
                            "400": {
                                "description": "Cannot delete running task",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Run not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                },
                "/api/profiles": {
                    "get": {
                        "tags": ["profiles"],
                        "summary": "List all profiles",
                        "description": "Get a list of all environment profiles",
                        "operationId": "listProfiles",
                        "responses": {
                            "200": {
                                "description": "List of profiles",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ProfileList"}
                                    }
                                },
                            }
                        },
                    },
                    "post": {
                        "tags": ["profiles"],
                        "summary": "Create a new profile",
                        "description": "Create a new environment profile",
                        "operationId": "createProfile",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ProfileCreate"}
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Profile created successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ProfileResponse"}
                                    }
                                },
                            },
                            "400": {
                                "description": "Invalid request",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                },
                "/api/profiles/{profileId}": {
                    "get": {
                        "tags": ["profiles"],
                        "summary": "Get a profile",
                        "description": "Get a single profile by ID with full details",
                        "operationId": "getProfile",
                        "parameters": [
                            {
                                "name": "profileId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Profile UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Profile details",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ProfileResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Profile not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                    "put": {
                        "tags": ["profiles"],
                        "summary": "Update a profile",
                        "description": "Update an existing profile. Partial updates supported.",
                        "operationId": "updateProfile",
                        "parameters": [
                            {
                                "name": "profileId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Profile UUID",
                            }
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ProfileUpdate"}
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Profile updated successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ProfileResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Profile not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                    "delete": {
                        "tags": ["profiles"],
                        "summary": "Delete a profile",
                        "description": "Delete an environment profile",
                        "operationId": "deleteProfile",
                        "parameters": [
                            {
                                "name": "profileId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Profile UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Profile deleted successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Profile not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                },
                "/api/jobs": {
                    "get": {
                        "tags": ["jobs"],
                        "summary": "List all jobs",
                        "description": "Get a list of all jobs",
                        "operationId": "listJobs",
                        "responses": {
                            "200": {
                                "description": "List of jobs",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/JobList"}
                                    }
                                },
                            }
                        },
                    },
                    "post": {
                        "tags": ["jobs"],
                        "summary": "Create a new job",
                        "description": "Create a new job container for tasks",
                        "operationId": "createJob",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/JobCreate"}
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Job created successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/JobResponse"}
                                    }
                                },
                            },
                            "400": {
                                "description": "Invalid input",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                },
                "/api/jobs/{jobId}": {
                    "get": {
                        "tags": ["jobs"],
                        "summary": "Get a job",
                        "description": "Get a single job by ID with full details",
                        "operationId": "getJob",
                        "parameters": [
                            {
                                "name": "jobId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Job UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Job details",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/JobResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Job not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                    "put": {
                        "tags": ["jobs"],
                        "summary": "Update a job",
                        "description": "Update an existing job. Partial updates supported.",
                        "operationId": "updateJob",
                        "parameters": [
                            {
                                "name": "jobId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Job UUID",
                            }
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/JobUpdate"}
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Job updated successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/JobResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Job not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                    "delete": {
                        "tags": ["jobs"],
                        "summary": "Delete a job",
                        "description": "Delete a job and cascade delete all tasks and runs",
                        "operationId": "deleteJob",
                        "parameters": [
                            {
                                "name": "jobId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Job UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Job deleted successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Job not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                },
                "/api/jobs/{jobId}/tasks": {
                    "get": {
                        "tags": ["jobs"],
                        "summary": "List tasks in a job",
                        "description": "Get all tasks belonging to a job",
                        "operationId": "listJobTasks",
                        "parameters": [
                            {
                                "name": "jobId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Job UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "List of tasks",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/TaskList"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Job not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    }
                },
                "/api/jobs/{jobId}/run": {
                    "post": {
                        "tags": ["jobs"],
                        "summary": "Run a job",
                        "description": "Start sequential execution of all tasks in the job",
                        "operationId": "runJob",
                        "parameters": [
                            {
                                "name": "jobId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Job UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Job started successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                    }
                                },
                            },
                            "400": {
                                "description": "Job has no tasks or is already running",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Job not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    }
                },
                "/api/jobs/{jobId}/stop": {
                    "post": {
                        "tags": ["jobs"],
                        "summary": "Stop a running job",
                        "description": "Stop sequential execution of a running job",
                        "operationId": "stopJob",
                        "parameters": [
                            {
                                "name": "jobId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Job UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Job stopped successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                    }
                                },
                            },
                            "400": {
                                "description": "Job is not running",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Job not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    }
                },
                "/api/jobs/{jobId}/export": {
                    "get": {
                        "tags": ["jobs"],
                        "summary": "Export job and tasks as JSON",
                        "description": "Export job and tasks in JSON format",
                        "operationId": "exportJob",
                        "parameters": [
                            {
                                "name": "jobId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Job UUID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Job export data",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "version": {"type": "string"},
                                                "exported_at": {
                                                    "type": "string",
                                                    "format": "date-time",
                                                },
                                                "job": {"type": "object"},
                                                "tasks": {"type": "array"},
                                                "metadata": {"type": "object"},
                                            },
                                        }
                                    }
                                },
                            },
                            "404": {
                                "description": "Job not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                    "post": {
                        "tags": ["jobs"],
                        "summary": "Export job and tasks to file",
                        "description": "Export job and its tasks to a JSON file on disk",
                        "operationId": "exportJobToFile",
                        "parameters": [
                            {
                                "name": "jobId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string", "format": "uuid"},
                                "description": "Job UUID",
                            }
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["output_path"],
                                        "properties": {
                                            "output_path": {
                                                "type": "string",
                                                "description": "Output file path",
                                            }
                                        },
                                    }
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Job exported successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "success": {"type": "boolean"},
                                                "output_path": {"type": "string"},
                                                "message": {"type": "string"},
                                            },
                                        }
                                    }
                                },
                            },
                            "400": {
                                "description": "Invalid output path or missing request body",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "Job not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    },
                },
                "/api/jobs/import": {
                    "post": {
                        "tags": ["jobs"],
                        "summary": "Import job from file",
                        "description": "Import job and tasks from a JSON file",
                        "operationId": "importJob",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "file_path": {
                                                "type": "string",
                                                "description": "Path to JSON file to import",
                                            },
                                            "force": {
                                                "type": "boolean",
                                                "description": (
                                                    "Overwrite existing job if UUID conflict"
                                                ),
                                                "default": False,
                                            },
                                        },
                                        "required": ["file_path"],
                                    }
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Job imported successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "success": {"type": "boolean"},
                                                "job": {"type": "object"},
                                                "tasks_imported": {"type": "integer"},
                                                "warnings": {
                                                    "type": "array",
                                                    "items": {"type": "string"},
                                                },
                                            },
                                        }
                                    }
                                },
                            },
                            "400": {
                                "description": "Invalid JSON or validation failed",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                            "404": {
                                "description": "File not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                            "409": {
                                "description": "Job UUID already exists",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                            "422": {
                                "description": "Profile not found",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                },
                            },
                        },
                    }
                },
                "/api/scheduler": {
                    "get": {
                        "tags": ["state"],
                        "summary": "Get scheduler status",
                        "description": "Get information about the scheduler and scheduled tasks",
                        "operationId": "getScheduler",
                        "responses": {
                            "200": {
                                "description": "Scheduler status",
                                "content": {"application/json": {"schema": {"type": "object"}}},
                            }
                        },
                    }
                },
                "/api/ui": {
                    "get": {
                        "tags": ["ui"],
                        "summary": "Get UI state",
                        "description": "Get UI geometry and layout information",
                        "operationId": "getUiState",
                        "responses": {
                            "200": {
                                "description": "UI state",
                                "content": {"application/json": {"schema": {"type": "object"}}},
                            }
                        },
                    }
                },
                "/api/ui/analysis": {
                    "get": {
                        "tags": ["ui"],
                        "summary": "Get UI analysis",
                        "description": "Get UI overlap analysis with grid representation",
                        "operationId": "getUiAnalysis",
                        "responses": {
                            "200": {
                                "description": "UI analysis",
                                "content": {"application/json": {"schema": {"type": "object"}}},
                            }
                        },
                    }
                },
                "/api/ui/screenshot/{panel}": {
                    "get": {
                        "tags": ["ui"],
                        "summary": "Capture screenshot",
                        "description": "Capture a screenshot of a UI panel",
                        "operationId": "captureScreenshot",
                        "parameters": [
                            {
                                "name": "panel",
                                "in": "path",
                                "required": True,
                                "schema": {
                                    "type": "string",
                                    "enum": [
                                        "task_list",
                                        "task_editor",
                                        "runs",
                                        "logs",
                                        "window",
                                        "all",
                                    ],
                                },
                                "description": "Panel to capture",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Screenshot captured",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/ScreenshotResponse"
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
            },
            "components": {
                "schemas": {
                    "HealthResponse": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "example": "ok"},
                            "message": {"type": "string", "example": "Debug server running"},
                        },
                    },
                    "SuccessResponse": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": True},
                            "message": {"type": "string"},
                        },
                    },
                    "ErrorResponse": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": False},
                            "error": {"type": "string"},
                        },
                    },
                    "Task": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "name": {"type": "string"},
                            "enabled": {"type": "boolean"},
                            "model": {
                                "type": "string",
                                "enum": ["opus", "sonnet", "haiku"],
                                "description": "Claude model to use",
                            },
                            "prompt": {
                                "type": "string",
                                "description": "The prompt text or slash command",
                            },
                            "prompt_type": {
                                "type": "string",
                                "enum": ["prompt", "slash_command"],
                            },
                            "permissions": {
                                "type": "string",
                                "enum": ["default", "bypass", "acceptEdits", "plan"],
                            },
                            "session_mode": {
                                "type": "string",
                                "enum": ["new", "reuse", "fork"],
                            },
                            "profile": {
                                "type": "string",
                                "nullable": True,
                                "description": "Profile ID for environment variables",
                            },
                            "schedule_type": {
                                "type": "string",
                                "enum": ["manual", "interval", "calendar", "startup", "file_watch"],
                            },
                        },
                    },
                    "TaskCreate": {
                        "type": "object",
                        "required": ["name", "prompt", "profile"],
                        "properties": {
                            "name": {"type": "string", "description": "Task name"},
                            "prompt": {
                                "type": "string",
                                "description": "The prompt text or slash command",
                            },
                            "model": {
                                "type": "string",
                                "enum": ["opus", "sonnet", "haiku"],
                                "default": "sonnet",
                            },
                            "enabled": {"type": "boolean", "default": False},
                            "permissions": {
                                "type": "string",
                                "enum": ["default", "bypass", "acceptEdits", "plan"],
                                "default": "bypass",
                            },
                            "session_mode": {
                                "type": "string",
                                "enum": ["new", "reuse", "fork"],
                                "default": "new",
                            },
                            "prompt_type": {
                                "type": "string",
                                "enum": ["prompt", "slash_command"],
                                "default": "prompt",
                            },
                            "profile": {
                                "type": "string",
                                "format": "uuid",
                                "description": "Profile ID (UUID) for env vars (required)",
                            },
                            "schedule": {
                                "$ref": "#/components/schemas/ScheduleConfig",
                                "description": "Schedule configuration",
                            },
                            "retry": {
                                "$ref": "#/components/schemas/RetryConfig",
                                "description": "Retry configuration for failed tasks",
                            },
                            "notifications": {
                                "$ref": "#/components/schemas/NotificationConfig",
                                "description": "Notification preferences",
                            },
                            "allowed_tools": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                                "description": "List of allowed tools (empty = all allowed)",
                            },
                            "disallowed_tools": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                                "description": "List of disallowed tools",
                            },
                        },
                    },
                    "TaskUpdate": {
                        "type": "object",
                        "description": "Partial update - only include fields to change",
                        "properties": {
                            "name": {"type": "string"},
                            "prompt": {"type": "string"},
                            "model": {
                                "type": "string",
                                "enum": ["opus", "sonnet", "haiku"],
                            },
                            "enabled": {"type": "boolean"},
                            "permissions": {
                                "type": "string",
                                "enum": ["default", "bypass", "acceptEdits", "plan"],
                            },
                            "session_mode": {
                                "type": "string",
                                "enum": ["new", "reuse", "fork"],
                            },
                            "command_type": {
                                "type": "string",
                                "enum": ["prompt", "slash_command"],
                            },
                            "profile": {"type": "string", "nullable": True},
                            "schedule": {"$ref": "#/components/schemas/ScheduleConfig"},
                            "retry": {"$ref": "#/components/schemas/RetryConfig"},
                            "notifications": {"$ref": "#/components/schemas/NotificationConfig"},
                            "allowed_tools": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "disallowed_tools": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                    "TaskResponse": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "task": {"$ref": "#/components/schemas/Task"},
                        },
                    },
                    "TaskList": {
                        "type": "object",
                        "properties": {
                            "tasks": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Task"},
                            }
                        },
                    },
                    "Run": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "task_id": {"type": "string", "format": "uuid"},
                            "task_name": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["upcoming", "running", "success", "failed", "cancelled"],
                            },
                            "scheduled_time": {
                                "type": "string",
                                "format": "date-time",
                                "nullable": True,
                            },
                            "start_time": {
                                "type": "string",
                                "format": "date-time",
                                "nullable": True,
                            },
                            "end_time": {"type": "string", "format": "date-time", "nullable": True},
                            "exit_code": {"type": "integer", "nullable": True},
                        },
                    },
                    "RunList": {
                        "type": "object",
                        "properties": {
                            "runs": {"type": "array", "items": {"$ref": "#/components/schemas/Run"}}
                        },
                    },
                    "RunResponse": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "run": {"$ref": "#/components/schemas/Run"},
                        },
                    },
                    "ApplicationState": {
                        "type": "object",
                        "properties": {
                            "tasks": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Task"},
                            },
                            "runs": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Run"},
                            },
                            "profiles": {"type": "array", "items": {"type": "object"}},
                            "settings": {"type": "object"},
                            "scheduler": {"type": "object"},
                        },
                    },
                    "ScreenshotResponse": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string"},
                            "panel": {"type": "string"},
                            "path": {
                                "type": "string",
                                "description": "File path to saved screenshot",
                            },
                            "timestamp": {"type": "string"},
                            "size": {
                                "type": "object",
                                "properties": {
                                    "width": {"type": "integer"},
                                    "height": {"type": "integer"},
                                },
                            },
                        },
                    },
                    "EnvVar": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Environment variable name",
                            },
                            "source": {
                                "type": "string",
                                "enum": [
                                    "static",
                                    "environment",
                                    "keychain",
                                    "aws_secrets_manager",
                                    "aws_ssm",
                                    "command",
                                ],
                                "description": "Source type for the value",
                            },
                            "value": {
                                "type": "string",
                                "description": "Source-specific reference string",
                            },
                            "config": {
                                "type": "object",
                                "nullable": True,
                                "description": "Additional config (e.g., AWS region, profile)",
                            },
                        },
                        "required": ["name", "source", "value"],
                    },
                    "ScheduleConfig": {
                        "type": "object",
                        "description": "Schedule configuration for task execution",
                        "properties": {
                            "schedule_type": {
                                "type": "string",
                                "enum": ["manual", "interval", "calendar", "startup", "file_watch"],
                                "default": "manual",
                                "description": "Type of schedule",
                            },
                            "timezone": {
                                "type": "string",
                                "default": "Europe/Amsterdam",
                                "description": "Timezone for schedule",
                            },
                            "calendar_frequency": {
                                "type": "string",
                                "enum": ["daily", "weekly", "monthly"],
                                "nullable": True,
                                "description": "Calendar frequency (for calendar type)",
                            },
                            "calendar_time": {
                                "type": "string",
                                "format": "time",
                                "nullable": True,
                                "description": "Time of day (HH:MM format)",
                            },
                            "calendar_days_of_week": {
                                "type": "array",
                                "items": {"type": "integer", "minimum": 0, "maximum": 6},
                                "nullable": True,
                                "description": "Days of week (0=Mon, 6=Sun) for weekly",
                            },
                            "calendar_day_of_month": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 31,
                                "nullable": True,
                                "description": "Day of month (1-31) for monthly",
                            },
                            "interval_type": {
                                "type": "string",
                                "enum": ["simple", "custom", "cron"],
                                "nullable": True,
                                "description": "Interval type (for interval schedule)",
                            },
                            "interval_preset": {
                                "type": "string",
                                "enum": ["5min", "15min", "30min", "1hour"],
                                "nullable": True,
                                "description": "Preset interval (for simple type)",
                            },
                            "interval_value": {
                                "type": "integer",
                                "nullable": True,
                                "description": "Custom interval value",
                            },
                            "interval_unit": {
                                "type": "string",
                                "enum": ["minutes", "hours", "days"],
                                "nullable": True,
                                "description": "Custom interval unit",
                            },
                            "interval_cron": {
                                "type": "string",
                                "nullable": True,
                                "description": "Cron expression (e.g., '0 */2 * * *')",
                            },
                            "watch_directory": {
                                "type": "string",
                                "nullable": True,
                                "description": "Directory to watch (for file_watch type)",
                            },
                            "watch_recursive": {
                                "type": "boolean",
                                "default": True,
                                "description": "Watch subdirectories recursively",
                            },
                            "watch_debounce_seconds": {
                                "type": "integer",
                                "default": 5,
                                "description": "Debounce delay after file change",
                            },
                        },
                    },
                    "RetryConfig": {
                        "type": "object",
                        "description": "Retry configuration for failed tasks",
                        "properties": {
                            "enabled": {
                                "type": "boolean",
                                "default": False,
                                "description": "Enable retry on failure",
                            },
                            "max_attempts": {
                                "type": "integer",
                                "default": 3,
                                "minimum": 1,
                                "maximum": 10,
                                "description": "Maximum retry attempts",
                            },
                            "delay_seconds": {
                                "type": "integer",
                                "default": 60,
                                "description": "Initial delay between retries (seconds)",
                            },
                            "backoff_multiplier": {
                                "type": "number",
                                "default": 2.0,
                                "description": "Backoff multiplier (1.0=fixed, 2.0=exponential)",
                            },
                        },
                    },
                    "NotificationConfig": {
                        "type": "object",
                        "description": "Notification preferences for task events",
                        "properties": {
                            "on_start": {
                                "type": "boolean",
                                "default": False,
                                "description": "Notify when task starts",
                            },
                            "on_end": {
                                "type": "boolean",
                                "default": False,
                                "description": "Notify when task completes successfully",
                            },
                            "on_failure": {
                                "type": "boolean",
                                "default": False,
                                "description": "Notify when task fails",
                            },
                        },
                    },
                    "Profile": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "env_vars": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/EnvVar"},
                            },
                            "created_at": {"type": "string", "format": "date-time"},
                            "updated_at": {"type": "string", "format": "date-time"},
                        },
                    },
                    "ProfileCreate": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string", "description": "Profile name"},
                            "description": {
                                "type": "string",
                                "description": "Optional description",
                            },
                            "env_vars": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/EnvVar"},
                                "description": "Environment variables",
                            },
                        },
                    },
                    "ProfileUpdate": {
                        "type": "object",
                        "description": "Partial update - only include fields to change",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "env_vars": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/EnvVar"},
                            },
                        },
                    },
                    "ProfileResponse": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "profile": {"$ref": "#/components/schemas/Profile"},
                        },
                    },
                    "ProfileList": {
                        "type": "object",
                        "properties": {
                            "profiles": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Profile"},
                            }
                        },
                    },
                    "JobWorkingDirectory": {
                        "type": "object",
                        "description": "Working directory configuration for a Job",
                        "properties": {
                            "path": {
                                "type": "string",
                                "default": "~/projects",
                                "description": "Base directory path",
                            },
                            "use_git_worktree": {
                                "type": "boolean",
                                "default": False,
                                "description": "If true, create/use git worktree",
                            },
                            "worktree_name": {
                                "type": "string",
                                "nullable": True,
                                "description": "Worktree name (default: job-{id[:8]})",
                            },
                            "worktree_branch": {
                                "type": "string",
                                "nullable": True,
                                "description": "Branch to checkout",
                            },
                        },
                    },
                    "Job": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "name": {"type": "string"},
                            "description": {"type": "string", "nullable": True},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed", "failed"],
                            },
                            "working_directory": {
                                "$ref": "#/components/schemas/JobWorkingDirectory",
                            },
                            "task_order": {
                                "type": "array",
                                "items": {"type": "string", "format": "uuid"},
                                "description": "Ordered list of task IDs for sequential execution",
                            },
                            "created_at": {"type": "string", "format": "date-time"},
                            "updated_at": {"type": "string", "format": "date-time"},
                        },
                    },
                    "JobCreate": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string", "description": "Job name"},
                            "description": {
                                "type": "string",
                                "description": "Optional description",
                            },
                            "working_directory": {
                                "$ref": "#/components/schemas/JobWorkingDirectory",
                                "description": "Working directory config (optional)",
                            },
                        },
                    },
                    "JobUpdate": {
                        "type": "object",
                        "description": "Partial update - only include fields to change",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed", "failed"],
                            },
                            "working_directory": {
                                "$ref": "#/components/schemas/JobWorkingDirectory",
                            },
                            "task_order": {
                                "type": "array",
                                "items": {"type": "string", "format": "uuid"},
                            },
                        },
                    },
                    "JobResponse": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "job": {"$ref": "#/components/schemas/Job"},
                        },
                    },
                    "JobList": {
                        "type": "object",
                        "properties": {
                            "jobs": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Job"},
                            }
                        },
                    },
                },
            },
        }

    def _get_full_state(self) -> dict[str, Any]:
        """Get full application state."""
        if self.state_provider:
            return self.state_provider()
        return {"error": "State provider not configured"}

    def _get_runs(self) -> dict[str, Any]:
        """Get runs from state."""
        state = self._get_full_state()
        return {"runs": state.get("runs", [])}

    def _get_tasks(self) -> dict[str, Any]:
        """Get tasks from state."""
        state = self._get_full_state()
        return {"tasks": state.get("tasks", [])}

    def _get_scheduler(self) -> dict[str, Any]:
        """Get scheduler info from state."""
        state = self._get_full_state()
        return {"scheduler": state.get("scheduler", {})}

    def _get_ui_state(self) -> dict[str, Any]:
        """Get UI geometry and layout state."""
        if self.ui_state_provider:
            return self.ui_state_provider()
        return {"error": "UI state provider not configured"}

    def _get_ui_analysis(self) -> dict[str, Any]:
        """Get UI overlap analysis with grid representation."""
        if self.ui_analysis_provider:
            return self.ui_analysis_provider()
        return {"error": "UI analysis provider not configured"}

    def _get_screenshot(self) -> dict[str, Any]:
        """Capture screenshot of UI panel."""
        # Extract panel name from path: /api/ui/screenshot/task_list -> task_list
        parts = self.path.split("/")
        panel_name = parts[-1] if len(parts) > 4 else "all"
        if self.screenshot_provider:
            return self.screenshot_provider(panel_name)
        return {"error": "Screenshot provider not configured"}

    def _send_json(self, data: dict[str, Any]) -> None:
        """Send JSON response."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode())

    def _send_error(self, code: int, message: str) -> None:
        """Send error response."""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())

    def _send_help(self) -> None:
        """Send self-describing API documentation."""
        api_doc = {
            "name": "Claude Code Scheduler GUI API",
            "version": "2.0.0",
            "description": "RESTful API for inspecting and controlling the GUI application",
            "base_url": f"http://127.0.0.1:{self.server_port}",
            "openapi_spec": f"http://127.0.0.1:{self.server_port}/api/openapi.json",
            "endpoints": {
                "read": {
                    "/": {
                        "method": "GET",
                        "description": "API documentation (this page)",
                    },
                    "/api/openapi.json": {
                        "method": "GET",
                        "description": "OpenAPI 3.0 specification for this API",
                    },
                    "/api/health": {
                        "method": "GET",
                        "description": "Health check - verify server is running",
                        "example_response": {"status": "ok"},
                    },
                    "/api/state": {
                        "method": "GET",
                        "description": "Full application state (tasks, runs, profiles, settings)",
                    },
                    "/api/tasks": {
                        "method": "GET",
                        "description": "List all configured tasks",
                    },
                    "/api/tasks/{id}": {
                        "method": "GET",
                        "description": "Get single task with full details",
                    },
                    "/api/runs": {
                        "method": "GET",
                        "description": "List all runs (including running processes)",
                    },
                    "/api/runs/{id}": {
                        "method": "GET",
                        "description": "Get single run with full details",
                    },
                    "/api/runs/{id}/logs": {
                        "method": "GET",
                        "description": "Get log content for a specific run",
                        "example_response": {"logs": "Task output log content here..."},
                    },
                    "/api/profiles": {
                        "method": "GET",
                        "description": "List all environment profiles",
                    },
                    "/api/profiles/{id}": {
                        "method": "GET",
                        "description": "Get single profile with full details",
                    },
                    "/api/scheduler": {
                        "method": "GET",
                        "description": "Scheduler status and scheduled job IDs",
                    },
                    "/api/ui": {
                        "method": "GET",
                        "description": "UI geometry and layout state",
                    },
                    "/api/ui/analysis": {
                        "method": "GET",
                        "description": "UI overlap analysis with grid and fix suggestions",
                    },
                    "/api/ui/screenshot/<panel>": {
                        "method": "GET",
                        "description": "Capture screenshot of a panel",
                        "panels": ["task_list", "task_editor", "runs", "logs", "window", "all"],
                    },
                },
                "write": {
                    "POST /api/tasks": {
                        "description": "Create a new task",
                        "body": {
                            "name": "string (required)",
                            "prompt": "string (required) - the prompt text for Claude Code",
                            "model": "string (default: sonnet)",
                            "enabled": "boolean (default: false)",
                            "job_id": "string (uuid, working dir from job)",
                            "schedule_type": "string (once|cron|interval|file_watch)",
                        },
                        "example": 'curl -X POST -H "Content-Type: application/json" '
                        '-d \'{"name":"Test","prompt":"Review the code"}\' '
                        f"http://127.0.0.1:{self.server_port}/api/tasks",
                    },
                    "PUT /api/tasks/{id}": {
                        "description": "Update an existing task",
                        "body": "Same fields as POST (partial update supported)",
                        "example": f"curl -X PUT -H 'Content-Type: application/json' "
                        f'-d \'{{"name":"Updated"}}\' '
                        f"http://127.0.0.1:{self.server_port}/api/tasks/{{uuid}}",
                    },
                    "DELETE /api/tasks/{id}": {
                        "description": "Delete a task",
                        "example": f"curl -X DELETE http://127.0.0.1:{self.server_port}"
                        "/api/tasks/{uuid}",
                    },
                    "POST /api/tasks/{id}/run": {
                        "description": "Run a task immediately",
                        "example": f"curl -X POST http://127.0.0.1:{self.server_port}"
                        "/api/tasks/{uuid}/run",
                    },
                    "POST /api/tasks/{id}/enable": {
                        "description": "Enable a task",
                        "example": f"curl -X POST http://127.0.0.1:{self.server_port}"
                        "/api/tasks/{uuid}/enable",
                    },
                    "POST /api/tasks/{id}/disable": {
                        "description": "Disable a task",
                        "example": f"curl -X POST http://127.0.0.1:{self.server_port}"
                        "/api/tasks/{uuid}/disable",
                    },
                    "POST /api/runs/{id}/stop": {
                        "description": "Stop a running task",
                        "example": f"curl -X POST http://127.0.0.1:{self.server_port}"
                        "/api/runs/{uuid}/stop",
                    },
                    "POST /api/runs/{id}/restart": {
                        "description": "Restart a task from a run",
                        "example": f"curl -X POST http://127.0.0.1:{self.server_port}"
                        "/api/runs/{uuid}/restart",
                    },
                    "DELETE /api/runs/{id}": {
                        "description": "Delete a run record",
                        "example": f"curl -X DELETE http://127.0.0.1:{self.server_port}"
                        "/api/runs/{uuid}",
                    },
                    "POST /api/profiles": {
                        "description": "Create a new profile",
                        "body": {
                            "name": "string (required)",
                            "description": "string (optional)",
                            "env_vars": "array of env var objects (optional)",
                        },
                        "example": 'curl -X POST -H "Content-Type: application/json" '
                        '-d \'{"name":"Production"}\' '
                        f"http://127.0.0.1:{self.server_port}/api/profiles",
                    },
                    "PUT /api/profiles/{id}": {
                        "description": "Update an existing profile",
                        "body": "Same fields as POST (partial update supported)",
                        "example": f"curl -X PUT -H 'Content-Type: application/json' "
                        f'-d \'{{"name":"Updated"}}\' '
                        f"http://127.0.0.1:{self.server_port}/api/profiles/{{uuid}}",
                    },
                    "DELETE /api/profiles/{id}": {
                        "description": "Delete a profile",
                        "example": f"curl -X DELETE http://127.0.0.1:{self.server_port}"
                        "/api/profiles/{uuid}",
                    },
                },
            },
            "usage": {
                "list_tasks": f"curl http://127.0.0.1:{self.server_port}/api/tasks",
                "create_task": f'curl -X POST -H "Content-Type: application/json" '
                f'-d \'{{"name":"Test","prompt":"Review the code"}}\' '
                f"http://127.0.0.1:{self.server_port}/api/tasks",
                "run_task": f"curl -X POST http://127.0.0.1:{self.server_port}"
                "/api/tasks/{uuid}/run",
            },
        }
        self._send_json(api_doc)


class DebugServer:
    """HTTP server for runtime debugging and control.

    Runs in a background thread and exposes endpoints for state inspection
    and write operations (task CRUD, run control).
    """

    def __init__(
        self,
        port: int = DEFAULT_DEBUG_PORT,
        # Read providers
        state_provider: Callable[[], dict[str, Any]] | None = None,
        ui_state_provider: Callable[[], dict[str, Any]] | None = None,
        ui_analysis_provider: Callable[[], dict[str, Any]] | None = None,
        screenshot_provider: Callable[[str], dict[str, Any]] | None = None,
        # Read providers for single items
        task_get_provider: Callable[[UUID], dict[str, Any]] | None = None,
        run_get_provider: Callable[[UUID], dict[str, Any]] | None = None,
        run_logs_provider: Callable[[UUID], str | None] | None = None,
        # Write providers (action callbacks)
        task_create_provider: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        task_update_provider: Callable[[UUID, dict[str, Any]], dict[str, Any]] | None = None,
        task_delete_provider: Callable[[UUID], dict[str, Any]] | None = None,
        task_run_provider: Callable[[UUID], dict[str, Any]] | None = None,
        task_enable_provider: Callable[[UUID, bool], dict[str, Any]] | None = None,
        run_stop_provider: Callable[[UUID], dict[str, Any]] | None = None,
        run_restart_provider: Callable[[UUID], dict[str, Any]] | None = None,
        run_delete_provider: Callable[[UUID], dict[str, Any]] | None = None,
        # Profile providers
        profile_list_provider: Callable[[], dict[str, Any]] | None = None,
        profile_get_provider: Callable[[UUID], dict[str, Any]] | None = None,
        profile_create_provider: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        profile_update_provider: Callable[[UUID, dict[str, Any]], dict[str, Any]] | None = None,
        profile_delete_provider: Callable[[UUID], dict[str, Any]] | None = None,
        # Job providers
        job_list_provider: Callable[[], dict[str, Any]] | None = None,
        job_get_provider: Callable[[UUID], dict[str, Any]] | None = None,
        job_create_provider: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        job_update_provider: Callable[[UUID, dict[str, Any]], dict[str, Any]] | None = None,
        job_delete_provider: Callable[[UUID], dict[str, Any]] | None = None,
        job_tasks_provider: Callable[[UUID], dict[str, Any]] | None = None,
        job_run_provider: Callable[[UUID], dict[str, Any]] | None = None,
        job_stop_provider: Callable[[UUID], dict[str, Any]] | None = None,
        job_export_provider: Callable[[UUID], dict[str, Any]] | None = None,
        job_export_file_provider: Callable[[UUID, str], dict[str, Any]] | None = None,
        job_import_provider: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        """Initialize debug server.

        Args:
            port: Port to listen on.
            state_provider: Callback that returns current application state.
            ui_state_provider: Callback that returns UI geometry state.
            ui_analysis_provider: Callback that returns UI overlap analysis.
            screenshot_provider: Callback that captures panel screenshots.
            task_get_provider: Callback to get a single task.
            run_get_provider: Callback to get a single run.
            run_logs_provider: Callback to get log content for a run.
            task_create_provider: Callback to create a new task.
            task_update_provider: Callback to update an existing task.
            task_delete_provider: Callback to delete a task.
            task_run_provider: Callback to run a task immediately.
            task_enable_provider: Callback to enable/disable a task.
            run_stop_provider: Callback to stop a running task.
            run_restart_provider: Callback to restart a task from a run.
            run_delete_provider: Callback to delete a run record.
            profile_list_provider: Callback to list all profiles.
            profile_get_provider: Callback to get a single profile.
            profile_create_provider: Callback to create a new profile.
            profile_update_provider: Callback to update a profile.
            profile_delete_provider: Callback to delete a profile.
            job_list_provider: Callback to list all jobs.
            job_get_provider: Callback to get a single job.
            job_create_provider: Callback to create a new job.
            job_update_provider: Callback to update a job.
            job_delete_provider: Callback to delete a job.
            job_tasks_provider: Callback to list tasks for a job.
            job_run_provider: Callback to run a job (start sequential execution).
            job_stop_provider: Callback to stop a running job.
            job_export_provider: Callback to export job and tasks as JSON.
            job_export_file_provider: Callback to export job and tasks to file.
            job_import_provider: Callback to import job from file.
        """
        self.port = port
        # Read providers
        self.state_provider = state_provider
        self.ui_state_provider = ui_state_provider
        self.ui_analysis_provider = ui_analysis_provider
        self.screenshot_provider = screenshot_provider
        # Read providers for single items
        self.task_get_provider = task_get_provider
        self.run_get_provider = run_get_provider
        self.run_logs_provider = run_logs_provider
        # Write providers
        self.task_create_provider = task_create_provider
        self.task_update_provider = task_update_provider
        self.task_delete_provider = task_delete_provider
        self.task_run_provider = task_run_provider
        self.task_enable_provider = task_enable_provider
        self.run_stop_provider = run_stop_provider
        self.run_restart_provider = run_restart_provider
        self.run_delete_provider = run_delete_provider
        # Profile providers
        self.profile_list_provider = profile_list_provider
        self.profile_get_provider = profile_get_provider
        self.profile_create_provider = profile_create_provider
        self.profile_update_provider = profile_update_provider
        self.profile_delete_provider = profile_delete_provider
        # Job providers
        self.job_list_provider = job_list_provider
        self.job_get_provider = job_get_provider
        self.job_create_provider = job_create_provider
        self.job_update_provider = job_update_provider
        self.job_delete_provider = job_delete_provider
        self.job_tasks_provider = job_tasks_provider
        self.job_run_provider = job_run_provider
        self.job_stop_provider = job_stop_provider
        self.job_export_provider = job_export_provider
        self.job_export_file_provider = job_export_file_provider
        self.job_import_provider = job_import_provider
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the debug server in a background thread."""
        # Set read providers and port on handler class
        DebugRequestHandler.state_provider = self.state_provider
        DebugRequestHandler.ui_state_provider = self.ui_state_provider
        DebugRequestHandler.ui_analysis_provider = self.ui_analysis_provider
        DebugRequestHandler.screenshot_provider = self.screenshot_provider
        # Set single item read providers on handler class
        DebugRequestHandler.task_get_provider = self.task_get_provider
        DebugRequestHandler.run_get_provider = self.run_get_provider
        DebugRequestHandler.run_logs_provider = self.run_logs_provider
        # Set write providers on handler class
        DebugRequestHandler.task_create_provider = self.task_create_provider
        DebugRequestHandler.task_update_provider = self.task_update_provider
        DebugRequestHandler.task_delete_provider = self.task_delete_provider
        DebugRequestHandler.task_run_provider = self.task_run_provider
        DebugRequestHandler.task_enable_provider = self.task_enable_provider
        DebugRequestHandler.run_stop_provider = self.run_stop_provider
        DebugRequestHandler.run_restart_provider = self.run_restart_provider
        DebugRequestHandler.run_delete_provider = self.run_delete_provider
        # Set profile providers on handler class
        DebugRequestHandler.profile_list_provider = self.profile_list_provider
        DebugRequestHandler.profile_get_provider = self.profile_get_provider
        DebugRequestHandler.profile_create_provider = self.profile_create_provider
        DebugRequestHandler.profile_update_provider = self.profile_update_provider
        DebugRequestHandler.profile_delete_provider = self.profile_delete_provider
        # Set job providers on handler class
        DebugRequestHandler.job_list_provider = self.job_list_provider
        DebugRequestHandler.job_get_provider = self.job_get_provider
        DebugRequestHandler.job_create_provider = self.job_create_provider
        DebugRequestHandler.job_update_provider = self.job_update_provider
        DebugRequestHandler.job_delete_provider = self.job_delete_provider
        DebugRequestHandler.job_tasks_provider = self.job_tasks_provider
        DebugRequestHandler.job_run_provider = self.job_run_provider
        DebugRequestHandler.job_stop_provider = self.job_stop_provider
        DebugRequestHandler.job_export_provider = self.job_export_provider
        DebugRequestHandler.job_export_file_provider = self.job_export_file_provider
        DebugRequestHandler.job_import_provider = self.job_import_provider
        DebugRequestHandler.server_port = self.port

        try:
            self._server = HTTPServer(("127.0.0.1", self.port), DebugRequestHandler)
            self._thread = threading.Thread(target=self._serve, daemon=True)
            self._thread.start()
            logger.info("Debug server started on http://127.0.0.1:%d", self.port)
        except OSError as e:
            logger.warning("Could not start debug server on port %d: %s", self.port, e)

    def _serve(self) -> None:
        """Serve requests (runs in background thread)."""
        if self._server:
            self._server.serve_forever()

    def stop(self) -> None:
        """Stop the debug server."""
        if self._server:
            self._server.shutdown()
            logger.info("Debug server stopped")
