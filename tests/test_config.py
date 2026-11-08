from pathlib import Path

import pytest
from pydantic import ValidationError

from tab.core.config import PomodoroSettings, load_settings, save_settings


def test_missing_file_returns_defaults(tmp_path: Path) -> None:
    assert load_settings(tmp_path / "settings.json") == PomodoroSettings()


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    settings_file_path = tmp_path / "nested" / "settings.json"
    save_settings(PomodoroSettings(work_duration_minutes=40), settings_file_path)
    assert load_settings(settings_file_path).work_duration_minutes == 40


def test_invalid_file_raises_instead_of_falling_back(tmp_path: Path) -> None:
    settings_file_path = tmp_path / "settings.json"
    settings_file_path.write_text('{"work_duration_minutes": 0}')
    with pytest.raises(ValidationError):
        load_settings(settings_file_path)


def test_invalid_assignment_raises() -> None:
    with pytest.raises(ValidationError):
        PomodoroSettings().short_break_duration_minutes = -5
