from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QResizeEvent, QShortcut, QShowEvent
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from tab.core.config import PomodoroSettings
from tab.core.timer import PomodoroTimer
from tab.views.profile import ProfileView
from tab.views.settings import SettingsView
from tab.views.timer_view import TimerView
from tab.views.workspace import WorkspaceView
from tab.widgets.background import WallBackground
from tab.widgets.tab_switcher import SwitcherEntry, TabSwitcher
from tab.widgets.themed_icon_button import ThemedIconButton
from tab.widgets.view_icons import (
    paint_profile_icon,
    paint_settings_icon,
    paint_timer_icon,
    paint_workspace_icon,
)

PROFILE_BUTTON_ICON_SIZE_PIXELS = 24
PROFILE_BUTTON_MARGIN_PIXELS = 16


class MainScreen(QWidget):
    """Views fill the window over the graffiti wall. Tab opens the switcher; Profile sits
    in the bottom-left corner."""

    def __init__(self, settings: PomodoroSettings, pomodoro_timer: PomodoroTimer) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        switcher_entries_with_views: list[tuple[SwitcherEntry, QWidget]] = [
            (SwitcherEntry("Workspace", paint_workspace_icon), WorkspaceView()),
            (SwitcherEntry("Timer", paint_timer_icon), TimerView(pomodoro_timer, settings)),
            (SwitcherEntry("Settings", paint_settings_icon), SettingsView(settings)),
        ]

        self._content_area = QStackedWidget()
        self._content_area.setObjectName("content_area")
        for _, view in switcher_entries_with_views:
            self._content_area.addWidget(view)
        self._profile_view = ProfileView(pomodoro_timer)
        self._content_area.addWidget(self._profile_view)

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
        self._profile_button.setParent(self)
        self._profile_button.show()
        self._profile_button.clicked.connect(self._show_profile)

        self._tab_switcher = TabSwitcher(
            [entry for entry, _ in switcher_entries_with_views], parent=self
        )
        self._tab_switcher.tab_chosen.connect(self._show_view)

        # A shortcut sees Tab before Qt's focus-chain handling would swallow it.
        toggle_switcher_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Tab), self)
        toggle_switcher_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        # Holding Tab makes the OS repeat it ~30x a second, which flickered the switcher open and
        # shut; a hold counts as one press, so it toggles once and stays put while you scroll.
        toggle_switcher_shortcut.setAutoRepeat(False)
        toggle_switcher_shortcut.activated.connect(self._toggle_tab_switcher)

    def showEvent(self, show_event: QShowEvent) -> None:
        super().showEvent(show_event)
        self.setFocus()

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
        current_view_is_in_switcher = self._content_area.currentWidget() is not self._profile_view
        highlighted_index = self._content_area.currentIndex() if current_view_is_in_switcher else 0
        self._tab_switcher.open_with_highlight_on(highlighted_index)

    def _show_view(self, view_index: int) -> None:
        self._content_area.setCurrentIndex(view_index)
        self._profile_button.setChecked(False)

    def _show_profile(self) -> None:
        self._content_area.setCurrentWidget(self._profile_view)
        self._profile_button.setChecked(True)
