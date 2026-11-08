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
    )
    save_timer_progress(saved_progress, progress_file_path)
    assert load_timer_progress(progress_file_path) == saved_progress
    assert list(progress_file_path.parent.iterdir()) == [progress_file_path]
