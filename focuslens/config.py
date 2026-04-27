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


DEFAULT_CONFIG = FocusLensConfig()
