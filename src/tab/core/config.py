import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from tab.core.json_storage import load_json_model, save_json_model_atomically


class PomodoroSettings(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    work_duration_minutes: int = Field(default=25, ge=1)
    short_break_duration_minutes: int = Field(default=5, ge=1)
    long_break_duration_minutes: int = Field(default=15, ge=1)
    use_abbreviated_phase_labels: bool = False
    is_intro_sound_enabled: bool = True
    is_phase_end_notification_enabled: bool = True
    # Work phases and the duration share one clock (break time stays separate). Off by default.
    is_work_linked_with_duration: bool = False


def default_settings_file_path() -> Path:
    config_home_directory = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home_directory / "tab" / "settings.json"


def load_settings(settings_file_path: Path | None = None) -> PomodoroSettings:
    """Return defaults if the file doesn't exist yet; raise if it exists but is invalid."""
    saved_settings = load_json_model(
        settings_file_path or default_settings_file_path(), PomodoroSettings
    )
    return saved_settings or PomodoroSettings()


def save_settings(settings: PomodoroSettings, settings_file_path: Path | None = None) -> None:
    save_json_model_atomically(settings, settings_file_path or default_settings_file_path())
