"""
Advanced Options Panel Widget.

Panel for configuring advanced task options: retry and tool restrictions.
Notifications are handled separately in the task editor panel.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from claude_code_scheduler.models.task import RetryConfig


class AdvancedOptionsPanel(QFrame):
    """Panel for configuring advanced task options (retry, tool restrictions)."""

    config_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("advancedOptionsPanel")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Retry group
        retry_group = QGroupBox("Retry on Failure")
        retry_layout = QVBoxLayout(retry_group)

        self.retry_enabled_cb = QCheckBox("Enable retry")
        self.retry_enabled_cb.stateChanged.connect(self._on_retry_toggled)
        retry_layout.addWidget(self.retry_enabled_cb)

        retry_form = QFormLayout()
        retry_form.setSpacing(8)

        self.max_attempts_spin = QSpinBox()
        self.max_attempts_spin.setRange(1, 10)
        self.max_attempts_spin.setValue(3)
        retry_form.addRow("Max attempts:", self.max_attempts_spin)

        self.retry_delay_spin = QSpinBox()
        self.retry_delay_spin.setRange(1, 3600)
        self.retry_delay_spin.setValue(60)
        self.retry_delay_spin.setSuffix(" seconds")
        retry_form.addRow("Delay:", self.retry_delay_spin)

        self.backoff_spin = QDoubleSpinBox()
        self.backoff_spin.setRange(1.0, 5.0)
        self.backoff_spin.setValue(2.0)
        self.backoff_spin.setSingleStep(0.5)
        retry_form.addRow("Backoff multiplier:", self.backoff_spin)

        retry_layout.addLayout(retry_form)
        layout.addWidget(retry_group)

        # Tool restrictions group
        tools_group = QGroupBox("Tool Restrictions")
        tools_layout = QVBoxLayout(tools_group)

        allowed_label = QLabel("Allowed tools (comma-separated):")
        allowed_label.setObjectName("helpLabel")
        tools_layout.addWidget(allowed_label)

        self.allowed_tools_edit = QLineEdit()
        self.allowed_tools_edit.setPlaceholderText("Leave empty for all tools")
        tools_layout.addWidget(self.allowed_tools_edit)

        disallowed_label = QLabel("Disallowed tools (comma-separated):")
        disallowed_label.setObjectName("helpLabel")
        tools_layout.addWidget(disallowed_label)

        self.disallowed_tools_edit = QLineEdit()
        self.disallowed_tools_edit.setPlaceholderText("e.g., Bash, Write")
        tools_layout.addWidget(self.disallowed_tools_edit)

        layout.addWidget(tools_group)

        # Initialize state
        self._on_retry_toggled()

    def _on_retry_toggled(self) -> None:
        """Handle retry enabled toggle."""
        enabled = self.retry_enabled_cb.isChecked()
        self.max_attempts_spin.setEnabled(enabled)
        self.retry_delay_spin.setEnabled(enabled)
        self.backoff_spin.setEnabled(enabled)

    def get_retry_config(self) -> RetryConfig:
        """Get the retry configuration."""
        return RetryConfig(
            enabled=self.retry_enabled_cb.isChecked(),
            max_attempts=self.max_attempts_spin.value(),
            delay_seconds=self.retry_delay_spin.value(),
            backoff_multiplier=self.backoff_spin.value(),
        )

    def set_retry_config(self, config: RetryConfig) -> None:
        """Set the retry configuration."""
        self.retry_enabled_cb.setChecked(config.enabled)
        self.max_attempts_spin.setValue(config.max_attempts)
        self.retry_delay_spin.setValue(config.delay_seconds)
        self.backoff_spin.setValue(config.backoff_multiplier)
        self._on_retry_toggled()

    def get_allowed_tools(self) -> list[str]:
        """Get the allowed tools list."""
        text = self.allowed_tools_edit.text().strip()
        if not text:
            return []
        return [t.strip() for t in text.split(",") if t.strip()]

    def set_allowed_tools(self, tools: list[str]) -> None:
        """Set the allowed tools list."""
        self.allowed_tools_edit.setText(", ".join(tools))

    def get_disallowed_tools(self) -> list[str]:
        """Get the disallowed tools list."""
        text = self.disallowed_tools_edit.text().strip()
        if not text:
            return []
        return [t.strip() for t in text.split(",") if t.strip()]

    def set_disallowed_tools(self, tools: list[str]) -> None:
        """Set the disallowed tools list."""
        self.disallowed_tools_edit.setText(", ".join(tools))
