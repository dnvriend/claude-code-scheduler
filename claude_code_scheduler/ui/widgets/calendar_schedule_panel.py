"""
Calendar Schedule Panel Widget.

Panel for configuring calendar-based schedules (daily, weekly, monthly).

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from claude_code_scheduler.models.task import ScheduleConfig


class CalendarSchedulePanel(QFrame):
    """Panel for configuring calendar-based schedules."""

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

        # Frequency selector
        freq_layout = QHBoxLayout()
        freq_label = QLabel("Frequency:")
        freq_label.setMinimumWidth(80)
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.freq_combo.currentTextChanged.connect(self._on_frequency_changed)
        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.freq_combo, 1)
        layout.addLayout(freq_layout)

        # Time selector
        time_layout = QHBoxLayout()
        time_label = QLabel("Time:")
        time_label.setMinimumWidth(80)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(self.time_edit.time().fromString("09:00", "HH:mm"))
        self.time_edit.timeChanged.connect(self._on_config_changed)
        time_layout.addWidget(time_label)
        time_layout.addWidget(self.time_edit, 1)
        layout.addLayout(time_layout)

        # Weekly: Day of week selector
        self.weekly_container = QWidget()
        weekly_layout = QVBoxLayout(self.weekly_container)
        weekly_layout.setContentsMargins(0, 0, 0, 0)
        weekly_layout.setSpacing(8)

        days_label = QLabel("Days:")
        weekly_layout.addWidget(days_label)

        days_row = QHBoxLayout()
        days_row.setSpacing(4)
        self.day_checkboxes: list[QCheckBox] = []
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(day_names):
            cb = QCheckBox(day)
            cb.stateChanged.connect(self._on_config_changed)
            self.day_checkboxes.append(cb)
            days_row.addWidget(cb)
        days_row.addStretch()
        weekly_layout.addLayout(days_row)

        layout.addWidget(self.weekly_container)
        self.weekly_container.hide()

        # Monthly: Day of month selector
        self.monthly_container = QWidget()
        monthly_layout = QHBoxLayout(self.monthly_container)
        monthly_layout.setContentsMargins(0, 0, 0, 0)

        day_of_month_label = QLabel("Day of month:")
        day_of_month_label.setMinimumWidth(80)
        self.day_of_month_spin = QSpinBox()
        self.day_of_month_spin.setRange(1, 31)
        self.day_of_month_spin.setValue(1)
        self.day_of_month_spin.valueChanged.connect(self._on_config_changed)
        monthly_layout.addWidget(day_of_month_label)
        monthly_layout.addWidget(self.day_of_month_spin, 1)

        layout.addWidget(self.monthly_container)
        self.monthly_container.hide()

        layout.addStretch()

    def _on_frequency_changed(self, frequency: str) -> None:
        """Handle frequency selection change."""
        self.weekly_container.setVisible(frequency == "Weekly")
        self.monthly_container.setVisible(frequency == "Monthly")
        self._on_config_changed()

    def _on_config_changed(self) -> None:
        """Emit config changed signal."""
        self.config_changed.emit()

    def get_config(self) -> dict[str, object]:
        """Get the current schedule configuration."""
        freq = self.freq_combo.currentText().lower()
        config: dict[str, object] = {
            "calendar_frequency": freq,
            "calendar_time": self.time_edit.time().toPyTime(),
        }

        if freq == "weekly":
            selected_days = [i for i, cb in enumerate(self.day_checkboxes) if cb.isChecked()]
            config["calendar_days_of_week"] = selected_days if selected_days else [0]
        elif freq == "monthly":
            config["calendar_day_of_month"] = self.day_of_month_spin.value()

        return config

    def set_config(self, schedule: ScheduleConfig) -> None:
        """Set the panel state from a ScheduleConfig."""
        # Set frequency
        freq = schedule.calendar_frequency or "daily"
        index = {"daily": 0, "weekly": 1, "monthly": 2}.get(freq, 0)
        self.freq_combo.setCurrentIndex(index)

        # Set time
        if schedule.calendar_time:
            from PyQt6.QtCore import QTime

            self.time_edit.setTime(
                QTime(schedule.calendar_time.hour, schedule.calendar_time.minute)
            )

        # Set weekly days
        if schedule.calendar_days_of_week:
            for i, cb in enumerate(self.day_checkboxes):
                cb.setChecked(i in schedule.calendar_days_of_week)
        else:
            # Default: Monday
            self.day_checkboxes[0].setChecked(True)

        # Set monthly day
        if schedule.calendar_day_of_month:
            self.day_of_month_spin.setValue(schedule.calendar_day_of_month)

        # Update visibility
        self._on_frequency_changed(freq.capitalize())
