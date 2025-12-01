"""
macOS integration service for Finder and Terminal operations.

Provides AppleScript utilities for opening directories in Finder
and running commands in Terminal.app.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import shlex
import subprocess  # nosec B404 - required for AppleScript execution
from pathlib import Path

from claude_code_scheduler.logging_config import get_logger

logger = get_logger(__name__)


class AppleScriptService:
    """Service for interacting with macOS applications via AppleScript."""

    def __init__(self) -> None:
        """Initialize the AppleScript service."""
        self._finder_template = """
        tell application "Finder"
            activate
            open POSIX file "{path}"
        end tell
        """

        self._terminal_template = """
        tell application "Terminal"
            activate
            do script "cd {working_dir}
{env_exports}
{command}"
        end tell
        """

        self._terminal_new_window_template = """
        tell application "Terminal"
            activate
            do script "cd {working_dir}
{env_exports}
{command}" in window 1
        end tell
        """

    def is_available(self) -> bool:
        """Check if AppleScript is available on this system.

        Returns:
            True if running on macOS with osascript available, False otherwise.
        """
        try:
            # Test if osascript is available
            result = subprocess.run(  # nosec: B603, B607
                ["osascript", "-e", 'return "available"'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            available = result.returncode == 0 and "available" in result.stdout
            if available:
                logger.debug("AppleScript service is available")
            else:
                logger.debug("AppleScript service is not available")
            return available
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug("AppleScript availability check failed: %s", e)
            return False

    def open_finder(self, path: str | Path) -> bool:
        """Open a directory in Finder.

        Args:
            path: Directory path to open in Finder.

        Returns:
            True if the directory was successfully opened, False otherwise.
        """
        if not self.is_available():
            logger.warning("AppleScript service is not available")
            return False

        try:
            # Convert to Path object if needed
            dir_path = Path(path)

            if not dir_path.exists():
                logger.warning("Directory does not exist: %s", dir_path)
                return False

            if not dir_path.is_dir():
                logger.warning("Path is not a directory: %s", dir_path)
                return False

            # Escape path for AppleScript
            escaped_path = str(dir_path.resolve()).replace('"', '\\"')

            # Build the AppleScript
            applescript = self._finder_template.format(path=escaped_path).strip()

            logger.debug("Opening directory in Finder: %s", escaped_path)

            # Execute the AppleScript
            result = subprocess.run(  # nosec: B603, B607
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                logger.info("Successfully opened directory in Finder: %s", dir_path)
                return True
            else:
                logger.warning(
                    "Failed to execute Finder AppleScript: %s (stderr: %s)",
                    result.stdout.strip(),
                    result.stderr.strip(),
                )
                return False

        except subprocess.TimeoutExpired:
            logger.warning("Finder AppleScript execution timed out")
            return False
        except subprocess.SubprocessError as e:
            logger.warning("Finder AppleScript execution failed: %s", e)
            return False
        except Exception as e:
            logger.warning("Unexpected error opening Finder: %s", e)
            return False

    def run_in_terminal(
        self,
        command: str,
        working_dir: str | Path,
        env_vars: dict[str, str] | None = None,
        new_window: bool = True,
    ) -> bool:
        """Run a command in Terminal.app.

        Args:
            command: Command to run in the terminal.
            working_dir: Working directory for the command.
            env_vars: Optional dictionary of environment variables to export.
            new_window: Whether to open a new terminal window (True) or use existing (False).

        Returns:
            True if the command was successfully started in Terminal, False otherwise.
        """
        if not self.is_available():
            logger.warning("AppleScript service is not available")
            return False

        try:
            # Convert to Path object if needed
            work_dir = Path(working_dir)

            if not work_dir.exists():
                logger.warning("Working directory does not exist: %s", work_dir)
                return False

            if not work_dir.is_dir():
                logger.warning("Working directory is not a directory: %s", work_dir)
                return False

            # Prepare environment variable exports
            env_exports = []
            if env_vars:
                for key, value in env_vars.items():
                    if value:  # Skip empty values
                        # Use shlex.quote for proper shell escaping
                        escaped_key = shlex.quote(key)
                        escaped_value = shlex.quote(value)
                        env_exports.append(f"export {escaped_key}={escaped_value}")

            env_exports_str = "\n".join(env_exports)

            # Escape working directory for AppleScript
            escaped_working_dir = str(work_dir.resolve()).replace('"', '\\"')

            # Choose the appropriate template
            template = self._terminal_new_window_template if new_window else self._terminal_template

            # Build the complete AppleScript
            applescript = template.format(
                working_dir=escaped_working_dir,
                env_exports=env_exports_str,
                command=command,
            ).strip()

            logger.debug(
                "Running command in Terminal: %s in %s",
                command,
                escaped_working_dir,
            )

            if env_vars:
                env_count = len([v for v in env_vars.values() if v])
                logger.debug("Exporting %d environment variables", env_count)

            # Execute the AppleScript
            result = subprocess.run(  # nosec: B603, B607
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                logger.info("Successfully started command in Terminal")
                return True
            else:
                logger.warning(
                    "Failed to execute Terminal AppleScript: %s (stderr: %s)",
                    result.stdout.strip(),
                    result.stderr.strip(),
                )
                return False

        except subprocess.TimeoutExpired:
            logger.warning("Terminal AppleScript execution timed out")
            return False
        except subprocess.SubprocessError as e:
            logger.warning("Terminal AppleScript execution failed: %s", e)
            return False
        except Exception as e:
            logger.warning("Unexpected error running command in Terminal: %s", e)
            return False

    def get_log_directory_path(self) -> Path:
        """Get the path to the log directory.

        Returns:
            Path to the ~/.claude-scheduler/logs directory.
        """
        return Path.home() / ".claude-scheduler" / "logs"

    def open_log_directory(self) -> bool:
        """Open the log directory in Finder.

        Returns:
            True if the log directory was successfully opened, False otherwise.
        """
        log_dir = self.get_log_directory_path()

        # Create the directory if it doesn't exist
        log_dir.mkdir(parents=True, exist_ok=True)

        return self.open_finder(log_dir)

    def build_claude_command(
        self,
        task_command: str,
        task_command_type: str = "prompt",
        task_model: str = "sonnet",
        task_profile: str | None = None,
        task_permissions: str = "default",
        task_session_mode: str = "new",
    ) -> str:
        """Build a claude CLI command from task parameters.

        Args:
            task_command: The command or prompt text.
            task_command_type: Type of command ("prompt" or "slash_command").
            task_model: Model to use (sonnet, opus, haiku).
            task_profile: Profile ID to use.
            task_permissions: Permissions setting.
            task_session_mode: Session mode.

        Returns:
            Complete claude CLI command as a string.
        """
        # Start with base command
        parts = ["claude"]

        # Add model flag
        parts.extend(["--model", task_model])

        # Add profile if specified
        if task_profile:
            parts.extend(["--profile", task_profile])

        # Add permissions if not default
        if task_permissions != "default":
            parts.extend(["--permissions", task_permissions])

        # Add session mode if not new
        if task_session_mode != "new":
            parts.extend(["--session-mode", task_session_mode])

        # Add the command itself
        if task_command_type == "slash_command" and not task_command.startswith("/"):
            # Ensure slash commands start with /
            command = f"/{task_command}"
        else:
            command = task_command

        parts.append(command)

        return " ".join(parts)
