import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from tab.app import APP_DISPLAY_NAME, APP_ICON_PATH, TabApplicationWindow, load_theme_stylesheet
from tab.core.config import load_settings


def main() -> None:
    application = QApplication(sys.argv)
    application.setApplicationName("tab")
    application.setApplicationDisplayName(APP_DISPLAY_NAME)
    application.setDesktopFileName("tab")  # Wayland desktops match the taskbar icon by this id
    application.setWindowIcon(_load_app_icon())
    application.setStyleSheet(load_theme_stylesheet())

    window = TabApplicationWindow(load_settings())
    window.show()
    sys.exit(application.exec())


def _load_app_icon() -> QIcon:
    app_icon = QIcon(str(APP_ICON_PATH))
    if app_icon.isNull():
        raise FileNotFoundError(f"App icon missing or unreadable: {APP_ICON_PATH}")
    return app_icon


if __name__ == "__main__":
    main()
