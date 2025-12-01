"""
Interval Schedule Panel Widget.

Panel for configuring interval-based schedules (presets, custom, cron).

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from claude_code_scheduler.models.enums import IntervalType
from claude_code_scheduler.models.task import ScheduleConfig


class IntervalSchedulePanel(QFrame):
    """Panel for configuring interval-based schedules."""

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

        # Interval type selector
        type_layout = QHBoxLayout()
        type_label = QLabel("Type:")
        type_label.setMinimumWidth(80)

        self.type_group = QButtonGroup(self)
        self.simple_btn = QPushButton("Simple")
        self.simple_btn.setCheckable(True)
        self.simple_btn.setChecked(True)
        self.custom_btn = QPushButton("Custom")
        self.custom_btn.setCheckable(True)
        self.cron_btn = QPushButton("Cron")
        self.cron_btn.setCheckable(True)

        self.type_group.addButton(self.simple_btn)
        self.type_group.addButton(self.custom_btn)
        self.type_group.addButton(self.cron_btn)

        self.simple_btn.clicked.connect(lambda: self._on_type_changed("simple"))
        self.custom_btn.clicked.connect(lambda: self._on_type_changed("custom"))
        self.cron_btn.clicked.connect(lambda: self._on_type_changed("cron"))

        type_layout.addWidget(type_label)
        type_layout.addWidget(self.simple_btn)
        type_layout.addWidget(self.custom_btn)
        type_layout.addWidget(self.cron_btn)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        # Simple: Preset selector
        self.simple_container = QWidget()
        simple_layout = QHBoxLayout(self.simple_container)
        simple_layout.setContentsMargins(0, 0, 0, 0)

        preset_label = QLabel("Preset:")
        preset_label.setMinimumWidth(80)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(
            ["5min", "15min", "30min", "1hour", "2hours", "6hours", "12hours"]
        )
        self.preset_combo.currentTextChanged.connect(self._on_config_changed)
        simple_layout.addWidget(preset_label)
        simple_layout.addWidget(self.preset_combo, 1)

        layout.addWidget(self.simple_container)

        # Custom: Value + Unit
        self.custom_container = QWidget()
        custom_layout = QHBoxLayout(self.custom_container)
        custom_layout.setContentsMargins(0, 0, 0, 0)

        every_label = QLabel("Every:")
        every_label.setMinimumWidth(80)
        self.value_spin = QSpinBox()
        self.value_spin.setRange(1, 999)
        self.value_spin.setValue(5)
        self.value_spin.valueChanged.connect(self._on_config_changed)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["minutes", "hours", "days"])
        self.unit_combo.currentTextChanged.connect(self._on_config_changed)

        custom_layout.addWidget(every_label)
        custom_layout.addWidget(self.value_spin)
        custom_layout.addWidget(self.unit_combo, 1)

        layout.addWidget(self.custom_container)
        self.custom_container.hide()

        # Cron: Expression input
        self.cron_container = QWidget()
        cron_layout = QVBoxLayout(self.cron_container)
        cron_layout.setContentsMargins(0, 0, 0, 0)
        cron_layout.setSpacing(8)

        cron_row = QHBoxLayout()
        cron_label = QLabel("Expression:")
        cron_label.setMinimumWidth(80)
        self.cron_input = QLineEdit()
        self.cron_input.setPlaceholderText("* * * * * (min hour day month weekday)")
        self.cron_input.setText("0 * * * *")  # Every hour
        self.cron_input.textChanged.connect(self._on_config_changed)
        cron_row.addWidget(cron_label)
        cron_row.addWidget(self.cron_input, 1)
        cron_layout.addLayout(cron_row)

        # Cron help text
        help_label = QLabel("Format: minute hour day-of-month month day-of-week")
        help_label.setObjectName("helpLabel")
        cron_layout.addWidget(help_label)

        layout.addWidget(self.cron_container)
        self.cron_container.hide()

        layout.addStretch()

    def _on_type_changed(self, interval_type: str) -> None:
        """Handle interval type selection change."""
        self.simple_container.setVisible(interval_type == "simple")
        self.custom_container.setVisible(interval_type == "custom")
        self.cron_container.setVisible(interval_type == "cron")
        self._on_config_changed()

    def _on_config_changed(self) -> None:
        """Emit config changed signal."""
        self.config_changed.emit()

    def get_config(self) -> dict[str, object]:
        """Get the current schedule configuration."""
        config: dict[str, object] = {}

        if self.simple_btn.isChecked():
            config["interval_type"] = IntervalType.SIMPLE
            config["interval_preset"] = self.preset_combo.currentText()
        elif self.custom_btn.isChecked():
            config["interval_type"] = IntervalType.CUSTOM
            config["interval_value"] = self.value_spin.value()
            config["interval_unit"] = self.unit_combo.currentText()
        elif self.cron_btn.isChecked():
            config["interval_type"] = IntervalType.CRON
            config["interval_cron"] = self.cron_input.text()

        return config

    def set_config(self, schedule: ScheduleConfig) -> None:
        """Set the panel state from a ScheduleConfig."""
        interval_type = schedule.interval_type

        if interval_type == IntervalType.SIMPLE or schedule.interval_preset:
            self.simple_btn.setChecked(True)
            self._on_type_changed("simple")
            if schedule.interval_preset:
                index = self.preset_combo.findText(schedule.interval_preset)
                if index >= 0:
                    self.preset_combo.setCurrentIndex(index)
        elif interval_type == IntervalType.CUSTOM or (
            schedule.interval_value and schedule.interval_unit
        ):
            self.custom_btn.setChecked(True)
            self._on_type_changed("custom")
            if schedule.interval_value:
                self.value_spin.setValue(schedule.interval_value)
            if schedule.interval_unit:
                index = self.unit_combo.findText(schedule.interval_unit)
                if index >= 0:
                    self.unit_combo.setCurrentIndex(index)
        elif interval_type == IntervalType.CRON or schedule.interval_cron:
            self.cron_btn.setChecked(True)
            self._on_type_changed("cron")
            if schedule.interval_cron:
                self.cron_input.setText(schedule.interval_cron)
        else:
            # Default to simple
            self.simple_btn.setChecked(True)
            self._on_type_changed("simple")
