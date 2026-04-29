"""Top-level package exports for FocusLens."""

from focuslens.attention import (
    AttentionAnalysis,
    AttentionState,
    FaceObservation,
    analyze_attention,
    classify_attention,
)
from focuslens.config import DEFAULT_CONFIG, FocusLensConfig

__version__ = "0.1.0"

__all__ = [
    "AttentionAnalysis",
    "AttentionState",
    "DEFAULT_CONFIG",
    "FaceObservation",
    "FocusLensConfig",
    "__version__",
    "analyze_attention",
    "classify_attention",
]
