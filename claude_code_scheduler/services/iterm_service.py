"""
iTerm2 integration service for launching Claude Code sessions.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import os
import shlex
import subprocess  # nosec B404 - required for AppleScript/iTerm execution

from claude_code_scheduler.logging_config import get_logger

logger = get_logger(__name__)


class ITermService:
    """Service for interacting with iTerm2 to launch Claude Code sessions."""

    def __init__(self) -> None:
        """Initialize the iTerm2 service."""
        self._applescript_template = """
        tell application "iTerm2"
            activate
            create window with default profile
            tell current session of current window
                write text "cd {working_dir}"
                {env_exports}
                write text "claude {command_args}"
            end tell
        end tell
        """

    def is_available(self) -> bool:
        """Check if iTerm2 is installed and available.

        Returns:
            True if iTerm2 is installed and can be controlled via AppleScript,
            False otherwise.
        """
        try:
            # Test if iTerm2 is installed and responds to AppleScript
            result = subprocess.run(  # nosec: B603, B607
                ["osascript", "-e", 'tell application "iTerm2" to get version'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            available = result.returncode == 0
            if available:
                logger.debug("iTerm2 is available (version: %s)", result.stdout.strip())
            else:
                logger.debug("iTerm2 is not available: %s", result.stderr.strip())
            return available
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug("iTerm2 availability check failed: %s", e)
            return False

    def open_session(
        self,
        command_args: list[str],
        working_dir: str,
        env_vars: dict[str, str],
    ) -> bool:
        """Open a new iTerm2 session and run Claude Code with specified arguments.

        Args:
            command_args: List of command arguments to pass to Claude Code.
            working_dir: Working directory to change to before running the command.
            env_vars: Dictionary of environment variables to export.

        Returns:
            True if the session was successfully opened, False otherwise.
        """
        if not self.is_available():
            logger.warning("iTerm2 is not available, cannot open session")
            return False

        try:
            # Validate inputs
            if not command_args:
                logger.warning("No command arguments provided")
                return False

            if not os.path.isdir(working_dir):
                logger.warning("Working directory does not exist: %s", working_dir)
                return False

            # Prepare environment variable exports
            env_exports = []
            for key, value in env_vars.items():
                if value:  # Skip empty values
                    # Use shlex.quote for proper shell escaping
                    escaped_key = shlex.quote(key)
                    escaped_value = shlex.quote(value)
                    env_exports.append(f'write text "export {escaped_key}={escaped_value}"')

            env_exports_str = "\n                ".join(env_exports)

            # Prepare command arguments
            quoted_args = [shlex.quote(arg) for arg in command_args]
            command_args_str = " ".join(quoted_args)

            # Escape working directory for AppleScript
            escaped_working_dir = working_dir.replace('"', '\\"')

            # Build the complete AppleScript
            applescript = self._applescript_template.format(
                working_dir=escaped_working_dir,
                env_exports=env_exports_str,
                command_args=command_args_str,
            ).strip()

            logger.debug(
                "Opening iTerm2 session in %s with command: claude %s",
                working_dir,
                command_args_str,
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
                logger.info("Successfully opened iTerm2 session")
                return True
            else:
                logger.warning(
                    "Failed to execute AppleScript: %s (stderr: %s)",
                    result.stdout.strip(),
                    result.stderr.strip(),
                )
                return False

        except subprocess.TimeoutExpired:
            logger.warning("AppleScript execution timed out")
            return False
        except subprocess.SubprocessError as e:
            logger.warning("AppleScript execution failed: %s", e)
            return False
        except Exception as e:
            logger.warning("Unexpected error opening iTerm2 session: %s", e)
            return False
