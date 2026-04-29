"""Central configuration values for FocusLens."""

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_SAVE_DIR = Path("sessions")


@dataclass(frozen=True, slots=True)
class FocusLensConfig:
    """Runtime thresholds used by the camera, attention, and session layers."""

    min_face_ratio: float = 0.05
    max_face_ratio: float = 0.45
    looking_away_threshold: float = 0.16
    min_event_duration_seconds: float = 1.0
    event_cooldown_seconds: float = 2.0
    save_dir: Path = field(default_factory=lambda: DEFAULT_SAVE_DIR)
    camera_index: int = 0
    window_title: str = "FocusLens"

    def __post_init__(self) -> None:
        """Reject configuration values that cannot produce useful thresholds."""

        if not 0 <= self.min_face_ratio <= 1:
            raise ValueError("min_face_ratio must be between 0 and 1")

        if not 0 <= self.max_face_ratio <= 1:
            raise ValueError("max_face_ratio must be between 0 and 1")

        if self.min_face_ratio >= self.max_face_ratio:
            raise ValueError("min_face_ratio must be lower than max_face_ratio")

        if self.looking_away_threshold < 0:
            raise ValueError("looking_away_threshold must be non-negative")

        if self.min_event_duration_seconds < 0:
            raise ValueError("min_event_duration_seconds must be non-negative")

        if self.event_cooldown_seconds < 0:
            raise ValueError("event_cooldown_seconds must be non-negative")

        if self.camera_index < 0:
            raise ValueError("camera_index must be non-negative")


DEFAULT_CONFIG = FocusLensConfig()
