"""
Profile Editor Dialog for Claude Code Scheduler.

Modal dialog for creating and editing profiles with environment variables.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from claude_code_scheduler.models.enums import EnvVarSource
from claude_code_scheduler.models.profile import EnvVar, Profile


class EnvVarItemWidget(QFrame):
    """Widget for displaying/editing a single environment variable."""

    deleted = pyqtSignal(object)  # Emits self

    def __init__(self, env_var: EnvVar | None = None) -> None:
        super().__init__()
        self.setObjectName("envVarItem")
        self.env_var = env_var
        self._setup_ui()
        if env_var:
            self._load_env_var(env_var)

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Top row: Name and Source
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Name field
        name_container = QVBoxLayout()
        name_label = QLabel("Name")
        name_label.setObjectName("fieldLabel")
        name_container.addWidget(name_label)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("AWS_REGION")
        name_container.addWidget(self.name_edit)
        top_row.addLayout(name_container, 1)

        # Source selector
        source_container = QVBoxLayout()
        source_label = QLabel("Source")
        source_label.setObjectName("fieldLabel")
        source_container.addWidget(source_label)
        self.source_combo = QComboBox()
        self.source_combo.addItem("Static Value", EnvVarSource.STATIC.value)
        self.source_combo.addItem("Environment Variable", EnvVarSource.ENVIRONMENT.value)
        self.source_combo.addItem("macOS Keychain", EnvVarSource.KEYCHAIN.value)
        self.source_combo.addItem("AWS Secrets Manager", EnvVarSource.AWS_SECRETS_MANAGER.value)
        self.source_combo.addItem("AWS SSM Parameter", EnvVarSource.AWS_SSM.value)
        self.source_combo.addItem("Shell Command", EnvVarSource.COMMAND.value)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        source_container.addWidget(self.source_combo)
        top_row.addLayout(source_container, 1)

        # Delete button
        delete_container = QVBoxLayout()
        delete_spacer = QLabel("")
        delete_spacer.setObjectName("fieldLabel")
        delete_container.addWidget(delete_spacer)
        self.delete_btn = QPushButton("X")
        self.delete_btn.setObjectName("smallButton")
        self.delete_btn.setFixedWidth(30)
        self.delete_btn.clicked.connect(lambda: self.deleted.emit(self))
        delete_container.addWidget(self.delete_btn)
        top_row.addLayout(delete_container)

        layout.addLayout(top_row)

        # Value field (changes based on source)
        self.value_label = QLabel("Value")
        self.value_label.setObjectName("fieldLabel")
        layout.addWidget(self.value_label)
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Enter value...")
        layout.addWidget(self.value_edit)

        # Help text
        self.help_label = QLabel("Enter the static value for this variable.")
        self.help_label.setObjectName("helpLabel")
        self.help_label.setWordWrap(True)
        layout.addWidget(self.help_label)

    def _on_source_changed(self, index: int) -> None:
        """Update help text and placeholder based on source."""
        source = self.source_combo.currentData()
        help_texts = {
            EnvVarSource.STATIC.value: (
                "Value",
                "Enter the static value",
                "Enter the exact value for this variable.",
            ),
            EnvVarSource.ENVIRONMENT.value: (
                "Variable Name",
                "HOME",
                "Name of existing environment variable to copy.",
            ),
            EnvVarSource.KEYCHAIN.value: (
                "Service/Account",
                "my-service/my-account",
                "macOS Keychain: service/account format.",
            ),
            EnvVarSource.AWS_SECRETS_MANAGER.value: (
                "Secret Name",
                "prod/api/claude-key",
                "AWS Secrets Manager secret name or ARN.",
            ),
            EnvVarSource.AWS_SSM.value: (
                "Parameter Path",
                "/prod/claude/api-key",
                "AWS SSM Parameter Store parameter path.",
            ),
            EnvVarSource.COMMAND.value: (
                "Command",
                "aws configure get region",
                "Shell command to execute. Output will be used as value.",
            ),
        }
        label, placeholder, help_text = help_texts.get(
            source, ("Value", "Enter value...", "Enter the value.")
        )
        self.value_label.setText(label)
        self.value_edit.setPlaceholderText(placeholder)
        self.help_label.setText(help_text)

    def _load_env_var(self, env_var: EnvVar) -> None:
        """Load an existing env var into the widget."""
        self.name_edit.setText(env_var.name)
        # Find and select the source
        for i in range(self.source_combo.count()):
            if self.source_combo.itemData(i) == env_var.source.value:
                self.source_combo.setCurrentIndex(i)
                break
        self.value_edit.setText(env_var.value)

    def get_env_var(self) -> EnvVar:
        """Build EnvVar from current widget state."""
        source_value = self.source_combo.currentData()
        return EnvVar(
            name=self.name_edit.text() or "UNNAMED",
            source=EnvVarSource(source_value),
            value=self.value_edit.text(),
            config=None,  # TODO: Add config UI for AWS region/profile
        )


class ProfileEditorDialog(QDialog):
    """Dialog for managing profiles and their environment variables."""

    profiles_changed = pyqtSignal(list)  # Emits updated profile list

    def __init__(self, profiles: list[Profile], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.profiles = [Profile(**vars(p)) for p in profiles]  # Deep copy
        self.current_profile: Profile | None = None
        self.env_var_widgets: list[EnvVarItemWidget] = []
        self._setup_ui()
        self._load_profiles()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Manage Profiles")
        self.setMinimumSize(700, 500)
        self.setModal(True)

        layout = QHBoxLayout(self)
        layout.setSpacing(16)

        # Left side: Profile list
        left_panel = self._create_profile_list_panel()
        layout.addWidget(left_panel)

        # Right side: Profile editor
        right_panel = self._create_profile_editor_panel()
        layout.addWidget(right_panel, 1)

    def _create_profile_list_panel(self) -> QWidget:
        """Create the left panel with profile list."""
        widget = QFrame()
        widget.setObjectName("schedulePanel")
        widget.setMinimumWidth(200)
        widget.setMaximumWidth(250)
        layout = QVBoxLayout(widget)

        # Header
        header = QLabel("Profiles")
        header.setObjectName("panelTitle")
        layout.addWidget(header)

        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._on_profile_selected)
        layout.addWidget(self.profile_list, 1)

        # Add/Delete buttons
        btn_layout = QHBoxLayout()
        self.add_profile_btn = QPushButton("Add")
        self.add_profile_btn.setObjectName("secondaryButton")
        self.add_profile_btn.clicked.connect(self._add_profile)
        btn_layout.addWidget(self.add_profile_btn)

        self.delete_profile_btn = QPushButton("Delete")
        self.delete_profile_btn.setObjectName("secondaryButton")
        self.delete_profile_btn.clicked.connect(self._delete_profile)
        btn_layout.addWidget(self.delete_profile_btn)
        layout.addLayout(btn_layout)

        return widget

    def _create_profile_editor_panel(self) -> QWidget:
        """Create the right panel for editing profile details."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        # Profile name
        name_label = QLabel("Profile Name")
        name_label.setObjectName("fieldLabel")
        layout.addWidget(name_label)
        self.profile_name_edit = QLineEdit()
        self.profile_name_edit.setPlaceholderText("Enter profile name...")
        self.profile_name_edit.textChanged.connect(self._on_name_changed)
        layout.addWidget(self.profile_name_edit)

        # Description
        desc_label = QLabel("Description")
        desc_label.setObjectName("fieldLabel")
        layout.addWidget(desc_label)
        self.profile_desc_edit = QTextEdit()
        self.profile_desc_edit.setPlaceholderText("Optional description...")
        self.profile_desc_edit.setMaximumHeight(60)
        layout.addWidget(self.profile_desc_edit)

        # Environment Variables section
        env_header = QHBoxLayout()
        env_label = QLabel("Environment Variables")
        env_label.setObjectName("sectionLabel")
        env_header.addWidget(env_label)
        env_header.addStretch()
        self.add_env_btn = QPushButton("+ Add Variable")
        self.add_env_btn.setObjectName("smallButton")
        self.add_env_btn.clicked.connect(self._add_env_var)
        env_header.addWidget(self.add_env_btn)
        layout.addLayout(env_header)

        # Env var container (scrollable)
        from PyQt6.QtWidgets import QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.env_vars_container = QWidget()
        self.env_vars_layout = QVBoxLayout(self.env_vars_container)
        self.env_vars_layout.setContentsMargins(0, 0, 0, 0)
        self.env_vars_layout.setSpacing(8)
        self.env_vars_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.env_vars_container)
        layout.addWidget(scroll, 1)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        return widget

    def _load_profiles(self) -> None:
        """Populate the profile list."""
        self.profile_list.clear()
        for profile in self.profiles:
            item = QListWidgetItem(profile.name)
            item.setData(Qt.ItemDataRole.UserRole, str(profile.id))
            self.profile_list.addItem(item)
        if self.profiles:
            self.profile_list.setCurrentRow(0)

    def _on_profile_selected(
        self, current: QListWidgetItem | None, previous: QListWidgetItem | None
    ) -> None:
        """Handle profile selection change."""
        # Save previous profile state
        if self.current_profile:
            self._save_current_profile()

        if not current:
            self.current_profile = None
            self._clear_editor()
            return

        # Load selected profile
        profile_id = current.data(Qt.ItemDataRole.UserRole)
        for profile in self.profiles:
            if str(profile.id) == profile_id:
                self.current_profile = profile
                self._load_profile(profile)
                break

    def _load_profile(self, profile: Profile) -> None:
        """Load profile data into the editor."""
        self.profile_name_edit.setText(profile.name)
        self.profile_desc_edit.setPlainText(profile.description)

        # Clear existing env var widgets
        for widget in self.env_var_widgets:
            self.env_vars_layout.removeWidget(widget)
            widget.deleteLater()
        self.env_var_widgets.clear()

        # Add env var widgets
        for env_var in profile.env_vars:
            self._add_env_var_widget(env_var)

    def _clear_editor(self) -> None:
        """Clear the editor panel."""
        self.profile_name_edit.clear()
        self.profile_desc_edit.clear()
        for widget in self.env_var_widgets:
            self.env_vars_layout.removeWidget(widget)
            widget.deleteLater()
        self.env_var_widgets.clear()

    def _save_current_profile(self) -> None:
        """Save current editor state to the current profile."""
        if not self.current_profile:
            return
        self.current_profile.name = self.profile_name_edit.text() or "Untitled Profile"
        self.current_profile.description = self.profile_desc_edit.toPlainText()
        self.current_profile.env_vars = [w.get_env_var() for w in self.env_var_widgets]

    def _on_name_changed(self, text: str) -> None:
        """Update list item when name changes."""
        current_item = self.profile_list.currentItem()
        if current_item:
            current_item.setText(text or "Untitled Profile")

    def _add_profile(self) -> None:
        """Add a new profile."""
        new_profile = Profile(name="New Profile")
        self.profiles.append(new_profile)
        item = QListWidgetItem(new_profile.name)
        item.setData(Qt.ItemDataRole.UserRole, str(new_profile.id))
        self.profile_list.addItem(item)
        self.profile_list.setCurrentItem(item)

    def _delete_profile(self) -> None:
        """Delete the selected profile."""
        current_item = self.profile_list.currentItem()
        if not current_item:
            return
        profile_id = current_item.data(Qt.ItemDataRole.UserRole)
        # Remove from list
        self.profiles = [p for p in self.profiles if str(p.id) != profile_id]
        row = self.profile_list.row(current_item)
        self.profile_list.takeItem(row)
        self.current_profile = None

    def _add_env_var(self) -> None:
        """Add a new environment variable to the current profile."""
        self._add_env_var_widget(None)

    def _add_env_var_widget(self, env_var: EnvVar | None) -> None:
        """Add an env var widget to the container."""
        widget = EnvVarItemWidget(env_var)
        widget.deleted.connect(self._delete_env_var)
        self.env_var_widgets.append(widget)
        self.env_vars_layout.addWidget(widget)

    def _delete_env_var(self, widget: EnvVarItemWidget) -> None:
        """Delete an environment variable widget."""
        if widget in self.env_var_widgets:
            self.env_var_widgets.remove(widget)
            self.env_vars_layout.removeWidget(widget)
            widget.deleteLater()

    def _on_accept(self) -> None:
        """Save all profiles and close dialog."""
        self._save_current_profile()
        # Update list items with final names
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item:
                profile_id = item.data(Qt.ItemDataRole.UserRole)
                for profile in self.profiles:
                    if str(profile.id) == profile_id:
                        profile.name = item.text() or "Untitled Profile"
                        break
        self.profiles_changed.emit(self.profiles)
        self.accept()

    def get_profiles(self) -> list[Profile]:
        """Get the list of profiles."""
        return self.profiles
