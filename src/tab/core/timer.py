import time
from collections.abc import Callable
from enum import Enum

from pydantic import BaseModel, Field

from tab.core.config import PomodoroSettings
from tab.core.stopwatch import Stopwatch

WORK_SESSIONS_BEFORE_LONG_BREAK = 4


class TimerPhase(Enum):
    """Values are stable identifiers written to disk; display labels live in the UI."""

    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


class TimerProgressSnapshot(BaseModel):
    """Everything needed to restore the timer after a close or crash."""

    current_phase: TimerPhase = TimerPhase.WORK
    elapsed_seconds_in_phase: float = Field(default=0.0, ge=0)
    completed_work_sessions: int = Field(default=0, ge=0)
    focus_totaliser_seconds: float = Field(default=0.0, ge=0)


class PomodoroTimer:
    """Pure Pomodoro state machine. Knows nothing about Qt; the UI polls it.

    Phase durations are read from the shared settings on every query, so edits apply
    immediately. The focus totaliser only runs while the timer runs in the WORK phase.
    """

    def __init__(
        self,
        settings: PomodoroSettings,
        restored_progress: TimerProgressSnapshot | None = None,
        monotonic_clock_seconds: Callable[[], float] = time.monotonic,
    ) -> None:
        restored_progress = restored_progress or TimerProgressSnapshot()
        self._settings = settings
        self.current_phase = restored_progress.current_phase
        self.completed_work_sessions = restored_progress.completed_work_sessions
        self._phase_stopwatch = Stopwatch(monotonic_clock_seconds)
        self._phase_stopwatch.reset(restored_progress.elapsed_seconds_in_phase)
        self._focus_totaliser_stopwatch = Stopwatch(monotonic_clock_seconds)
        self._focus_totaliser_stopwatch.reset(restored_progress.focus_totaliser_seconds)

    @property
    def is_running(self) -> bool:
        return self._phase_stopwatch.is_running

    def completed_work_sessions_in_current_cycle(self) -> int:
        """0 to WORK_SESSIONS_BEFORE_LONG_BREAK; stays full during the long break."""
        sessions_in_cycle = self.completed_work_sessions % WORK_SESSIONS_BEFORE_LONG_BREAK
        if sessions_in_cycle == 0 and self.current_phase is TimerPhase.LONG_BREAK:
            return WORK_SESSIONS_BEFORE_LONG_BREAK
        return sessions_in_cycle

    def current_phase_duration_seconds(self) -> float:
        minutes_by_phase = {
            TimerPhase.WORK: self._settings.work_duration_minutes,
            TimerPhase.SHORT_BREAK: self._settings.short_break_duration_minutes,
            TimerPhase.LONG_BREAK: self._settings.long_break_duration_minutes,
        }
        return minutes_by_phase[self.current_phase] * 60.0

    def elapsed_seconds_in_phase(self) -> float:
        return min(self._phase_stopwatch.elapsed_seconds(), self.current_phase_duration_seconds())

    def remaining_seconds_in_phase(self) -> float:
        return self.current_phase_duration_seconds() - self.elapsed_seconds_in_phase()

    def focus_totaliser_seconds(self) -> float:
        return self._focus_totaliser_stopwatch.elapsed_seconds()

    def start(self) -> None:
        self._phase_stopwatch.start()
        if self.current_phase is TimerPhase.WORK:
            self._focus_totaliser_stopwatch.start()

    def pause(self) -> None:
        self._phase_stopwatch.pause()
        self._focus_totaliser_stopwatch.pause()

    def reset(self) -> None:
        """Restart the current phase at full duration, stopped. Focus time spent is kept."""
        self._phase_stopwatch.reset()
        self._focus_totaliser_stopwatch.pause()

    def reset_focus_totaliser(self) -> None:
        was_counting_focus = self._focus_totaliser_stopwatch.is_running
        self._focus_totaliser_stopwatch.reset()
        if was_counting_focus:
            self._focus_totaliser_stopwatch.start()

    def switch_to_phase(self, phase: TimerPhase) -> None:
        """Jump to a phase at its full duration, stopped. Doesn't count as a completed session."""
        self.current_phase = phase
        self.reset()

    def is_current_phase_finished(self) -> bool:
        return self.remaining_seconds_in_phase() <= 0

    def advance_phase_if_finished(self) -> bool:
        """Move to the next phase (stopped) once the current one ends. Returns True if it moved."""
        phase_overrun_seconds = (
            self._phase_stopwatch.elapsed_seconds() - self.current_phase_duration_seconds()
        )
        if phase_overrun_seconds < 0:
            return False
        upcoming_phase = self.upcoming_phase()
        if self.current_phase is TimerPhase.WORK:
            self._remove_overrun_from_focus_totaliser(phase_overrun_seconds)
            self.completed_work_sessions += 1
        self.current_phase = upcoming_phase
        self.reset()
        return True

    def upcoming_phase(self) -> TimerPhase:
        """The phase that follows the current one when it finishes."""
        if self.current_phase is not TimerPhase.WORK:
            return TimerPhase.WORK
        is_long_break_due = (
            self.completed_work_sessions + 1
        ) % WORK_SESSIONS_BEFORE_LONG_BREAK == 0
        return TimerPhase.LONG_BREAK if is_long_break_due else TimerPhase.SHORT_BREAK

    def snapshot(self) -> TimerProgressSnapshot:
        return TimerProgressSnapshot(
            current_phase=self.current_phase,
            elapsed_seconds_in_phase=self.elapsed_seconds_in_phase(),
            completed_work_sessions=self.completed_work_sessions,
            focus_totaliser_seconds=self.focus_totaliser_seconds(),
        )

    def _remove_overrun_from_focus_totaliser(self, phase_overrun_seconds: float) -> None:
        """The UI polls, so a phase is noticed slightly after it ends; don't count that gap."""
        self._focus_totaliser_stopwatch.pause()
        trimmed_focus_seconds = max(
            0.0, self._focus_totaliser_stopwatch.elapsed_seconds() - phase_overrun_seconds
        )
        self._focus_totaliser_stopwatch.reset(trimmed_focus_seconds)
