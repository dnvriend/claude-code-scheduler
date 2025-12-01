"""Main entry point for the Claude Code Scheduler GUI application.

This module initializes the PyQt6 application, applies theming, and
launches the main window with the debug REST API server.

Key Components:
    - main: Application entry point function

Dependencies:
    - PyQt6: GUI framework (QApplication, QIcon)
    - claude_code_scheduler.ui.main_window: MainWindow class
    - claude_code_scheduler.ui.theme: Dark/light theme stylesheets

Related Modules:
    - cli: CLI entry point that invokes this module via gui_command
    - ui.main_window: Main application window with 4-panel layout
    - services.debug_server: REST API server started by MainWindow

Calls:
    - QApplication: PyQt6 application instance
    - MainWindow: Main GUI window
    - get_theme: Theme stylesheet retrieval

Called By:
    - cli.gui_command: CLI command that launches the GUI

Example:
    >>> from claude_code_scheduler.main import main
    >>> exit_code = main(restport=5679)

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from claude_code_scheduler.ui.main_window import MainWindow
from claude_code_scheduler.ui.theme import get_theme


def main(restport: int = 5679) -> int:
    """Launch the Claude Code Scheduler GUI application.

    Args:
        restport: Port for debug REST API server.
    """
    # Set application name before creating QApplication to override "python" in macOS title bar
    sys.argv[0] = "Claude Code Scheduler"
    app = QApplication(sys.argv)
    app.setApplicationName("Claude Code Scheduler")
    app.setApplicationDisplayName("Claude Code Scheduler")
    app.setOrganizationName("Claude Code Scheduler")
    app.setOrganizationDomain("claude-code-scheduler.local")

    # Set application icon
    icon_path = Path(__file__).parent / "icons" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Apply dark theme by default
    app.setStyleSheet(get_theme(dark=True))

    window = MainWindow(restport=restport)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
