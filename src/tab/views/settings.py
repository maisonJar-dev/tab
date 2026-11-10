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
from tab.core.timer import PomodoroTimer
from tab.widgets.callout_card import (
    CALLOUT_CARD_WIDTH_PIXELS,
    create_callout_card,
    create_callout_card_row,
    create_callout_card_title,
)
from tab.widgets.rotary_picker import ITEM_SPACING_PIXELS, RotaryPicker
from tab.widgets.themed_icon_button import ThemedIconButton
from tab.widgets.view_icons import paint_shortcuts_icon

MAXIMUM_DURATION_HOURS = 3
MINIMUM_DURATION_MINUTES = 1
DURATION_DRUM_WIDTH_PIXELS = 64
COLLAPSED_DRUM_HEIGHT_PIXELS = ITEM_SPACING_PIXELS  # just the selection band: the picked number
SHORTCUTS_BUTTON_ICON_SIZE_PIXELS = 24  # same as the Profile button
SHORTCUTS_CARD_GAP_PIXELS = 12  # the gap between stacked cards
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
    """Stacked callout cards: one per phase duration, then General, then Shortcuts. Saves on
    every change.

    Toggling "Link work and duration" goes through the timer, which pauses both clocks.
    The square ⌘ button beside the Shortcuts title card emits
    `shortcuts_page_requested`; the main screen opens the page.
    """

    shortcuts_page_requested = Signal()

    def __init__(self, settings: PomodoroSettings, pomodoro_timer: PomodoroTimer) -> None:
        super().__init__()
        self._settings = settings
        self._pomodoro_timer = pomodoro_timer

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
        intro_sound_checkbox = QCheckBox("On")
        intro_sound_checkbox.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        intro_sound_checkbox.setChecked(self._settings.is_intro_sound_enabled)
        intro_sound_checkbox.toggled.connect(
            lambda is_checked: self._update_and_save_setting("is_intro_sound_enabled", is_checked)
        )
        phase_end_notification_checkbox = QCheckBox("On")
        phase_end_notification_checkbox.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        phase_end_notification_checkbox.setChecked(self._settings.is_phase_end_notification_enabled)
        phase_end_notification_checkbox.toggled.connect(
            lambda is_checked: self._update_and_save_setting(
                "is_phase_end_notification_enabled", is_checked
            )
        )
        link_work_with_duration_checkbox = QCheckBox("On")
        link_work_with_duration_checkbox.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        link_work_with_duration_checkbox.setChecked(self._settings.is_work_linked_with_duration)
        link_work_with_duration_checkbox.toggled.connect(self._change_work_duration_linking)
        general_card_layout = QVBoxLayout()
        general_card_layout.setSpacing(12)
        general_card_layout.addWidget(create_callout_card_title("General"))
        general_card_layout.addLayout(
            create_callout_card_row(QLabel("Phase labels"), abbreviate_phase_labels_checkbox)
        )
        general_card_layout.addLayout(
            create_callout_card_row(QLabel("Intro sound"), intro_sound_checkbox)
        )
        general_card_layout.addLayout(
            create_callout_card_row(QLabel("Notifications"), phase_end_notification_checkbox)
        )
        general_card_layout.addLayout(
            create_callout_card_row(
                QLabel("Link work and duration"), link_work_with_duration_checkbox
            )
        )
        page_layout.addWidget(
            create_callout_card(general_card_layout), alignment=Qt.AlignmentFlag.AlignLeft
        )

        shortcuts_button = ThemedIconButton(
            "Shortcuts (Ctrl+S)",
            paint_shortcuts_icon,
            SHORTCUTS_BUTTON_ICON_SIZE_PIXELS,
            is_checkable=False,
        )
        shortcuts_button.setObjectName("settings_shortcuts_button")
        shortcuts_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        shortcuts_button.clicked.connect(self.shortcuts_page_requested.emit)
        shortcuts_title_card_layout = QVBoxLayout()
        shortcuts_title_card_layout.addWidget(create_callout_card_title("Shortcuts"))
        shortcuts_title_card = create_callout_card(shortcuts_title_card_layout)
        # A square as tall as the title card; together they span one card's width, so the
        # button's right edge lines up with the cards above.
        shortcuts_title_card.ensurePolished()  # theme.qss font sizes feed the height
        # Rounded up to even: the 24 px icon then has equal space on each side (on an odd side
        # Qt splits the leftover unevenly and the icon sits half a pixel off centre).
        title_card_height_pixels = shortcuts_title_card.sizeHint().height()
        shortcuts_button_side_pixels = title_card_height_pixels + title_card_height_pixels % 2
        shortcuts_title_card.setFixedHeight(shortcuts_button_side_pixels)
        shortcuts_button.setFixedSize(shortcuts_button_side_pixels, shortcuts_button_side_pixels)
        shortcuts_title_card.setFixedWidth(
            CALLOUT_CARD_WIDTH_PIXELS - SHORTCUTS_CARD_GAP_PIXELS - shortcuts_button_side_pixels
        )
        shortcuts_row_layout = QHBoxLayout()
        shortcuts_row_layout.setSpacing(SHORTCUTS_CARD_GAP_PIXELS)
        shortcuts_row_layout.addWidget(shortcuts_title_card)
        shortcuts_row_layout.addWidget(shortcuts_button)
        shortcuts_row_layout.addStretch(1)
        page_layout.addLayout(shortcuts_row_layout)
        page_layout.addStretch(1)  # stretch > 0 takes all spare height, so the cards don't grow

    def _create_duration_picker(self, settings_field_name: str) -> DurationPicker:
        duration_picker = DurationPicker(getattr(self._settings, settings_field_name))
        duration_picker.duration_minutes_changed_by_user.connect(
            lambda new_minutes: self._update_and_save_setting(settings_field_name, new_minutes)
        )
        return duration_picker

    def _change_work_duration_linking(self, is_linked: bool) -> None:
        self._pomodoro_timer.set_work_linked_with_duration(is_linked)
        save_settings(self._settings)

    def _update_and_save_setting(self, settings_field_name: str, new_value: int | bool) -> None:
        setattr(self._settings, settings_field_name, new_value)
        save_settings(self._settings)
