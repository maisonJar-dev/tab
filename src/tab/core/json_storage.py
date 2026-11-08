import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


def load_json_model(json_file_path: Path, model_type: type[ModelType]) -> ModelType | None:
    """Return None if the file doesn't exist yet; raise if it exists but is invalid."""
    if not json_file_path.exists():
        return None
    return model_type.model_validate_json(json_file_path.read_text(encoding="utf-8"))


def save_json_model_atomically(model: BaseModel, json_file_path: Path) -> None:
    """Write to a temp file then rename over the target, so a crash mid-write can't corrupt it."""
    json_file_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_file_path = json_file_path.with_suffix(json_file_path.suffix + ".tmp")
    temporary_file_path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    os.replace(temporary_file_path, json_file_path)
