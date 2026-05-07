"""OpenCV webcam boundary for FocusLens.

This module owns camera access and frame color conversion. Frames are processed
in memory only: no images or video are stored here.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from importlib import import_module
from math import isfinite
from time import perf_counter
from typing import Any, Protocol

CAMERA_BACKENDS = {
    "auto": None,
    "any": "CAP_ANY",
    "dshow": "CAP_DSHOW",
    "msmf": "CAP_MSMF",
}


@dataclass(frozen=True, slots=True)
class CameraFrame:
    """In-memory webcam frame only. Do not persist, serialize, or log this."""

    bgr: object
    rgb: object
    timestamp_ms: int


class Camera(Protocol):
    """Interface implemented by concrete frame sources."""

    def read(self) -> CameraFrame:
        """Return the next camera frame."""
        ...


class OpenCVUnavailableError(RuntimeError):
    """Raised when OpenCV is required but is not installed."""


class CameraOpenError(RuntimeError):
    """Raised when the webcam cannot be opened."""


class CameraReadError(RuntimeError):
    """Raised when a frame cannot be read from the webcam."""


class WebcamCamera:
    """Synchronous OpenCV webcam adapter."""

    def __init__(
        self,
        camera_index: int = 0,
        *,
        backend: str = "auto",
        frame_width: int | None = None,
        frame_height: int | None = None,
        fps: float | None = None,
        fourcc: str | None = None,
        cv2_module: Any | None = None,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        if camera_index < 0:
            raise ValueError("camera_index must be non-negative")

        self.backend = _validate_backend(backend)
        self.frame_width = _validate_optional_positive_int(
            "frame_width",
            frame_width,
        )
        self.frame_height = _validate_optional_positive_int(
            "frame_height",
            frame_height,
        )
        self.fps = _validate_optional_positive_number("fps", fps)
        self.fourcc = _validate_fourcc(fourcc)
        self.camera_index = camera_index
        self._cv2_module = cv2_module
        self._clock = clock
        self._cv2: Any | None = None
        self._capture: Any | None = None
        self._started_at: float | None = None
        self._last_timestamp_ms: int | None = None

    def __enter__(self) -> WebcamCamera:
        """Open the webcam for use in a context manager."""

        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        """Release the webcam when leaving a context manager."""

        self.close()

    def open(self) -> None:
        """Open the configured webcam if it is not already open."""

        if self._capture is not None:
            return

        cv2 = self._cv2_module or _load_cv2()
        backend_code = _backend_code(cv2, self.backend)
        if backend_code is None:
            capture = cv2.VideoCapture(self.camera_index)
        else:
            capture = cv2.VideoCapture(self.camera_index, backend_code)

        if not capture.isOpened():
            capture.release()
            raise CameraOpenError(f"Could not open webcam at index {self.camera_index}")

        _apply_capture_options(
            capture,
            cv2,
            frame_width=self.frame_width,
            frame_height=self.frame_height,
            fps=self.fps,
            fourcc=self.fourcc,
        )

        self._cv2 = cv2
        self._capture = capture
        self._started_at = self._clock()
        self._last_timestamp_ms = None

    def close(self) -> None:
        """Release the webcam if it is open."""

        if self._capture is None:
            return

        self._capture.release()
        self._capture = None
        self._cv2 = None
        self._started_at = None
        self._last_timestamp_ms = None

    def read(self) -> CameraFrame:
        """Read one BGR frame and return it with an RGB copy."""

        self.open()
        if self._capture is None or self._cv2 is None:
            raise RuntimeError("WebcamCamera failed to initialize")

        ok, frame_bgr = self._capture.read()
        if not ok or frame_bgr is None:
            raise CameraReadError("Could not read frame from webcam")

        frame_rgb = bgr_to_rgb(frame_bgr, cv2_module=self._cv2)
        return CameraFrame(
            bgr=frame_bgr,
            rgb=frame_rgb,
            timestamp_ms=self._next_timestamp_ms(),
        )

    def frames(self, *, limit: int | None = None) -> Iterator[CameraFrame]:
        """Yield camera frames.

        Without a limit this generator is intentionally infinite and should be
        stopped by caller-controlled input such as a quit key or signal.
        """

        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")

        count = 0
        while limit is None or count < limit:
            yield self.read()
            count += 1

    def _next_timestamp_ms(self) -> int:
        started_at = self._started_at
        if started_at is None:
            started_at = self._clock()
            self._started_at = started_at

        timestamp_ms = max(0, int((self._clock() - started_at) * 1000))
        if (
            self._last_timestamp_ms is not None
            and timestamp_ms <= self._last_timestamp_ms
        ):
            timestamp_ms = self._last_timestamp_ms + 1

        self._last_timestamp_ms = timestamp_ms
        return timestamp_ms


def bgr_to_rgb(frame_bgr: object, *, cv2_module: Any | None = None) -> object:
    """Convert an OpenCV BGR frame into RGB for MediaPipe."""

    _validate_frame_shape(frame_bgr, "frame_bgr")
    cv2 = cv2_module or _load_cv2()
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)


def _validate_backend(backend: str) -> str:
    if not isinstance(backend, str):
        raise ValueError("backend must be a string")

    normalized = backend.strip().lower()
    if normalized not in CAMERA_BACKENDS:
        choices = ", ".join(sorted(CAMERA_BACKENDS))
        raise ValueError(f"backend must be one of: {choices}")

    return normalized


def _validate_optional_positive_int(name: str, value: int | None) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a positive integer")

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")

    return value


def _validate_optional_positive_number(name: str, value: float | None) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a positive number")

    parsed = float(value)
    if not isfinite(parsed) or parsed <= 0:
        raise ValueError(f"{name} must be a positive finite number")

    return parsed


def _validate_fourcc(fourcc: str | None) -> str | None:
    if fourcc is None:
        return None

    if not isinstance(fourcc, str):
        raise ValueError("fourcc must be a string")

    normalized = fourcc.strip().upper()
    if len(normalized) != 4:
        raise ValueError("fourcc must contain exactly four characters")

    if not normalized.isascii() or not normalized.isprintable():
        raise ValueError("fourcc must contain printable ASCII characters")

    return normalized


def _backend_code(cv2: Any, backend: str) -> int | None:
    attribute_name = CAMERA_BACKENDS[backend]
    if attribute_name is None:
        return None

    try:
        return int(getattr(cv2, attribute_name))
    except AttributeError as exc:
        raise ValueError(
            f"OpenCV does not expose the requested camera backend: {backend}"
        ) from exc


def _apply_capture_options(
    capture: Any,
    cv2: Any,
    *,
    frame_width: int | None,
    frame_height: int | None,
    fps: float | None,
    fourcc: str | None,
) -> None:
    if fourcc is not None:
        _set_capture_property(
            capture,
            cv2,
            "CAP_PROP_FOURCC",
            cv2.VideoWriter_fourcc(*fourcc),
        )

    if frame_width is not None:
        _set_capture_property(capture, cv2, "CAP_PROP_FRAME_WIDTH", frame_width)

    if frame_height is not None:
        _set_capture_property(capture, cv2, "CAP_PROP_FRAME_HEIGHT", frame_height)

    if fps is not None:
        _set_capture_property(capture, cv2, "CAP_PROP_FPS", fps)


def _set_capture_property(
    capture: Any,
    cv2: Any,
    property_name: str,
    value: float,
) -> None:
    property_id = getattr(cv2, property_name, None)
    set_property = getattr(capture, "set", None)
    if property_id is None or set_property is None:
        return

    set_property(property_id, value)


def _load_cv2() -> Any:
    try:
        return import_module("cv2")
    except ImportError as exc:
        raise OpenCVUnavailableError(
            "OpenCV is required to use WebcamCamera. "
            'Install it with: python -m pip install "opencv-python>=4.9"'
        ) from exc


def _validate_frame_shape(frame: object, name: str) -> None:
    shape = getattr(frame, "shape", None)
    if shape is None or len(shape) != 3 or shape[2] != 3:
        raise ValueError(f"{name} must be an image array shaped (height, width, 3)")


__all__ = [
    "Camera",
    "CameraFrame",
    "CameraOpenError",
    "CameraReadError",
    "OpenCVUnavailableError",
    "WebcamCamera",
    "bgr_to_rgb",
]
