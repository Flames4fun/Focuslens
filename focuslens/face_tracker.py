"""Face landmark tracking boundary for FocusLens.

This module keeps MediaPipe-specific code away from the attention classifier.
It processes frames in memory only: no image storage, video recording, network
access, or model downloads happen here.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from importlib import import_module
from math import isfinite
from pathlib import Path
from typing import Any, Protocol

from focuslens.attention import Landmark


@dataclass(frozen=True, slots=True)
class FaceResult:
    """Face tracker output consumed by the attention classifier."""

    detected: bool
    landmarks: tuple[Landmark, ...] = ()
    face_bbox_ratio: float | None = None


class FaceTracker(Protocol):
    """Interface implemented by concrete face trackers."""

    def track(self, frame_rgb: object, timestamp_ms: int) -> FaceResult:
        """Return the current face result for an RGB frame."""
        ...


class MediaPipeUnavailableError(RuntimeError):
    """Raised when MediaPipe is required but is not installed."""


class MediaPipeFaceTracker:
    """Synchronous MediaPipe Face Landmarker adapter for webcam video frames."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        num_faces: int = 1,
        min_face_detection_confidence: float = 0.5,
        min_face_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Face Landmarker model not found: {self.model_path}"
            )

        if num_faces <= 0:
            raise ValueError("num_faces must be greater than zero")

        self.num_faces = num_faces
        self.min_face_detection_confidence = _validate_confidence(
            "min_face_detection_confidence",
            min_face_detection_confidence,
        )
        self.min_face_presence_confidence = _validate_confidence(
            "min_face_presence_confidence",
            min_face_presence_confidence,
        )
        self.min_tracking_confidence = _validate_confidence(
            "min_tracking_confidence",
            min_tracking_confidence,
        )
        self._mp: Any | None = None
        self._landmarker: Any | None = None
        self._last_timestamp_ms: int | None = None

    def __enter__(self) -> MediaPipeFaceTracker:
        """Open the local MediaPipe model for use in a context manager."""

        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        """Release MediaPipe resources when leaving a context manager."""

        self.close()

    def open(self) -> None:
        """Load the local Face Landmarker model if it is not already open."""

        if self._landmarker is not None:
            return

        mp = _load_mediapipe()

        base_options = mp.tasks.BaseOptions(model_asset_path=str(self.model_path))
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=self.num_faces,
            min_face_detection_confidence=self.min_face_detection_confidence,
            min_face_presence_confidence=self.min_face_presence_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self._mp = mp

    def close(self) -> None:
        """Release the MediaPipe task instance."""

        if self._landmarker is None:
            return

        self._landmarker.close()
        self._landmarker = None
        self._mp = None
        self._last_timestamp_ms = None

    def track(self, frame_rgb: object, timestamp_ms: int) -> FaceResult:
        """Run face landmark detection on an RGB frame.

        OpenCV frames should be converted from BGR to RGB before calling this
        method. The frame is passed to MediaPipe in memory and is not retained.
        """

        _validate_frame_shape(frame_rgb)

        if timestamp_ms < 0:
            raise ValueError("timestamp_ms must be non-negative")

        if (
            self._last_timestamp_ms is not None
            and timestamp_ms <= self._last_timestamp_ms
        ):
            raise ValueError("timestamp_ms must increase between frames")

        self.open()
        if self._mp is None or self._landmarker is None:
            raise RuntimeError("MediaPipeFaceTracker failed to initialize")

        mp_image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB,
            data=frame_rgb,
        )
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        self._last_timestamp_ms = timestamp_ms
        return face_result_from_mediapipe_result(result)


def face_result_from_mediapipe_result(result: object) -> FaceResult:
    """Build a FocusLens face result from a MediaPipe task result."""

    faces = getattr(result, "face_landmarks", None)
    if not faces:
        return FaceResult(detected=False)

    candidates = [
        face_result_from_landmarks(face_landmarks) for face_landmarks in faces
    ]
    return max(candidates, key=lambda face: face.face_bbox_ratio or 0.0)


def face_result_from_landmarks(landmarks: Sequence[object] | None) -> FaceResult:
    """Build a face result from a single face's normalized landmarks."""

    if not landmarks:
        return FaceResult(detected=False)

    normalized_landmarks = landmarks_to_tuples(landmarks)
    if not normalized_landmarks:
        return FaceResult(detected=False)

    face_bbox_ratio = calculate_face_bbox_ratio(normalized_landmarks)
    if face_bbox_ratio is None:
        return FaceResult(detected=False)

    return FaceResult(
        detected=True,
        landmarks=normalized_landmarks,
        face_bbox_ratio=face_bbox_ratio,
    )


def landmarks_to_tuples(landmarks: Sequence[object]) -> tuple[Landmark, ...]:
    """Convert MediaPipe landmark objects into plain immutable tuples."""

    return tuple(_landmark_to_tuple(landmark) for landmark in landmarks)


def calculate_face_bbox_ratio(landmarks: Sequence[Landmark]) -> float | None:
    """Return normalized bounding-box area for the visible face landmarks."""

    points = tuple(_finite_clamped_points(landmarks))
    if not points:
        return None

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    return width * height


def _landmark_to_tuple(landmark: object) -> Landmark:
    if isinstance(landmark, Sequence) and not isinstance(landmark, (str, bytes)):
        if len(landmark) < 3:
            raise ValueError("landmark sequences must contain x, y, and z")
        return (float(landmark[0]), float(landmark[1]), float(landmark[2]))

    try:
        return (
            float(landmark.x),
            float(landmark.y),
            float(landmark.z),
        )
    except AttributeError as exc:
        raise TypeError("landmark must expose x, y, and z values") from exc


def _load_mediapipe() -> Any:
    try:
        return import_module("mediapipe")
    except ImportError as exc:
        raise MediaPipeUnavailableError(
            "MediaPipe is required to use MediaPipeFaceTracker. "
            'Install it with: python -m pip install "mediapipe>=0.10"'
        ) from exc


def _finite_clamped_points(
    landmarks: Sequence[Landmark],
) -> Iterator[tuple[float, float]]:
    for x, y, _ in landmarks:
        if isfinite(x) and isfinite(y):
            yield (_clamp01(x), _clamp01(y))


def _clamp01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _validate_confidence(name: str, value: float) -> float:
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")

    return value


def _validate_frame_shape(frame_rgb: object) -> None:
    shape = getattr(frame_rgb, "shape", None)
    if shape is None or len(shape) != 3 or shape[2] != 3:
        raise ValueError(
            "frame_rgb must be an RGB image array shaped (height, width, 3)"
        )


__all__ = [
    "FaceResult",
    "FaceTracker",
    "MediaPipeFaceTracker",
    "MediaPipeUnavailableError",
    "calculate_face_bbox_ratio",
    "face_result_from_landmarks",
    "face_result_from_mediapipe_result",
    "landmarks_to_tuples",
]
