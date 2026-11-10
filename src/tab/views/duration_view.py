import math
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QHideEvent, QResizeEvent, QShowEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from tab.core.timer import PomodoroTimer, format_clock_time
from tab.widgets.duration_knot import DurationKnot
from tab.widgets.info_article import create_info_button
from tab.widgets.session_rating_row import SessionRatingRow
from tab.widgets.themed_icon_button import PaintIcon, ThemedIconButton
from tab.widgets.view_icons import (
    paint_finish_icon,
    paint_pause_icon,
    paint_reset_icon,
    paint_start_icon,
)

DISPLAY_REFRESH_INTERVAL_MILLISECONDS = 250
CONTROL_ICON_SIZE_PIXELS = 20
CONTROL_ROW_WIDTH_PIXELS = 240
RESET_PRESS_FLASH_MILLISECONDS = 180  # a click can be shorter than a frame; hold :pressed visibly
KNOT_INFO_ARTICLE_PATH = Path(__file__).parent.parent / "assets" / "trefoil_knot.md"


class DurationView(QWidget):
    """Open-ended focus session: a count-up clock under the animated knot, with Start, Pause
    and Reset in a row, Finish full-width beneath (the Timer's layout). Time counts as focus
    while it runs; Reset zeroes it without a session; Finish asks for the session's impact
    rating.
    The "i" beside the clock opens a short read on the trefoil knot. It sits on the clock's
    row, its icon's right edge in line with Finish's outer edge, so clock and controls read
    as one box; it floats over the layout so the clock stays centred.

    Starting it pauses the Pomodoro timer and vice versa (the timer enforces this), so the view
    reads the running state back from the timer on every refresh rather than from clicks.
    """

    def __init__(self, pomodoro_timer: PomodoroTimer) -> None:
        super().__init__()
        self._pomodoro_timer = pomodoro_timer

        self._duration_knot = DurationKnot()

        self._elapsed_label = QLabel()
        self._elapsed_label.setObjectName("duration_elapsed_label")
        self._elapsed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._start_button = self._create_control_button("Start", paint_start_icon, True)
        self._pause_button = self._create_control_button("Pause", paint_pause_icon, True)
        self._reset_button = self._create_control_button("Reset", paint_reset_icon, False)
        self._finish_button = self._create_control_button("Finish", paint_finish_icon, False)
        self._finish_button.setProperty("controlRole", "complete_session")  # green hover
        self._start_button.clicked.connect(self._pomodoro_timer.start_duration)
        self._pause_button.clicked.connect(self._pomodoro_timer.pause_duration)
        self._reset_button.clicked.connect(self._pomodoro_timer.reset_duration)
        self._reset_button.clicked.connect(self._flash_reset_button_as_pressed)
        self._finish_button.clicked.connect(self._pomodoro_timer.finish_duration)

        control_button_row_layout = QHBoxLayout()
        control_button_row_layout.setSpacing(8)
        for control_button in (self._start_button, self._pause_button, self._reset_button):
            control_button_row_layout.addWidget(control_button)
        self._control_buttons = control_buttons = QWidget()
        control_buttons.setFixedWidth(CONTROL_ROW_WIDTH_PIXELS)
        control_buttons_layout = QVBoxLayout(control_buttons)
        control_buttons_layout.setContentsMargins(0, 0, 0, 0)
        control_buttons_layout.setSpacing(8)
        control_buttons_layout.addLayout(control_button_row_layout)
        control_buttons_layout.addWidget(self._finish_button)  # full width beneath the row
        for control_button in (
            self._start_button,
            self._pause_button,
            self._reset_button,
            self._finish_button,
        ):
            control_button.clicked.connect(self._refresh_display)

        self._session_rating_row = SessionRatingRow(horizontal_inset_pixels=0)
        self._session_rating_row.setFixedWidth(CONTROL_ROW_WIDTH_PIXELS)
        self._session_rating_row.rating_chosen.connect(self._rate_last_session)
        self._session_rating_row.rating_skipped.connect(self._skip_session_rating)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)
        layout.addWidget(self._duration_knot, stretch=1)
        layout.addWidget(self._elapsed_label)
        layout.addWidget(control_buttons, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._session_rating_row, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._knot_info_button = create_info_button(
            "The trefoil knot", KNOT_INFO_ARTICLE_PATH, parent=self
        )

        # Only polls while shown: a pause or start from the Timer view is picked up on return.
        self._display_refresh_timer = QTimer(self)
        self._display_refresh_timer.setInterval(DISPLAY_REFRESH_INTERVAL_MILLISECONDS)
        self._display_refresh_timer.timeout.connect(self._refresh_display)
        self._refresh_display()

    def showEvent(self, show_event: QShowEvent) -> None:
        super().showEvent(show_event)
        self._place_knot_info_button_beside_clock()  # the layout has run by now
        self._refresh_display()
        self._display_refresh_timer.start()

    def hideEvent(self, hide_event: QHideEvent) -> None:
        super().hideEvent(hide_event)
        self._display_refresh_timer.stop()

    def resizeEvent(self, resize_event: QResizeEvent) -> None:
        super().resizeEvent(resize_event)
        self._place_knot_info_button_beside_clock()

    def _place_knot_info_button_beside_clock(self) -> None:
        """Clock's row, vertically centred on it; the icon (not its hover padding) ends where
        the control row ends."""
        knot_info_button = self._knot_info_button
        knot_info_button.adjustSize()
        icon_inset_pixels = (knot_info_button.width() - knot_info_button.iconSize().width()) // 2
        knot_info_button.move(
            self._control_buttons.geometry().right()
            + 1
            - knot_info_button.width()
            + icon_inset_pixels,
            self._elapsed_label.geometry().center().y() - knot_info_button.height() // 2,
        )
        knot_info_button.raise_()

    def toggle_running(self) -> None:
        """Start if paused, pause if running: what Space does while this view is open."""
        if self._pomodoro_timer.is_duration_running:
            self._pomodoro_timer.pause_duration()
        else:
            self._pomodoro_timer.start_duration()
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

    def _flash_reset_button_as_pressed(self) -> None:
        self._reset_button.setDown(True)
        QTimer.singleShot(RESET_PRESS_FLASH_MILLISECONDS, lambda: self._reset_button.setDown(False))

    def _skip_session_rating(self) -> None:
        self._pomodoro_timer.skip_session_rating()
        self._refresh_display()

    def _rate_last_session(self, rating: int) -> None:
        self._pomodoro_timer.rate_last_work_session(rating)
        self._refresh_display()

    def _refresh_display(self) -> None:
        is_duration_running = self._pomodoro_timer.is_duration_running
        elapsed_seconds = self._pomodoro_timer.duration_elapsed_seconds()
        self._start_button.setChecked(is_duration_running)
        self._pause_button.setChecked(not is_duration_running)
        self._finish_button.setEnabled(elapsed_seconds > 0)
        self._session_rating_row.setVisible(self._pomodoro_timer.is_awaiting_session_rating)
        self._duration_knot.set_is_timer_running(is_duration_running)
        self._elapsed_label.setText(format_clock_time(math.floor(elapsed_seconds)))
