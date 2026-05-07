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
from focuslens.session import SessionSummary, SessionTracker
from focuslens.storage import (
    SessionSaveResult,
    append_session_csv,
    ensure_save_dir,
    save_session_summary,
    write_session_json,
)

__version__ = "0.2.0"

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
    "SessionSummary",
    "SessionTracker",
    "SessionSaveResult",
    "WebcamCamera",
    "__version__",
    "analyze_attention",
    "append_session_csv",
    "build_overlay_lines",
    "classify_attention",
    "ensure_save_dir",
    "render_overlay",
    "save_session_summary",
    "write_session_json",
]
