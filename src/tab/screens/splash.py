import math
import time

from PySide6.QtCore import QEasingCurve, QLineF, Qt, QTimer, QVariantAnimation, Signal
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
from PySide6.QtWidgets import QLabel, QWidget

from tab.core.cube_to_word_animation import (
    TOTAL_DURATION_SECONDS,
    CubeToWordAnimation,
    animation_scale_for_viewport,
)
from tab.core.stopwatch import Stopwatch
from tab.widgets.theme_colors import raise_if_theme_colors_missing, theme_color_property

CONTINUE_KEYS = (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter)
FRAME_INTERVAL_MILLISECONDS = 16  # ~60 fps
MINIMUM_STROKE_WIDTH_PIXELS = 1.2
HINT_GAP_BELOW_WORD_PIXELS = 36
HINT_BOUNCE_HEIGHT_PIXELS = 6
HINT_BOUNCE_CYCLE_MILLISECONDS = 1400
THEME_COLOR_PROPERTY_NAMES = ["lineColor"]


class SplashScreen(QWidget):
    """Plays the cube-to-"tab" intro, then shows a bouncing hint.

    The geometry lives in core.cube_to_word_animation; this widget only supplies the clock,
    paints the segments and handles keys. Space/Enter during the intro skips to the end;
    pressed again it emits `continue_requested`.
    """

    continue_requested = Signal()

    lineColor = theme_color_property("_line_color")

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("splash_screen")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._line_color = QColor()

        self._intro_stopwatch = Stopwatch(time.monotonic)
        self._cube_to_word_animation = self._create_animation_for_current_size()

        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(FRAME_INTERVAL_MILLISECONDS)
        self._frame_timer.timeout.connect(self._advance_frame)

        self._continue_hint_label = QLabel("Press space to continue", self)
        self._continue_hint_label.setObjectName("splash_continue_hint")
        self._continue_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._continue_hint_label.hide()
        self._set_hint_bounce_lift(0.0)

        # Progress runs 0 -> 1 linearly; lift = sin(pi * progress) so the hint hangs at the
        # top and rebounds quickly off the bottom, like a soft bounce.
        self._hint_bounce_animation = QVariantAnimation(self)
        self._hint_bounce_animation.setStartValue(0.0)
        self._hint_bounce_animation.setEndValue(1.0)
        self._hint_bounce_animation.setDuration(HINT_BOUNCE_CYCLE_MILLISECONDS)
        self._hint_bounce_animation.setEasingCurve(QEasingCurve.Type.Linear)
        self._hint_bounce_animation.setLoopCount(-1)
        self._hint_bounce_animation.valueChanged.connect(
            lambda progress: self._set_hint_bounce_lift(math.sin(math.pi * progress))
        )

    @property
    def is_intro_finished(self) -> bool:
        return self._intro_stopwatch.elapsed_seconds() >= TOTAL_DURATION_SECONDS

    def showEvent(self, show_event: QShowEvent) -> None:
        super().showEvent(show_event)
        self.setFocus()
        self._intro_stopwatch.reset()
        self._intro_stopwatch.start()
        self._continue_hint_label.hide()
        self._frame_timer.start()

    def hideEvent(self, hide_event: QHideEvent) -> None:
        super().hideEvent(hide_event)
        self._frame_timer.stop()
        self._hint_bounce_animation.stop()
        self._intro_stopwatch.pause()

    def resizeEvent(self, resize_event: QResizeEvent) -> None:
        super().resizeEvent(resize_event)
        self._cube_to_word_animation = self._create_animation_for_current_size()
        self._position_continue_hint()

    def keyPressEvent(self, key_event: QKeyEvent) -> None:
        if key_event.key() not in CONTINUE_KEYS:
            super().keyPressEvent(key_event)
            return
        if self.is_intro_finished:
            self.continue_requested.emit()
            return
        self._intro_stopwatch.reset(TOTAL_DURATION_SECONDS)
        self._intro_stopwatch.start()
        self._advance_frame()

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
            self._show_bouncing_hint()

    def _show_bouncing_hint(self) -> None:
        if self._continue_hint_label.isVisible():
            return
        self._position_continue_hint()
        self._continue_hint_label.show()
        self._hint_bounce_animation.start()

    def _position_continue_hint(self) -> None:
        self._continue_hint_label.adjustSize()
        hint_top_y = (
            self.height() / 2
            + self._cube_to_word_animation.word_bottom_y_pixels
            + HINT_GAP_BELOW_WORD_PIXELS
        )
        self._continue_hint_label.move(
            round((self.width() - self._continue_hint_label.width()) / 2), round(hint_top_y)
        )

    def _set_hint_bounce_lift(self, lift_fraction: float) -> None:
        """Shift the text inside the label without resizing it, so its position never changes."""
        lift_pixels = round(lift_fraction * HINT_BOUNCE_HEIGHT_PIXELS)
        self._continue_hint_label.setContentsMargins(
            0, HINT_BOUNCE_HEIGHT_PIXELS - lift_pixels, 0, lift_pixels
        )
