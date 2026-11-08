from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFormLayout, QLabel, QPushButton, QWidget

from tab.core.timer import PomodoroTimer

PROFILE_REFRESH_INTERVAL_MILLISECONDS = 1000


class ProfileView(QWidget):
    """Lifetime stats, plus the reset for the dial's focus-hours totaliser."""

    def __init__(self, pomodoro_timer: PomodoroTimer) -> None:
        super().__init__()
        self._pomodoro_timer = pomodoro_timer

        self._completed_work_sessions_label = QLabel()
        self._completed_work_sessions_label.setObjectName("profile_stat_value")
        self._focus_totaliser_label = QLabel()
        self._focus_totaliser_label.setObjectName("profile_stat_value")

        reset_focus_totaliser_button = QPushButton("Reset focus hours")
        reset_focus_totaliser_button.clicked.connect(self._pomodoro_timer.reset_focus_totaliser)
        reset_focus_totaliser_button.clicked.connect(self._refresh_stats)

        form_layout = QFormLayout(self)
        form_layout.setContentsMargins(32, 32, 32, 32)
        form_layout.setVerticalSpacing(14)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        form_layout.addRow("Completed work sessions", self._completed_work_sessions_label)
        form_layout.addRow("Focus hours on dial", self._focus_totaliser_label)
        form_layout.addRow("", reset_focus_totaliser_button)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_stats)
        self._refresh_timer.start(PROFILE_REFRESH_INTERVAL_MILLISECONDS)
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        self._completed_work_sessions_label.setText(
            str(self._pomodoro_timer.completed_work_sessions)
        )
        focus_total_minutes = int(self._pomodoro_timer.focus_totaliser_seconds() // 60)
        focus_hours, focus_minutes = divmod(focus_total_minutes, 60)
        self._focus_totaliser_label.setText(f"{focus_hours}h {focus_minutes:02d}m")
