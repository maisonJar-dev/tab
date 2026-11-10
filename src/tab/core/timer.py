import math
import time
from collections.abc import Callable
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from tab.core.config import PomodoroSettings
from tab.core.stopwatch import Stopwatch

WORK_SESSIONS_BEFORE_LONG_BREAK = 4
SECONDS_PER_DIAL_LAP = 3600  # the minutes hand goes round once an hour
SESSION_RATINGS = (1, 2, 3, 5, 8)  # Fibonacci: the gaps widen, so the top ratings mean more


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
    # The local day the two "today" counters belong to; None in files saved before they existed.
    today_date: date | None = None
    focus_seconds_today: float = Field(default=0.0, ge=0)
    completed_work_sessions_today: int = Field(default=0, ge=0)
    # None in files saved before it existed; restored from the dial totaliser, a lower bound.
    focus_seconds_all_time: float | None = Field(default=None, ge=0)
    is_awaiting_session_rating: bool = False
    session_rating_sum: int = Field(default=0, ge=0)
    rated_work_sessions: int = Field(default=0, ge=0)
    # Drives the long break; unlike completed_work_sessions it survives an all-time reset.
    # None in files saved before it existed, when completed_work_sessions did this job.
    work_sessions_counted_for_break_cycle: int | None = Field(default=None, ge=0)
    # The day all-time stats began (or were last reset); None in files saved before it existed,
    # which then count from the day they're first loaded.
    all_time_stats_since_date: date | None = None


class PomodoroTimer:
    """Pure Pomodoro state machine. Knows nothing about Qt; the UI polls it.

    Phase durations are read from the shared settings on every query, so edits apply
    immediately. Focus time only counts while the timer runs in the WORK phase, into three
    stopwatches: the dial's totaliser (reset by the user), focus today and focus all time.

    Each finished work session can be rated (SESSION_RATINGS) during the break after it;
    starting the next work session skips the rating.

    Resetting all-time stats zeroes completed sessions, all-time focus and ratings, but keeps
    today, the dial's totaliser and the position in the long-break cycle.

    "Today" (focus seconds and completed work sessions) starts over whenever the local date
    changes, checked each time today's numbers are read, updated or saved.
    """

    def __init__(
        self,
        settings: PomodoroSettings,
        restored_progress: TimerProgressSnapshot | None = None,
        monotonic_clock_seconds: Callable[[], float] = time.monotonic,
        local_date: Callable[[], date] = date.today,
    ) -> None:
        restored_progress = restored_progress or TimerProgressSnapshot()
        self._settings = settings
        self._local_date = local_date
        self.current_phase = restored_progress.current_phase
        self.completed_work_sessions = restored_progress.completed_work_sessions
        self.all_time_stats_since_date = restored_progress.all_time_stats_since_date or local_date()
        self._work_sessions_counted_for_break_cycle = (
            restored_progress.completed_work_sessions
            if restored_progress.work_sessions_counted_for_break_cycle is None
            else restored_progress.work_sessions_counted_for_break_cycle
        )
        self._phase_stopwatch = Stopwatch(monotonic_clock_seconds)
        self._phase_stopwatch.reset(restored_progress.elapsed_seconds_in_phase)
        self._focus_totaliser_stopwatch = Stopwatch(monotonic_clock_seconds)
        self._focus_totaliser_stopwatch.reset(restored_progress.focus_totaliser_seconds)
        self._focus_today_stopwatch = Stopwatch(monotonic_clock_seconds)
        self._focus_all_time_stopwatch = Stopwatch(monotonic_clock_seconds)
        self._focus_all_time_stopwatch.reset(
            restored_progress.focus_totaliser_seconds
            if restored_progress.focus_seconds_all_time is None
            else restored_progress.focus_seconds_all_time
        )
        self._focus_stopwatches = (
            self._focus_totaliser_stopwatch,
            self._focus_today_stopwatch,
            self._focus_all_time_stopwatch,
        )
        self.is_awaiting_session_rating = restored_progress.is_awaiting_session_rating
        self._session_rating_sum = restored_progress.session_rating_sum
        self._rated_work_sessions = restored_progress.rated_work_sessions

        self._today_date = local_date()
        self._completed_work_sessions_today = 0
        if restored_progress.today_date == self._today_date:
            self._focus_today_stopwatch.reset(restored_progress.focus_seconds_today)
            self._completed_work_sessions_today = restored_progress.completed_work_sessions_today

    @property
    def is_running(self) -> bool:
        return self._phase_stopwatch.is_running

    def completed_work_sessions_in_current_cycle(self) -> int:
        """0 to WORK_SESSIONS_BEFORE_LONG_BREAK; stays full during the long break."""
        sessions_in_cycle = (
            self._work_sessions_counted_for_break_cycle % WORK_SESSIONS_BEFORE_LONG_BREAK
        )
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

    def focus_seconds_today(self) -> float:
        self._start_new_day_if_date_changed()
        return self._focus_today_stopwatch.elapsed_seconds()

    def completed_work_sessions_today(self) -> int:
        self._start_new_day_if_date_changed()
        return self._completed_work_sessions_today

    def focus_seconds_all_time(self) -> float:
        return self._focus_all_time_stopwatch.elapsed_seconds()

    def average_session_rating(self) -> float | None:
        """Mean of the rated work sessions; None until one has been rated."""
        if self._rated_work_sessions == 0:
            return None
        return self._session_rating_sum / self._rated_work_sessions

    def rate_last_work_session(self, rating: int) -> None:
        if not self.is_awaiting_session_rating:
            raise ValueError("There's no finished work session waiting for a rating")
        if rating not in SESSION_RATINGS:
            raise ValueError(f"Session rating must be one of {SESSION_RATINGS}, got {rating}")
        self._session_rating_sum += rating
        self._rated_work_sessions += 1
        self.is_awaiting_session_rating = False

    def reset_all_time_stats(self) -> None:
        self.all_time_stats_since_date = self._local_date()
        self.completed_work_sessions = 0
        _restart_from_zero_keeping_run_state(self._focus_all_time_stopwatch)
        self._session_rating_sum = 0
        self._rated_work_sessions = 0
        self.is_awaiting_session_rating = False  # its session no longer counts

    def start(self) -> None:
        self._start_new_day_if_date_changed()
        self._phase_stopwatch.start()
        if self.current_phase is TimerPhase.WORK:
            self.is_awaiting_session_rating = False  # moved on without rating the last one
            for focus_stopwatch in self._focus_stopwatches:
                focus_stopwatch.start()

    def pause(self) -> None:
        self._phase_stopwatch.pause()
        for focus_stopwatch in self._focus_stopwatches:
            focus_stopwatch.pause()

    def reset(self) -> None:
        """Restart the current phase at full duration, stopped. Focus time spent is kept."""
        self._phase_stopwatch.reset()
        for focus_stopwatch in self._focus_stopwatches:
            focus_stopwatch.pause()

    def reset_focus_totaliser(self) -> None:
        """Zero the dial's totaliser only; focus today is kept."""
        _restart_from_zero_keeping_run_state(self._focus_totaliser_stopwatch)

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
        self._start_new_day_if_date_changed()
        upcoming_phase = self.upcoming_phase()
        if self.current_phase is TimerPhase.WORK:
            self._remove_overrun_from_focus_stopwatches(phase_overrun_seconds)
            self.completed_work_sessions += 1
            self._work_sessions_counted_for_break_cycle += 1
            self._completed_work_sessions_today += 1
            self.is_awaiting_session_rating = True
        self.current_phase = upcoming_phase
        self.reset()
        return True

    def upcoming_phase(self) -> TimerPhase:
        """The phase that follows the current one when it finishes."""
        if self.current_phase is not TimerPhase.WORK:
            return TimerPhase.WORK
        is_long_break_due = (
            self._work_sessions_counted_for_break_cycle + 1
        ) % WORK_SESSIONS_BEFORE_LONG_BREAK == 0
        return TimerPhase.LONG_BREAK if is_long_break_due else TimerPhase.SHORT_BREAK

    def snapshot(self) -> TimerProgressSnapshot:
        return TimerProgressSnapshot(
            current_phase=self.current_phase,
            elapsed_seconds_in_phase=self.elapsed_seconds_in_phase(),
            completed_work_sessions=self.completed_work_sessions,
            focus_totaliser_seconds=self.focus_totaliser_seconds(),
            focus_seconds_today=self.focus_seconds_today(),  # checks the date first
            today_date=self._today_date,
            completed_work_sessions_today=self._completed_work_sessions_today,
            focus_seconds_all_time=self.focus_seconds_all_time(),
            is_awaiting_session_rating=self.is_awaiting_session_rating,
            session_rating_sum=self._session_rating_sum,
            rated_work_sessions=self._rated_work_sessions,
            work_sessions_counted_for_break_cycle=self._work_sessions_counted_for_break_cycle,
            all_time_stats_since_date=self.all_time_stats_since_date,
        )

    def _start_new_day_if_date_changed(self) -> None:
        """Zero today's counters at the first check after midnight; a running session keeps
        counting into the new day. Focus between midnight and that check (one UI poll) is lost."""
        current_date = self._local_date()
        if current_date == self._today_date:
            return
        self._today_date = current_date
        self._completed_work_sessions_today = 0
        _restart_from_zero_keeping_run_state(self._focus_today_stopwatch)

    def _remove_overrun_from_focus_stopwatches(self, phase_overrun_seconds: float) -> None:
        """The UI polls, so a phase is noticed slightly after it ends; don't count that gap."""
        for focus_stopwatch in self._focus_stopwatches:
            focus_stopwatch.pause()
            trimmed_focus_seconds = max(
                0.0, focus_stopwatch.elapsed_seconds() - phase_overrun_seconds
            )
            focus_stopwatch.reset(trimmed_focus_seconds)


def _restart_from_zero_keeping_run_state(stopwatch: Stopwatch) -> None:
    was_running = stopwatch.is_running
    stopwatch.reset()
    if was_running:
        stopwatch.start()


def lap_fractions_from_current_lap(
    phase_duration_seconds: float, elapsed_seconds_in_phase: float
) -> list[float]:
    """How much of each dial lap the phase fills, from the lap the hand is on to the last.

    A phase longer than an hour laps the dial, so 1:45 is [1.0, 0.75]: a full lap, then three
    quarters. Finished laps drop off the front; at the phase end the last lap is still returned.
    """
    if phase_duration_seconds <= 0:
        raise ValueError(f"Phase duration must be positive, got {phase_duration_seconds} s")
    if elapsed_seconds_in_phase < 0:
        raise ValueError(f"Phase elapsed time can't be negative, got {elapsed_seconds_in_phase} s")
    lap_count = math.ceil(phase_duration_seconds / SECONDS_PER_DIAL_LAP)
    current_lap_index = min(int(elapsed_seconds_in_phase // SECONDS_PER_DIAL_LAP), lap_count - 1)
    return [
        min(1.0, (phase_duration_seconds - lap_index * SECONDS_PER_DIAL_LAP) / SECONDS_PER_DIAL_LAP)
        for lap_index in range(current_lap_index, lap_count)
    ]
