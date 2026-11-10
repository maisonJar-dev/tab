import time

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QHideEvent, QMouseEvent, QPainter, QPaintEvent, QShowEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from tab.core.knot_animation import KnotAnimationState
from tab.widgets.theme_colors import raise_if_theme_colors_missing, theme_color_property

FRAME_INTERVAL_MILLISECONDS = 33  # ~30 fps: smooth enough for slow drift, light on the CPU
LONGEST_FRAME_STEP_SECONDS = 0.1  # a stalled frame (busy event loop) doesn't make dots jump
KNOT_FILL_FRACTION_OF_WIDGET = 0.92
THEME_COLOR_PROPERTY_NAMES = ["nearColor", "farColor"]


class DurationKnot(QWidget):
    """The Duration view's trefoil (geometry in core/knot_animation.py).

    Running: dots of varying size flow along the knot as it tumbles. Paused: they slow, stop
    and swell into one solid tube. Dots are painted far to near, each shaded exactly by its
    depth between `farColor` and `nearColor` (no banding), so crossings read as over and under.

    While paused it's a fidget toy: drag to turn it any way (open hand, closed while dragging),
    flick to set it coasting. While running, drags are ignored.

    Redraws at ~30 fps only while something moves on its own (running, solidifying, coasting);
    a drag redraws per pointer move. Once solid and still (or hidden) the frame timer stops, so
    a paused knot costs nothing.
    """

    nearColor = theme_color_property("_near_color")
    farColor = theme_color_property("_far_color")

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("duration_knot")
        self.setMinimumSize(240, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._near_color = QColor()
        self._far_color = QColor()
        self._animation_state = KnotAnimationState()
        self._is_timer_running = False
        self._last_frame_seconds = time.monotonic()
        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(FRAME_INTERVAL_MILLISECONDS)
        self._frame_timer.timeout.connect(self._advance_frame)
        self._last_drag_position: QPointF | None = None  # None while not dragging
        self._last_drag_step_seconds = 0.0
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_is_timer_running(self, is_timer_running: bool) -> None:
        if is_timer_running == self._is_timer_running:
            return
        self._is_timer_running = is_timer_running
        if is_timer_running:
            self._last_drag_position = None  # the state cancels the drag on its next advance
        self.setCursor(
            Qt.CursorShape.ArrowCursor if is_timer_running else Qt.CursorShape.OpenHandCursor
        )
        self._start_frames_if_animating()

    def mousePressEvent(self, mouse_event: QMouseEvent) -> None:
        if self._is_timer_running or mouse_event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(mouse_event)
            return
        self._last_drag_position = mouse_event.position()
        self._last_drag_step_seconds = time.monotonic()
        self._animation_state.grab()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, mouse_event: QMouseEvent) -> None:
        if self._last_drag_position is None:
            super().mouseMoveEvent(mouse_event)
            return
        drag_step_seconds = time.monotonic()
        pointer_movement = mouse_event.position() - self._last_drag_position
        half_size_pixels = self._knot_half_size_pixels()
        self._animation_state.turn_by_drag(
            pointer_movement.x() / half_size_pixels,
            pointer_movement.y() / half_size_pixels,
            drag_step_seconds - self._last_drag_step_seconds,
        )
        self._last_drag_position = mouse_event.position()
        self._last_drag_step_seconds = drag_step_seconds
        self.update()

    def mouseReleaseEvent(self, mouse_event: QMouseEvent) -> None:
        if self._last_drag_position is None or mouse_event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(mouse_event)
            return
        self._last_drag_position = None
        self._animation_state.release_drag(time.monotonic() - self._last_drag_step_seconds)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._start_frames_if_animating()  # a flick coasts

    def showEvent(self, show_event: QShowEvent) -> None:
        super().showEvent(show_event)
        self._start_frames_if_animating()

    def hideEvent(self, hide_event: QHideEvent) -> None:
        super().hideEvent(hide_event)
        self._frame_timer.stop()

    def _start_frames_if_animating(self) -> None:
        is_animating = self._is_timer_running or not self._animation_state.is_settled
        if is_animating and self.isVisible() and not self._frame_timer.isActive():
            self._last_frame_seconds = time.monotonic()
            self._frame_timer.start()

    def _advance_frame(self) -> None:
        frame_seconds = time.monotonic()
        elapsed_seconds = min(frame_seconds - self._last_frame_seconds, LONGEST_FRAME_STEP_SECONDS)
        self._last_frame_seconds = frame_seconds
        self._animation_state.advance(elapsed_seconds, self._is_timer_running)
        self.update()
        if not self._is_timer_running and self._animation_state.is_settled:
            self._frame_timer.stop()

    def _knot_half_size_pixels(self) -> float:
        return min(self.width(), self.height()) / 2 * KNOT_FILL_FRACTION_OF_WIDGET

    def paintEvent(self, paint_event: QPaintEvent) -> None:
        raise_if_theme_colors_missing(self, THEME_COLOR_PROPERTY_NAMES)
        half_size_pixels = self._knot_half_size_pixels()
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.translate(self.width() / 2, self.height() / 2)
            painter.setPen(Qt.PenStyle.NoPen)
            for dot in sorted(self._animation_state.dots(), key=lambda dot: dot.depth):
                painter.setBrush(
                    _mix_colors(self._far_color, self._near_color, (dot.depth + 1) / 2)
                )
                dot_radius_pixels = dot.radius * half_size_pixels
                painter.drawEllipse(
                    QPointF(dot.x * half_size_pixels, dot.y * half_size_pixels),
                    dot_radius_pixels,
                    dot_radius_pixels,
                )
        finally:
            painter.end()


def _mix_colors(start_color: QColor, end_color: QColor, blend: float) -> QColor:
    return QColor.fromRgbF(
        start_color.redF() + (end_color.redF() - start_color.redF()) * blend,
        start_color.greenF() + (end_color.greenF() - start_color.greenF()) * blend,
        start_color.blueF() + (end_color.blueF() - start_color.blueF()) * blend,
    )
