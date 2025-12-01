"""Centralized logging configuration with multi-level verbosity support.

This module provides a centralized logging system with progressive verbosity
levels controlled by CLI flags (-v, -vv, -vvv).

Key Components:
    - setup_logging: Configure logging based on verbosity count
    - get_logger: Get a module-specific logger instance

Dependencies:
    - logging: Python standard library logging

Related Modules:
    - cli: Calls setup_logging() from all CLI commands
    - All services: Use get_logger(__name__) for logging

Called By:
    - cli.main: Root CLI group
    - cli.gui_command: GUI launcher
    - cli_group: REST API client commands
    - All service modules

Example:
    >>> from claude_code_scheduler.logging_config import setup_logging, get_logger
    >>> setup_logging(verbose_count=2)  # Enable DEBUG logging
    >>> logger = get_logger(__name__)
    >>> logger.info("Operation started")

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import logging
import sys


def setup_logging(verbose_count: int = 0) -> None:
    """Configure logging based on verbosity level.

    Maps CLI verbosity count to Python logging levels and configures
    both application and dependent library loggers.

    Args:
        verbose_count: Number of -v flags (0-3+)
            0: WARNING level (quiet mode)
            1: INFO level (normal verbose)
            2: DEBUG level (detailed debugging)
            3+: DEBUG + enable dependent library logging (trace mode)

    Example:
        >>> setup_logging(0)  # No -v flag: WARNING only
        >>> setup_logging(1)  # -v: INFO level
        >>> setup_logging(2)  # -vv: DEBUG level
        >>> setup_logging(3)  # -vvv: DEBUG + library internals
    """
    # Map verbosity count to logging levels
    if verbose_count == 0:
        level = logging.WARNING
    elif verbose_count == 1:
        level = logging.INFO
    elif verbose_count >= 2:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    # Configure root logger with comprehensive format:
    # [datetime][level][module] message
    logging.basicConfig(
        level=level,
        format="[%(asctime)s][%(levelname)s][%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
        force=True,  # Override any existing configuration
    )

    # Configure dependent library loggers at TRACE level (-vvv)
    if verbose_count >= 3:
        # APScheduler internals
        logging.getLogger("apscheduler").setLevel(logging.DEBUG)
        # PyQt6 (if any debug logs)
        logging.getLogger("PyQt6").setLevel(logging.DEBUG)
    else:
        # Suppress noisy libraries at lower verbosity levels
        logging.getLogger("apscheduler").setLevel(logging.WARNING)
        logging.getLogger("PyQt6").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    This is a convenience wrapper around logging.getLogger() that
    ensures consistent logger naming across your application.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Operation started")
        >>> logger.debug("Detailed operation info")
    """
    return logging.getLogger(name)
