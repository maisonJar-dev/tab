from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from tab.core.config import PomodoroSettings
from tab.core.progress import load_timer_progress, save_timer_progress
from tab.core.timer import PomodoroTimer
from tab.screens.main import MainScreen
from tab.screens.splash import SplashScreen

THEME_STYLESHEET_PATH = Path(__file__).parent / "styles" / "theme.qss"
APP_ICON_PATH = Path(__file__).parent / "assets" / "tab_icon.svg"
APP_DISPLAY_NAME = "Tab"
INITIAL_WINDOW_WIDTH_PIXELS = 1040
INITIAL_WINDOW_HEIGHT_PIXELS = 680
PROGRESS_AUTOSAVE_INTERVAL_MILLISECONDS = 5000


def load_theme_stylesheet() -> str:
    return THEME_STYLESHEET_PATH.read_text(encoding="utf-8")


class TabApplicationWindow(QMainWindow):
    """Top-level window. Owns the screen stack (splash, then main) and timer persistence.

    Progress is autosaved every few seconds so a crash loses at most that much; the timer is
    always restored paused.
    """

    def __init__(self, settings: PomodoroSettings) -> None:
        super().__init__()
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(INITIAL_WINDOW_WIDTH_PIXELS, INITIAL_WINDOW_HEIGHT_PIXELS)

        self._pomodoro_timer = PomodoroTimer(settings, load_timer_progress())
        self._splash_screen = SplashScreen(settings)
        self._main_screen = MainScreen(settings, self._pomodoro_timer)

        self._screen_stack = QStackedWidget()
        self._screen_stack.addWidget(self._splash_screen)
        self._screen_stack.addWidget(self._main_screen)
        self.setCentralWidget(self._screen_stack)

        self._splash_screen.continue_requested.connect(self._show_main_screen)

        self._progress_autosave_timer = QTimer(self)
        self._progress_autosave_timer.timeout.connect(self._save_progress)
        self._progress_autosave_timer.start(PROGRESS_AUTOSAVE_INTERVAL_MILLISECONDS)

    def closeEvent(self, close_event: QCloseEvent) -> None:
        self._save_progress()
        super().closeEvent(close_event)

    def _show_main_screen(self) -> None:
        self._screen_stack.setCurrentWidget(self._main_screen)

    def _save_progress(self) -> None:
        save_timer_progress(self._pomodoro_timer.snapshot())
