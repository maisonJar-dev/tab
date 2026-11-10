"""Line icons for views and controls, drawn on a 24x24 grid with the painter's current pen."""

import math

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QPolygonF

from tab.core.knot_animation import FACE_ON_ORIENTATION, knot_dots

KNOT_ICON_HALF_SIZE_ON_GRID = 9.5  # the strand's centre line; the pen adds the rest
# A strand passing under another stops this close to it (in knot units), as in a knot diagram.
KNOT_ICON_UNDER_CROSSING_GAP = 0.3


def paint_workspace_icon(painter: QPainter) -> None:
    for tile_left, tile_top in ((4, 4), (13, 4), (4, 13), (13, 13)):
        painter.drawRoundedRect(QRectF(tile_left, tile_top, 7, 7), 1.5, 1.5)


def paint_timer_icon(painter: QPainter) -> None:
    painter.drawEllipse(QPointF(12, 13.5), 7.5, 7.5)
    painter.drawLine(QPointF(10, 3), QPointF(14, 3))
    painter.drawLine(QPointF(12, 13.5), QPointF(12, 9))
    painter.drawLine(QPointF(12, 13.5), QPointF(15, 15))


def paint_duration_icon(painter: QPainter) -> None:
    """The Duration view's trefoil, face-on, drawn as a knot diagram: at each crossing the
    lower strand breaks either side of the upper one."""
    knot_points = knot_dots(
        flow_laps=0, wobble_radians=0, orientation=FACE_ON_ORIENTATION, solidity=1
    )
    point_count = len(knot_points)
    neighbours_to_skip = point_count // 20  # a point's own stretch of strand isn't a crossing
    left, right = min(point.x for point in knot_points), max(point.x for point in knot_points)
    top, bottom = min(point.y for point in knot_points), max(point.y for point in knot_points)
    knot_to_grid = KNOT_ICON_HALF_SIZE_ON_GRID / (max(right - left, bottom - top) / 2)

    def is_under_a_crossing(point_index: int) -> bool:
        point = knot_points[point_index]
        for other_index, other_point in enumerate(knot_points):
            index_gap = abs(other_index - point_index)
            if min(index_gap, point_count - index_gap) <= neighbours_to_skip:
                continue
            is_close = (
                math.hypot(other_point.x - point.x, other_point.y - point.y)
                < KNOT_ICON_UNDER_CROSSING_GAP
            )
            if is_close and other_point.depth > point.depth:
                return True
        return False

    knot_outline = QPainterPath()
    is_pen_down = False
    for step in range(point_count + 1):
        point_index = step % point_count
        if is_under_a_crossing(point_index):
            is_pen_down = False
            continue
        grid_point = QPointF(
            12 + (knot_points[point_index].x - (left + right) / 2) * knot_to_grid,
            12 + (knot_points[point_index].y - (top + bottom) / 2) * knot_to_grid,
        )
        if is_pen_down:
            knot_outline.lineTo(grid_point)
        else:
            knot_outline.moveTo(grid_point)
            is_pen_down = True
    painter.drawPath(knot_outline)


def paint_settings_icon(painter: QPainter) -> None:
    for slider_y, knob_x in ((6, 15), (12, 8), (18, 13)):
        painter.drawLine(QPointF(4, slider_y), QPointF(20, slider_y))
        painter.drawEllipse(QPointF(knob_x, slider_y), 2, 2)


def paint_shortcuts_icon(painter: QPainter) -> None:
    """The ⌘ (command key) symbol: a # of two horizontal and two vertical lines, each pair of
    line ends at a corner joined by a three-quarter loop."""
    half_square = 3.2  # half the side of the square in the middle
    loop_radius = 3.0
    line_reach = half_square + loop_radius  # from the centre to where a line meets its loop
    command_symbol = QPainterPath()
    for offset in (-half_square, half_square):
        command_symbol.moveTo(QPointF(12 + offset, 12 - line_reach))
        command_symbol.lineTo(QPointF(12 + offset, 12 + line_reach))
        command_symbol.moveTo(QPointF(12 - line_reach, 12 + offset))
        command_symbol.lineTo(QPointF(12 + line_reach, 12 + offset))
    # Each loop leaves out the quarter facing the middle; angles are Qt's (counterclockwise).
    for horizontal_side, vertical_side, start_degrees in (
        (-1, -1, 0),  # top left
        (1, -1, 270),  # top right
        (1, 1, 180),  # bottom right
        (-1, 1, 90),  # bottom left
    ):
        loop_bounds = QRectF(
            12 + horizontal_side * line_reach - loop_radius,
            12 + vertical_side * line_reach - loop_radius,
            2 * loop_radius,
            2 * loop_radius,
        )
        command_symbol.arcMoveTo(loop_bounds, start_degrees)
        command_symbol.arcTo(loop_bounds, start_degrees, 270)
    painter.drawPath(command_symbol)


def paint_profile_icon(painter: QPainter) -> None:
    painter.drawEllipse(QPointF(12, 8.5), 3.8, 3.8)
    painter.drawArc(QRectF(5, 15, 14, 12), 0, 180 * 16)


def paint_info_icon(painter: QPainter) -> None:
    painter.drawEllipse(QPointF(12, 12), 9, 9)
    painter.drawLine(QPointF(12, 11), QPointF(12, 16.5))
    painter.drawPoint(QPointF(12, 7.6))


def paint_close_icon(painter: QPainter) -> None:
    painter.drawLine(QPointF(6, 6), QPointF(18, 18))
    painter.drawLine(QPointF(18, 6), QPointF(6, 18))


def paint_start_icon(painter: QPainter) -> None:
    painter.drawPolygon(QPolygonF([QPointF(8, 5), QPointF(19, 12), QPointF(8, 19)]))


def paint_pause_icon(painter: QPainter) -> None:
    painter.drawLine(QPointF(9, 5), QPointF(9, 19))
    painter.drawLine(QPointF(15, 5), QPointF(15, 19))


def paint_finish_icon(painter: QPainter) -> None:
    painter.drawLine(QPointF(5, 12.5), QPointF(10, 17.5))
    painter.drawLine(QPointF(10, 17.5), QPointF(19, 7))


def paint_reset_icon(painter: QPainter) -> None:
    painter.drawArc(QRectF(5, 5, 14, 14), 90 * 16, 270 * 16)
    painter.drawLine(QPointF(19, 10), QPointF(16.5, 12.5))
    painter.drawLine(QPointF(19, 10), QPointF(21.5, 12.5))
