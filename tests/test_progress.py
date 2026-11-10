from datetime import date
from pathlib import Path

from tab.core.progress import load_timer_progress, save_timer_progress
from tab.core.timer import TimerPhase, TimerProgressSnapshot


def test_missing_file_returns_fresh_progress(tmp_path: Path) -> None:
    assert load_timer_progress(tmp_path / "progress.json") == TimerProgressSnapshot()


def test_save_then_load_round_trips_without_leaving_temp_file(tmp_path: Path) -> None:
    progress_file_path = tmp_path / "state" / "progress.json"
    saved_progress = TimerProgressSnapshot(
        current_phase=TimerPhase.LONG_BREAK,
        elapsed_seconds_in_phase=42.5,
        completed_work_sessions=8,
        focus_totaliser_seconds=7200,
        today_date=date(2026, 11, 9),
        focus_seconds_today=1500,
        completed_work_sessions_today=1,
        focus_seconds_all_time=90000,
        is_awaiting_session_rating=True,
        session_rating_sum=21,
        rated_work_sessions=5,
        work_sessions_counted_for_break_cycle=11,
        all_time_stats_since_date=date(2026, 10, 1),
    )
    save_timer_progress(saved_progress, progress_file_path)
    assert load_timer_progress(progress_file_path) == saved_progress
    assert list(progress_file_path.parent.iterdir()) == [progress_file_path]
