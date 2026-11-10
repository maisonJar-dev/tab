from PySide6.QtCore import QEasingCurve, QEvent, QObject, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from tab.core.config import PomodoroSettings, save_settings
from tab.widgets.callout_card import (
    create_callout_card,
    create_callout_card_row,
    create_callout_card_title,
)
from tab.widgets.rotary_picker import ITEM_SPACING_PIXELS, RotaryPicker

MAXIMUM_DURATION_HOURS = 3
MINIMUM_DURATION_MINUTES = 1
DURATION_DRUM_WIDTH_PIXELS = 64
COLLAPSED_DRUM_HEIGHT_PIXELS = ITEM_SPACING_PIXELS  # just the selection band: the picked number
EXPANDED_DRUM_HEIGHT_PIXELS = 156  # the whole visible drum: no item is cut at the edges
DRUM_EXPAND_ANIMATION_MILLISECONDS = 160


class DurationPicker(QWidget):
    """Hours and minutes drums side by side, read as hours:minutes (0:25 = 25 minutes).

    Collapsed it shows only the picked value; it expands to show neighbouring values while the
    mouse is over it, a drum is being dragged, or a drum got keyboard focus (Up/Down then step).
    0:00 isn't a valid duration, so it snaps up to 0:01.
    """

    duration_minutes_changed_by_user = Signal(int)

    def __init__(self, initial_duration_minutes: int) -> None:
        super().__init__()
        maximum_duration_minutes = MAXIMUM_DURATION_HOURS * 60 + 59
        if not MINIMUM_DURATION_MINUTES <= initial_duration_minutes <= maximum_duration_minutes:
            raise ValueError(
                f"Duration {initial_duration_minutes} min is outside the picker's range "
                f"{MINIMUM_DURATION_MINUTES}-{maximum_duration_minutes} min"
            )
        initial_hours, initial_minutes = divmod(initial_duration_minutes, 60)

        self._hours_drum = self._create_drum(
            [str(hours) for hours in range(MAXIMUM_DURATION_HOURS + 1)]
        )
        self._minutes_drum = self._create_drum([f"{minutes:02d}" for minutes in range(60)])
        self._hours_drum.set_selected_index(initial_hours)
        self._minutes_drum.set_selected_index(initial_minutes)

        hours_minutes_separator = QLabel(":")
        hours_minutes_separator.setObjectName("duration_picker_separator")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._hours_drum)
        layout.addWidget(hours_minutes_separator)
        layout.addWidget(self._minutes_drum)

        self._drum_height_animation = QVariantAnimation(self)
        self._drum_height_animation.setDuration(DRUM_EXPAND_ANIMATION_MILLISECONDS)
        self._drum_height_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._drum_height_animation.valueChanged.connect(self._set_drum_heights)
        self._is_expanded = False
        self._set_drum_heights(COLLAPSED_DRUM_HEIGHT_PIXELS)

    def enterEvent(self, enter_event: QEnterEvent) -> None:
        super().enterEvent(enter_event)
        self._update_expansion()

    def leaveEvent(self, leave_event: QEvent) -> None:
        super().leaveEvent(leave_event)
        self._update_expansion()

    def eventFilter(self, watched_object: QObject, event: QEvent) -> bool:
        if event.type() in (
            QEvent.Type.FocusIn,
            QEvent.Type.FocusOut,
            QEvent.Type.MouseButtonRelease,
        ):
            # Deferred: the drum's own handler (ending a drag, noting the focus reason) runs after.
            QTimer.singleShot(0, self._update_expansion)
        return False

    def _create_drum(self, item_labels: list[str]) -> RotaryPicker:
        drum = RotaryPicker(item_labels)
        drum.setFixedWidth(DURATION_DRUM_WIDTH_PIXELS)
        drum.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        drum.installEventFilter(self)
        drum.selected_index_changed_by_user.connect(self._emit_picked_duration)
        return drum

    def _update_expansion(self) -> None:
        should_be_expanded = self.underMouse() or any(
            drum.is_being_dragged or drum.has_keyboard_focus
            for drum in (self._hours_drum, self._minutes_drum)
        )
        if should_be_expanded == self._is_expanded:
            return
        self._is_expanded = should_be_expanded
        self._drum_height_animation.stop()
        self._drum_height_animation.setStartValue(self._hours_drum.height())
        self._drum_height_animation.setEndValue(
            EXPANDED_DRUM_HEIGHT_PIXELS if should_be_expanded else COLLAPSED_DRUM_HEIGHT_PIXELS
        )
        self._drum_height_animation.start()

    def _set_drum_heights(self, drum_height_pixels: int) -> None:
        self._hours_drum.setFixedHeight(drum_height_pixels)
        self._minutes_drum.setFixedHeight(drum_height_pixels)

    def _emit_picked_duration(self) -> None:
        picked_duration_minutes = (
            self._hours_drum.selected_index * 60 + self._minutes_drum.selected_index
        )
        if picked_duration_minutes < MINIMUM_DURATION_MINUTES:
            self._minutes_drum.set_selected_index(MINIMUM_DURATION_MINUTES)
            picked_duration_minutes = MINIMUM_DURATION_MINUTES
        self.duration_minutes_changed_by_user.emit(picked_duration_minutes)


class SettingsView(QWidget):
    """Stacked callout cards: one per phase duration, then General. Saves on every change."""

    def __init__(self, settings: PomodoroSettings) -> None:
        super().__init__()
        self._settings = settings

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(32, 32, 32, 32)
        page_layout.setSpacing(12)

        for callout_title, settings_field_name in (
            ("Pomodoro", "work_duration_minutes"),
            ("Short break", "short_break_duration_minutes"),
            ("Long break", "long_break_duration_minutes"),
        ):
            duration_card_layout = create_callout_card_row(
                create_callout_card_title(callout_title),
                self._create_duration_picker(settings_field_name),
            )
            page_layout.addWidget(
                create_callout_card(duration_card_layout), alignment=Qt.AlignmentFlag.AlignLeft
            )

        abbreviate_phase_labels_checkbox = QCheckBox("W / S / L")
        abbreviate_phase_labels_checkbox.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        abbreviate_phase_labels_checkbox.setChecked(self._settings.use_abbreviated_phase_labels)
        abbreviate_phase_labels_checkbox.toggled.connect(
            lambda is_checked: self._update_and_save_setting(
                "use_abbreviated_phase_labels", is_checked
            )
        )
        general_card_layout = QVBoxLayout()
        general_card_layout.setSpacing(12)
        general_card_layout.addWidget(create_callout_card_title("General"))
        general_card_layout.addLayout(
            create_callout_card_row(QLabel("Phase labels"), abbreviate_phase_labels_checkbox)
        )
        page_layout.addWidget(
            create_callout_card(general_card_layout), alignment=Qt.AlignmentFlag.AlignLeft
        )
        page_layout.addStretch(1)  # stretch > 0 takes all spare height, so the cards don't grow

    def _create_duration_picker(self, settings_field_name: str) -> DurationPicker:
        duration_picker = DurationPicker(getattr(self._settings, settings_field_name))
        duration_picker.duration_minutes_changed_by_user.connect(
            lambda new_minutes: self._update_and_save_setting(settings_field_name, new_minutes)
        )
        return duration_picker

    def _update_and_save_setting(self, settings_field_name: str, new_value: int | bool) -> None:
        setattr(self._settings, settings_field_name, new_value)
        save_settings(self._settings)
