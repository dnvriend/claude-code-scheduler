"""
Schedule Type Selector Widget.

A button group for selecting the schedule type (Manual, Startup, Calendar, Interval,
File Watch, Sequential).

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from claude_code_scheduler.models.enums import ScheduleType


class ScheduleTypeSelector(QWidget):
    """Widget for selecting schedule type with toggle buttons."""

    # Signal emitted when schedule type changes
    schedule_type_changed = pyqtSignal(ScheduleType)

    def __init__(self) -> None:
        super().__init__()
        self._current_type = ScheduleType.MANUAL
        self._has_job = False  # Track if task has a job assigned
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the button group layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        # Define schedule types with labels
        schedule_options = [
            (ScheduleType.MANUAL, "Manual"),
            (ScheduleType.STARTUP, "Startup"),
            (ScheduleType.CALENDAR, "Calendar"),
            (ScheduleType.INTERVAL, "Interval"),
            (ScheduleType.FILE_WATCH, "File Watch"),
            (ScheduleType.SEQUENTIAL, "Sequential"),
        ]

        self.buttons: dict[ScheduleType, QPushButton] = {}

        for stype, label in schedule_options:
            btn = QPushButton(label)
            btn.setObjectName("scheduleTypeButton")
            btn.setCheckable(True)
            btn.setMinimumWidth(70)
            self.buttons[stype] = btn
            self.button_group.addButton(btn)
            layout.addWidget(btn)

            # Connect click handler
            btn.clicked.connect(lambda checked, t=stype: self._on_button_clicked(t))

        # Set default selection
        self.buttons[ScheduleType.MANUAL].setChecked(True)

        # Sequential is disabled by default (requires job assignment)
        self.buttons[ScheduleType.SEQUENTIAL].setEnabled(False)
        self.buttons[ScheduleType.SEQUENTIAL].setToolTip("Requires task to be assigned to a Job")

    def _on_button_clicked(self, schedule_type: ScheduleType) -> None:
        """Handle button click."""
        if schedule_type != self._current_type:
            self._current_type = schedule_type
            self.schedule_type_changed.emit(schedule_type)

    def get_schedule_type(self) -> ScheduleType:
        """Get the currently selected schedule type."""
        return self._current_type

    def set_schedule_type(self, schedule_type: ScheduleType) -> None:
        """Set the selected schedule type."""
        self._current_type = schedule_type
        if schedule_type in self.buttons:
            self.buttons[schedule_type].setChecked(True)

    def set_has_job(self, has_job: bool) -> None:
        """Enable/disable Sequential button based on job assignment.

        Args:
            has_job: True if task is assigned to a job.
        """
        self._has_job = has_job
        self.buttons[ScheduleType.SEQUENTIAL].setEnabled(has_job)

        if has_job:
            self.buttons[ScheduleType.SEQUENTIAL].setToolTip("Run as part of job sequence")
        else:
            self.buttons[ScheduleType.SEQUENTIAL].setToolTip(
                "Requires task to be assigned to a Job"
            )

        # If Sequential was selected but job removed, switch to Manual
        if not has_job and self._current_type == ScheduleType.SEQUENTIAL:
            self.set_schedule_type(ScheduleType.MANUAL)
            self.schedule_type_changed.emit(ScheduleType.MANUAL)
