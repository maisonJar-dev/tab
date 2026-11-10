import time
from pathlib import Path

from PySide6.QtCore import QLineF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QHideEvent,
    QKeyEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QResizeEvent,
    QShowEvent,
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QWidget

from tab.core.config import PomodoroSettings
from tab.core.cube_to_word_animation import (
    TOTAL_DURATION_SECONDS,
    CubeToWordAnimation,
    animation_scale_for_viewport,
)
from tab.core.stopwatch import Stopwatch
from tab.widgets.theme_colors import raise_if_theme_colors_missing, theme_color_property

CONTINUE_KEYS = (Qt.Key.Key_Tab, Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter)
FRAME_INTERVAL_MILLISECONDS = 16  # ~60 fps
MINIMUM_STROKE_WIDTH_PIXELS = 1.2
AUTO_CONTINUE_DELAY_AFTER_INTRO_MILLISECONDS = 3000
THEME_COLOR_PROPERTY_NAMES = ["lineColor"]
# One recording timed to the animation's constants: regenerate it if they change.
INTRO_SOUND_PATH = Path(__file__).parent.parent / "assets" / "splash_intro.wav"


class SplashScreen(QWidget):
    """Plays the cube-to-"tab" intro and its soundtrack, then emits `continue_requested` 3 s
    after it ends.

    Tab, Space or Enter emits it straight away, even mid-intro. The soundtrack is skipped when
    the "Intro sound" setting is off (read each time the splash shows). The geometry lives in
    core.cube_to_word_animation; this widget only supplies the clock, paints and handles keys.
    """

    continue_requested = Signal()

    lineColor = theme_color_property("_line_color")

    def __init__(self, settings: PomodoroSettings) -> None:
        super().__init__()
        self._settings = settings
        self.setObjectName("splash_screen")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._line_color = QColor()

        self._intro_stopwatch = Stopwatch(time.monotonic)
        self._cube_to_word_animation = self._create_animation_for_current_size()

        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(FRAME_INTERVAL_MILLISECONDS)
        self._frame_timer.timeout.connect(self._advance_frame)

        self._auto_continue_timer = QTimer(self)
        self._auto_continue_timer.setSingleShot(True)
        self._auto_continue_timer.setInterval(AUTO_CONTINUE_DELAY_AFTER_INTRO_MILLISECONDS)
        self._auto_continue_timer.timeout.connect(self.continue_requested.emit)

        if not INTRO_SOUND_PATH.is_file():
            raise FileNotFoundError(f"Splash intro sound missing: {INTRO_SOUND_PATH}")
        self._intro_sound_player = QMediaPlayer(self)
        self._intro_sound_player.setAudioOutput(QAudioOutput(self))
        self._intro_sound_player.setSource(QUrl.fromLocalFile(str(INTRO_SOUND_PATH)))

    @property
    def is_intro_finished(self) -> bool:
        return self._intro_stopwatch.elapsed_seconds() >= TOTAL_DURATION_SECONDS

    def showEvent(self, show_event: QShowEvent) -> None:
        super().showEvent(show_event)
        self.setFocus()
        self._intro_stopwatch.reset()
        self._intro_stopwatch.start()
        self._frame_timer.start()
        if self._settings.is_intro_sound_enabled:
            self._intro_sound_player.setPosition(0)
            self._intro_sound_player.play()

    def hideEvent(self, hide_event: QHideEvent) -> None:
        super().hideEvent(hide_event)
        self._frame_timer.stop()
        self._auto_continue_timer.stop()
        self._intro_stopwatch.pause()
        self._intro_sound_player.stop()  # skipped with Tab/Space/Enter: cut the sound too

    def resizeEvent(self, resize_event: QResizeEvent) -> None:
        super().resizeEvent(resize_event)
        self._cube_to_word_animation = self._create_animation_for_current_size()

    def focusNextPrevChild(self, is_moving_forward: bool) -> bool:
        """Returning False stops Qt using Tab for focus moves, so keyPressEvent receives it."""
        return False

    def keyPressEvent(self, key_event: QKeyEvent) -> None:
        if key_event.key() in CONTINUE_KEYS:
            self.continue_requested.emit()
            return
        super().keyPressEvent(key_event)

    def paintEvent(self, paint_event: QPaintEvent) -> None:
        raise_if_theme_colors_missing(self, THEME_COLOR_PROPERTY_NAMES)
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.translate(self.width() / 2, self.height() / 2)
            stroke_pen = QPen(
                self._line_color,
                max(MINIMUM_STROKE_WIDTH_PIXELS, self._cube_to_word_animation.stroke_width_pixels),
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
            painter.setPen(stroke_pen)
            elapsed_seconds = min(self._intro_stopwatch.elapsed_seconds(), TOTAL_DURATION_SECONDS)
            painter.drawLines(
                [
                    QLineF(start_x, start_y, end_x, end_y)
                    for (start_x, start_y), (end_x, end_y) in (
                        self._cube_to_word_animation.line_segments_at(elapsed_seconds)
                    )
                ]
            )
        finally:
            painter.end()

    def _create_animation_for_current_size(self) -> CubeToWordAnimation:
        return CubeToWordAnimation(
            scale_pixels=animation_scale_for_viewport(self.width(), self.height()),
            viewport_height_pixels=self.height(),
        )

    def _advance_frame(self) -> None:
        self.update()
        if self.is_intro_finished:
            self._frame_timer.stop()
            self._auto_continue_timer.start()
