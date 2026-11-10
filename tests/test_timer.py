from datetime import date, timedelta

import pytest

from tab.core.config import PomodoroSettings
from tab.core.timer import (
    PomodoroTimer,
    TimerPhase,
    TimerProgressSnapshot,
    format_clock_time,
    lap_fractions_from_current_lap,
)


class FakeMonotonicClock:
    def __init__(self) -> None:
        self.current_seconds = 0.0

    def __call__(self) -> float:
        return self.current_seconds


class FakeLocalDate:
    def __init__(self) -> None:
        self.current_date = date(2026, 11, 9)

    def __call__(self) -> date:
        return self.current_date


def create_timer_with_fake_clock() -> tuple[PomodoroTimer, PomodoroSettings, FakeMonotonicClock]:
    settings = PomodoroSettings()
    fake_clock = FakeMonotonicClock()
    return PomodoroTimer(settings, monotonic_clock_seconds=fake_clock), settings, fake_clock


def create_timer_with_separate_work_and_duration() -> tuple[PomodoroTimer, FakeMonotonicClock]:
    fake_clock = FakeMonotonicClock()
    settings = PomodoroSettings(is_work_linked_with_duration=False)
    return PomodoroTimer(settings, monotonic_clock_seconds=fake_clock), fake_clock


def create_timer_with_linked_work_and_duration() -> tuple[
    PomodoroTimer, PomodoroSettings, FakeMonotonicClock
]:
    settings = PomodoroSettings(is_work_linked_with_duration=True)
    fake_clock = FakeMonotonicClock()
    return PomodoroTimer(settings, monotonic_clock_seconds=fake_clock), settings, fake_clock


def create_timer_with_fake_clock_and_date() -> tuple[
    PomodoroTimer, PomodoroSettings, FakeMonotonicClock, FakeLocalDate
]:
    settings = PomodoroSettings()
    fake_clock = FakeMonotonicClock()
    fake_date = FakeLocalDate()
    pomodoro_timer = PomodoroTimer(
        settings, monotonic_clock_seconds=fake_clock, local_date=fake_date
    )
    return pomodoro_timer, settings, fake_clock, fake_date


def test_counts_down_only_while_running() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    fake_clock.current_seconds = 100
    assert pomodoro_timer.remaining_seconds_in_phase() == 25 * 60

    pomodoro_timer.start()
    fake_clock.current_seconds += 60
    pomodoro_timer.pause()
    fake_clock.current_seconds += 600
    assert pomodoro_timer.remaining_seconds_in_phase() == 24 * 60


def test_reset_restores_full_duration_and_stops() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    pomodoro_timer.start()
    fake_clock.current_seconds += 90
    pomodoro_timer.reset()
    assert not pomodoro_timer.is_running
    assert pomodoro_timer.remaining_seconds_in_phase() == 25 * 60


def test_settings_changes_apply_to_current_phase() -> None:
    pomodoro_timer, settings, _ = create_timer_with_fake_clock()
    settings.work_duration_minutes = 50
    assert pomodoro_timer.remaining_seconds_in_phase() == 50 * 60


def test_phase_cycle_takes_long_break_after_every_fourth_work_session() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    observed_phases = []
    for _ in range(8):
        pomodoro_timer.start()
        fake_clock.current_seconds += 60 * 60
        assert pomodoro_timer.advance_phase_if_finished()
        observed_phases.append(pomodoro_timer.current_phase)

    assert observed_phases == [
        TimerPhase.SHORT_BREAK,
        TimerPhase.WORK,
        TimerPhase.SHORT_BREAK,
        TimerPhase.WORK,
        TimerPhase.SHORT_BREAK,
        TimerPhase.WORK,
        TimerPhase.LONG_BREAK,
        TimerPhase.WORK,
    ]
    assert not pomodoro_timer.is_running


def test_upcoming_phase_matches_the_phase_advanced_into() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    for _ in range(8):
        predicted_phase = pomodoro_timer.upcoming_phase()
        pomodoro_timer.start()
        fake_clock.current_seconds += 60 * 60
        assert pomodoro_timer.is_current_phase_finished()
        pomodoro_timer.advance_phase_if_finished()
        assert pomodoro_timer.current_phase is predicted_phase
        assert not pomodoro_timer.is_current_phase_finished()


def test_cycle_count_stays_full_during_long_break_then_resets() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    observed_cycle_counts = []
    for _ in range(8):
        pomodoro_timer.start()
        fake_clock.current_seconds += 60 * 60
        pomodoro_timer.advance_phase_if_finished()
        observed_cycle_counts.append(pomodoro_timer.completed_work_sessions_in_current_cycle())

    assert observed_cycle_counts == [1, 1, 2, 2, 3, 3, 4, 0]


def test_switch_to_phase_resets_and_stops_without_counting_a_session() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    pomodoro_timer.start()
    fake_clock.current_seconds += 120
    pomodoro_timer.switch_to_phase(TimerPhase.LONG_BREAK)
    assert pomodoro_timer.current_phase is TimerPhase.LONG_BREAK
    assert not pomodoro_timer.is_running
    assert pomodoro_timer.remaining_seconds_in_phase() == 15 * 60
    assert pomodoro_timer.completed_work_sessions == 0


def test_focus_totaliser_counts_only_work_time_and_ignores_poll_overrun() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    pomodoro_timer.start()
    fake_clock.current_seconds += 25 * 60 + 3  # UI notices the end 3 s late
    pomodoro_timer.advance_phase_if_finished()
    assert pomodoro_timer.focus_totaliser_seconds() == 25 * 60

    pomodoro_timer.start()  # short break: totaliser must not move
    fake_clock.current_seconds += 60
    assert pomodoro_timer.focus_totaliser_seconds() == 25 * 60


def test_reset_focus_totaliser_keeps_counting_if_working() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    pomodoro_timer.start()
    fake_clock.current_seconds += 600
    pomodoro_timer.reset_focus_totaliser()
    fake_clock.current_seconds += 30
    assert pomodoro_timer.focus_totaliser_seconds() == 30


def test_snapshot_restores_paused_where_it_left_off() -> None:
    pomodoro_timer, settings, fake_clock = create_timer_with_fake_clock()
    pomodoro_timer.start()
    fake_clock.current_seconds += 25 * 60
    pomodoro_timer.advance_phase_if_finished()
    pomodoro_timer.start()
    fake_clock.current_seconds += 90
    snapshot_before_crash = pomodoro_timer.snapshot()

    restored_timer = PomodoroTimer(
        settings, snapshot_before_crash, monotonic_clock_seconds=fake_clock
    )
    fake_clock.current_seconds += 1000
    assert not restored_timer.is_running
    assert restored_timer.current_phase is TimerPhase.SHORT_BREAK
    assert restored_timer.elapsed_seconds_in_phase() == 90
    assert restored_timer.completed_work_sessions == 1
    assert restored_timer.focus_totaliser_seconds() == 25 * 60


def test_today_counts_work_focus_and_completed_work_sessions() -> None:
    pomodoro_timer, _, fake_clock, _ = create_timer_with_fake_clock_and_date()
    pomodoro_timer.start()
    fake_clock.current_seconds += 25 * 60 + 3  # UI notices the end 3 s late
    pomodoro_timer.advance_phase_if_finished()
    assert pomodoro_timer.focus_seconds_today() == 25 * 60
    assert pomodoro_timer.completed_work_sessions_today() == 1

    pomodoro_timer.start()  # short break: focus today must not move
    fake_clock.current_seconds += 60
    assert pomodoro_timer.focus_seconds_today() == 25 * 60


def test_today_starts_over_when_the_date_changes_even_mid_session() -> None:
    pomodoro_timer, _, fake_clock, fake_date = create_timer_with_fake_clock_and_date()
    pomodoro_timer.start()
    fake_clock.current_seconds += 25 * 60
    pomodoro_timer.advance_phase_if_finished()
    pomodoro_timer.switch_to_phase(TimerPhase.WORK)
    pomodoro_timer.start()
    fake_clock.current_seconds += 600

    fake_date.current_date += timedelta(days=1)
    assert pomodoro_timer.focus_seconds_today() == 0
    assert pomodoro_timer.completed_work_sessions_today() == 0
    fake_clock.current_seconds += 30
    assert pomodoro_timer.focus_seconds_today() == 30  # still counting after midnight
    assert pomodoro_timer.completed_work_sessions == 1  # lifetime count untouched
    assert pomodoro_timer.focus_totaliser_seconds() == 25 * 60 + 630


def test_resetting_the_dial_totaliser_keeps_focus_today() -> None:
    pomodoro_timer, _, fake_clock, _ = create_timer_with_fake_clock_and_date()
    pomodoro_timer.start()
    fake_clock.current_seconds += 600
    pomodoro_timer.reset_focus_totaliser()
    assert pomodoro_timer.focus_seconds_today() == 600


def test_snapshot_restores_today_only_on_the_same_day() -> None:
    pomodoro_timer, settings, fake_clock, fake_date = create_timer_with_fake_clock_and_date()
    pomodoro_timer.start()
    fake_clock.current_seconds += 25 * 60
    pomodoro_timer.advance_phase_if_finished()
    snapshot_before_close = pomodoro_timer.snapshot()

    same_day_timer = PomodoroTimer(
        settings, snapshot_before_close, monotonic_clock_seconds=fake_clock, local_date=fake_date
    )
    assert same_day_timer.focus_seconds_today() == 25 * 60
    assert same_day_timer.completed_work_sessions_today() == 1

    fake_date.current_date += timedelta(days=1)
    next_day_timer = PomodoroTimer(
        settings, snapshot_before_close, monotonic_clock_seconds=fake_clock, local_date=fake_date
    )
    assert next_day_timer.focus_seconds_today() == 0
    assert next_day_timer.completed_work_sessions_today() == 0


def test_progress_saved_before_today_existed_restores_with_empty_today() -> None:
    progress_from_older_version = TimerProgressSnapshot.model_validate(
        {"completed_work_sessions": 12, "focus_totaliser_seconds": 3600}
    )
    restored_timer = PomodoroTimer(
        PomodoroSettings(), progress_from_older_version, local_date=FakeLocalDate()
    )
    assert restored_timer.focus_seconds_today() == 0
    assert restored_timer.completed_work_sessions_today() == 0
    assert restored_timer.completed_work_sessions == 12


def test_lap_fractions_cover_the_phase_one_dial_hour_at_a_time() -> None:
    assert lap_fractions_from_current_lap(25 * 60, 0) == [25 / 60]
    assert lap_fractions_from_current_lap(60 * 60, 0) == [1.0]
    assert lap_fractions_from_current_lap(105 * 60, 0) == [1.0, 0.75]
    assert lap_fractions_from_current_lap(120 * 60, 30 * 60) == [1.0, 1.0]


def test_lap_fractions_drop_finished_laps() -> None:
    assert lap_fractions_from_current_lap(105 * 60, 60 * 60) == [0.75]
    assert lap_fractions_from_current_lap(239 * 60, 125 * 60) == [1.0, 59 / 60]


def test_lap_fractions_keep_the_last_lap_at_the_phase_end() -> None:
    assert lap_fractions_from_current_lap(120 * 60, 120 * 60) == [1.0]


def test_lap_fractions_reject_impossible_inputs() -> None:
    with pytest.raises(ValueError, match="duration"):
        lap_fractions_from_current_lap(0, 0)
    with pytest.raises(ValueError, match="elapsed"):
        lap_fractions_from_current_lap(60, -1)


def finish_one_work_session(pomodoro_timer: PomodoroTimer, fake_clock: FakeMonotonicClock) -> None:
    pomodoro_timer.switch_to_phase(TimerPhase.WORK)
    pomodoro_timer.start()
    fake_clock.current_seconds += 25 * 60
    pomodoro_timer.advance_phase_if_finished()


def test_focus_all_time_survives_resetting_the_dial_totaliser() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    finish_one_work_session(pomodoro_timer, fake_clock)
    pomodoro_timer.reset_focus_totaliser()
    finish_one_work_session(pomodoro_timer, fake_clock)
    assert pomodoro_timer.focus_totaliser_seconds() == 25 * 60
    assert pomodoro_timer.focus_seconds_all_time() == 50 * 60


def test_progress_saved_before_all_time_existed_starts_from_the_dial_totaliser() -> None:
    progress_from_older_version = TimerProgressSnapshot.model_validate(
        {"focus_totaliser_seconds": 7200}
    )
    restored_timer = PomodoroTimer(PomodoroSettings(), progress_from_older_version)
    assert restored_timer.focus_seconds_all_time() == 7200


def test_a_finished_work_session_waits_for_a_rating_until_rated() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    assert not pomodoro_timer.is_awaiting_session_rating
    finish_one_work_session(pomodoro_timer, fake_clock)
    assert pomodoro_timer.is_awaiting_session_rating

    pomodoro_timer.rate_last_work_session(5)
    assert not pomodoro_timer.is_awaiting_session_rating
    assert pomodoro_timer.average_session_rating() == 5


def test_starting_the_next_work_session_skips_rating_the_last_one() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    finish_one_work_session(pomodoro_timer, fake_clock)
    pomodoro_timer.start()  # the break: the rating can still be given
    assert pomodoro_timer.is_awaiting_session_rating
    pomodoro_timer.switch_to_phase(TimerPhase.WORK)
    pomodoro_timer.start()
    assert not pomodoro_timer.is_awaiting_session_rating
    assert pomodoro_timer.average_session_rating() is None


def test_average_session_rating_covers_rated_sessions_only() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    for rating in (8, 3, None, 1):
        finish_one_work_session(pomodoro_timer, fake_clock)
        if rating is not None:
            pomodoro_timer.rate_last_work_session(rating)
    assert pomodoro_timer.average_session_rating() == 4


def test_session_ratings_must_be_fibonacci_and_awaited() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    with pytest.raises(ValueError, match="no finished work session"):
        pomodoro_timer.rate_last_work_session(3)
    finish_one_work_session(pomodoro_timer, fake_clock)
    with pytest.raises(ValueError, match="4"):
        pomodoro_timer.rate_last_work_session(4)


def test_snapshot_restores_ratings_and_a_pending_rating() -> None:
    pomodoro_timer, settings, fake_clock = create_timer_with_fake_clock()
    finish_one_work_session(pomodoro_timer, fake_clock)
    pomodoro_timer.rate_last_work_session(8)
    finish_one_work_session(pomodoro_timer, fake_clock)

    restored_timer = PomodoroTimer(settings, pomodoro_timer.snapshot())
    assert restored_timer.is_awaiting_session_rating
    assert restored_timer.average_session_rating() == 8
    assert restored_timer.focus_seconds_all_time() == 50 * 60


def test_a_long_break_waits_for_a_rating_too() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    for _ in range(4):
        finish_one_work_session(pomodoro_timer, fake_clock)
    assert pomodoro_timer.current_phase is TimerPhase.LONG_BREAK
    assert pomodoro_timer.is_awaiting_session_rating


def finish_three_rated_work_sessions() -> tuple[
    PomodoroTimer, PomodoroSettings, FakeMonotonicClock
]:
    pomodoro_timer, settings, fake_clock = create_timer_with_fake_clock()
    for rating in (8, 5, 2):
        finish_one_work_session(pomodoro_timer, fake_clock)
        pomodoro_timer.rate_last_work_session(rating)
    return pomodoro_timer, settings, fake_clock


def test_reset_all_time_stats_zeroes_sessions_focus_and_impact_score() -> None:
    pomodoro_timer, _, _ = finish_three_rated_work_sessions()
    pomodoro_timer.reset_all_time_stats()
    assert pomodoro_timer.completed_work_sessions == 0
    assert pomodoro_timer.focus_seconds_all_time() == 0
    assert pomodoro_timer.average_session_rating() is None


def test_reset_all_time_stats_keeps_today_the_dial_and_the_break_cycle() -> None:
    pomodoro_timer, _, fake_clock = finish_three_rated_work_sessions()
    pomodoro_timer.reset_all_time_stats()
    assert pomodoro_timer.focus_seconds_today() == 75 * 60
    assert pomodoro_timer.completed_work_sessions_today() == 3
    assert pomodoro_timer.focus_totaliser_seconds() == 75 * 60
    assert pomodoro_timer.completed_work_sessions_in_current_cycle() == 3

    finish_one_work_session(pomodoro_timer, fake_clock)
    assert pomodoro_timer.current_phase is TimerPhase.LONG_BREAK


def test_reset_all_time_stats_drops_a_pending_rating() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    finish_one_work_session(pomodoro_timer, fake_clock)
    pomodoro_timer.reset_all_time_stats()
    assert not pomodoro_timer.is_awaiting_session_rating


def test_reset_all_time_stats_keeps_counting_if_working() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    pomodoro_timer.start()
    fake_clock.current_seconds += 600
    pomodoro_timer.reset_all_time_stats()
    fake_clock.current_seconds += 300
    assert pomodoro_timer.focus_seconds_all_time() == 300


def test_snapshot_restores_the_break_cycle_after_an_all_time_reset() -> None:
    pomodoro_timer, settings, _ = finish_three_rated_work_sessions()
    pomodoro_timer.reset_all_time_stats()
    restored_timer = PomodoroTimer(settings, pomodoro_timer.snapshot())
    assert restored_timer.completed_work_sessions == 0
    assert restored_timer.completed_work_sessions_in_current_cycle() == 3


def test_progress_saved_before_the_cycle_counter_existed_follows_completed_sessions() -> None:
    progress_from_older_version = TimerProgressSnapshot.model_validate(
        {"current_phase": "short_break", "completed_work_sessions": 7}
    )
    restored_timer = PomodoroTimer(PomodoroSettings(), progress_from_older_version)
    assert restored_timer.completed_work_sessions_in_current_cycle() == 3


def test_all_time_stats_count_since_the_day_tracking_began() -> None:
    pomodoro_timer, settings, _, fake_date = create_timer_with_fake_clock_and_date()
    assert pomodoro_timer.all_time_stats_since_date == date(2026, 11, 9)

    fake_date.current_date += timedelta(days=30)
    restored_timer = PomodoroTimer(settings, pomodoro_timer.snapshot(), local_date=fake_date)
    assert restored_timer.all_time_stats_since_date == date(2026, 11, 9)


def test_reset_all_time_stats_counts_since_the_reset_day() -> None:
    pomodoro_timer, _, _, fake_date = create_timer_with_fake_clock_and_date()
    fake_date.current_date += timedelta(days=3)
    pomodoro_timer.reset_all_time_stats()
    assert pomodoro_timer.all_time_stats_since_date == date(2026, 11, 12)


def test_progress_saved_before_the_since_date_existed_counts_since_today() -> None:
    fake_date = FakeLocalDate()
    progress_from_older_version = TimerProgressSnapshot.model_validate(
        {"completed_work_sessions": 8}
    )
    restored_timer = PomodoroTimer(
        PomodoroSettings(), progress_from_older_version, local_date=fake_date
    )
    assert restored_timer.all_time_stats_since_date == fake_date.current_date


def test_duration_counts_up_as_focus_only_while_running() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    pomodoro_timer.start_duration()
    fake_clock.current_seconds += 90
    pomodoro_timer.pause_duration()
    fake_clock.current_seconds += 600
    assert pomodoro_timer.duration_elapsed_seconds() == 90
    assert pomodoro_timer.focus_seconds_today() == 90
    assert pomodoro_timer.focus_seconds_all_time() == 90
    assert pomodoro_timer.focus_totaliser_seconds() == 90


def test_separate_finished_duration_is_its_own_session_awaiting_rating() -> None:
    pomodoro_timer, fake_clock = create_timer_with_separate_work_and_duration()
    pomodoro_timer.start_duration()
    fake_clock.current_seconds += 40 * 60
    pomodoro_timer.finish_duration()
    assert not pomodoro_timer.is_duration_running
    assert pomodoro_timer.duration_elapsed_seconds() == 0
    assert pomodoro_timer.completed_work_sessions == 1
    assert pomodoro_timer.completed_work_sessions_today() == 1
    assert pomodoro_timer.completed_work_sessions_in_current_cycle() == 0
    assert pomodoro_timer.focus_seconds_today() == 40 * 60

    pomodoro_timer.rate_last_work_session(8)
    assert pomodoro_timer.average_session_rating() == 8


def test_finishing_an_unstarted_duration_raises() -> None:
    pomodoro_timer, _, _ = create_timer_with_fake_clock()
    with pytest.raises(ValueError, match="hasn't been started"):
        pomodoro_timer.finish_duration()


def test_separate_duration_and_pomodoro_never_run_together() -> None:
    pomodoro_timer, fake_clock = create_timer_with_separate_work_and_duration()
    pomodoro_timer.start()
    fake_clock.current_seconds += 60
    pomodoro_timer.start_duration()
    assert not pomodoro_timer.is_running
    fake_clock.current_seconds += 60
    pomodoro_timer.start()
    assert not pomodoro_timer.is_duration_running
    fake_clock.current_seconds += 60
    pomodoro_timer.pause()
    assert pomodoro_timer.focus_seconds_today() == 180


def test_separate_pomodoro_pause_and_reset_leave_a_running_duration_counting() -> None:
    pomodoro_timer, fake_clock = create_timer_with_separate_work_and_duration()
    pomodoro_timer.start_duration()
    pomodoro_timer.pause()
    pomodoro_timer.reset()
    pomodoro_timer.switch_to_phase(TimerPhase.SHORT_BREAK)
    fake_clock.current_seconds += 120
    assert pomodoro_timer.is_duration_running
    assert pomodoro_timer.focus_seconds_today() == 120


def test_linked_work_phase_and_duration_share_one_clock() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_linked_work_and_duration()
    pomodoro_timer.start_duration()
    assert pomodoro_timer.is_running
    fake_clock.current_seconds += 60
    assert pomodoro_timer.remaining_seconds_in_phase() == 24 * 60
    assert pomodoro_timer.duration_elapsed_seconds() == 60
    assert pomodoro_timer.focus_seconds_today() == 60  # counted once, not twice


@pytest.mark.parametrize("pause_from", ["pomodoro", "duration"])
def test_pausing_either_linked_clock_pauses_both(pause_from: str) -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_linked_work_and_duration()
    pomodoro_timer.start()
    assert pomodoro_timer.is_duration_running
    fake_clock.current_seconds += 30
    if pause_from == "pomodoro":
        pomodoro_timer.pause()
    else:
        pomodoro_timer.pause_duration()
    fake_clock.current_seconds += 600
    assert not pomodoro_timer.is_running
    assert not pomodoro_timer.is_duration_running
    assert pomodoro_timer.focus_seconds_today() == 30


def test_linked_work_phase_running_out_completes_one_session_and_resets_both() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_linked_work_and_duration()
    pomodoro_timer.start()
    fake_clock.current_seconds += 25 * 60
    pomodoro_timer.pause()  # what the timer view does when the phase ends
    pomodoro_timer.advance_phase_if_finished()
    assert pomodoro_timer.current_phase is TimerPhase.SHORT_BREAK
    assert pomodoro_timer.duration_elapsed_seconds() == 0
    assert pomodoro_timer.completed_work_sessions_today() == 1
    assert pomodoro_timer.is_awaiting_session_rating


def test_linked_break_runs_without_the_duration() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_linked_work_and_duration()
    pomodoro_timer.switch_to_phase(TimerPhase.SHORT_BREAK)
    pomodoro_timer.start()
    fake_clock.current_seconds += 60
    assert not pomodoro_timer.is_duration_running
    assert pomodoro_timer.duration_elapsed_seconds() == 0
    assert pomodoro_timer.focus_seconds_today() == 0


def test_linked_duration_started_in_a_break_returns_to_work_with_both_running() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_linked_work_and_duration()
    pomodoro_timer.switch_to_phase(TimerPhase.SHORT_BREAK)
    pomodoro_timer.start()
    fake_clock.current_seconds += 60
    pomodoro_timer.start_duration()
    assert pomodoro_timer.current_phase is TimerPhase.WORK
    assert pomodoro_timer.is_running and pomodoro_timer.is_duration_running
    fake_clock.current_seconds += 60
    assert pomodoro_timer.remaining_seconds_in_phase() == 24 * 60  # a fresh work phase
    assert pomodoro_timer.duration_elapsed_seconds() == 60


def test_linked_finish_from_the_duration_completes_the_work_session_once() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_linked_work_and_duration()
    pomodoro_timer.start_duration()
    fake_clock.current_seconds += 10 * 60
    pomodoro_timer.finish_duration()
    assert pomodoro_timer.current_phase is TimerPhase.SHORT_BREAK
    assert not pomodoro_timer.is_running and not pomodoro_timer.is_duration_running
    assert pomodoro_timer.duration_elapsed_seconds() == 0
    assert pomodoro_timer.completed_work_sessions_today() == 1
    assert pomodoro_timer.completed_work_sessions_in_current_cycle() == 1
    assert pomodoro_timer.focus_seconds_today() == 10 * 60


def test_completing_a_work_session_manually_resets_both_when_linked() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_linked_work_and_duration()
    pomodoro_timer.start()
    fake_clock.current_seconds += 12 * 60
    pomodoro_timer.complete_work_session()
    assert pomodoro_timer.current_phase is TimerPhase.SHORT_BREAK
    assert pomodoro_timer.remaining_seconds_in_phase() == 5 * 60
    assert pomodoro_timer.duration_elapsed_seconds() == 0
    assert pomodoro_timer.completed_work_sessions_today() == 1
    assert pomodoro_timer.is_awaiting_session_rating


def test_separate_manual_completion_leaves_the_duration_alone() -> None:
    pomodoro_timer, fake_clock = create_timer_with_separate_work_and_duration()
    pomodoro_timer.start_duration()
    fake_clock.current_seconds += 60
    pomodoro_timer.start()  # pauses the duration
    fake_clock.current_seconds += 60
    pomodoro_timer.complete_work_session()
    assert pomodoro_timer.duration_elapsed_seconds() == 60
    assert pomodoro_timer.current_phase is TimerPhase.SHORT_BREAK


def test_completing_a_break_or_an_unstarted_work_phase_raises() -> None:
    pomodoro_timer, _, _ = create_timer_with_fake_clock()
    with pytest.raises(ValueError, match="hasn't been started"):
        pomodoro_timer.complete_work_session()
    pomodoro_timer.switch_to_phase(TimerPhase.SHORT_BREAK)
    with pytest.raises(ValueError, match="short_break"):
        pomodoro_timer.complete_work_session()


def test_unlinking_mid_session_keeps_focus_while_one_clock_runs() -> None:
    pomodoro_timer, settings, fake_clock = create_timer_with_linked_work_and_duration()
    pomodoro_timer.start()  # linked: both run
    settings.is_work_linked_with_duration = False
    pomodoro_timer.pause_duration()  # only the duration stops now
    fake_clock.current_seconds += 60
    assert pomodoro_timer.is_running
    assert pomodoro_timer.focus_seconds_today() == 60


def test_linked_duration_pauses_when_the_timer_switches_to_a_break() -> None:
    pomodoro_timer, settings, fake_clock = create_timer_with_linked_work_and_duration()
    settings.is_work_linked_with_duration = False
    pomodoro_timer.start_duration()  # running alone, then linking is switched on
    settings.is_work_linked_with_duration = True
    pomodoro_timer.switch_to_phase(TimerPhase.LONG_BREAK)
    fake_clock.current_seconds += 60
    assert not pomodoro_timer.is_duration_running
    assert pomodoro_timer.duration_elapsed_seconds() == 0


def test_work_and_duration_are_separate_by_default() -> None:
    assert not PomodoroSettings().is_work_linked_with_duration


def test_duration_is_restored_paused() -> None:
    settings = PomodoroSettings()
    fake_clock = FakeMonotonicClock()
    pomodoro_timer = PomodoroTimer(settings, monotonic_clock_seconds=fake_clock)
    pomodoro_timer.start_duration()
    fake_clock.current_seconds += 300
    restored_timer = PomodoroTimer(
        settings, pomodoro_timer.snapshot(), monotonic_clock_seconds=fake_clock
    )
    fake_clock.current_seconds += 300
    assert not restored_timer.is_duration_running
    assert restored_timer.duration_elapsed_seconds() == 300


def test_formats_clock_time_with_hours_only_when_needed() -> None:
    assert format_clock_time(65) == "01:05"
    assert format_clock_time(2 * 3600) == "2:00:00"
    with pytest.raises(ValueError, match="-1"):
        format_clock_time(-1)


def test_skipping_a_rating_clears_the_prompt_without_touching_the_score() -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_fake_clock()
    pomodoro_timer.start_duration()
    fake_clock.current_seconds += 60
    pomodoro_timer.finish_duration()
    pomodoro_timer.skip_session_rating()
    assert not pomodoro_timer.is_awaiting_session_rating
    assert pomodoro_timer.average_session_rating() is None


def test_skipping_with_no_rating_pending_raises() -> None:
    pomodoro_timer, _, _ = create_timer_with_fake_clock()
    with pytest.raises(ValueError, match="no finished session"):
        pomodoro_timer.skip_session_rating()


@pytest.mark.parametrize("was_linked", [True, False])
def test_toggling_the_linking_setting_pauses_both_clocks(was_linked: bool) -> None:
    fake_clock = FakeMonotonicClock()
    settings = PomodoroSettings(is_work_linked_with_duration=was_linked)
    pomodoro_timer = PomodoroTimer(settings, monotonic_clock_seconds=fake_clock)
    pomodoro_timer.start_duration()
    pomodoro_timer.start()  # linked: both run; separate: just the Pomodoro
    fake_clock.current_seconds += 60
    pomodoro_timer.set_work_linked_with_duration(not was_linked)
    fake_clock.current_seconds += 600
    assert settings.is_work_linked_with_duration is not was_linked
    assert not pomodoro_timer.is_running
    assert not pomodoro_timer.is_duration_running
    assert pomodoro_timer.focus_seconds_today() == 60


def test_resetting_the_duration_zeroes_it_without_a_session() -> None:
    pomodoro_timer, fake_clock = create_timer_with_separate_work_and_duration()
    pomodoro_timer.start()
    fake_clock.current_seconds += 60
    pomodoro_timer.start_duration()  # separate: pauses the Pomodoro
    fake_clock.current_seconds += 120
    pomodoro_timer.reset_duration()
    assert not pomodoro_timer.is_duration_running
    assert pomodoro_timer.duration_elapsed_seconds() == 0
    assert pomodoro_timer.completed_work_sessions_today() == 0
    assert pomodoro_timer.focus_seconds_today() == 180  # focus spent is kept
    assert pomodoro_timer.remaining_seconds_in_phase() == 24 * 60  # Pomodoro untouched


@pytest.mark.parametrize("reset_from", ["timer", "duration"])
def test_linked_reset_from_either_side_resets_both(reset_from: str) -> None:
    pomodoro_timer, _, fake_clock = create_timer_with_linked_work_and_duration()
    pomodoro_timer.start()
    fake_clock.current_seconds += 300
    if reset_from == "timer":
        pomodoro_timer.reset_phase()
    else:
        pomodoro_timer.reset_duration()
    assert not pomodoro_timer.is_running and not pomodoro_timer.is_duration_running
    assert pomodoro_timer.remaining_seconds_in_phase() == 25 * 60
    assert pomodoro_timer.duration_elapsed_seconds() == 0
    assert pomodoro_timer.focus_seconds_today() == 300


def test_separate_timer_reset_leaves_the_duration_alone() -> None:
    pomodoro_timer, fake_clock = create_timer_with_separate_work_and_duration()
    pomodoro_timer.start_duration()
    fake_clock.current_seconds += 60
    pomodoro_timer.start()
    fake_clock.current_seconds += 60
    pomodoro_timer.reset_phase()
    assert pomodoro_timer.duration_elapsed_seconds() == 60
