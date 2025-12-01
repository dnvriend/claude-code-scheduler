"""
File Watch Schedule Panel Widget.

Panel for configuring file watch-based schedules.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from claude_code_scheduler.models.task import ScheduleConfig


class FileWatchSchedulePanel(QFrame):
    """Panel for configuring file watch-based schedules."""

    # Signal emitted when schedule config changes
    config_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("schedulePanel")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Directory selector
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Directory:")
        dir_label.setMinimumWidth(80)
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("~/projects/my-repo")
        self.dir_input.textChanged.connect(self._on_config_changed)

        browse_btn = QPushButton("Browse...")
        browse_btn.setObjectName("smallButton")
        browse_btn.clicked.connect(self._on_browse_clicked)

        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_input, 1)
        dir_layout.addWidget(browse_btn)
        layout.addLayout(dir_layout)

        # Recursive checkbox
        self.recursive_cb = QCheckBox("Include subdirectories")
        self.recursive_cb.setChecked(True)
        self.recursive_cb.stateChanged.connect(self._on_config_changed)
        layout.addWidget(self.recursive_cb)

        # Debounce setting
        debounce_layout = QHBoxLayout()
        debounce_label = QLabel("Debounce:")
        debounce_label.setMinimumWidth(80)
        self.debounce_spin = QSpinBox()
        self.debounce_spin.setRange(1, 300)
        self.debounce_spin.setValue(5)
        self.debounce_spin.setSuffix(" seconds")
        self.debounce_spin.valueChanged.connect(self._on_config_changed)

        debounce_help = QLabel("(wait after last change)")
        debounce_help.setObjectName("helpLabel")

        debounce_layout.addWidget(debounce_label)
        debounce_layout.addWidget(self.debounce_spin)
        debounce_layout.addWidget(debounce_help)
        debounce_layout.addStretch()
        layout.addLayout(debounce_layout)

        layout.addStretch()

    def _on_browse_clicked(self) -> None:
        """Handle browse button click."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Watch",
            self.dir_input.text() or "~",
        )
        if directory:
            self.dir_input.setText(directory)

    def _on_config_changed(self) -> None:
        """Emit config changed signal."""
        self.config_changed.emit()

    def get_config(self) -> dict[str, object]:
        """Get the current schedule configuration."""
        return {
            "watch_directory": self.dir_input.text() or "~",
            "watch_recursive": self.recursive_cb.isChecked(),
            "watch_debounce_seconds": self.debounce_spin.value(),
        }

    def set_config(self, schedule: ScheduleConfig) -> None:
        """Set the panel state from a ScheduleConfig."""
        if schedule.watch_directory:
            self.dir_input.setText(schedule.watch_directory)

        if schedule.watch_recursive is not None:
            self.recursive_cb.setChecked(schedule.watch_recursive)

        if schedule.watch_debounce_seconds is not None:
            self.debounce_spin.setValue(schedule.watch_debounce_seconds)
