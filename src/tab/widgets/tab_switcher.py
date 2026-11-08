from typing import NamedTuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QVBoxLayout, QWidget

from tab.widgets.themed_icon_button import PaintIcon, ThemedIconButton

TILE_ICON_SIZE_PIXELS = 36
WHEEL_DELTA_PER_STEP = 120  # one mouse-wheel notch; trackpads send many smaller deltas
CHOOSE_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter)
# "Up" means forward: ↑ and → move right, ↓ and ← move left (scrolling follows ↑/↓).
MOVE_HIGHLIGHT_RIGHT_KEYS = (Qt.Key.Key_Right, Qt.Key.Key_Up)
MOVE_HIGHLIGHT_LEFT_KEYS = (Qt.Key.Key_Left, Qt.Key.Key_Down)


class SwitcherEntry(NamedTuple):
    title: str
    paint_icon: PaintIcon


class TabSwitcher(QWidget):
    """Transparent overlay with a centred, horizontal row of tabs floating over the view.

    ↑/→ or scrolling up moves the highlight right; ↓/← or scrolling down moves it left (wrapping).
    Enter, or a left click anywhere except on another tile, chooses the highlighted tab, so you
    can scroll then click without aiming. Clicking a tile chooses that tile. Esc or a right
    click closes without choosing. Tab (handled by the parent) enters the highlighted tab if
    the highlight was moved, otherwise closes. The parent decides what opens it.
    """

    tab_chosen = Signal(int)

    def __init__(self, entries: list[SwitcherEntry], parent: QWidget) -> None:
        super().__init__(parent)
        if not entries:
            raise ValueError("TabSwitcher needs at least one entry")
        self.setObjectName("tab_switcher")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._accumulated_wheel_delta = 0
        self._highlighted_index_when_opened = 0

        self._tile_group = QButtonGroup(self)
        self._tile_group.setExclusive(True)
        self._tile_group.idClicked.connect(self._choose)

        self._panel = QFrame()
        self._panel.setObjectName("tab_switcher_panel")
        tile_row_layout = QHBoxLayout(self._panel)
        tile_row_layout.setContentsMargins(16, 16, 16, 16)
        tile_row_layout.setSpacing(8)
        for entry_index, entry in enumerate(entries):
            tile = ThemedIconButton(entry.title, entry.paint_icon, TILE_ICON_SIZE_PIXELS)
            tile.setObjectName("tab_switcher_tile")
            self._tile_group.addButton(tile, entry_index)
            tile_row_layout.addWidget(tile)

        centring_layout = QVBoxLayout(self)
        centring_layout.addStretch()
        centring_layout.addWidget(self._panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        centring_layout.addStretch()
        self.hide()

    @property
    def highlighted_index(self) -> int:
        return self._tile_group.checkedId()

    def open_with_highlight_on(self, highlighted_index: int) -> None:
        self._tile_group.button(highlighted_index).setChecked(True)
        self._highlighted_index_when_opened = highlighted_index
        self._accumulated_wheel_delta = 0
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.setFocus()

    def choose_if_highlight_moved_else_close(self) -> None:
        """Tab while open: enter the highlighted tab if the user moved to it, else just close."""
        if self.highlighted_index != self._highlighted_index_when_opened:
            self._choose(self.highlighted_index)
        else:
            self.close_without_choosing()

    def close_without_choosing(self) -> None:
        self.hide()
        self.parentWidget().setFocus()

    def keyPressEvent(self, key_event: QKeyEvent) -> None:
        pressed_key = key_event.key()
        if pressed_key in MOVE_HIGHLIGHT_RIGHT_KEYS:
            self._move_highlight(1)
        elif pressed_key in MOVE_HIGHLIGHT_LEFT_KEYS:
            self._move_highlight(-1)
        elif pressed_key in CHOOSE_KEYS:
            self._choose(self.highlighted_index)
        elif pressed_key == Qt.Key.Key_Escape:
            self.close_without_choosing()
        else:
            super().keyPressEvent(key_event)

    def wheelEvent(self, wheel_event: QWheelEvent) -> None:
        wheel_delta = wheel_event.angleDelta().y() or wheel_event.angleDelta().x()
        scroll_direction_reversed = wheel_delta * self._accumulated_wheel_delta < 0
        if scroll_direction_reversed:
            self._accumulated_wheel_delta = 0
        self._accumulated_wheel_delta += wheel_delta
        while abs(self._accumulated_wheel_delta) >= WHEEL_DELTA_PER_STEP:
            scrolled_up = self._accumulated_wheel_delta > 0
            self._move_highlight(1 if scrolled_up else -1)
            self._accumulated_wheel_delta -= (
                WHEEL_DELTA_PER_STEP if scrolled_up else -WHEEL_DELTA_PER_STEP
            )

    def mousePressEvent(self, mouse_event: QMouseEvent) -> None:
        """Clicks that land on the overlay or the panel's padding (tiles handle their own)."""
        if mouse_event.button() == Qt.MouseButton.LeftButton:
            self._choose(self.highlighted_index)
        else:
            self.close_without_choosing()

    def _move_highlight(self, step: int) -> None:
        tile_count = len(self._tile_group.buttons())
        self._tile_group.button((self.highlighted_index + step) % tile_count).setChecked(True)

    def _choose(self, chosen_index: int) -> None:
        self.close_without_choosing()
        self.tab_chosen.emit(chosen_index)
