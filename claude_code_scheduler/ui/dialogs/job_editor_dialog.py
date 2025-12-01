"""
Job Editor Dialog - Modal dialog for creating and editing jobs.

Provides a form for entering job name, description, working directory,
and status. Branch selection uses a dropdown populated from the git repository.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import os
from typing import Any

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from claude_code_scheduler.logging_config import get_logger
from claude_code_scheduler.models.job import Job, JobWorkingDirectory
from claude_code_scheduler.models.profile import Profile
from claude_code_scheduler.services.git_service import GitService, GitServiceError

logger = get_logger(__name__)


class JobEditorDialog(QDialog):
    """Dialog for creating or editing a job."""

    def __init__(
        self, job: Job | None = None, profiles: list[Profile] | None = None, parent: object = None
    ) -> None:
        """Initialize the dialog.

        Args:
            job: Existing job to edit, or None to create new.
            profiles: List of available profiles for the dropdown.
            parent: Parent widget.
        """
        super().__init__(parent)  # type: ignore[arg-type]
        self.job = job
        self.profiles = profiles or []
        self.setWindowTitle("Edit Job" if job else "New Job")
        self.setMinimumWidth(400)
        self._setup_ui()
        if job:
            self._populate_form()

    def _setup_ui(self) -> None:
        """Set up the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Name field
        name_label = QLabel("Name")
        name_label.setObjectName("fieldLabel")
        layout.addWidget(name_label)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter job name")
        layout.addWidget(self.name_edit)

        # Description field
        desc_label = QLabel("Description")
        desc_label.setObjectName("fieldLabel")
        layout.addWidget(desc_label)
        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText("Enter job description (optional)")
        self.description_edit.setMaximumHeight(100)
        layout.addWidget(self.description_edit)

        # Profile field
        profile_label = QLabel("Default Profile")
        profile_label.setObjectName("fieldLabel")
        layout.addWidget(profile_label)
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("(None - use task profiles)", None)
        for profile in self.profiles:
            self.profile_combo.addItem(profile.name, str(profile.id))
        layout.addWidget(self.profile_combo)

        # Working Directory section
        wd_label = QLabel("Working Directory")
        wd_label.setObjectName("fieldLabel")
        layout.addWidget(wd_label)

        # Working directory row: text field + browse button
        wd_row = QHBoxLayout()
        wd_row.setSpacing(8)

        self.working_dir_edit = QLineEdit()
        self.working_dir_edit.setPlaceholderText("~/projects")
        # Default to current working directory
        self.working_dir_edit.setText(os.getcwd())
        wd_row.addWidget(self.working_dir_edit, 1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setObjectName("secondaryButton")
        self.browse_btn.setToolTip("Browse for directory")
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        wd_row.addWidget(self.browse_btn)

        layout.addLayout(wd_row)

        # Git Worktree options
        self.use_worktree_check = QCheckBox("Use Git Worktree for isolation")
        self.use_worktree_check.stateChanged.connect(self._on_worktree_toggled)
        layout.addWidget(self.use_worktree_check)

        # Worktree name field (hidden by default)
        self.worktree_name_label = QLabel("Worktree Name")
        self.worktree_name_label.setObjectName("fieldLabel")
        self.worktree_name_label.setVisible(False)
        layout.addWidget(self.worktree_name_label)

        self.worktree_name_edit = QLineEdit()
        self.worktree_name_edit.setPlaceholderText("Worktree name (default: job-{id[:8]})")
        self.worktree_name_edit.setVisible(False)
        layout.addWidget(self.worktree_name_edit)

        # Worktree branch dropdown (hidden by default)
        self.worktree_branch_label = QLabel("Branch")
        self.worktree_branch_label.setObjectName("fieldLabel")
        self.worktree_branch_label.setVisible(False)
        layout.addWidget(self.worktree_branch_label)

        self.worktree_branch_combo = QComboBox()
        self.worktree_branch_combo.setPlaceholderText("Select branch (optional)")
        self.worktree_branch_combo.setVisible(False)
        self.worktree_branch_combo.setEditable(True)  # Allow custom branch names
        layout.addWidget(self.worktree_branch_combo)

        # Connect working directory changes to branch refresh
        self.working_dir_edit.editingFinished.connect(self._refresh_branches)

        layout.addStretch()

        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("primaryButton")
        ok_btn.clicked.connect(self._on_ok_clicked)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

    def _on_browse_clicked(self) -> None:
        """Open directory browser dialog."""
        from pathlib import Path

        # Start from current value or home directory
        current_dir = self.working_dir_edit.text().strip()
        if current_dir:
            start_dir = str(Path(current_dir).expanduser())
        else:
            start_dir = str(Path.home())

        # Open directory dialog
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Working Directory",
            start_dir,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if selected_dir:
            self.working_dir_edit.setText(selected_dir)
            # Refresh branches if worktree is enabled
            if self.use_worktree_check.isChecked():
                self._refresh_branches()

    def _on_worktree_toggled(self, state: int) -> None:
        """Show/hide worktree options based on checkbox state."""
        is_checked = state != 0
        self.worktree_name_label.setVisible(is_checked)
        self.worktree_name_edit.setVisible(is_checked)
        self.worktree_branch_label.setVisible(is_checked)
        self.worktree_branch_combo.setVisible(is_checked)
        if is_checked:
            self._refresh_branches()

    def _refresh_branches(self) -> None:
        """Refresh branch dropdown from git repository."""
        working_dir = self.working_dir_edit.text().strip()
        if not working_dir:
            return

        # Expand ~ to home directory
        from pathlib import Path

        expanded_path = Path(working_dir).expanduser()

        # Clear existing items
        current_text = self.worktree_branch_combo.currentText()
        self.worktree_branch_combo.clear()

        try:
            git_service = GitService(str(expanded_path))
            branches = git_service.list_branches(include_remote=False)
            self.worktree_branch_combo.addItems(branches)

            # Restore previous selection if it exists
            if current_text:
                index = self.worktree_branch_combo.findText(current_text)
                if index >= 0:
                    self.worktree_branch_combo.setCurrentIndex(index)
                else:
                    # Keep custom text in editable combo
                    self.worktree_branch_combo.setCurrentText(current_text)

            logger.debug("Loaded %d branches from %s", len(branches), expanded_path)
        except GitServiceError as e:
            logger.warning("Could not load branches from %s: %s", expanded_path, e)
            # Not a git repo or error - leave combo empty (user can type custom)

    def _populate_form(self) -> None:
        """Populate form with existing job data."""
        if not self.job:
            return
        self.name_edit.setText(self.job.name)
        self.description_edit.setPlainText(self.job.description)

        # Set profile selection
        if self.job.profile:
            for i in range(self.profile_combo.count()):
                if self.profile_combo.itemData(i) == self.job.profile:
                    self.profile_combo.setCurrentIndex(i)
                    break
            else:
                # Profile not found, select None
                self.profile_combo.setCurrentIndex(0)
        else:
            self.profile_combo.setCurrentIndex(0)  # Select None by default

        # Populate working directory fields
        wd = self.job.working_directory
        self.working_dir_edit.setText(wd.path)
        self.use_worktree_check.setChecked(wd.use_git_worktree)
        if wd.worktree_name:
            self.worktree_name_edit.setText(wd.worktree_name)

        # Refresh branches and set selected branch
        if wd.use_git_worktree:
            self._refresh_branches()
            if wd.worktree_branch:
                index = self.worktree_branch_combo.findText(wd.worktree_branch)
                if index >= 0:
                    self.worktree_branch_combo.setCurrentIndex(index)
                else:
                    self.worktree_branch_combo.setCurrentText(wd.worktree_branch)

    def _on_ok_clicked(self) -> None:
        """Handle OK button click."""
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus()
            return
        self.accept()

    def get_job_data(self) -> dict[str, Any]:
        """Get the job data from the form.

        Returns:
            Dictionary with name, description, profile, and working_directory.
        """
        # Get selected profile ID
        profile_id = self.profile_combo.currentData()

        # Build working directory config
        working_directory = JobWorkingDirectory(
            path=self.working_dir_edit.text().strip() or "~/projects",
            use_git_worktree=self.use_worktree_check.isChecked(),
            worktree_name=self.worktree_name_edit.text().strip() or None,
            worktree_branch=self.worktree_branch_combo.currentText().strip() or None,
        )

        return {
            "name": self.name_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "profile": profile_id,
            "working_directory": working_directory.to_dict(),
        }
