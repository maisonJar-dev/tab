import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from tab.core.timer import WORK_SESSIONS_BEFORE_LONG_BREAK, lap_fractions_from_current_lap
from tab.widgets.theme_colors import raise_if_theme_colors_missing, theme_color_property

MECHANICAL_BEATS_PER_SECOND = 8
CURRENT_LAP_ARC_RADIUS = 95.0
UPCOMING_LAP_RING_FIRST_RADIUS = 101.0  # just outside the face's edge (98)
UPCOMING_LAP_RING_SPACING = 2.2
MAXIMUM_UPCOMING_LAP_RINGS = 3  # settings allow up to 3:59, i.e. four laps
LAP_ARC_PEN_WIDTH = 1.6
# Upcoming-lap rings are quiet hairlines in the minor-marking grey (tan stays on the lap you're
# in), and recede: each one out is fainter and thinner than the one inside it.
FIRST_UPCOMING_LAP_RING_OPACITY = 0.45
UPCOMING_LAP_RING_OPACITY_KEPT_PER_RING = 0.6
FIRST_UPCOMING_LAP_RING_PEN_WIDTH = 0.9
UPCOMING_LAP_RING_PEN_WIDTH_LOST_PER_RING = 0.2
# Painting space reaches the outermost upcoming-lap ring plus half its pen.
DIAL_UNIT_RADIUS = 106.5
SUBDIAL_DISTANCE_FROM_CENTRE = 45.0
SUBDIAL_RADIUS = 20.0
FOCUS_TOTALISER_HOURS_PER_TURN = 12
THEME_COLOR_PROPERTY_NAMES = [
    "faceColor",
    "subdialColor",
    "markingColor",
    "minorMarkingColor",
    "accentColor",
]


class ChronographDial(QWidget):
    """3-6-9 chronograph drawn with QPainter.

    - Centre hand: minutes elapsed in the phase; an accent arc marks where the phase ends.
      Phases over an hour lap the dial: the inner arc is the lap the hand is on, and each lap
      still to come is a faint grey ring outside the face, innermost next, each fainter and
      thinner than the one inside it so later laps recede. A ring drops as its lap starts.
    - 3 o'clock: seconds, stepping at a mechanical 8 beats per second.
    - 6 o'clock: work sessions completed in the current long-break cycle.
    - 9 o'clock: focus-time totaliser, one turn per 12 hours.

    Colours come from theme.qss via Qt properties; painting fails fast if any are unset.
    """

    faceColor = theme_color_property("_face_color")
    subdialColor = theme_color_property("_subdial_color")
    markingColor = theme_color_property("_marking_color")
    minorMarkingColor = theme_color_property("_minor_marking_color")
    accentColor = theme_color_property("_accent_color")

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("chronograph_dial")
        self.setMinimumSize(320, 320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._face_color = QColor()
        self._subdial_color = QColor()
        self._marking_color = QColor()
        self._minor_marking_color = QColor()
        self._accent_color = QColor()

        self._elapsed_seconds_in_phase = 0.0
        self._phase_duration_seconds = 60.0
        self._completed_work_sessions_in_cycle = 0
        self._focus_totaliser_seconds = 0.0

    def show_timer_state(
        self,
        *,
        elapsed_seconds_in_phase: float,
        phase_duration_seconds: float,
        completed_work_sessions_in_cycle: int,
        focus_totaliser_seconds: float,
    ) -> None:
        self._elapsed_seconds_in_phase = elapsed_seconds_in_phase
        self._phase_duration_seconds = phase_duration_seconds
        self._completed_work_sessions_in_cycle = completed_work_sessions_in_cycle
        self._focus_totaliser_seconds = focus_totaliser_seconds
        self.update()

    def paintEvent(self, paint_event: QPaintEvent) -> None:
        raise_if_theme_colors_missing(self, THEME_COLOR_PROPERTY_NAMES)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fixed coordinate system: origin at the centre, face radius ~100 units.
        dial_radius_pixels = min(self.width(), self.height()) / 2 - 2
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(dial_radius_pixels / DIAL_UNIT_RADIUS, dial_radius_pixels / DIAL_UNIT_RADIUS)

        # An exception while a QPainter is active segfaults Qt; always end it so the
        # traceback surfaces instead.
        try:
            self._draw_face_and_minute_track(painter)
            self._draw_phase_lap_arcs(painter)
            self._draw_text(
                painter, QPointF(0, -28), "tab", pixel_size=10, color=self._marking_color
            )
            self._draw_all_subdials(painter)
            self._draw_centre_minutes_hand(painter)
        finally:
            painter.end()

    def _draw_face_and_minute_track(self, painter: QPainter) -> None:
        painter.setPen(QPen(self._minor_marking_color, 1.5))
        painter.setBrush(self._face_color)
        painter.drawEllipse(QPointF(0, 0), 98, 98)

        for minute_index in range(60):
            is_five_minute_mark = minute_index % 5 == 0
            painter.save()
            painter.rotate(minute_index * 6)
            if is_five_minute_mark:
                painter.setPen(QPen(self._marking_color, 2))
                painter.drawLine(QPointF(0, -92), QPointF(0, -82))
            else:
                painter.setPen(QPen(self._minor_marking_color, 0.8))
                painter.drawLine(QPointF(0, -92), QPointF(0, -87))
            painter.restore()

        for numeral in range(5, 61, 5):
            numeral_position = _point_on_circle(radius=75, fraction_of_turn=numeral / 60)
            self._draw_text(
                painter, numeral_position, str(numeral), pixel_size=6, color=self._marking_color
            )

    def _draw_phase_lap_arcs(self, painter: QPainter) -> None:
        current_lap_fraction, *upcoming_lap_fractions = lap_fractions_from_current_lap(
            self._phase_duration_seconds, self._elapsed_seconds_in_phase
        )
        if len(upcoming_lap_fractions) > MAXIMUM_UPCOMING_LAP_RINGS:
            raise ValueError(
                f"Phase needs {len(upcoming_lap_fractions)} upcoming-lap rings; the dial has room "
                f"for {MAXIMUM_UPCOMING_LAP_RINGS}"
            )
        painter.setPen(_round_capped_pen(self._accent_color, LAP_ARC_PEN_WIDTH))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _draw_arc_from_twelve(painter, CURRENT_LAP_ARC_RADIUS, current_lap_fraction)
        for ring_index, upcoming_lap_fraction in enumerate(upcoming_lap_fractions):
            ring_radius = UPCOMING_LAP_RING_FIRST_RADIUS + ring_index * UPCOMING_LAP_RING_SPACING
            receding_color = QColor(self._minor_marking_color)
            receding_color.setAlphaF(
                FIRST_UPCOMING_LAP_RING_OPACITY
                * UPCOMING_LAP_RING_OPACITY_KEPT_PER_RING**ring_index
            )
            receding_pen_width = (
                FIRST_UPCOMING_LAP_RING_PEN_WIDTH
                - UPCOMING_LAP_RING_PEN_WIDTH_LOST_PER_RING * ring_index
            )
            painter.setPen(_round_capped_pen(receding_color, receding_pen_width))
            _draw_arc_from_twelve(painter, ring_radius, upcoming_lap_fraction)

    def _draw_all_subdials(self, painter: QPainter) -> None:
        beats_elapsed = int(self._elapsed_seconds_in_phase * MECHANICAL_BEATS_PER_SECOND)
        seconds_position = (beats_elapsed / MECHANICAL_BEATS_PER_SECOND) % 60
        self._draw_subdial(
            painter,
            centre=QPointF(SUBDIAL_DISTANCE_FROM_CENTRE, 0),
            tick_count=12,
            hand_fraction_of_turn=seconds_position / 60,
            hand_color=self._accent_color,
            caption="SEC",
        )
        self._draw_subdial(
            painter,
            centre=QPointF(0, SUBDIAL_DISTANCE_FROM_CENTRE),
            tick_count=WORK_SESSIONS_BEFORE_LONG_BREAK + 1,
            hand_fraction_of_turn=self._completed_work_sessions_in_cycle
            / (WORK_SESSIONS_BEFORE_LONG_BREAK + 1),
            hand_color=self._marking_color,
            tick_labels=[str(count) for count in range(WORK_SESSIONS_BEFORE_LONG_BREAK + 1)],
            highlighted_tick_index=WORK_SESSIONS_BEFORE_LONG_BREAK,
        )
        focus_totaliser_hours = self._focus_totaliser_seconds / 3600
        self._draw_subdial(
            painter,
            centre=QPointF(-SUBDIAL_DISTANCE_FROM_CENTRE, 0),
            tick_count=FOCUS_TOTALISER_HOURS_PER_TURN,
            hand_fraction_of_turn=focus_totaliser_hours / FOCUS_TOTALISER_HOURS_PER_TURN,
            hand_color=self._marking_color,
            caption="HRS",
        )

    def _draw_subdial(
        self,
        painter: QPainter,
        *,
        centre: QPointF,
        tick_count: int,
        hand_fraction_of_turn: float,
        hand_color: QColor,
        caption: str | None = None,
        tick_labels: list[str] | None = None,
        highlighted_tick_index: int | None = None,
    ) -> None:
        painter.save()
        painter.translate(centre)

        painter.setPen(QPen(self._minor_marking_color, 0.8))
        painter.setBrush(self._subdial_color)
        painter.drawEllipse(QPointF(0, 0), SUBDIAL_RADIUS, SUBDIAL_RADIUS)

        for tick_index in range(tick_count):
            is_highlighted = tick_index == highlighted_tick_index
            tick_color = self._accent_color if is_highlighted else self._marking_color
            fraction_of_turn = tick_index / tick_count
            painter.setPen(QPen(tick_color, 0.8))
            painter.drawLine(
                _point_on_circle(SUBDIAL_RADIUS, fraction_of_turn),
                _point_on_circle(SUBDIAL_RADIUS - 3, fraction_of_turn),
            )
            if tick_labels:
                label_position = _point_on_circle(SUBDIAL_RADIUS - 7, fraction_of_turn)
                self._draw_text(
                    painter, label_position, tick_labels[tick_index], pixel_size=5, color=tick_color
                )

        if caption:
            self._draw_text(
                painter, QPointF(0, 9), caption, pixel_size=4, color=self._minor_marking_color
            )

        painter.rotate(hand_fraction_of_turn * 360)
        painter.setPen(_round_capped_pen(hand_color, 1.4))
        hand_length = SUBDIAL_RADIUS - (11 if tick_labels else 4)
        painter.drawLine(QPointF(0, 3), QPointF(0, -hand_length))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(hand_color)
        painter.drawEllipse(QPointF(0, 0), 1.6, 1.6)
        painter.restore()

    def _draw_centre_minutes_hand(self, painter: QPainter) -> None:
        elapsed_minutes = self._elapsed_seconds_in_phase / 60

        painter.save()
        painter.rotate(elapsed_minutes * 6)
        painter.setPen(_round_capped_pen(self._marking_color, 2.2))
        painter.drawLine(QPointF(0, 14), QPointF(0, -84))
        painter.restore()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._marking_color)
        painter.drawEllipse(QPointF(0, 0), 3.5, 3.5)
        painter.setBrush(self._accent_color)
        painter.drawEllipse(QPointF(0, 0), 1.4, 1.4)

    def _draw_text(
        self, painter: QPainter, centre: QPointF, text: str, *, pixel_size: int, color: QColor
    ) -> None:
        font = QFont(painter.font())
        font.setPixelSize(pixel_size)
        painter.setFont(font)
        painter.setPen(color)
        text_box = QRectF(centre.x() - 15, centre.y() - pixel_size, 30, pixel_size * 2)
        painter.drawText(text_box, Qt.AlignmentFlag.AlignCenter, text)


def _draw_arc_from_twelve(painter: QPainter, radius: float, fraction_of_turn: float) -> None:
    arc_box = QRectF(-radius, -radius, radius * 2, radius * 2)
    # Qt arcs: 1/16th degree units, 0 = 3 o'clock, positive = counter-clockwise.
    twelve_o_clock_start_angle = 90 * 16
    clockwise_span_angle = -round(fraction_of_turn * 360 * 16)
    painter.drawArc(arc_box, twelve_o_clock_start_angle, clockwise_span_angle)


def _round_capped_pen(color: QColor, width: float) -> QPen:
    return QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)


def _point_on_circle(radius: float, fraction_of_turn: float) -> QPointF:
    """Clockwise from 12 o'clock, in Qt's y-down coordinates."""
    angle_radians = fraction_of_turn * math.tau
    return QPointF(radius * math.sin(angle_radians), -radius * math.cos(angle_radians))
