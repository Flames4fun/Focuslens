from focuslens import (
    AttentionAnalysis,
    Camera,
    CameraFrame,
    FaceObservation,
    FaceResult,
    FaceTracker,
    WebcamCamera,
    analyze_attention,
)
from focuslens.attention import AttentionAnalysis as AttentionAnalysisFromModule
from focuslens.camera import Camera as CameraFromModule
from focuslens.camera import CameraFrame as CameraFrameFromModule
from focuslens.camera import WebcamCamera as WebcamCameraFromModule
from focuslens.face_tracker import FaceResult as FaceResultFromModule
from focuslens.face_tracker import FaceTracker as FaceTrackerFromModule


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
