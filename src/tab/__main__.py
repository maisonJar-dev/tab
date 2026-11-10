import hashlib
import sys

from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMainWindow

from tab.app import APP_DISPLAY_NAME, APP_ICON_PATH, TabApplicationWindow, load_theme_stylesheet
from tab.core.config import load_settings
from tab.core.progress import default_progress_file_path

RUNNING_INSTANCE_CONNECT_TIMEOUT_MILLISECONDS = 500


def main() -> None:
    application = QApplication(sys.argv)
    application.setApplicationName("tab")
    application.setApplicationDisplayName(APP_DISPLAY_NAME)
    application.setDesktopFileName("tab")  # Wayland desktops match the taskbar icon by this id
    application.setWindowIcon(_load_app_icon())
    application.setStyleSheet(load_theme_stylesheet())

    # One app per progress file: each autosaves its whole state, so two would overwrite
    # each other's sessions. A second launch brings the first to the front and exits.
    single_instance_server_name = _single_instance_server_name()
    if _ask_running_instance_to_come_forward(single_instance_server_name):
        return

    window = TabApplicationWindow(load_settings())
    single_instance_server = _listen_for_later_launches(single_instance_server_name, window)
    window.show()
    exit_code = application.exec()
    single_instance_server.close()
    sys.exit(exit_code)


def _load_app_icon() -> QIcon:
    app_icon = QIcon(str(APP_ICON_PATH))
    if app_icon.isNull():
        raise FileNotFoundError(f"App icon missing or unreadable: {APP_ICON_PATH}")
    return app_icon


def _single_instance_server_name() -> str:
    """Named after the progress file the instance owns, so other state dirs don't collide."""
    progress_path_digest = hashlib.sha256(
        str(default_progress_file_path().resolve()).encode()
    ).hexdigest()
    return f"tab-{progress_path_digest[:16]}"


def _ask_running_instance_to_come_forward(server_name: str) -> bool:
    """Connecting is the whole message: the running instance shows itself on any connection."""
    running_instance_socket = QLocalSocket()
    running_instance_socket.connectToServer(server_name)
    is_instance_running = running_instance_socket.waitForConnected(
        RUNNING_INSTANCE_CONNECT_TIMEOUT_MILLISECONDS
    )
    running_instance_socket.abort()
    return is_instance_running


def _listen_for_later_launches(server_name: str, window: QMainWindow) -> QLocalServer:
    # Nothing answered, so any socket file under this name was left by a crash; clear it.
    QLocalServer.removeServer(server_name)
    single_instance_server = QLocalServer()
    if not single_instance_server.listen(server_name):
        raise RuntimeError(
            f"Couldn't start the single-instance server {server_name!r}: "
            f"{single_instance_server.errorString()}"
        )
    single_instance_server.newConnection.connect(
        lambda: _bring_window_forward(single_instance_server, window)
    )
    return single_instance_server


def _bring_window_forward(single_instance_server: QLocalServer, window: QMainWindow) -> None:
    later_launch_connection = single_instance_server.nextPendingConnection()
    later_launch_connection.close()
    later_launch_connection.deleteLater()
    if window.isMinimized():
        window.showNormal()  # only when minimised, so a maximised window stays maximised
    window.raise_()
    window.activateWindow()


if __name__ == "__main__":
    main()
