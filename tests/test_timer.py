from tab.core.config import PomodoroSettings
from tab.core.timer import PomodoroTimer, TimerPhase


class FakeMonotonicClock:
    def __init__(self) -> None:
        self.current_seconds = 0.0

    def __call__(self) -> float:
        return self.current_seconds


def create_timer_with_fake_clock() -> tuple[PomodoroTimer, PomodoroSettings, FakeMonotonicClock]:
    settings = PomodoroSettings()
    fake_clock = FakeMonotonicClock()
    return PomodoroTimer(settings, monotonic_clock_seconds=fake_clock), settings, fake_clock


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
