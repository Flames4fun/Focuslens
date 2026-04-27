"""Top-level package exports for FocusLens."""

from focuslens.attention import AttentionState, FaceObservation, classify_attention
from focuslens.config import DEFAULT_CONFIG, FocusLensConfig

__version__ = "0.1.0"

__all__ = [
    "AttentionState",
    "DEFAULT_CONFIG",
    "FaceObservation",
    "FocusLensConfig",
    "__version__",
    "classify_attention",
]
