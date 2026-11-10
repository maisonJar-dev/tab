from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tab.core.timer import SESSION_RATINGS, PomodoroTimer
from tab.widgets.callout_card import (
    create_callout_card,
    create_callout_card_row,
    create_callout_card_title,
)

PROFILE_REFRESH_INTERVAL_MILLISECONDS = 1000
ALL_TIME_RESET_CONFIRMATION_PHRASE = "hard work is the goal"
CONFIRMATION_DIALOG_TEXT_WIDTH_PIXELS = 352


class ProfileView(QWidget):
    """Stacked callout cards (styled like Settings): today's focus time and sessions; all-time
    focus, sessions and Impact Score (average session rating), with a reset behind a typed
    confirmation; then the dial's focus hours with its reset."""

    def __init__(self, pomodoro_timer: PomodoroTimer) -> None:
        super().__init__()
        self._pomodoro_timer = pomodoro_timer

        self._focus_today_label = _create_stat_value_label()
        self._completed_work_sessions_today_label = _create_stat_value_label()
        self._completed_work_sessions_label = _create_stat_value_label()
        self._focus_all_time_label = _create_stat_value_label()
        self._all_time_stats_since_label = QLabel()
        self._all_time_stats_since_label.setObjectName("callout_card_hint")
        self._average_session_rating_label = _create_stat_value_label()
        self._focus_totaliser_label = _create_stat_value_label()

        reset_focus_totaliser_button = QPushButton("Reset focus hours")
        reset_focus_totaliser_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        reset_focus_totaliser_button.clicked.connect(self._pomodoro_timer.reset_focus_totaliser)
        reset_focus_totaliser_button.clicked.connect(self._refresh_stats)

        reset_all_time_stats_button = QPushButton("Reset all-time stats")
        reset_all_time_stats_button.setObjectName("destructive_button")
        reset_all_time_stats_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        reset_all_time_stats_button.clicked.connect(self._confirm_then_reset_all_time_stats)

        today_card_layout = QVBoxLayout()
        today_card_layout.setSpacing(12)
        today_card_layout.addWidget(create_callout_card_title("Today"))
        today_card_layout.addLayout(
            create_callout_card_row(QLabel("Focus time"), self._focus_today_label)
        )
        today_card_layout.addLayout(
            create_callout_card_row(
                QLabel("Work sessions"), self._completed_work_sessions_today_label
            )
        )

        sessions_card_layout = QVBoxLayout()
        sessions_card_layout.setSpacing(12)
        sessions_card_layout.addWidget(create_callout_card_title("All time"))
        focus_all_time_with_since_layout = QVBoxLayout()
        focus_all_time_with_since_layout.setSpacing(2)  # the hint hugs its row
        focus_all_time_with_since_layout.addLayout(
            create_callout_card_row(QLabel("Focus time"), self._focus_all_time_label)
        )
        focus_all_time_with_since_layout.addWidget(self._all_time_stats_since_label)
        sessions_card_layout.addLayout(focus_all_time_with_since_layout)
        sessions_card_layout.addLayout(
            create_callout_card_row(
                QLabel("Completed work sessions"), self._completed_work_sessions_label
            )
        )
        sessions_card_layout.addLayout(
            create_callout_card_row(
                QLabel(f"Impact Score /{max(SESSION_RATINGS)}"), self._average_session_rating_label
            )
        )
        sessions_card_layout.addWidget(
            reset_all_time_stats_button, alignment=Qt.AlignmentFlag.AlignRight
        )

        focus_card_layout = QVBoxLayout()
        focus_card_layout.setSpacing(12)
        focus_card_layout.addWidget(create_callout_card_title("Focus"))
        focus_card_layout.addLayout(
            create_callout_card_row(QLabel("Hours on the dial"), self._focus_totaliser_label)
        )
        focus_card_layout.addWidget(
            reset_focus_totaliser_button, alignment=Qt.AlignmentFlag.AlignRight
        )

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(32, 32, 32, 32)
        page_layout.setSpacing(12)
        for card_layout in (today_card_layout, sessions_card_layout, focus_card_layout):
            page_layout.addWidget(
                create_callout_card(card_layout), alignment=Qt.AlignmentFlag.AlignLeft
            )
        page_layout.addStretch(1)  # stretch > 0 takes all spare height, so the cards don't grow

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_stats)
        self._refresh_timer.start(PROFILE_REFRESH_INTERVAL_MILLISECONDS)
        self._refresh_stats()

    def _confirm_then_reset_all_time_stats(self) -> None:
        if AllTimeResetConfirmationDialog(self).exec() == QDialog.DialogCode.Accepted:
            self._pomodoro_timer.reset_all_time_stats()
            self._refresh_stats()

    def _refresh_stats(self) -> None:
        self._focus_today_label.setText(
            _format_hours_and_minutes(self._pomodoro_timer.focus_seconds_today())
        )
        self._completed_work_sessions_today_label.setText(
            str(self._pomodoro_timer.completed_work_sessions_today())
        )
        self._completed_work_sessions_label.setText(
            str(self._pomodoro_timer.completed_work_sessions)
        )
        self._focus_all_time_label.setText(
            _format_hours_and_minutes(self._pomodoro_timer.focus_seconds_all_time())
        )
        self._all_time_stats_since_label.setText(
            f"Since: {self._pomodoro_timer.all_time_stats_since_date:%m/%d/%Y}"
        )
        average_session_rating = self._pomodoro_timer.average_session_rating()
        self._average_session_rating_label.setText(
            "–" if average_session_rating is None else f"{average_session_rating:.1f}"
        )
        self._focus_totaliser_label.setText(
            _format_hours_and_minutes(self._pomodoro_timer.focus_totaliser_seconds())
        )


class AllTimeResetConfirmationDialog(QDialog):
    """Asks for ALL_TIME_RESET_CONFIRMATION_PHRASE to be typed (case and spacing don't matter)
    before the all-time reset, which can't be undone. Reset stays disabled until it matches."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("confirmation_dialog")
        self.setWindowTitle("Reset all-time stats")
        self.setModal(True)

        title_label = QLabel("Reset all-time stats?")
        title_label.setObjectName("confirmation_dialog_title")
        explanation_label = QLabel(
            "All-time focus time, completed work sessions and your Impact Score go back to zero. "
            "Your daily stats, the dial's focus hours and your break cycle are kept."
        )
        irreversible_warning_label = QLabel("This can't be undone.")
        instruction_label = QLabel(f"Type “{ALL_TIME_RESET_CONFIRMATION_PHRASE}” to confirm:")
        for wrapped_label in (explanation_label, instruction_label):
            wrapped_label.setWordWrap(True)
            # A fixed width lets Qt work out the wrapped height before the dialog is sized.
            wrapped_label.setFixedWidth(CONFIRMATION_DIALOG_TEXT_WIDTH_PIXELS)

        self._confirmation_phrase_input = QLineEdit()
        self._confirmation_phrase_input.textChanged.connect(self._enable_reset_if_phrase_matches)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        self._confirm_reset_button = QPushButton("Reset")
        self._confirm_reset_button.setObjectName("destructive_button")
        self._confirm_reset_button.setEnabled(False)
        self._confirm_reset_button.clicked.connect(self.accept)

        button_row_layout = QHBoxLayout()
        button_row_layout.addStretch()
        button_row_layout.addWidget(cancel_button)
        button_row_layout.addWidget(self._confirm_reset_button)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(24, 20, 24, 20)
        dialog_layout.setSpacing(12)
        dialog_layout.addWidget(title_label)
        dialog_layout.addWidget(explanation_label)
        dialog_layout.addWidget(irreversible_warning_label)
        dialog_layout.addWidget(instruction_label)
        dialog_layout.addWidget(self._confirmation_phrase_input)
        dialog_layout.addLayout(button_row_layout)
        dialog_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self._confirmation_phrase_input.setFocus()

    def _enable_reset_if_phrase_matches(self, typed_text: str) -> None:
        normalised_typed_text = " ".join(typed_text.split()).casefold()
        is_phrase_matching = normalised_typed_text == ALL_TIME_RESET_CONFIRMATION_PHRASE
        self._confirm_reset_button.setEnabled(is_phrase_matching)
        self._confirm_reset_button.setDefault(is_phrase_matching)  # Enter confirms once it matches


def _create_stat_value_label() -> QLabel:
    stat_value_label = QLabel()
    stat_value_label.setObjectName("profile_stat_value")
    return stat_value_label


def _format_hours_and_minutes(total_seconds: float) -> str:
    """Whole minutes, as "1h 05m"."""
    hours, minutes = divmod(int(total_seconds // 60), 60)
    return f"{hours}h {minutes:02d}m"
