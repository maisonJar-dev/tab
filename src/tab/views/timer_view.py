import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tab.core.config import PomodoroSettings
from tab.core.timer import PomodoroTimer, TimerPhase
from tab.widgets.chronograph_dial import MECHANICAL_BEATS_PER_SECOND, ChronographDial
from tab.widgets.rotary_picker import SELECTION_BAND_INSET_PIXELS as PHASE_PICKER_BAND_INSET_PIXELS
from tab.widgets.rotary_picker import RotaryPicker
from tab.widgets.themed_icon_button import PaintIcon, ThemedIconButton
from tab.widgets.view_icons import paint_pause_icon, paint_reset_icon, paint_start_icon

DISPLAY_REFRESH_INTERVAL_MILLISECONDS = 1000 // MECHANICAL_BEATS_PER_SECOND
PHASES_IN_PICKER_ORDER = [TimerPhase.WORK, TimerPhase.SHORT_BREAK, TimerPhase.LONG_BREAK]
FULL_PHASE_LABELS = ["Working", "Short Break", "Long Break"]
ABBREVIATED_PHASE_LABELS = ["W", "S", "L"]
CONTROL_ICON_SIZE_PIXELS = 20
RESET_PRESS_FLASH_MILLISECONDS = 180  # a click can be shorter than a frame; hold :pressed visibly


class TimerView(QWidget):
    """Phase picker with icon controls beneath it on the left; dial and countdown on the right."""

    def __init__(self, pomodoro_timer: PomodoroTimer, settings: PomodoroSettings) -> None:
        super().__init__()
        self._pomodoro_timer = pomodoro_timer
        self._settings = settings

        self._phase_picker = RotaryPicker(self._phase_labels_for_current_settings())
        self._phase_picker.selected_index_changed_by_user.connect(self._switch_to_picked_phase)

        self._chronograph_dial = ChronographDial()

        self._countdown_label = QLabel()
        self._countdown_label.setObjectName("timer_countdown_label")
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        control_button_row_layout = QHBoxLayout()
        control_button_row_layout.setSpacing(8)
        # Inset like the wheel's selection band, so the buttons line up with it.
        control_button_row_layout.setContentsMargins(
            PHASE_PICKER_BAND_INSET_PIXELS, 0, PHASE_PICKER_BAND_INSET_PIXELS, 0
        )
        self._start_button = self._create_control_button(
            "Start", paint_start_icon, is_checkable=True
        )
        self._pause_button = self._create_control_button(
            "Pause", paint_pause_icon, is_checkable=True
        )
        self._reset_button = self._create_control_button(
            "Reset", paint_reset_icon, is_checkable=False
        )
        self._start_button.clicked.connect(self._pomodoro_timer.start)
        self._pause_button.clicked.connect(self._pomodoro_timer.pause)
        self._reset_button.clicked.connect(self._pomodoro_timer.reset)
        self._reset_button.clicked.connect(self._flash_reset_button_as_pressed)
        # Exactly one of Start/Pause is lit, mirroring whether the timer is running.
        self._running_state_button_group = QButtonGroup(self)
        self._running_state_button_group.setExclusive(True)
        for control_button in (self._start_button, self._pause_button, self._reset_button):
            control_button.clicked.connect(self._refresh_display)
            control_button_row_layout.addWidget(control_button)
        self._running_state_button_group.addButton(self._start_button)
        self._running_state_button_group.addButton(self._pause_button)

        # The column is as wide as the picker, so the button row matches the wheel above it.
        picker_and_controls_column = QWidget()
        picker_and_controls_column.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        picker_and_controls_layout = QVBoxLayout(picker_and_controls_column)
        picker_and_controls_layout.setContentsMargins(0, 0, 0, 0)
        # Wheel and buttons are centred as one group, so the buttons sit right under the wheel.
        self._phase_picker.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        picker_and_controls_layout.addStretch()
        picker_and_controls_layout.addWidget(self._phase_picker)
        picker_and_controls_layout.addLayout(control_button_row_layout)
        picker_and_controls_layout.addStretch()

        dial_and_countdown_layout = QVBoxLayout()
        dial_and_countdown_layout.addWidget(self._chronograph_dial, stretch=1)
        dial_and_countdown_layout.addWidget(self._countdown_label)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)
        layout.addWidget(picker_and_controls_column)
        layout.addLayout(dial_and_countdown_layout, stretch=1)

        self._display_refresh_timer = QTimer(self)
        self._display_refresh_timer.timeout.connect(self._refresh_display)
        self._display_refresh_timer.start(DISPLAY_REFRESH_INTERVAL_MILLISECONDS)
        self._refresh_display()

    def _create_control_button(
        self, title: str, paint_icon: PaintIcon, is_checkable: bool
    ) -> ThemedIconButton:
        control_button = ThemedIconButton(
            title, paint_icon, CONTROL_ICON_SIZE_PIXELS, is_checkable=is_checkable
        )
        control_button.setObjectName("timer_control_button")
        control_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return control_button

    def _flash_reset_button_as_pressed(self) -> None:
        self._reset_button.setDown(True)
        QTimer.singleShot(RESET_PRESS_FLASH_MILLISECONDS, lambda: self._reset_button.setDown(False))

    def _phase_labels_for_current_settings(self) -> list[str]:
        if self._settings.use_abbreviated_phase_labels:
            return ABBREVIATED_PHASE_LABELS
        return FULL_PHASE_LABELS

    def _switch_to_picked_phase(self, picked_index: int) -> None:
        self._pomodoro_timer.switch_to_phase(PHASES_IN_PICKER_ORDER[picked_index])
        self._refresh_display()

    def _refresh_display(self) -> None:
        self._pomodoro_timer.advance_phase_if_finished()
        # Read from the timer, not the last click: it also stops itself at a phase's end.
        running_state_button = (
            self._start_button if self._pomodoro_timer.is_running else self._pause_button
        )
        running_state_button.setChecked(True)
        self._phase_picker.set_item_labels(self._phase_labels_for_current_settings())
        self._phase_picker.set_selected_index(
            PHASES_IN_PICKER_ORDER.index(self._pomodoro_timer.current_phase)
        )
        self._chronograph_dial.show_timer_state(
            elapsed_seconds_in_phase=self._pomodoro_timer.elapsed_seconds_in_phase(),
            phase_duration_seconds=self._pomodoro_timer.current_phase_duration_seconds(),
            completed_work_sessions_in_cycle=self._pomodoro_timer.completed_work_sessions_in_current_cycle(),
            focus_totaliser_seconds=self._pomodoro_timer.focus_totaliser_seconds(),
        )
        remaining_whole_seconds = math.ceil(self._pomodoro_timer.remaining_seconds_in_phase())
        minutes, seconds = divmod(remaining_whole_seconds, 60)
        self._countdown_label.setText(f"{minutes:02d}:{seconds:02d}")
