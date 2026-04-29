from dataclasses import dataclass

import pytest

from focuslens.face_tracker import (
    FaceResult,
    MediaPipeFaceTracker,
    calculate_face_bbox_ratio,
    face_result_from_landmarks,
    face_result_from_mediapipe_result,
    landmarks_to_tuples,
)


@dataclass(frozen=True)
class FakeLandmark:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class FakeMediaPipeResult:
    face_landmarks: list[list[object]]


class FakeFrame:
    shape = (480, 640, 3)


class FakeImageFormat:
    SRGB = "SRGB"


class FakeMediaPipe:
    ImageFormat = FakeImageFormat

    @staticmethod
    def Image(*, image_format, data):
        return {"image_format": image_format, "data": data}


class FakeLandmarker:
    def detect_for_video(self, image, timestamp_ms):
        return FakeMediaPipeResult(face_landmarks=[])

    def close(self):
        pass


def test_face_result_from_landmarks_returns_not_detected_without_landmarks():
    assert face_result_from_landmarks([]) == FaceResult(detected=False)


def test_landmarks_to_tuples_accepts_mediapipe_like_objects():
    landmarks = [
        FakeLandmark(x=0.2, y=0.3, z=-0.01),
        FakeLandmark(x=0.7, y=0.8, z=0.02),
    ]

    assert landmarks_to_tuples(landmarks) == (
        (0.2, 0.3, -0.01),
        (0.7, 0.8, 0.02),
    )


def test_landmarks_to_tuples_accepts_plain_sequences():
    assert landmarks_to_tuples([(0.1, 0.2, 0.3)]) == ((0.1, 0.2, 0.3),)


def test_face_result_from_landmarks_calculates_bbox_ratio():
    landmarks = [
        FakeLandmark(x=0.2, y=0.3, z=0.0),
        FakeLandmark(x=0.7, y=0.9, z=0.0),
    ]

    result = face_result_from_landmarks(landmarks)

    assert result.detected is True
    assert result.landmarks == ((0.2, 0.3, 0.0), (0.7, 0.9, 0.0))
    assert round(result.face_bbox_ratio, 2) == 0.30


def test_face_result_from_landmarks_returns_not_detected_without_finite_bbox():
    landmarks = [
        FakeLandmark(x=float("nan"), y=float("nan"), z=0.0),
        FakeLandmark(x=float("inf"), y=float("inf"), z=0.0),
    ]

    assert face_result_from_landmarks(landmarks) == FaceResult(detected=False)


def test_calculate_face_bbox_ratio_clamps_points_to_frame_bounds():
    landmarks = [(-0.5, 0.25, 0.0), (1.5, 0.75, 0.0)]

    assert calculate_face_bbox_ratio(landmarks) == 0.5


def test_calculate_face_bbox_ratio_ignores_non_finite_points():
    landmarks = [(float("nan"), 0.0, 0.0), (0.2, 0.3, 0.0), (0.7, 0.8, 0.0)]

    assert round(calculate_face_bbox_ratio(landmarks), 2) == 0.25


def test_face_result_from_mediapipe_result_uses_largest_detected_face():
    small_face = [
        FakeLandmark(x=0.1, y=0.1, z=0.0),
        FakeLandmark(x=0.2, y=0.2, z=0.0),
    ]
    large_face = [
        FakeLandmark(x=0.2, y=0.2, z=0.0),
        FakeLandmark(x=0.8, y=0.9, z=0.0),
    ]
    result = FakeMediaPipeResult(face_landmarks=[small_face, large_face])

    face_result = face_result_from_mediapipe_result(result)

    assert face_result.detected is True
    assert round(face_result.face_bbox_ratio, 2) == 0.42


def test_face_result_from_mediapipe_result_handles_no_faces():
    result = FakeMediaPipeResult(face_landmarks=[])

    assert face_result_from_mediapipe_result(result) == FaceResult(detected=False)


def test_mediapipe_tracker_requires_existing_local_model(tmp_path):
    with pytest.raises(FileNotFoundError, match="Face Landmarker model not found"):
        MediaPipeFaceTracker(tmp_path / "missing.task")


def test_mediapipe_tracker_rejects_invalid_confidence(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    model_path.write_bytes(b"placeholder")

    with pytest.raises(
        ValueError,
        match="min_face_detection_confidence must be between 0 and 1",
    ):
        MediaPipeFaceTracker(model_path, min_face_detection_confidence=2)


def test_mediapipe_tracker_rejects_invalid_num_faces(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    model_path.write_bytes(b"placeholder")

    with pytest.raises(ValueError, match="num_faces must be greater than zero"):
        MediaPipeFaceTracker(model_path, num_faces=0)


def test_mediapipe_tracker_rejects_invalid_frame_shape(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    model_path.write_bytes(b"placeholder")
    tracker = MediaPipeFaceTracker(model_path)

    with pytest.raises(ValueError, match="frame_rgb must be an RGB image array"):
        tracker.track(object(), 0)


def test_mediapipe_tracker_requires_increasing_timestamps(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    model_path.write_bytes(b"placeholder")
    tracker = MediaPipeFaceTracker(model_path)
    tracker._mp = FakeMediaPipe
    tracker._landmarker = FakeLandmarker()

    assert tracker.track(FakeFrame(), 1000) == FaceResult(detected=False)

    with pytest.raises(ValueError, match="timestamp_ms must increase between frames"):
        tracker.track(FakeFrame(), 900)


def test_landmarks_to_tuples_rejects_short_sequences():
    with pytest.raises(ValueError, match="landmark sequences must contain"):
        landmarks_to_tuples([(0.1, 0.2)])


def test_landmarks_to_tuples_rejects_invalid_objects():
    with pytest.raises(TypeError, match="landmark must expose x, y, and z"):
        landmarks_to_tuples([object()])
