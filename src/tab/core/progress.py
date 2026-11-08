import os
from pathlib import Path

from tab.core.json_storage import load_json_model, save_json_model_atomically
from tab.core.timer import TimerProgressSnapshot


def default_progress_file_path() -> Path:
    """XDG state directory: data that should survive restarts but isn't user config."""
    state_home_directory = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return state_home_directory / "tab" / "progress.json"


def load_timer_progress(progress_file_path: Path | None = None) -> TimerProgressSnapshot:
    saved_progress = load_json_model(
        progress_file_path or default_progress_file_path(), TimerProgressSnapshot
    )
    return saved_progress or TimerProgressSnapshot()


def save_timer_progress(
    progress: TimerProgressSnapshot, progress_file_path: Path | None = None
) -> None:
    save_json_model_atomically(progress, progress_file_path or default_progress_file_path())
