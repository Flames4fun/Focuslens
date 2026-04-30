from focuslens import (
    AttentionAnalysis,
    Camera,
    CameraFrame,
    FaceObservation,
    FaceResult,
    FaceTracker,
    OpenCVOverlayRenderer,
    OverlayMetrics,
    OverlayRenderer,
    OverlayTheme,
    SessionSaveResult,
    SessionSummary,
    SessionTracker,
    WebcamCamera,
    analyze_attention,
    append_session_csv,
    build_overlay_lines,
    render_overlay,
    save_session_summary,
    write_session_json,
)
from focuslens.attention import AttentionAnalysis as AttentionAnalysisFromModule
from focuslens.camera import Camera as CameraFromModule
from focuslens.camera import CameraFrame as CameraFrameFromModule
from focuslens.camera import WebcamCamera as WebcamCameraFromModule
from focuslens.face_tracker import FaceResult as FaceResultFromModule
from focuslens.face_tracker import FaceTracker as FaceTrackerFromModule
from focuslens.overlay import OpenCVOverlayRenderer as OpenCVOverlayRendererFromModule
from focuslens.overlay import OverlayMetrics as OverlayMetricsFromModule
from focuslens.overlay import OverlayRenderer as OverlayRendererFromModule
from focuslens.overlay import OverlayTheme as OverlayThemeFromModule
from focuslens.overlay import build_overlay_lines as build_overlay_lines_from_module
from focuslens.overlay import render_overlay as render_overlay_from_module
from focuslens.session import SessionSummary as SessionSummaryFromModule
from focuslens.session import SessionTracker as SessionTrackerFromModule
from focuslens.storage import SessionSaveResult as SessionSaveResultFromModule
from focuslens.storage import append_session_csv as append_session_csv_from_module
from focuslens.storage import save_session_summary as save_session_summary_from_module
from focuslens.storage import write_session_json as write_session_json_from_module


def test_package_exports_detailed_attention_api():
    analysis = analyze_attention(FaceObservation(detected=False))

    assert AttentionAnalysis is AttentionAnalysisFromModule
    assert isinstance(analysis, AttentionAnalysis)


def test_package_exports_face_tracker_result():
    assert FaceResult is FaceResultFromModule
    assert FaceTracker is FaceTrackerFromModule


def test_package_exports_camera_api():
    assert Camera is CameraFromModule
    assert CameraFrame is CameraFrameFromModule
    assert WebcamCamera is WebcamCameraFromModule


def test_package_exports_overlay_api():
    assert OpenCVOverlayRenderer is OpenCVOverlayRendererFromModule
    assert OverlayMetrics is OverlayMetricsFromModule
    assert OverlayRenderer is OverlayRendererFromModule
    assert OverlayTheme is OverlayThemeFromModule
    assert build_overlay_lines is build_overlay_lines_from_module
    assert render_overlay is render_overlay_from_module


def test_package_exports_session_api():
    assert SessionSummary is SessionSummaryFromModule
    assert SessionTracker is SessionTrackerFromModule


def test_package_exports_storage_api():
    assert SessionSaveResult is SessionSaveResultFromModule
    assert append_session_csv is append_session_csv_from_module
    assert save_session_summary is save_session_summary_from_module
    assert write_session_json is write_session_json_from_module
