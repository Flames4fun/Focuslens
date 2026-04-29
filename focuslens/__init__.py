"""Top-level package exports for FocusLens."""

from focuslens.attention import (
    AttentionAnalysis,
    AttentionState,
    FaceObservation,
    analyze_attention,
    classify_attention,
)
from focuslens.camera import Camera, CameraFrame, WebcamCamera
from focuslens.config import DEFAULT_CONFIG, FocusLensConfig
from focuslens.face_tracker import FaceResult, FaceTracker
from focuslens.overlay import (
    OpenCVOverlayRenderer,
    OverlayMetrics,
    OverlayRenderer,
    OverlayTheme,
    build_overlay_lines,
    render_overlay,
)

__version__ = "0.1.0"

__all__ = [
    "AttentionAnalysis",
    "AttentionState",
    "Camera",
    "CameraFrame",
    "DEFAULT_CONFIG",
    "FaceObservation",
    "FaceResult",
    "FaceTracker",
    "FocusLensConfig",
    "OpenCVOverlayRenderer",
    "OverlayMetrics",
    "OverlayRenderer",
    "OverlayTheme",
    "WebcamCamera",
    "__version__",
    "analyze_attention",
    "build_overlay_lines",
    "classify_attention",
    "render_overlay",
]
