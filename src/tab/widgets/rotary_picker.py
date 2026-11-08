import math

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from tab.widgets.theme_colors import raise_if_theme_colors_missing, theme_color_property

SELECTION_BAND_INSET_PIXELS = 8
SELECTION_BAND_CORNER_RADIUS_PIXELS = 10  # theme.qss #timer_control_button matches this
ITEM_SPACING_PIXELS = 44
DEGREES_BETWEEN_ITEMS_ON_DRUM = 36
DISTANT_ITEM_MINIMUM_SCALE = 0.7
SELECTED_ITEM_PIXEL_SIZE = 22
SNAP_ANIMATION_MILLISECONDS = 220
WHEEL_DELTA_PER_NOTCH = 120
THEME_COLOR_PROPERTY_NAMES = ["selectedTextColor", "unselectedTextColor", "selectionBandColor"]


class RotaryPicker(QWidget):
    """Drum-style picker: items sit on a cylinder that you scroll or drag, snapping to one.

    `scroll_position` is a float index (1.0 = second item centred). Painting maps each item's
    distance from the centre to an angle on the drum, which sets its height, size and fade.
    """

    selected_index_changed_by_user = Signal(int)

    selectedTextColor = theme_color_property("_selected_text_color")
    unselectedTextColor = theme_color_property("_unselected_text_color")
    selectionBandColor = theme_color_property("_selection_band_color")

    def __init__(self, item_labels: list[str]) -> None:
        super().__init__()
        if not item_labels:
            raise ValueError("RotaryPicker needs at least one item label")
        self.setObjectName("rotary_picker")
        self.setMinimumSize(180, 260)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self._selected_text_color = QColor()
        self._unselected_text_color = QColor()
        self._selection_band_color = QColor()

        self._item_labels = item_labels
        self._selected_index = 0
        self._scroll_position = 0.0
        self._drag_start_mouse_y: float | None = None
        self._drag_start_scroll_position = 0.0

        self._snap_animation = QVariantAnimation(self)
        self._snap_animation.setDuration(SNAP_ANIMATION_MILLISECONDS)
        self._snap_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._snap_animation.valueChanged.connect(self._set_scroll_position)

    @property
    def selected_index(self) -> int:
        return self._selected_index

    @property
    def is_being_dragged(self) -> bool:
        return self._drag_start_mouse_y is not None

    def set_item_labels(self, item_labels: list[str]) -> None:
        if len(item_labels) != len(self._item_labels):
            raise ValueError(
                f"Expected {len(self._item_labels)} labels to keep the selection, "
                f"got {len(item_labels)}"
            )
        self._item_labels = item_labels
        self.update()

    def set_selected_index(self, index: int) -> None:
        """Programmatic selection: animates, but does not emit the user signal."""
        if index == self._selected_index or self.is_being_dragged:
            return
        self._select_and_snap_to(index)

    def wheelEvent(self, wheel_event: QWheelEvent) -> None:
        notches_scrolled = wheel_event.angleDelta().y() / WHEEL_DELTA_PER_NOTCH
        if notches_scrolled == 0:
            return
        step = -1 if notches_scrolled > 0 else 1
        self._select_by_user(self._selected_index + step)

    def mousePressEvent(self, mouse_event: QMouseEvent) -> None:
        self._snap_animation.stop()
        self._drag_start_mouse_y = mouse_event.position().y()
        self._drag_start_scroll_position = self._scroll_position
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, mouse_event: QMouseEvent) -> None:
        if self._drag_start_mouse_y is None:
            return
        dragged_pixels = mouse_event.position().y() - self._drag_start_mouse_y
        self._set_scroll_position(
            self._drag_start_scroll_position - dragged_pixels / ITEM_SPACING_PIXELS
        )

    def mouseReleaseEvent(self, mouse_event: QMouseEvent) -> None:
        if self._drag_start_mouse_y is None:
            return
        was_click_without_drag = abs(mouse_event.position().y() - self._drag_start_mouse_y) < 4
        self._drag_start_mouse_y = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if was_click_without_drag:
            clicked_offset_from_centre = (mouse_event.position().y() - self.height() / 2) / (
                ITEM_SPACING_PIXELS
            )
            self._select_by_user(round(self._scroll_position + clicked_offset_from_centre))
        else:
            self._select_by_user(round(self._scroll_position))

    def paintEvent(self, paint_event: QPaintEvent) -> None:
        raise_if_theme_colors_missing(self, THEME_COLOR_PROPERTY_NAMES)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        try:
            self._draw_selection_band(painter)
            for item_index, item_label in enumerate(self._item_labels):
                self._draw_item_on_drum(painter, item_index, item_label)
        finally:
            painter.end()

    def _select_by_user(self, requested_index: int) -> None:
        clamped_index = max(0, min(requested_index, len(self._item_labels) - 1))
        index_changed = clamped_index != self._selected_index
        self._select_and_snap_to(clamped_index)
        if index_changed:
            self.selected_index_changed_by_user.emit(clamped_index)

    def _select_and_snap_to(self, index: int) -> None:
        self._selected_index = index
        self._snap_animation.stop()
        self._snap_animation.setStartValue(self._scroll_position)
        self._snap_animation.setEndValue(float(index))
        self._snap_animation.start()

    def _set_scroll_position(self, scroll_position: float) -> None:
        self._scroll_position = scroll_position
        self.update()

    def _draw_selection_band(self, painter: QPainter) -> None:
        band_height = ITEM_SPACING_PIXELS
        band_rect = QRectF(
            SELECTION_BAND_INSET_PIXELS,
            self.height() / 2 - band_height / 2,
            self.width() - 2 * SELECTION_BAND_INSET_PIXELS,
            band_height,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._selection_band_color)
        painter.drawRoundedRect(
            band_rect, SELECTION_BAND_CORNER_RADIUS_PIXELS, SELECTION_BAND_CORNER_RADIUS_PIXELS
        )

    def _draw_item_on_drum(self, painter: QPainter, item_index: int, item_label: str) -> None:
        offset_in_items = item_index - self._scroll_position
        angle_on_drum_radians = math.radians(offset_in_items * DEGREES_BETWEEN_ITEMS_ON_DRUM)
        if abs(angle_on_drum_radians) >= math.pi / 2:
            return  # rotated round the back of the drum

        drum_radius_pixels = ITEM_SPACING_PIXELS / math.radians(DEGREES_BETWEEN_ITEMS_ON_DRUM)
        item_centre_y = self.height() / 2 + drum_radius_pixels * math.sin(angle_on_drum_radians)
        facing_camera = math.cos(angle_on_drum_radians)  # 1 at centre, 0 at the drum's edge

        closeness_to_centre = max(0.0, 1.0 - abs(offset_in_items))
        text_color = _blend_colors(
            self._unselected_text_color, self._selected_text_color, closeness_to_centre
        )
        text_color.setAlphaF(facing_camera**1.5)  # fades faster than it turns: reads as depth

        # Perspective: text further round the drum is smaller overall and, because the surface
        # is tilted away, squashed vertically by cos(angle) while keeping its width.
        distance_scale = (
            DISTANT_ITEM_MINIMUM_SCALE + (1 - DISTANT_ITEM_MINIMUM_SCALE) * facing_camera
        )
        font = QFont(painter.font())
        font.setPixelSize(max(1, round(SELECTED_ITEM_PIXEL_SIZE * distance_scale)))
        painter.save()
        painter.translate(self.width() / 2, item_centre_y)
        painter.scale(1.0, facing_camera)
        painter.setFont(font)
        painter.setPen(text_color)
        text_box = QRectF(
            -self.width() / 2, -ITEM_SPACING_PIXELS / 2, self.width(), ITEM_SPACING_PIXELS
        )
        painter.drawText(text_box, Qt.AlignmentFlag.AlignCenter, item_label)
        painter.restore()


def _blend_colors(from_color: QColor, to_color: QColor, blend_fraction: float) -> QColor:
    return QColor.fromRgbF(
        from_color.redF() + (to_color.redF() - from_color.redF()) * blend_fraction,
        from_color.greenF() + (to_color.greenF() - from_color.greenF()) * blend_fraction,
        from_color.blueF() + (to_color.blueF() - from_color.blueF()) * blend_fraction,
    )
