from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFormLayout, QFrame, QSpinBox, QVBoxLayout, QWidget

from tab.core.config import PomodoroSettings, save_settings

MAXIMUM_DURATION_MINUTES = 180


class SettingsView(QWidget):
    """Edits the shared PomodoroSettings in place and saves on every change."""

    def __init__(self, settings: PomodoroSettings) -> None:
        super().__init__()
        self._settings = settings

        # A solid panel behind the form separates it from the wall behind the main screen.
        settings_panel = QFrame()
        settings_panel.setObjectName("settings_panel")
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(32, 32, 32, 32)
        page_layout.addWidget(
            settings_panel, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        form_layout = QFormLayout(settings_panel)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setVerticalSpacing(14)
        for row_label, settings_field_name in (
            ("Pomodoro length (min)", "work_duration_minutes"),
            ("Short break (min)", "short_break_duration_minutes"),
            ("Long break (min)", "long_break_duration_minutes"),
        ):
            form_layout.addRow(row_label, self._create_minutes_spin_box(settings_field_name))

        abbreviate_phase_labels_checkbox = QCheckBox("Show phases as W / S / L")
        abbreviate_phase_labels_checkbox.setChecked(self._settings.use_abbreviated_phase_labels)
        abbreviate_phase_labels_checkbox.toggled.connect(
            lambda is_checked: self._update_and_save_setting(
                "use_abbreviated_phase_labels", is_checked
            )
        )
        form_layout.addRow("Phase labels", abbreviate_phase_labels_checkbox)

    def _create_minutes_spin_box(self, settings_field_name: str) -> QSpinBox:
        minutes_spin_box = QSpinBox()
        minutes_spin_box.setRange(1, MAXIMUM_DURATION_MINUTES)
        minutes_spin_box.setValue(getattr(self._settings, settings_field_name))
        minutes_spin_box.valueChanged.connect(
            lambda new_minutes: self._update_and_save_setting(settings_field_name, new_minutes)
        )
        return minutes_spin_box

    def _update_and_save_setting(self, settings_field_name: str, new_value: int | bool) -> None:
        setattr(self._settings, settings_field_name, new_value)
        save_settings(self._settings)
