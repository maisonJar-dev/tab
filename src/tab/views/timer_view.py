import math
import os
import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from tab.core.config import PomodoroSettings
from tab.core.timer import SESSION_RATINGS, PomodoroTimer, TimerPhase
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
PHASE_END_NOTIFICATION_MILLISECONDS = 3000
IN_WINDOW_NOTIFICATION_TOP_MARGIN_PIXELS = 24
PHASE_END_SOUND_PATH = Path(__file__).parent.parent / "assets" / "swoosh_snap.wav"
# tab.app also names this file; importing it from here would be circular (app imports the views).
NOTIFICATION_ICON_PATH = Path(__file__).parent.parent / "assets" / "tab_icon.svg"
FREEDESKTOP_NOTIFICATIONS_SERVICE = "org.freedesktop.Notifications"
NORMAL_NOTIFICATION_URGENCY = 1  # 0 low (GNOME lists it without a banner), 1 normal, 2 critical
DBUS_REPLY_TIMEOUT_SECONDS = 2
UPCOMING_PHASE_NOTIFICATION_MESSAGES = {
    TimerPhase.WORK: "🥊 Get to work!",
    TimerPhase.SHORT_BREAK: "🧠 Take a quick reset",
    TimerPhase.LONG_BREAK: "☕ Reset",
}


class TimerView(QWidget):
    """Phase picker with icon controls beneath it on the left; dial and countdown on the right.

    When a phase ends the timer pauses, a notification names the next phase and the swoosh snap
    plays; the view holds on 00:00 while it shows, then moves to the next phase, stopped until
    Start.
    The notification goes straight to the freedesktop notification service over D-Bus on Linux
    (Qt's tray sends it as low urgency, which GNOME files away without a banner), through the
    system tray elsewhere, and as a toast in the window when there's neither.
    """

    def __init__(self, pomodoro_timer: PomodoroTimer, settings: PomodoroSettings) -> None:
        super().__init__()
        self._pomodoro_timer = pomodoro_timer
        self._settings = settings

        self._phase_picker = RotaryPicker(self._phase_labels_for_current_settings())
        self._phase_picker.selected_index_changed_by_user.connect(self._switch_to_picked_phase)
        self._phase_picker.setFocusPolicy(Qt.FocusPolicy.TabFocus)

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
        for control_button in (self._start_button, self._pause_button, self._reset_button):
            control_button.clicked.connect(self._refresh_display)
            control_button_row_layout.addWidget(control_button)

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
        self._session_rating_row = self._create_session_rating_row()
        picker_and_controls_layout.addWidget(self._session_rating_row)
        picker_and_controls_layout.addStretch()

        dial_and_countdown_layout = QVBoxLayout()
        dial_and_countdown_layout.addWidget(self._chronograph_dial, stretch=1)
        dial_and_countdown_layout.addWidget(self._countdown_label)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)
        layout.addWidget(picker_and_controls_column)
        layout.addLayout(dial_and_countdown_layout, stretch=1)

        self._is_phase_end_announcement_pending = False
        self._show_phase_end_notification = self._choose_phase_end_notification_method()
        if not PHASE_END_SOUND_PATH.is_file():
            raise FileNotFoundError(f"Phase-end sound missing: {PHASE_END_SOUND_PATH}")
        # Not QSoundEffect: on PulseAudio it silently drops clips under about a second.
        self._phase_end_sound_player = QMediaPlayer(self)
        self._phase_end_sound_player.setAudioOutput(QAudioOutput(self))
        self._phase_end_sound_player.setSource(QUrl.fromLocalFile(str(PHASE_END_SOUND_PATH)))

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
        control_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        control_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return control_button

    def _choose_phase_end_notification_method(self) -> Callable[[str], None]:
        if _is_freedesktop_notification_service_running():
            from jeepney.io.blocking import open_dbus_connection

            self._session_bus_connection = open_dbus_connection(bus="SESSION")
            return self._show_freedesktop_notification
        is_desktop_notification_supported = (
            QSystemTrayIcon.isSystemTrayAvailable() and QSystemTrayIcon.supportsMessages()
        )
        if not is_desktop_notification_supported:
            self._in_window_notification_label = QLabel()
            self._in_window_notification_label.setObjectName("in_window_notification_label")
            self._in_window_notification_label.hide()
            return self._show_in_window_notification
        self._phase_end_tray_icon = QSystemTrayIcon(QApplication.windowIcon(), self)
        self._phase_end_tray_icon.setToolTip("Tab")
        self._phase_end_tray_icon.show()
        return self._show_desktop_notification

    def _show_freedesktop_notification(self, message: str) -> None:
        from jeepney import DBusAddress, MessageType, new_method_call

        notifications_address = DBusAddress(
            "/org/freedesktop/Notifications",
            bus_name=FREEDESKTOP_NOTIFICATIONS_SERVICE,
            interface=FREEDESKTOP_NOTIFICATIONS_SERVICE,
        )
        notify_call = new_method_call(
            notifications_address,
            "Notify",
            "susssasa{sv}i",
            (
                "Tab",  # app name
                0,  # replaces no earlier notification
                str(NOTIFICATION_ICON_PATH),
                "Tab",
                message,
                [],  # no action buttons
                {
                    "urgency": ("y", NORMAL_NOTIFICATION_URGENCY),
                    "desktop-entry": ("s", "tab"),
                },
                PHASE_END_NOTIFICATION_MILLISECONDS,
            ),
        )
        reply = self._session_bus_connection.send_and_get_reply(
            notify_call, timeout=DBUS_REPLY_TIMEOUT_SECONDS
        )
        if reply.header.message_type is MessageType.error:
            raise RuntimeError(f"Desktop notification refused: {reply.body}")

    def _show_desktop_notification(self, message: str) -> None:
        self._phase_end_tray_icon.showMessage(
            "Tab", message, QSystemTrayIcon.MessageIcon.NoIcon, PHASE_END_NOTIFICATION_MILLISECONDS
        )

    def _show_in_window_notification(self, message: str) -> None:
        # Parented to the top-level window, not this view, so it shows whichever view is open.
        top_level_window = self.window()
        notification_label = self._in_window_notification_label
        notification_label.setParent(top_level_window)
        notification_label.setText(message)
        notification_label.adjustSize()
        notification_label.move(
            (top_level_window.width() - notification_label.width()) // 2,
            IN_WINDOW_NOTIFICATION_TOP_MARGIN_PIXELS,
        )
        notification_label.raise_()
        notification_label.show()
        QTimer.singleShot(PHASE_END_NOTIFICATION_MILLISECONDS, notification_label.hide)

    def _announce_phase_end_then_advance(self) -> None:
        self._is_phase_end_announcement_pending = True
        self._pomodoro_timer.pause()
        self._show_phase_end_notification(
            UPCOMING_PHASE_NOTIFICATION_MESSAGES[self._pomodoro_timer.upcoming_phase()]
        )
        self._phase_end_sound_player.play()
        QTimer.singleShot(PHASE_END_NOTIFICATION_MILLISECONDS, self._advance_after_announcement)

    def _advance_after_announcement(self) -> None:
        # Reset or a phase pick during the hold leaves nothing finished, so this is a no-op then.
        self._pomodoro_timer.advance_phase_if_finished()
        self._is_phase_end_announcement_pending = False
        self._refresh_display()

    def _create_session_rating_row(self) -> QWidget:
        """Shown during the break after a work session, until it's rated or the next one starts."""
        session_rating_row = QWidget()
        # Keep its space while hidden, so the picker and controls don't jump when it appears.
        session_rating_size_policy = session_rating_row.sizePolicy()
        session_rating_size_policy.setRetainSizeWhenHidden(True)
        session_rating_row.setSizePolicy(session_rating_size_policy)

        session_rating_prompt = QLabel("Rate that session")
        session_rating_prompt.setObjectName("session_rating_prompt")
        session_rating_prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rating_button_row_layout = QHBoxLayout()
        rating_button_row_layout.setSpacing(6)
        for rating in SESSION_RATINGS:
            rating_button = QPushButton(str(rating))
            rating_button.setObjectName("session_rating_button")
            rating_button.setAccessibleName(f"Rate session {rating}")
            rating_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            rating_button.setCursor(Qt.CursorShape.PointingHandCursor)
            rating_button.clicked.connect(
                lambda _checked=False, rating=rating: self._rate_last_work_session(rating)
            )
            rating_button_row_layout.addWidget(rating_button)

        session_rating_layout = QVBoxLayout(session_rating_row)
        session_rating_layout.setContentsMargins(
            PHASE_PICKER_BAND_INSET_PIXELS, 16, PHASE_PICKER_BAND_INSET_PIXELS, 0
        )
        session_rating_layout.setSpacing(8)
        session_rating_layout.addWidget(session_rating_prompt)
        session_rating_layout.addLayout(rating_button_row_layout)
        return session_rating_row

    def _rate_last_work_session(self, rating: int) -> None:
        self._pomodoro_timer.rate_last_work_session(rating)
        self._refresh_display()

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
        is_new_phase_end = (
            self._pomodoro_timer.is_current_phase_finished()
            and not self._is_phase_end_announcement_pending
        )
        if is_new_phase_end:
            self._announce_phase_end_then_advance()
        # Exactly one of Start/Pause is lit, read from the timer rather than the last click: it
        # also stops itself at a phase's end. Not a QButtonGroup: an exclusive group lets only the
        # lit button take Ctrl+Tab focus.
        self._start_button.setChecked(self._pomodoro_timer.is_running)
        self._pause_button.setChecked(not self._pomodoro_timer.is_running)
        self._session_rating_row.setVisible(self._pomodoro_timer.is_awaiting_session_rating)
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
        self._countdown_label.setText(_format_countdown(remaining_whole_seconds))


def _format_countdown(remaining_whole_seconds: int) -> str:
    """MM:SS under an hour, H:MM:SS from an hour up (2:00:00 rather than 120:00)."""
    hours, seconds_within_hour = divmod(remaining_whole_seconds, 3600)
    minutes, seconds = divmod(seconds_within_hour, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _is_freedesktop_notification_service_running() -> bool:
    """Linux desktops with a session bus where something (GNOME Shell, KDE, dunst) owns the
    notifications name."""
    if sys.platform != "linux" or "DBUS_SESSION_BUS_ADDRESS" not in os.environ:
        return False
    from jeepney.bus_messages import message_bus
    from jeepney.io.blocking import open_dbus_connection

    with open_dbus_connection(bus="SESSION") as session_bus_connection:
        name_has_owner_reply = session_bus_connection.send_and_get_reply(
            message_bus.NameHasOwner(FREEDESKTOP_NOTIFICATIONS_SERVICE),
            timeout=DBUS_REPLY_TIMEOUT_SECONDS,
        )
    return bool(name_has_owner_reply.body[0])
