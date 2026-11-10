from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QKeySequence, QResizeEvent, QShortcut, QShowEvent
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from tab.core.config import PomodoroSettings
from tab.core.timer import PomodoroTimer
from tab.views.duration_view import DurationView
from tab.views.profile import ProfileView
from tab.views.settings import SettingsView
from tab.views.shortcuts import ShortcutsView
from tab.views.timer_view import TimerView
from tab.views.workspace import WorkspaceView
from tab.widgets.background import WallBackground
from tab.widgets.tab_switcher import SwitcherEntry, TabSwitcher
from tab.widgets.themed_icon_button import ThemedIconButton
from tab.widgets.view_icons import (
    paint_duration_icon,
    paint_profile_icon,
    paint_settings_icon,
    paint_timer_icon,
    paint_workspace_icon,
)

PROFILE_BUTTON_ICON_SIZE_PIXELS = 24
PROFILE_BUTTON_MARGIN_PIXELS = 16


class MainScreen(QWidget):
    """Views fill the window over the graffiti wall. Tab opens the switcher; Profile sits
    in the bottom-left corner.

    Ctrl+Tab / Ctrl+Shift+Tab move keyboard focus through the tabbable controls (focus policy
    TabFocus) of the open view; while the switcher is open they move its highlight instead.
    Plain Tab stays the switcher's key.

    Ctrl+S opens the Shortcuts page (also reached from Settings) and Ctrl+P opens Profile; the
    same key pressed on that page returns to the page you came from. Neither is in the switcher.

    Space starts or pauses the open Timer or Duration view. It's handled in keyPressEvent, not
    as a shortcut, so it only gets a Space nothing else used: a control focused with Ctrl+Tab
    still presses on Space, and the open switcher (which passes Space up unused) is skipped.
    """

    def __init__(self, settings: PomodoroSettings, pomodoro_timer: PomodoroTimer) -> None:
        super().__init__()
        # Click, not Tab: the screen holds focus for its shortcuts but isn't a Ctrl+Tab stop.
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        settings_view = SettingsView(settings, pomodoro_timer)
        switcher_entries_with_views: list[tuple[SwitcherEntry, QWidget]] = [
            (SwitcherEntry("Workspace", paint_workspace_icon), WorkspaceView()),
            (SwitcherEntry("Timer", paint_timer_icon), TimerView(pomodoro_timer, settings)),
            (SwitcherEntry("Duration", paint_duration_icon), DurationView(pomodoro_timer)),
            (SwitcherEntry("Settings", paint_settings_icon), settings_view),
        ]

        self._content_area = QStackedWidget()
        self._content_area.setObjectName("content_area")
        for _, view in switcher_entries_with_views:
            self._content_area.addWidget(view)
        self._switcher_view_count = len(switcher_entries_with_views)
        self._profile_view = ProfileView(pomodoro_timer)
        self._content_area.addWidget(self._profile_view)
        self._shortcuts_view = ShortcutsView()
        self._content_area.addWidget(self._shortcuts_view)
        # Profile and Shortcuts each remember the page they were opened from, so their key
        # (Ctrl+P / Ctrl+S) takes you back there.
        self._page_opened_from_by_page: dict[QWidget, QWidget] = {}
        settings_view.shortcuts_page_requested.connect(
            lambda: self._toggle_page(self._shortcuts_view)
        )

        wall_background = WallBackground()
        wall_layout = QVBoxLayout(wall_background)
        wall_layout.setContentsMargins(0, 0, 0, 0)
        wall_layout.addWidget(self._content_area)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(wall_background)

        self._profile_button = ThemedIconButton(
            "Profile", paint_profile_icon, PROFILE_BUTTON_ICON_SIZE_PIXELS
        )
        self._profile_button.setObjectName("profile_corner_button")
        self._profile_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._profile_button.setParent(self)
        self._profile_button.show()
        self._profile_button.clicked.connect(self._show_profile)

        self._tab_switcher = TabSwitcher(
            [entry for entry, _ in switcher_entries_with_views], parent=self
        )
        self._tab_switcher.tab_chosen.connect(self._show_view)

        # Shortcuts see Tab before Qt's focus-chain handling would swallow it.
        # Holding Tab makes the OS repeat it ~30x a second, which flickered the switcher open and
        # shut; a hold counts as one press, so it toggles once and stays put while you scroll.
        self._add_shortcut(
            "Tab",
            self._toggle_tab_switcher,
            is_auto_repeat=False,
            closes_open_tab_switcher=False,
        )
        for key_sequence, step in (
            ("Ctrl+Tab", 1),
            ("Ctrl+Shift+Tab", -1),
            ("Ctrl+Shift+Backtab", -1),  # X11/Wayland spelling of Ctrl+Shift+Tab
        ):
            self._add_shortcut(
                key_sequence,
                lambda step=step: self._navigate_by_keyboard(step),
                is_auto_repeat=True,  # hold to keep stepping through controls
                closes_open_tab_switcher=False,  # moves the open switcher's highlight instead
            )
        self._add_shortcut("Ctrl+S", lambda: self._toggle_page(self._shortcuts_view))
        self._add_shortcut("Ctrl+P", lambda: self._toggle_page(self._profile_view))

    def _add_shortcut(
        self,
        key_sequence: str,
        on_activated: Callable[[], None],
        is_auto_repeat: bool = False,
        closes_open_tab_switcher: bool = True,
    ) -> None:
        """Register a shortcut that works anywhere on this screen. By default an open switcher
        closes first, since the shortcut is the user's choice of what to do next; only keys that
        drive the switcher itself opt out. Held keys fire once unless `is_auto_repeat`."""

        def close_tab_switcher_then_act() -> None:
            if closes_open_tab_switcher and self._tab_switcher.isVisible():
                self._tab_switcher.close_without_choosing()
            on_activated()

        shortcut = QShortcut(QKeySequence(key_sequence), self)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.setAutoRepeat(is_auto_repeat)
        shortcut.activated.connect(close_tab_switcher_then_act)

    def showEvent(self, show_event: QShowEvent) -> None:
        super().showEvent(show_event)
        self.setFocus()

    def keyPressEvent(self, key_event: QKeyEvent) -> None:
        open_view = self._content_area.currentWidget()
        is_space_for_the_open_view = (
            key_event.key() == Qt.Key.Key_Space
            and not key_event.isAutoRepeat()  # holding Space toggles once, not on and off
            and not self._tab_switcher.isVisible()
            and isinstance(open_view, (TimerView, DurationView))
        )
        if is_space_for_the_open_view:
            open_view.toggle_running()
            return
        super().keyPressEvent(key_event)

    def resizeEvent(self, resize_event: QResizeEvent) -> None:
        super().resizeEvent(resize_event)
        self._profile_button.adjustSize()
        self._profile_button.move(
            PROFILE_BUTTON_MARGIN_PIXELS,
            self.height() - self._profile_button.height() - PROFILE_BUTTON_MARGIN_PIXELS,
        )
        self._profile_button.raise_()
        if self._tab_switcher.isVisible():
            self._tab_switcher.setGeometry(self.rect())
            self._tab_switcher.raise_()

    def _toggle_tab_switcher(self) -> None:
        if self._tab_switcher.isVisible():
            self._tab_switcher.choose_if_highlight_moved_else_close()
            return
        current_view_is_in_switcher = self._content_area.currentIndex() < self._switcher_view_count
        highlighted_index = self._content_area.currentIndex() if current_view_is_in_switcher else 0
        self._tab_switcher.open_with_highlight_on(highlighted_index)

    def _navigate_by_keyboard(self, step: int) -> None:
        """Ctrl+Tab (+1) / Ctrl+Shift+Tab (-1): the open switcher, else the open view's controls."""
        if self._tab_switcher.isVisible():
            self._tab_switcher.move_highlight(step)
        elif step > 0:
            # Hidden widgets are skipped by Qt's focus chain, so this only visits the open view.
            self.focusNextChild()
        else:
            self.focusPreviousChild()

    def _show_view(self, view_index: int) -> None:
        self._content_area.setCurrentIndex(view_index)
        self._profile_button.setChecked(False)
        self.setFocus()  # don't let focus drift from the hidden view into a random control

    def _toggle_page(self, page: QWidget) -> None:
        """Open `page`, remembering where from; if it's already open, go back there."""
        open_page = self._content_area.currentWidget()
        if open_page is page:
            self._open_page(self._page_opened_from_by_page[page])
        else:
            self._page_opened_from_by_page[page] = open_page
            self._open_page(page)

    def _open_page(self, page: QWidget) -> None:
        self._content_area.setCurrentWidget(page)
        self._profile_button.setChecked(page is self._profile_view)
        self.setFocus()

    def _show_profile(self) -> None:
        if self._content_area.currentWidget() is not self._profile_view:
            self._page_opened_from_by_page[self._profile_view] = self._content_area.currentWidget()
        self._open_page(self._profile_view)
