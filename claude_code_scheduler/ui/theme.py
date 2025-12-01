"""Theme stylesheet for Claude Code Scheduler.

This module contains dark and light theme stylesheets for the PyQt6 application,
providing Apple-inspired styling.

Key Components:
    - DARK_THEME: Dark mode stylesheet (default)
    - LIGHT_THEME: Light mode stylesheet
    - get_theme: Function to retrieve theme by name

Dependencies:
    - PyQt6: Stylesheets applied via QApplication.setStyleSheet

Related Modules:
    - main: Applies theme at startup
    - ui.main_window: Theme switching
    - models.settings: Theme preference storage

Called By:
    - main.main: Apply initial theme
    - SettingsDialog: Theme change

Example:
    >>> from claude_code_scheduler.ui.theme import get_theme
    >>> app.setStyleSheet(get_theme(dark=True))

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

DARK_THEME = """
/* Apple-inspired dark theme with grays, blacks, and blue accents */

/* Main window */
QMainWindow {
    background-color: #1c1c1e;
}

/* Panels */
QFrame#taskListPanel,
QFrame#taskEditorPanel,
QFrame#runsPanel,
QFrame#logsPanel {
    background-color: #2c2c2e;
    border: 1px solid #3a3a3c;
    border-radius: 10px;
}

/* Panel headers */
QWidget#panelHeader {
    background-color: #3a3a3c;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}

/* Titles */
QLabel#appTitle {
    color: #0a84ff;
    font-size: 18px;
    font-weight: bold;
}

QLabel#panelTitle {
    color: #ffffff;
    font-size: 14px;
    font-weight: bold;
}

/* Labels */
QLabel {
    color: #98989d;
}

QLabel#emptyStateLabel {
    color: #636366;
    font-size: 13px;
}

QLabel#versionLabel {
    color: #48484a;
    font-size: 11px;
    padding: 8px;
}

QLabel#sortLabel {
    color: #8e8e93;
    font-size: 12px;
}

/* Buttons */
QPushButton {
    background-color: #3a3a3c;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 10px 16px;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #48484a;
}

QPushButton:pressed {
    background-color: #2c2c2e;
}

QPushButton#primaryButton {
    background-color: #0a84ff;
    color: #ffffff;
}

QPushButton#primaryButton:hover {
    background-color: #409cff;
}

QPushButton#primaryButton:pressed {
    background-color: #0064d2;
}

QPushButton#secondaryButton {
    background-color: transparent;
    border: 1px solid #48484a;
    color: #98989d;
}

QPushButton#secondaryButton:hover {
    background-color: #3a3a3c;
    color: #ffffff;
}

QPushButton#smallButton {
    padding: 4px 10px;
    font-size: 11px;
}

/* Task Item Widget */
QFrame#taskItem {
    background-color: #2c2c2e;
    border: 1px solid #3a3a3c;
    border-radius: 8px;
}

QFrame#taskItem:hover {
    border-color: #0a84ff;
}

QFrame#taskItem[selected="true"] {
    border-color: #0a84ff;
    border-width: 2px;
}

QLabel#taskName {
    color: #ffffff;
    font-size: 14px;
    font-weight: bold;
}

QLabel#scheduleLabel {
    color: #8e8e93;
    font-size: 12px;
}

QLabel#statusLabel {
    color: #98989d;
    font-size: 12px;
}

QLabel#modelBadge {
    background-color: #3a3a3c;
    color: #98989d;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
}

QLabel#modelBadge[model="opus"] {
    background-color: #bf5af2;
    color: #ffffff;
}

QLabel#modelBadge[model="sonnet"] {
    background-color: #0a84ff;
    color: #ffffff;
}

QLabel#modelBadge[model="haiku"] {
    background-color: #30d158;
    color: #ffffff;
}

QLabel#profileBadge {
    background-color: #5e5ce6;
    color: #ffffff;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
}

QPushButton#actionButton {
    background-color: transparent;
    border: 1px solid #3a3a3c;
    border-radius: 4px;
    padding: 0px;
    font-size: 12px;
}

QPushButton#actionButton:hover {
    background-color: #3a3a3c;
}

QPushButton#toggleButton {
    background-color: #48484a;
    border-radius: 11px;
    border: none;
}

/* View mode labels */
QLabel#sectionLabel {
    color: #8e8e93;
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
}

QLabel#viewValue {
    color: #ffffff;
    font-size: 13px;
}

QLabel#fieldLabel {
    color: #8e8e93;
    font-size: 12px;
    margin-bottom: 4px;
}

/* Form inputs */
QLineEdit {
    background-color: #1c1c1e;
    color: #ffffff;
    border: 1px solid #3a3a3c;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus {
    border-color: #0a84ff;
}

QPlainTextEdit {
    background-color: #1c1c1e;
    color: #ffffff;
    border: 1px solid #3a3a3c;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}

QPlainTextEdit:focus {
    border-color: #0a84ff;
}

/* Scroll areas */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    background-color: #1c1c1e;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #48484a;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #636366;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #1c1c1e;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #48484a;
    border-radius: 4px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #636366;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Combo boxes */
QComboBox {
    background-color: #3a3a3c;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    min-width: 100px;
}

QComboBox:hover {
    background-color: #48484a;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #ffffff;
}

QComboBox QAbstractItemView {
    background-color: #2c2c2e;
    color: #ffffff;
    selection-background-color: #3a3a3c;
    border: 1px solid #3a3a3c;
    border-radius: 6px;
}

/* Tab widget */
QTabWidget::pane {
    border: none;
    background-color: transparent;
}

QTabBar::tab {
    background-color: transparent;
    color: #636366;
    padding: 8px 16px;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:selected {
    color: #0a84ff;
    border-bottom: 2px solid #0a84ff;
}

QTabBar::tab:hover:!selected {
    color: #98989d;
}

/* Text edit (logs) */
QPlainTextEdit#logTextEdit {
    background-color: #1c1c1e;
    color: #30d158;
    border: none;
    font-family: "Menlo", "Monaco", monospace;
    font-size: 12px;
    padding: 12px;
}

/* Schedule panels */
QFrame#schedulePanel {
    background-color: #2c2c2e;
    border: 1px solid #3a3a3c;
    border-radius: 6px;
    padding: 8px;
}

/* Schedule type selector buttons */
QPushButton#scheduleTypeButton {
    background-color: #3a3a3c;
    color: #98989d;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 12px;
}

QPushButton#scheduleTypeButton:hover {
    background-color: #48484a;
}

QPushButton#scheduleTypeButton:checked {
    background-color: #0a84ff;
    color: #ffffff;
}

/* Help labels */
QLabel#helpLabel {
    color: #636366;
    font-size: 11px;
    font-style: italic;
}

/* Spinbox styling */
QSpinBox {
    background-color: #1c1c1e;
    color: #ffffff;
    border: 1px solid #3a3a3c;
    border-radius: 6px;
    padding: 4px 8px;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: #3a3a3c;
    border: none;
    width: 16px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #48484a;
}

/* Double spinbox styling */
QDoubleSpinBox {
    background-color: #1c1c1e;
    color: #ffffff;
    border: 1px solid #3a3a3c;
    border-radius: 6px;
    padding: 4px 8px;
}

QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: #3a3a3c;
    border: none;
    width: 16px;
}

QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #48484a;
}

/* Time edit styling */
QTimeEdit {
    background-color: #1c1c1e;
    color: #ffffff;
    border: 1px solid #3a3a3c;
    border-radius: 6px;
    padding: 4px 8px;
}

/* Checkbox styling */
QCheckBox {
    color: #e5e5e7;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #48484a;
    background-color: #1c1c1e;
}

QCheckBox::indicator:checked {
    background-color: #0a84ff;
    border-color: #0a84ff;
}

/* Dialogs */
QDialog {
    background-color: #1c1c1e;
}

QGroupBox {
    color: #e5e5e7;
    font-weight: bold;
    border: 1px solid #3a3a3c;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QDialogButtonBox QPushButton {
    min-width: 80px;
}

/* Splitters */
QSplitter::handle {
    background-color: #3a3a3c;
}

QSplitter::handle:horizontal {
    width: 1px;
}

QSplitter::handle:vertical {
    height: 1px;
}

/* Task list container */
QWidget#taskListContainer,
QWidget#runsListContainer,
QWidget#taskEditorContent {
    background-color: transparent;
}

/* Bottom buttons area */
QWidget#bottomButtons {
    background-color: #3a3a3c;
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
}

/* Run item widget */
QFrame#runItem {
    background-color: #2c2c2e;
    border: 1px solid #3a3a3c;
    border-radius: 8px;
}

QFrame#runItem:hover {
    border-color: #0a84ff;
}

QLabel#runTaskName {
    color: #ffffff;
    font-size: 13px;
    font-weight: bold;
}

QLabel#runTimeLabel {
    color: #8e8e93;
    font-size: 11px;
}

QLabel#runDurationLabel {
    color: #636366;
    font-size: 11px;
}

QLabel#runStatusBadge {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: bold;
}

QLabel#runStatusBadge[status="upcoming"] {
    background-color: #0a84ff;
    color: #ffffff;
}

QLabel#runStatusBadge[status="running"] {
    background-color: #ff9f0a;
    color: #ffffff;
}

QLabel#runStatusBadge[status="success"] {
    background-color: #30d158;
    color: #ffffff;
}

QLabel#runStatusBadge[status="failed"] {
    background-color: #ff453a;
    color: #ffffff;
}

QLabel#runStatusBadge[status="cancelled"] {
    background-color: #8e8e93;
    color: #ffffff;
}

/* Command type selector */
QFrame#commandTypeSelector {
    background-color: #3a3a3c;
    border-radius: 8px;
    padding: 2px;
}

QPushButton#commandTypeButton {
    background-color: transparent;
    color: #8e8e93;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 13px;
    min-width: 120px;
}

QPushButton#commandTypeButton:hover {
    color: #e5e5e7;
}

QPushButton#commandTypeButton:checked {
    background-color: #0a84ff;
    color: #ffffff;
}

/* Collapsible widget */
QFrame#collapsibleWidget {
    background-color: transparent;
    border: none;
}

QWidget#collapsibleHeader {
    background-color: transparent;
}

QLabel#collapsibleTriangle {
    color: #0a84ff;
    font-size: 10px;
}

QLabel#collapsibleTitle {
    color: #98989d;
    font-size: 12px;
    font-weight: bold;
}

QWidget#collapsibleContent {
    background-color: transparent;
}

/* Section separator */
QFrame#sectionSeparator {
    background-color: #3a3a3c;
    max-height: 1px;
    margin: 12px 0;
}
"""

LIGHT_THEME = """
/* Main window */
QMainWindow {
    background-color: #f5f5f5;
}

/* Panels */
QFrame#taskListPanel,
QFrame#taskEditorPanel,
QFrame#runsPanel,
QFrame#logsPanel {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
}

/* Panel headers */
QWidget#panelHeader {
    background-color: #f8f8f8;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border-bottom: 1px solid #e0e0e0;
}

/* Titles */
QLabel#appTitle {
    color: #e94560;
    font-size: 18px;
    font-weight: bold;
}

QLabel#panelTitle {
    color: #333333;
    font-size: 14px;
    font-weight: bold;
}

/* Labels */
QLabel {
    color: #666666;
}

QLabel#emptyStateLabel {
    color: #999999;
    font-size: 13px;
}

QLabel#versionLabel {
    color: #bbbbbb;
    font-size: 11px;
    padding: 8px;
}

QLabel#sortLabel {
    color: #888888;
    font-size: 12px;
}

/* Buttons */
QPushButton {
    background-color: #f0f0f0;
    color: #333333;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 10px 16px;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #e8e8e8;
}

QPushButton:pressed {
    background-color: #d8d8d8;
}

QPushButton#primaryButton {
    background-color: #e94560;
    color: #ffffff;
    border: none;
}

QPushButton#primaryButton:hover {
    background-color: #ff5a75;
}

QPushButton#primaryButton:pressed {
    background-color: #c93550;
}

QPushButton#secondaryButton {
    background-color: transparent;
    border: 1px solid #e0e0e0;
    color: #666666;
}

QPushButton#secondaryButton:hover {
    background-color: #f8f8f8;
    color: #333333;
}

QPushButton#smallButton {
    padding: 4px 10px;
    font-size: 11px;
}

/* Scroll areas */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    background-color: #f5f5f5;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #d0d0d0;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #b0b0b0;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #f5f5f5;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #d0d0d0;
    border-radius: 4px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #b0b0b0;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Combo boxes */
QComboBox {
    background-color: #ffffff;
    color: #333333;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 12px;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #c0c0c0;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #666666;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #333333;
    selection-background-color: #f0f0f0;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
}

/* Tab widget */
QTabWidget::pane {
    border: none;
    background-color: transparent;
}

QTabBar::tab {
    background-color: transparent;
    color: #999999;
    padding: 8px 16px;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:selected {
    color: #e94560;
    border-bottom: 2px solid #e94560;
}

QTabBar::tab:hover:!selected {
    color: #666666;
}

/* Text edit (logs) */
QPlainTextEdit#logTextEdit {
    background-color: #fafafa;
    color: #228b22;
    border: none;
    font-family: "Menlo", "Monaco", monospace;
    font-size: 12px;
    padding: 12px;
}

/* Splitters */
QSplitter::handle {
    background-color: #e0e0e0;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

/* Task list container */
QWidget#taskListContainer,
QWidget#runsListContainer,
QWidget#taskEditorContent {
    background-color: transparent;
}

/* Bottom buttons area */
QWidget#bottomButtons {
    background-color: #f8f8f8;
    border-bottom-left-radius: 8px;
    border-bottom-right-radius: 8px;
    border-top: 1px solid #e0e0e0;
}
"""


def get_theme(dark: bool = True) -> str:
    """Get the stylesheet for the specified theme.

    Args:
        dark: If True, return dark theme. If False, return light theme.

    Returns:
        CSS stylesheet string.
    """
    return DARK_THEME if dark else LIGHT_THEME
