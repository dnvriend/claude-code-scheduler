"""
Logs Panel - Right-bottom panel showing task execution logs.

Displays log output with tabs for Output, Raw, and Errors views.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from uuid import UUID

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from claude_code_scheduler.models.run import Run


class LogsPanel(QFrame):
    """Right-bottom panel containing log output with tabbed views."""

    # Signals
    session_opened = pyqtSignal(UUID)  # Emitted when user wants to open session (run_id)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("logsPanel")
        self.current_run: Run | None = None
        self.auto_scroll = True
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Tab widget for different log views
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("logsTabs")

        # Live tab (real-time process output)
        self.live_text = self._create_log_view()
        self.live_text.setPlaceholderText(
            "Live process output will appear here.\nRun a task to see real-time output."
        )
        self.tab_widget.addTab(self.live_text, "Live")

        # Output tab (formatted/parsed output)
        self.output_text = self._create_log_view()
        self.tab_widget.addTab(self.output_text, "Output")

        # Raw tab (raw JSONL stream)
        self.raw_text = self._create_log_view()
        self.tab_widget.addTab(self.raw_text, "Raw")

        # Errors tab (errors only)
        self.errors_text = self._create_log_view()
        self.tab_widget.addTab(self.errors_text, "Errors")

        layout.addWidget(self.tab_widget, 1)

    def _create_header(self) -> QWidget:
        """Create the panel header with action buttons."""
        header = QWidget()
        header.setObjectName("panelHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)

        self.title_label = QLabel("Logs")
        self.title_label.setObjectName("panelTitle")
        layout.addWidget(self.title_label)

        layout.addStretch()

        # Open Session button
        self.open_session_btn = QPushButton("Open Session")
        self.open_session_btn.setObjectName("smallButton")
        self.open_session_btn.clicked.connect(self._on_open_session)
        self.open_session_btn.hide()  # Only show when a run is selected
        layout.addWidget(self.open_session_btn)

        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("smallButton")
        self.clear_btn.clicked.connect(self.clear)
        layout.addWidget(self.clear_btn)

        # Copy button
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setObjectName("smallButton")
        self.copy_btn.clicked.connect(self._on_copy)
        layout.addWidget(self.copy_btn)

        return header

    def _create_log_view(self) -> QPlainTextEdit:
        """Create a log view widget with text display."""
        text_edit = QPlainTextEdit()
        text_edit.setObjectName("logTextEdit")
        text_edit.setReadOnly(True)
        text_edit.setPlaceholderText("No logs to display.\nSelect a run to view its logs.")
        text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        return text_edit

    def show_run_logs(self, run: Run) -> None:
        """Display logs for a specific run."""
        self.current_run = run
        self.title_label.setText(f"Logs: {run.task_name}")

        # Show/hide open session button
        if run.session_id:
            self.open_session_btn.show()
        else:
            self.open_session_btn.hide()

        # Populate output tab
        self.output_text.setPlainText(run.output or "(no output)")

        # Populate raw tab
        self.raw_text.setPlainText(run.raw_output or "(no raw output)")

        # Populate errors tab
        self.errors_text.setPlainText(run.errors or "(no errors)")

        # Update error tab label if there are errors (index 3 = Errors tab)
        if run.errors:
            self.tab_widget.setTabText(3, f"Errors ({len(run.errors.splitlines())})")
        else:
            self.tab_widget.setTabText(3, "Errors")

    def append_output(self, text: str) -> None:
        """Append text to the output log."""
        self._append_to_view(self.output_text, text)

    def append_raw(self, text: str) -> None:
        """Append text to the raw log."""
        self._append_to_view(self.raw_text, text)

    def append_error(self, text: str) -> None:
        """Append text to the errors log."""
        self._append_to_view(self.errors_text, text)
        # Update error count
        doc = self.errors_text.document()
        line_count = doc.blockCount() if doc else 0
        self.tab_widget.setTabText(3, f"Errors ({line_count})")

    def append_live(self, text: str) -> None:
        """Append text to the live output log."""
        self._append_to_view(self.live_text, text)

    def clear_live(self) -> None:
        """Clear the live output tab."""
        self.live_text.clear()

    def start_live_output(self, task_name: str) -> None:
        """Prepare live tab for new task output."""
        self.live_text.clear()
        self.title_label.setText(f"Live: {task_name}")
        # Switch to live tab
        self.tab_widget.setCurrentIndex(0)

    def _append_to_view(
        self, text_edit: QPlainTextEdit, text: str, fmt: QTextCharFormat | None = None
    ) -> None:
        """Append text to a text edit with optional formatting."""
        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if fmt:
            cursor.insertText(text, fmt)
        else:
            cursor.insertText(text)
        if self.auto_scroll:
            text_edit.ensureCursorVisible()

    def clear(self) -> None:
        """Clear all log views."""
        self.current_run = None
        self.title_label.setText("Logs")
        self.open_session_btn.hide()
        self.live_text.clear()
        self.output_text.clear()
        self.raw_text.clear()
        self.errors_text.clear()
        self.tab_widget.setTabText(3, "Errors")

    def _on_copy(self) -> None:
        """Copy current tab content to clipboard."""
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, QPlainTextEdit):
            text = current_widget.toPlainText()
        elif current_widget is not None:
            # Find QPlainTextEdit in widget
            text_edit = current_widget.findChild(QPlainTextEdit)
            text = text_edit.toPlainText() if text_edit else ""
        else:
            text = ""

        if text:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)

    def _on_open_session(self) -> None:
        """Handle open session button click."""
        if self.current_run and self.current_run.session_id:
            self.session_opened.emit(self.current_run.id)

    def set_auto_scroll(self, enabled: bool) -> None:
        """Enable or disable auto-scrolling."""
        self.auto_scroll = enabled
