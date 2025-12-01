"""Startup banner logging for CLI components.

This module provides consistent startup banners logged to the logging system,
displaying version, configuration, and runtime parameters at application start.

Key Components:
    - log_startup_banner: Generic banner logger with configuration display
    - log_gui_banner: Pre-configured banner for GUI startup

Dependencies:
    - logging: Python standard library logging
    - claude_code_scheduler._version: Version information

Related Modules:
    - cli: gui_command calls log_gui_banner before launching
    - logging_config: Logging system used by banner output

Called By:
    - cli.gui_command: Logs GUI startup banner

Example:
    >>> from claude_code_scheduler.startup_banner import log_gui_banner
    >>> log_gui_banner(verbose_count=1, rest_port=5679)

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import logging
import sys
from typing import Any

from claude_code_scheduler._version import __version__

logger = logging.getLogger(__name__)


def _get_log_level_name(verbose_count: int) -> str:
    """Convert verbose count to log level name.

    Args:
        verbose_count: Number of -v flags

    Returns:
        Log level name (WARNING, INFO, DEBUG, TRACE)
    """
    if verbose_count == 0:
        return "WARNING"
    elif verbose_count == 1:
        return "INFO"
    elif verbose_count == 2:
        return "DEBUG"
    else:
        return "TRACE"


def log_startup_banner(
    component: str,
    config: dict[str, Any],
    verbose_count: int = 0,
) -> None:
    """Log startup banner with component info and configuration.

    Args:
        component: Component name (gui)
        config: Configuration key-value pairs to display
        verbose_count: Verbosity level for log level display
    """
    separator = "=" * 60
    title = f"Claude Code Scheduler - {component.title()}"
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    log_level = _get_log_level_name(verbose_count)

    # Log banner header
    logger.info(separator)
    logger.info("%s v%s", title, __version__)
    logger.info(separator)

    # Log configuration items
    for key, value in config.items():
        if value is None:
            continue
        # Format value based on type
        if isinstance(value, bool):
            display_value = "enabled" if value else "disabled"
        else:
            display_value = str(value)

        logger.info("  %s: %s", key, display_value)

    # Log runtime info
    logger.info("  Log Level: %s", log_level)
    logger.info("  Python: %s", py_version)
    logger.info(separator)


def log_gui_banner(
    verbose_count: int,
    rest_port: int,
) -> None:
    """Log standalone GUI startup banner.

    Args:
        verbose_count: Verbosity level
        rest_port: Debug REST API port
    """
    log_startup_banner(
        "GUI",
        {
            "REST Port": rest_port,
            "Mode": "Standalone",
        },
        verbose_count,
    )
