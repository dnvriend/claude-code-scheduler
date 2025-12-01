"""
Command Type Selector Widget.

Toggle button group for selecting between Claude Prompt and Existing Command.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QPushButton,
)


class CommandTypeSelector(QFrame):
    """Toggle selector for command type (prompt vs command)."""

    command_type_changed = pyqtSignal(str)  # "prompt" or "command"

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("commandTypeSelector")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        # Claude Prompt button
        self.prompt_btn = QPushButton("Claude Prompt")
        self.prompt_btn.setObjectName("commandTypeButton")
        self.prompt_btn.setCheckable(True)
        self.prompt_btn.setChecked(True)
        self.button_group.addButton(self.prompt_btn, 0)
        layout.addWidget(self.prompt_btn)

        # Existing Command button
        self.command_btn = QPushButton("Existing Command")
        self.command_btn.setObjectName("commandTypeButton")
        self.command_btn.setCheckable(True)
        self.button_group.addButton(self.command_btn, 1)
        layout.addWidget(self.command_btn)

        # Connect signal
        self.button_group.idClicked.connect(self._on_button_clicked)

    def _on_button_clicked(self, button_id: int) -> None:
        """Handle button click."""
        command_type = "prompt" if button_id == 0 else "command"
        self.command_type_changed.emit(command_type)

    def get_command_type(self) -> str:
        """Get the currently selected command type."""
        return "prompt" if self.prompt_btn.isChecked() else "command"

    def set_command_type(self, command_type: str) -> None:
        """Set the command type."""
        if command_type == "prompt":
            self.prompt_btn.setChecked(True)
        else:
            self.command_btn.setChecked(True)
