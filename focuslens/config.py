"""Central configuration values for FocusLens."""

from dataclasses import dataclass, field
from math import isfinite
from os import PathLike
from pathlib import Path
from typing import Any

DEFAULT_SAVE_DIR = Path("sessions")


@dataclass(frozen=True, slots=True)
class FocusLensConfig:
    """Runtime thresholds used by the camera, attention, and session layers."""

    min_face_ratio: float = 0.05
    max_face_ratio: float = 0.45
    looking_away_threshold: float = 0.28
    min_event_duration_seconds: float = 1.0
    event_cooldown_seconds: float = 2.0
    save_dir: Path = field(default_factory=lambda: DEFAULT_SAVE_DIR)
    camera_index: int = 0
    window_title: str = "FocusLens"

    def __post_init__(self) -> None:
        """Reject configuration values that cannot produce useful thresholds."""

        min_face_ratio = _validate_number("min_face_ratio", self.min_face_ratio)
        max_face_ratio = _validate_number("max_face_ratio", self.max_face_ratio)
        looking_away_threshold = _validate_number(
            "looking_away_threshold",
            self.looking_away_threshold,
        )
        min_event_duration_seconds = _validate_number(
            "min_event_duration_seconds",
            self.min_event_duration_seconds,
        )
        event_cooldown_seconds = _validate_number(
            "event_cooldown_seconds",
            self.event_cooldown_seconds,
        )
        save_dir = _validate_save_dir(self.save_dir)
        camera_index = _validate_non_negative_int("camera_index", self.camera_index)
        window_title = _validate_non_empty_string("window_title", self.window_title)

        object.__setattr__(self, "min_face_ratio", min_face_ratio)
        object.__setattr__(self, "max_face_ratio", max_face_ratio)
        object.__setattr__(self, "looking_away_threshold", looking_away_threshold)
        object.__setattr__(
            self,
            "min_event_duration_seconds",
            min_event_duration_seconds,
        )
        object.__setattr__(
            self,
            "event_cooldown_seconds",
            event_cooldown_seconds,
        )
        object.__setattr__(self, "save_dir", save_dir)
        object.__setattr__(self, "camera_index", camera_index)
        object.__setattr__(self, "window_title", window_title)

        if not 0 <= min_face_ratio <= 1:
            raise ValueError("min_face_ratio must be between 0 and 1")

        if not 0 <= max_face_ratio <= 1:
            raise ValueError("max_face_ratio must be between 0 and 1")

        if min_face_ratio >= max_face_ratio:
            raise ValueError("min_face_ratio must be lower than max_face_ratio")

        if looking_away_threshold < 0:
            raise ValueError("looking_away_threshold must be non-negative")

        if min_event_duration_seconds < 0:
            raise ValueError("min_event_duration_seconds must be non-negative")

        if event_cooldown_seconds < 0:
            raise ValueError("event_cooldown_seconds must be non-negative")


def _validate_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a number")

    parsed = float(value)
    if not isfinite(parsed):
        raise ValueError(f"{name} must be finite")

    return parsed


def _validate_non_negative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a non-negative integer")

    if value < 0:
        raise ValueError(f"{name} must be non-negative")

    return value


def _validate_non_empty_string(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")

    if not value.strip():
        raise ValueError(f"{name} must not be empty")

    return value


def _validate_save_dir(value: Any) -> Path:
    if not isinstance(value, str | PathLike):
        raise ValueError("save_dir must be a path-like value")

    if isinstance(value, str) and not value.strip():
        raise ValueError("save_dir must not be empty")

    return Path(value).expanduser()


DEFAULT_CONFIG = FocusLensConfig()
