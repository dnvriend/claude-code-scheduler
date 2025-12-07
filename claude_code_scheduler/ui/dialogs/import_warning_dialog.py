"""Import Warning Dialog - Modal dialog for showing import validation warnings.

Provides a dialog to display import warnings, conflicts, and get user
confirmation before proceeding with an import operation.

This module provides:
- ImportWarningDialog: Modal dialog showing warnings/conflicts with confirmation

Key Components:
- ImportWarningDialog: QDialog subclass with warning list and overwrite toggle

Dependencies:
- PyQt6.QtWidgets: Dialog and widget classes
- services.import_service: ImportResult dataclass

Related Modules:
- ui.main_window: Shows this dialog during import
- services.import_service: Provides validation results

Collaborators:
- ImportResult: Contains warnings/errors to display
- MainWindow: Parent window that triggers dialog

Example:
    >>> from PyQt6.QtWidgets import QApplication
    >>> dialog = ImportWarningDialog(import_result, file_path, parent)
    >>> if dialog.exec() == QDialog.DialogCode.Accepted:
    ...     proceed, force = dialog.get_result()

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from claude_code_scheduler.logging_config import get_logger
from claude_code_scheduler.services.import_service import ImportResult

logger = get_logger(__name__)


class ImportWarningDialog(QDialog):
    """Dialog for displaying import warnings and getting user confirmation.

    Shows a modal dialog with validation warnings and conflict errors from an
    import operation. Users can review warnings and choose to proceed or cancel.

    Responsibilities:
    - Display import validation warnings in scrollable list
    - Show conflict errors when UUIDs already exist
    - Provide overwrite toggle for conflict resolution
    - Return user decision (proceed/cancel, force overwrite)

    Attributes:
        import_result: ImportResult with warnings/errors to display
        file_path: Path to file being imported
        force_overwrite: Whether user chose to overwrite conflicts

    Collaborators:
        MainWindow: Shows this dialog and handles result
        ImportService: Provides ImportResult from validation

    See Also:
        ImportService.validate_import: Creates the ImportResult shown here
    """

    def __init__(
        self,
        import_result: ImportResult,
        file_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the import warning dialog.

        Args:
            import_result: Result from import validation with warnings/errors
            file_path: Path to the file being imported (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        self.import_result = import_result
        self.file_path = file_path
        self.force_overwrite = False

        self.setWindowTitle("Import Warnings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setMaximumWidth(700)
        self.setMaximumHeight(800)
        self.setModal(True)

        self._setup_ui()
        self._populate_content()

    def _setup_ui(self) -> None:
        """Set up the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title and file path
        title_label = QLabel("Import Warnings")
        title_label.setObjectName("panelTitle")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff9f0a;")
        layout.addWidget(title_label)

        if self.file_path:
            file_label = QLabel(f"File: {self.file_path}")
            file_label.setStyleSheet("color: #8e8e93; font-size: 12px;")
            layout.addWidget(file_label)

        # Warning message
        if self.import_result.warnings:
            msg_label = QLabel("The following warnings were found during validation:")
            msg_label.setStyleSheet("color: #98989d; font-size: 13px; margin: 8px 0;")
            layout.addWidget(msg_label)

            # Scrollable warnings area
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMinimumHeight(150)
            scroll.setMaximumHeight(300)

            warnings_widget = QWidget()
            warnings_layout = QVBoxLayout(warnings_widget)
            warnings_layout.setSpacing(8)
            warnings_layout.setContentsMargins(8, 8, 8, 8)

            self._setup_warnings_list(warnings_layout)

            scroll.setWidget(warnings_widget)
            layout.addWidget(scroll)

        # Conflict information
        self._setup_conflict_section(layout)

        # Overwrite checkbox (shown only if there are conflicts)
        self.overwrite_check = QCheckBox("Overwrite existing job")
        self.overwrite_check.setObjectName("fieldLabel")
        self.overwrite_check.setStyleSheet("color: #e5e5e7; font-size: 13px; margin: 12px 0;")
        self.overwrite_check.stateChanged.connect(self._on_overwrite_toggled)
        layout.addWidget(self.overwrite_check)

        # Hide overwrite checkbox initially, show only if there are conflicts
        self.overwrite_check.setVisible(False)

        layout.addStretch()

        # Button row
        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)

        # Import Anyway button
        self.import_btn = QPushButton("Import Anyway")
        self.import_btn.setObjectName("primaryButton")
        self.import_btn.clicked.connect(self._on_import_clicked)
        button_layout.addWidget(self.import_btn)

        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _setup_warnings_list(self, layout: QVBoxLayout) -> None:
        """Set up the list of warnings.

        Args:
            layout: Layout to add warning items to
        """
        for warning in self.import_result.warnings:
            warning_label = QLabel(f"⚠️ {warning}")
            warning_label.setWordWrap(True)
            warning_label.setStyleSheet(
                """
                color: #ff9f0a;
                font-size: 12px;
                padding: 8px 12px;
                background-color: rgba(255, 159, 10, 0.1);
                border: 1px solid rgba(255, 159, 10, 0.3);
                border-radius: 6px;
                margin: 2px 0;
            """
            )
            layout.addWidget(warning_label)

    def _setup_conflict_section(self, layout: QVBoxLayout) -> None:
        """Set up the conflict information section.

        Args:
            layout: Main dialog layout
        """
        # Check for conflict errors
        conflict_errors = [e for e in self.import_result.errors if "already exists" in e]

        if conflict_errors:
            conflict_label = QLabel("⚠️ Conflict Detected")
            conflict_label.setStyleSheet(
                """
                color: #ff453a;
                font-size: 14px;
                font-weight: bold;
                margin: 12px 0 8px 0;
            """
            )
            layout.addWidget(conflict_label)

            for error in conflict_errors:
                error_label = QLabel(f"❌ {error}")
                error_label.setWordWrap(True)
                error_label.setStyleSheet(
                    """
                    color: #ff453a;
                    font-size: 12px;
                    padding: 8px 12px;
                    background-color: rgba(255, 69, 58, 0.1);
                    border: 1px solid rgba(255, 69, 58, 0.3);
                    border-radius: 6px;
                    margin: 2px 0;
                """
                )
                layout.addWidget(error_label)

            # Show overwrite checkbox for conflicts
            self.overwrite_check.setVisible(True)

    def _populate_content(self) -> None:
        """Populate dialog content based on import result."""
        # If there are no warnings but there are errors (other than conflicts),
        # this shouldn't happen - this dialog is for warnings only
        if not self.import_result.warnings:
            # Check if we only have conflicts (which are warnings for this dialog)
            conflict_errors = [e for e in self.import_result.errors if "already exists" in e]
            if not conflict_errors:
                # No warnings or conflicts - this dialog shouldn't be shown
                logger.warning("ImportWarningDialog shown with no warnings or conflicts")
                return

    def _on_overwrite_toggled(self, state: int) -> None:
        """Handle overwrite checkbox state change.

        Args:
            state: Checkbox state (0=unchecked, 2=checked)
        """
        self.force_overwrite = state == 2

        # Update button text based on overwrite state
        if self.force_overwrite:
            self.import_btn.setText("Import with Overwrite")
        else:
            self.import_btn.setText("Import Anyway")

    def _on_import_clicked(self) -> None:
        """Handle Import Anyway button click."""
        # If there are conflicts and overwrite is not checked, don't proceed
        conflict_errors = [e for e in self.import_result.errors if "already exists" in e]
        if conflict_errors and not self.force_overwrite:
            # Show error message
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Conflict Resolution Required",
                "Please check 'Overwrite existing job' to resolve the conflict.",
            )
            return

        self.accept()

    def get_result(self) -> tuple[bool, bool]:
        """Get the dialog result.

        Returns:
            Tuple of (proceed: bool, force: bool)
            - proceed: True if user clicked Import Anyway
            - force: True if overwrite checkbox was checked
        """
        return (self.result() == QDialog.DialogCode.Accepted, self.force_overwrite)
