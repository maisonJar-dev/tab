from collections.abc import Callable

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QColor, QEnterEvent, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QToolButton

from tab.widgets.theme_colors import raise_if_theme_colors_missing, theme_color_property

ICON_GRID_SIZE = 24  # view icons are drawn on a 24x24 grid, then scaled
ICON_STROKE_WIDTH_ON_GRID = 2.2
ICON_RENDER_SCALE = 2  # draw at 2x so icons stay crisp on HiDPI screens
THEME_COLOR_PROPERTY_NAMES = [
    "iconColor",
    "hoverIconColor",
    "selectedIconColor",
    "disabledIconColor",
]

PaintIcon = Callable[[QPainter], None]


class ThemedIconButton(QToolButton):
    """Button whose line icon takes its colours from theme.qss.

    The icon is drawn in `iconColor`, `hoverIconColor` under the mouse (unchecked only),
    `selectedIconColor` while checked, and `disabledIconColor` while disabled (so it fades with
    the button's outline; Qt's own generated disabled icon barely changes under a stylesheet).

    The colours are baked into pixmaps, which a stylesheet :hover can't reach (qproperty values
    apply once, at polish), so the button keeps a resting and a hovered icon and swaps them on
    enter and leave.
    """

    iconColor = theme_color_property("_icon_color")
    hoverIconColor = theme_color_property("_hover_icon_color")
    selectedIconColor = theme_color_property("_selected_icon_color")
    disabledIconColor = theme_color_property("_disabled_icon_color")

    def __init__(
        self,
        title: str,
        paint_icon: PaintIcon,
        icon_size_pixels: int,
        is_checkable: bool = True,
    ) -> None:
        super().__init__()
        self._icon_color = QColor()
        self._hover_icon_color = QColor()
        self._selected_icon_color = QColor()
        self._resting_icon = QIcon()
        self._hovered_icon = QIcon()
        self._disabled_icon_color = QColor()
        self._paint_icon = paint_icon
        self._icon_size_pixels = icon_size_pixels

        self.setText(title)
        self.setAccessibleName(title)
        self.setToolTip(title)
        self.setCheckable(is_checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setIconSize(QSize(icon_size_pixels, icon_size_pixels))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

    def event(self, event: QEvent) -> bool:
        handled = super().event(event)
        if event.type() == QEvent.Type.Polish:
            # theme.qss qproperty colours are applied during polish, so the icon is built after.
            self._rebuild_icon()
        return handled

    def enterEvent(self, enter_event: QEnterEvent) -> None:
        super().enterEvent(enter_event)
        self.setIcon(self._hovered_icon)

    def leaveEvent(self, leave_event: QEvent) -> None:
        super().leaveEvent(leave_event)
        self.setIcon(self._resting_icon)

    def _rebuild_icon(self) -> None:
        raise_if_theme_colors_missing(self, THEME_COLOR_PROPERTY_NAMES)
        self._resting_icon = self._build_icon(unchecked_icon_color=self._icon_color)
        self._hovered_icon = self._build_icon(unchecked_icon_color=self._hover_icon_color)
        self.setIcon(self._hovered_icon if self.underMouse() else self._resting_icon)

    def _build_icon(self, unchecked_icon_color: QColor) -> QIcon:
        themed_icon = QIcon()
        themed_icon.addPixmap(self._render_icon(unchecked_icon_color), state=QIcon.State.Off)
        themed_icon.addPixmap(self._render_icon(self._selected_icon_color), state=QIcon.State.On)
        disabled_icon_pixmap = self._render_icon(self._disabled_icon_color)
        for icon_state in (QIcon.State.Off, QIcon.State.On):
            themed_icon.addPixmap(disabled_icon_pixmap, QIcon.Mode.Disabled, icon_state)
        return themed_icon

    def _render_icon(self, icon_color: QColor) -> QPixmap:
        rendered_size_pixels = self._icon_size_pixels * ICON_RENDER_SCALE
        icon_pixmap = QPixmap(rendered_size_pixels, rendered_size_pixels)
        icon_pixmap.setDevicePixelRatio(ICON_RENDER_SCALE)
        icon_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(icon_pixmap)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            grid_to_pixels = self._icon_size_pixels / ICON_GRID_SIZE
            painter.scale(grid_to_pixels, grid_to_pixels)
            painter.setPen(
                QPen(
                    icon_color,
                    ICON_STROKE_WIDTH_ON_GRID,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                )
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            self._paint_icon(painter)
        finally:
            painter.end()
        return icon_pixmap
