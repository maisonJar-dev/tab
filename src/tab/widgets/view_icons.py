"""Line icons for views and controls, drawn on a 24x24 grid with the painter's current pen."""

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter, QPolygonF


def paint_workspace_icon(painter: QPainter) -> None:
    for tile_left, tile_top in ((4, 4), (13, 4), (4, 13), (13, 13)):
        painter.drawRoundedRect(QRectF(tile_left, tile_top, 7, 7), 1.5, 1.5)


def paint_timer_icon(painter: QPainter) -> None:
    painter.drawEllipse(QPointF(12, 13.5), 7.5, 7.5)
    painter.drawLine(QPointF(10, 3), QPointF(14, 3))
    painter.drawLine(QPointF(12, 13.5), QPointF(12, 9))
    painter.drawLine(QPointF(12, 13.5), QPointF(15, 15))


def paint_settings_icon(painter: QPainter) -> None:
    for slider_y, knob_x in ((6, 15), (12, 8), (18, 13)):
        painter.drawLine(QPointF(4, slider_y), QPointF(20, slider_y))
        painter.drawEllipse(QPointF(knob_x, slider_y), 2, 2)


def paint_profile_icon(painter: QPainter) -> None:
    painter.drawEllipse(QPointF(12, 8.5), 3.8, 3.8)
    painter.drawArc(QRectF(5, 15, 14, 12), 0, 180 * 16)


def paint_start_icon(painter: QPainter) -> None:
    painter.drawPolygon(QPolygonF([QPointF(8, 5), QPointF(19, 12), QPointF(8, 19)]))


def paint_pause_icon(painter: QPainter) -> None:
    painter.drawLine(QPointF(9, 5), QPointF(9, 19))
    painter.drawLine(QPointF(15, 5), QPointF(15, 19))


def paint_reset_icon(painter: QPainter) -> None:
    painter.drawArc(QRectF(5, 5, 14, 14), 90 * 16, 270 * 16)
    painter.drawLine(QPointF(19, 10), QPointF(16.5, 12.5))
    painter.drawLine(QPointF(19, 10), QPointF(21.5, 12.5))
