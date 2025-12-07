"""Task Executor for Claude Code Scheduler.

This module handles execution of scheduled tasks using the Claude Code CLI
or mock mode for testing. It manages subprocess lifecycle, output streaming,
and run record creation.

Key Components:
    - TaskExecutor: Main executor class for task execution
    - find_claude_cli: Locate Claude Code CLI executable

Dependencies:
    - subprocess: Process execution
    - shutil: CLI path detection
    - json: JSONL output parsing
    - models.task: Task data model
    - models.run: Run record data model
    - models.profile: Profile for environment variables
    - services.env_resolver: Environment variable resolution

Related Modules:
    - services.scheduler: Schedules tasks for execution
    - services.sequential_scheduler: Sequential job execution
    - storage.config_storage: Persists run records

Calls:
    - EnvVarResolver.resolve_profile: Resolve profile environment variables
    - subprocess.Popen: Execute CLI subprocess

Called By:
    - TaskScheduler.execute_task: Scheduled task execution
    - SequentialScheduler: Job task execution

Example:
    >>> from claude_code_scheduler.services.executor import TaskExecutor
    >>> executor = TaskExecutor(mock_mode=False)
    >>> run = executor.execute(task, profile)

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import json
import os
import random
import shlex
import shutil
import subprocess  # nosec B404 - required for CLI execution
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from claude_code_scheduler.logging_config import get_logger
from claude_code_scheduler.models.enums import RunStatus
from claude_code_scheduler.models.profile import Profile
from claude_code_scheduler.models.run import Run
from claude_code_scheduler.models.task import Task
from claude_code_scheduler.services.env_resolver import EnvVarResolver

logger = get_logger(__name__)


def find_claude_cli() -> str | None:
    """Find the Claude Code CLI executable.

    Returns:
        Path to claude CLI or None if not found.
    """
    # Check common locations
    cli_path = shutil.which("claude")
    if cli_path:
        return cli_path

    # Check ~/.claude/local/claude
    local_claude = Path.home() / ".claude" / "local" / "claude"
    if local_claude.exists():
        return str(local_claude)

    # Check npm global
    npm_claude = shutil.which("npx")
    if npm_claude:
        # Could use npx claude but prefer direct path
        pass

    return None


class TaskExecutor:
    """Executes tasks and produces Run records.

    In mock mode, generates simulated JSONL output.
    In real mode (Milestone 7), will invoke Claude Code CLI.
    """

    def __init__(
        self,
        on_run_started: Callable[[Run], None] | None = None,
        on_run_completed: Callable[[Run], None] | None = None,
        on_output: Callable[[UUID, str], None] | None = None,
        mock_mode: bool = True,
        unmask_env_vars: bool = False,
        log_dir: str | None = None,
    ) -> None:
        """Initialize executor.

        Args:
            on_run_started: Callback when a run starts.
            on_run_completed: Callback when a run completes.
            on_output: Callback for streaming output (run_id, line).
            mock_mode: If True, generate mock output instead of calling CLI.
            unmask_env_vars: If True, show full env var values in debug logs.
            log_dir: Directory for output log files (default: ~/.claude-scheduler/logs).
        """
        self.on_run_started = on_run_started
        self.on_run_completed = on_run_completed
        self.on_output = on_output
        self.mock_mode = mock_mode
        self.unmask_env_vars = unmask_env_vars
        self.log_dir = Path(log_dir) if log_dir else Path.home() / ".claude-scheduler" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        # Track running processes by run_id for stopping
        self._running_processes: dict[UUID, subprocess.Popen[str]] = {}
        # Track runs that were manually stopped (to set CANCELLED status)
        self._stopped_runs: set[UUID] = set()

    def execute(
        self,
        task: Task,
        profile: Profile | None = None,
        working_directory: str | None = None,
    ) -> Run:
        """Execute a task and return the resulting Run.

        Args:
            task: The task to execute.
            profile: Optional profile with environment variables to set.
            working_directory: Working directory for execution (from Job).
                              Defaults to ~/projects if not specified.

        Returns:
            Run record with execution results.
        """
        logger.info("Executing task: %s", task.name)

        # Resolve profile environment variables
        resolved_env: dict[str, str] = {}
        if profile:
            logger.info("Resolving env vars from profile: %s", profile.name)
            resolver = EnvVarResolver()
            resolved_env = resolver.resolve_profile(profile)
            logger.debug("Resolved %d env vars", len(resolved_env))

        # Create run record
        run = Run(
            id=uuid4(),
            task_id=task.id,
            task_name=task.name,
            status=RunStatus.RUNNING,
            scheduled_time=datetime.now(),
            start_time=datetime.now(),
            session_id=uuid4(),  # Mock session ID
        )

        # Notify start
        if self.on_run_started:
            self.on_run_started(run)

        try:
            if self.mock_mode:
                self._execute_mock(run, task)
            else:
                self._execute_real(run, task, resolved_env, working_directory)

            run.status = RunStatus.SUCCESS
            run.exit_code = 0

            # Auto-commit changes if enabled and working directory is set
            if task.commit_on_success and working_directory:
                self._commit_changes(task, working_directory)
        except Exception as e:
            logger.error("Task execution failed: %s", e)
            # Check if this was a manual stop (CANCELLED) vs failure
            if run.id in self._stopped_runs:
                run.status = RunStatus.CANCELLED
                run.errors = "Task was manually stopped"
                self._stopped_runs.discard(run.id)
            else:
                run.status = RunStatus.FAILED
                run.errors = str(e)
            run.exit_code = 1

        # Set end time and duration
        run.end_time = datetime.now()
        if run.start_time:
            run.duration = run.end_time - run.start_time

        # Notify completion
        if self.on_run_completed:
            self.on_run_completed(run)

        logger.info(
            "Task completed: %s (status=%s, duration=%s)",
            task.name,
            run.status.value,
            run.duration,
        )

        return run

    def _execute_mock(self, run: Run, task: Task) -> None:
        """Execute task in mock mode with simulated output.

        Args:
            run: The run record to populate.
            task: The task being executed.
        """
        # Simulate execution time (0.5-2 seconds)
        exec_time = random.uniform(0.5, 2.0)  # nosec B311 - mock data only
        time.sleep(exec_time)

        # Generate mock JSONL output
        jsonl_lines = self._generate_mock_jsonl(task, run.session_id)
        run.raw_output = "\n".join(jsonl_lines)

        # Generate formatted output from JSONL
        run.output = self._format_jsonl_output(jsonl_lines)

    def _execute_real(
        self,
        run: Run,
        task: Task,
        env_vars: dict[str, str] | None = None,
        working_directory: str | None = None,
    ) -> None:
        """Execute task using Claude Code CLI.

        Args:
            run: The run record to populate.
            task: The task being executed.
            env_vars: Optional environment variables to set for the subprocess.
            working_directory: Working directory for execution (from Job).

        Raises:
            RuntimeError: If Claude CLI not found or execution fails.
        """
        cli_path = find_claude_cli()
        if not cli_path:
            raise RuntimeError(
                "Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
            )

        # Build command
        cmd = [cli_path]

        # Print mode for non-interactive output
        cmd.extend(["--print"])

        # Verbose mode required for stream-json output format
        cmd.extend(["--verbose"])

        # Output format - stream-json for JSONL
        cmd.extend(["--output-format", "stream-json"])

        # Model selection
        if task.model:
            cmd.extend(["--model", task.model])

        # Permission mode mapping
        perm_map = {
            "default": "default",
            "bypass": "bypassPermissions",
            "acceptEdits": "acceptEdits",
            "plan": "plan",
        }
        perm_mode = perm_map.get(task.permissions, "default")
        cmd.extend(["--permission-mode", perm_mode])

        # Session handling
        if run.session_id:
            cmd.extend(["--session-id", str(run.session_id)])

        # Session mode (resume, fork)
        if task.session_mode == "reuse":
            cmd.extend(["--continue"])
        elif task.session_mode == "fork":
            cmd.extend(["--continue", "--fork-session"])

        # Tool restrictions
        if task.allowed_tools:
            cmd.extend(["--allowed-tools", ",".join(task.allowed_tools)])
        if task.disallowed_tools:
            cmd.extend(["--disallowed-tools", ",".join(task.disallowed_tools)])

        # Add the prompt text
        prompt_text = task.prompt or task.name
        cmd.append(prompt_text)

        # Set working directory (from Job, or default to ~/projects)
        wd_path = working_directory or "~/projects"
        working_dir = os.path.expanduser(wd_path)
        working_dir = os.path.expandvars(working_dir)

        if not Path(working_dir).exists():
            working_dir = str(Path.home())
            logger.warning("Working directory not found, using home: %s", working_dir)

        # Build environment - inherit current env and add profile vars
        exec_env = os.environ.copy()
        logger.debug(
            "Base environment has %d vars, ANTHROPIC/CLAUDE vars: %s",
            len(exec_env),
            [k for k in exec_env.keys() if "ANTHROPIC" in k or "CLAUDE" in k],
        )
        if env_vars:
            # Import sentinel for unset detection
            from claude_code_scheduler.services.env_resolver import EnvVarResolver

            unset_count = 0
            set_count = 0
            skip_count = 0
            for key, value in env_vars.items():
                if value == EnvVarResolver.UNSET_SENTINEL:
                    # UNSET: delete from environment
                    if key in exec_env:
                        del exec_env[key]
                        logger.debug("  ENV UNSET: %s (was set)", key)
                    else:
                        logger.debug("  ENV UNSET: %s (was not set)", key)
                    unset_count += 1
                elif value == "" or value is None:
                    # SKIP: empty values are skipped to avoid overriding with empty
                    logger.warning("  ENV SKIP: %s (empty value - would break auth)", key)
                    skip_count += 1
                else:
                    # SET: add/update in environment
                    exec_env[key] = value
                    if self.unmask_env_vars:
                        logger.debug("  ENV SET: %s=%s", key, value)
                    else:
                        # Mask sensitive values (show first 4 chars only)
                        masked = value[:4] + "****" if len(value) > 4 else "****"
                        logger.debug("  ENV SET: %s=%s", key, masked)
                    set_count += 1
            logger.info(
                "Profile env vars: %d set, %d unset, %d skipped", set_count, unset_count, skip_count
            )

        # Log effective values of all ANTHROPIC/CLAUDE env vars for debugging
        relevant_vars = {
            k: v for k, v in exec_env.items() if "ANTHROPIC" in k or "CLAUDE" in k or "API" in k
        }
        logger.info("Effective ANTHROPIC/CLAUDE/API env vars (%d):", len(relevant_vars))
        for key, value in sorted(relevant_vars.items()):
            if self.unmask_env_vars:
                logger.info("  %s=%s", key, value)
            else:
                masked = value[:4] + "****" if len(value) > 4 else "****"
                logger.info("  %s=%s", key, masked)

        logger.info("Executing: %s", shlex.join(cmd))
        logger.debug("Working directory: %s", working_dir)
        logger.debug("Full command: %s", cmd)

        # Create log file for this run
        log_file_path = self.log_dir / f"run_{run.id}.log"
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        # Execute the CLI with streaming output
        try:
            with open(log_file_path, "w") as log_file:  # nosec B603
                process = subprocess.Popen(  # nosec B603 - CLI path is validated
                    cmd,
                    cwd=working_dir,
                    env=exec_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # Line buffered
                )
                # Track process for potential stopping
                self._running_processes[run.id] = process

                logger.debug(
                    "Subprocess started: pid=%d, run_id=%s, task=%s",
                    process.pid,
                    run.id,
                    run.task_name,
                )
                logger.debug(
                    "Subprocess tracking: %d active processes",
                    len(self._running_processes),
                )

                # Stream stdout in real-time
                line_count = 0
                if process.stdout:
                    for line in process.stdout:
                        stdout_lines.append(line)
                        line_count += 1
                        # Write to log file
                        log_file.write(line)
                        log_file.flush()
                        # Stream to console with prefix for observability
                        prefixed_line = f"[STDOUT] {line}"
                        sys.stdout.write(prefixed_line)
                        sys.stdout.flush()
                        # Stream to callback with run ID
                        if self.on_output:
                            self.on_output(run.id, line)
                        # Log progress every 100 lines
                        if line_count % 100 == 0:
                            logger.debug(
                                "Subprocess pid=%d: read %d stdout lines",
                                process.pid,
                                line_count,
                            )

                logger.debug(
                    "Subprocess pid=%d: stdout complete (%d lines), waiting for stderr",
                    process.pid,
                    line_count,
                )

                # Wait for process to complete and get stderr
                _, stderr = process.communicate()

                logger.debug(
                    "Subprocess pid=%d: communicate() returned, exit_code=%s",
                    process.pid,
                    process.returncode,
                )

                if stderr:
                    stderr_lines = stderr.splitlines(keepends=True)
                    logger.debug(
                        "Subprocess pid=%d: captured %d stderr lines",
                        process.pid,
                        len(stderr_lines),
                    )
                    for line in stderr_lines:
                        prefixed_line = f"[STDERR] {line}"
                        log_file.write(prefixed_line)
                        # Stream to console stderr for observability
                        sys.stderr.write(prefixed_line)
                        sys.stderr.flush()
                        if self.on_output:
                            self.on_output(run.id, prefixed_line)

            run.raw_output = "".join(stdout_lines)
            run.errors = "".join(stderr_lines)
            run.exit_code = process.returncode

            # Parse JSONL output
            jsonl_lines = [line for line in run.raw_output.split("\n") if line.strip()]
            run.output = self._format_jsonl_output(jsonl_lines)

            # Extract session ID from output if available
            for line in jsonl_lines:
                try:
                    data = json.loads(line)
                    if data.get("type") == "system" and data.get("subtype") == "init":
                        session_id_str = data.get("session_id")
                        if session_id_str:
                            run.session_id = UUID(session_id_str)
                        break
                except (json.JSONDecodeError, ValueError):
                    continue

            if process.returncode != 0:
                raise RuntimeError(
                    f"CLI exited with code {process.returncode}: {''.join(stderr_lines)}"
                )

        except Exception as e:
            logger.error("Execution failed: %s", e)
            logger.debug(
                "Subprocess exception details: run_id=%s, error_type=%s",
                run.id,
                type(e).__name__,
            )
            run.errors = str(e)
            raise
        finally:
            # Remove from tracking
            removed = self._running_processes.pop(run.id, None)
            logger.debug(
                "Subprocess cleanup: run_id=%s, was_tracked=%s, remaining=%d",
                run.id,
                removed is not None,
                len(self._running_processes),
            )

    def stop_run(self, run_id: UUID) -> bool:
        """Stop a running process by its run ID.

        Args:
            run_id: UUID of the run to stop.

        Returns:
            True if the process was stopped, False if not found or already stopped.
        """
        logger.debug(
            "stop_run called: run_id=%s, tracked_processes=%s",
            run_id,
            list(self._running_processes.keys()),
        )

        process = self._running_processes.get(run_id)
        if process is None:
            logger.warning("No running process found for run: %s", run_id)
            logger.debug(
                "stop_run failed: run_id=%s not in tracking dict (size=%d)",
                run_id,
                len(self._running_processes),
            )
            return False

        logger.info("Terminating process for run: %s (pid=%d)", run_id, process.pid)
        logger.debug(
            "Process state before terminate: pid=%d, poll=%s",
            process.pid,
            process.poll(),
        )

        # Mark as stopped so we set CANCELLED status instead of FAILED
        self._stopped_runs.add(run_id)

        # Write cancellation message to log file
        log_file_path = self.log_dir / f"run_{run_id}.log"
        try:
            with open(log_file_path, "a") as log_file:
                log_file.write("\n[CANCELLED] Task was manually stopped by user\n")
            # Also stream to output callback
            if self.on_output:
                self.on_output(run_id, "\n[CANCELLED] Task was manually stopped by user\n")
        except Exception as e:
            logger.warning("Could not write cancellation to log: %s", e)

        try:
            logger.debug("Sending SIGTERM to pid=%d", process.pid)
            process.terminate()
            # Wait briefly for graceful termination
            try:
                exit_code = process.wait(timeout=3)
                logger.debug(
                    "Process pid=%d terminated gracefully, exit_code=%s",
                    process.pid,
                    exit_code,
                )
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                logger.warning(
                    "Process did not terminate, killing: %s (pid=%d)", run_id, process.pid
                )
                logger.debug("Sending SIGKILL to pid=%d", process.pid)
                process.kill()
                exit_code = process.wait()
                logger.debug(
                    "Process pid=%d killed, exit_code=%s",
                    process.pid,
                    exit_code,
                )
            return True
        except Exception as e:
            logger.error("Failed to stop process: %s", e)
            logger.debug(
                "stop_run exception: pid=%d, error_type=%s, error=%s",
                process.pid,
                type(e).__name__,
                e,
            )
            return False

    def _commit_changes(self, task: Task, working_directory: str) -> None:
        """Commit changes after successful task execution.

        Args:
            task: The task that was executed.
            working_directory: The working directory where git operations should be performed.
        """
        try:
            # Expand working directory path
            work_dir = os.path.expanduser(working_directory)
            work_dir = os.path.expandvars(work_dir)

            # Check if the directory exists and is a git repository
            if not Path(work_dir).exists():
                logger.warning("Cannot commit: working directory does not exist: %s", work_dir)
                return

            git_dir = Path(work_dir) / ".git"
            if not git_dir.exists():
                logger.warning("Cannot commit: not a git repository: %s", work_dir)
                return

            # Build git command
            commit_message = f"task: {task.name}"
            cmd = ["git", "-C", work_dir, "add", "-A"]

            logger.info("Running git add in %s", work_dir)
            result = subprocess.run(  # nosec: B603, B607
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
            )

            if result.returncode != 0:
                logger.warning("Git add failed in %s: %s", work_dir, result.stderr.strip())
                return

            # Check if there are any changes to commit
            status_cmd = ["git", "-C", work_dir, "status", "--porcelain"]
            status_result = subprocess.run(  # nosec: B603, B607
                status_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if status_result.returncode != 0:
                logger.warning(
                    "Git status check failed in %s: %s", work_dir, status_result.stderr.strip()
                )
                return

            # If no changes to commit, skip commit
            if not status_result.stdout.strip():
                logger.info("No changes to commit in %s", work_dir)
                return

            # Commit the changes
            commit_cmd = ["git", "-C", work_dir, "commit", "-m", commit_message]
            logger.info("Running git commit in %s with message: %s", work_dir, commit_message)

            commit_result = subprocess.run(  # nosec: B603, B607
                commit_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if commit_result.returncode != 0:
                logger.warning(
                    "Git commit failed in %s: %s", work_dir, commit_result.stderr.strip()
                )
            else:
                logger.info(
                    "Successfully committed changes in %s: %s",
                    work_dir,
                    commit_result.stdout.strip(),
                )

        except subprocess.TimeoutExpired:
            logger.warning("Git command timed out in %s", working_directory)
        except Exception as e:
            logger.warning("Failed to commit changes in %s: %s", working_directory, e)

    def _generate_mock_jsonl(self, task: Task, session_id: UUID | None) -> list[str]:
        """Generate mock JSONL output simulating Claude Code CLI.

        Args:
            task: The task being executed.
            session_id: The session ID for this execution.

        Returns:
            List of JSONL lines.
        """
        lines: list[str] = []

        # System init message
        lines.append(
            json.dumps(
                {
                    "type": "system",
                    "subtype": "init",
                    "session_id": str(session_id) if session_id else None,
                    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                    "model": task.model,
                }
            )
        )

        # Assistant thinking
        lines.append(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": f"I'll help you with: {task.prompt or task.name}",
                    },
                }
            )
        )

        # Simulate some tool calls based on task
        mock_actions = [
            {
                "type": "tool_use",
                "tool": "Read",
                "input": {"file_path": "/mock/path/file.py"},
            },
            {
                "type": "tool_result",
                "tool": "Read",
                "output": "# Mock file content\nprint('hello world')",
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": "I've analyzed the file. Here's what I found...",
                },
            },
        ]

        for action in mock_actions:
            lines.append(json.dumps(action))

        # Final result
        lines.append(
            json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "cost_usd": round(random.uniform(0.001, 0.05), 4),  # nosec B311
                    "duration_ms": random.randint(500, 2000),  # nosec B311
                    "duration_api_ms": random.randint(400, 1800),  # nosec B311
                    "num_turns": random.randint(1, 5),  # nosec B311
                }
            )
        )

        return lines

    def _format_jsonl_output(self, jsonl_lines: list[str]) -> str:
        """Format JSONL output into human-readable text.

        Args:
            jsonl_lines: Raw JSONL lines.

        Returns:
            Formatted output string.
        """
        formatted_parts: list[str] = []

        for line in jsonl_lines:
            try:
                data = json.loads(line)
                msg_type = data.get("type", "")

                if msg_type == "system" and data.get("subtype") == "init":
                    model = data.get("model", "unknown")
                    formatted_parts.append(f"[Session started with model: {model}]")

                elif msg_type == "assistant":
                    content = data.get("message", {}).get("content", "")
                    if content:
                        formatted_parts.append(f"Claude: {content}")

                elif msg_type == "tool_use":
                    tool = data.get("tool", "unknown")
                    formatted_parts.append(f"[Using tool: {tool}]")

                elif msg_type == "tool_result":
                    tool = data.get("tool", "unknown")
                    output = data.get("output", "")
                    if output:
                        preview = output[:100] + "..." if len(output) > 100 else output
                        formatted_parts.append(f"[{tool} result: {preview}]")

                elif msg_type == "result":
                    cost = data.get("cost_usd", 0)
                    turns = data.get("num_turns", 0)
                    formatted_parts.append(f"\n[Completed: {turns} turns, ${cost:.4f}]")

            except json.JSONDecodeError:
                continue

        return "\n".join(formatted_parts)
