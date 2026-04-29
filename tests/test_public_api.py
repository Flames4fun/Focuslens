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
    WebcamCamera,
    analyze_attention,
    build_overlay_lines,
    render_overlay,
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
