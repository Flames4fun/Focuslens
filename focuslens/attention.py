"""Pure attention-state classification for FocusLens."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from focuslens.config import DEFAULT_CONFIG, FocusLensConfig

Landmark = tuple[float, float, float]

NOSE_TIP_INDEX = 1
LEFT_EYE_OUTER_INDEX = 33
RIGHT_EYE_OUTER_INDEX = 263
MIN_EYE_SPAN = 1e-6
HEAD_OFFSET_TOLERANCE = 1e-9


class AttentionState(StrEnum):
    """Session states produced by the attention classifier."""

    FOCUSED = "focused"
    LOOKING_AWAY = "looking_away"
    AWAY = "away"
    TOO_CLOSE = "too_close"
    TOO_FAR = "too_far"
    PAUSED = "paused"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FaceObservation:
    """Small face-detection result consumed by the attention classifier."""

    detected: bool
    landmarks: Sequence[Landmark] = ()
    face_bbox_ratio: float | None = None


class FaceLike(Protocol):
    """Protocol for future face tracker results."""

    detected: bool
    landmarks: Sequence[Landmark]
    face_bbox_ratio: float | None


@dataclass(frozen=True, slots=True)
class AttentionAnalysis:
    """Detailed classification output for overlays, logs, and tests."""

    state: AttentionState
    face_bbox_ratio: float | None = None
    head_offset: float | None = None
    reason: str = ""


def classify_attention(
    face: FaceLike,
    config: FocusLensConfig = DEFAULT_CONFIG,
    *,
    paused: bool = False,
) -> AttentionState:
    """Return only the current attention state for a detected face result."""

    return analyze_attention(face, config, paused=paused).state


def analyze_attention(
    face: FaceLike,
    config: FocusLensConfig = DEFAULT_CONFIG,
    *,
    paused: bool = False,
) -> AttentionAnalysis:
    """Classify a face observation into one of the FocusLens attention states."""

    if paused:
        return AttentionAnalysis(state=AttentionState.PAUSED, reason="manual_pause")

    if not face.detected:
        return AttentionAnalysis(state=AttentionState.AWAY, reason="face_not_detected")

    face_bbox_ratio = face.face_bbox_ratio

    if face_bbox_ratio is not None:
        if face_bbox_ratio < config.min_face_ratio:
            return AttentionAnalysis(
                state=AttentionState.TOO_FAR,
                face_bbox_ratio=face_bbox_ratio,
                reason="face_too_small",
            )

        if face_bbox_ratio > config.max_face_ratio:
            return AttentionAnalysis(
                state=AttentionState.TOO_CLOSE,
                face_bbox_ratio=face_bbox_ratio,
                reason="face_too_large",
            )

    head_offset = calculate_head_offset(face.landmarks)

    if head_offset is None:
        return AttentionAnalysis(
            state=AttentionState.UNKNOWN,
            face_bbox_ratio=face_bbox_ratio,
            reason="orientation_landmarks_missing",
        )

    if head_offset > config.looking_away_threshold + HEAD_OFFSET_TOLERANCE:
        return AttentionAnalysis(
            state=AttentionState.LOOKING_AWAY,
            face_bbox_ratio=face_bbox_ratio,
            head_offset=head_offset,
            reason="head_offset_over_threshold",
        )

    return AttentionAnalysis(
        state=AttentionState.FOCUSED,
        face_bbox_ratio=face_bbox_ratio,
        head_offset=head_offset,
        reason="within_thresholds",
    )


def calculate_head_offset(landmarks: Sequence[Landmark]) -> float | None:
    """Estimate horizontal head turn normalized by visible eye span."""

    if not has_orientation_landmarks(landmarks):
        return None

    nose_x = landmarks[NOSE_TIP_INDEX][0]
    left_eye_x = landmarks[LEFT_EYE_OUTER_INDEX][0]
    right_eye_x = landmarks[RIGHT_EYE_OUTER_INDEX][0]
    eye_center_x = (left_eye_x + right_eye_x) / 2
    eye_span = abs(right_eye_x - left_eye_x)

    if eye_span <= MIN_EYE_SPAN:
        return None

    return abs(nose_x - eye_center_x) / eye_span


def has_orientation_landmarks(landmarks: Sequence[Landmark]) -> bool:
    """Return whether the landmarks needed for basic head offset exist."""

    required_index = max(NOSE_TIP_INDEX, LEFT_EYE_OUTER_INDEX, RIGHT_EYE_OUTER_INDEX)
    return len(landmarks) > required_index


__all__ = [
    "AttentionAnalysis",
    "AttentionState",
    "FaceLike",
    "FaceObservation",
    "Landmark",
    "analyze_attention",
    "calculate_head_offset",
    "classify_attention",
    "has_orientation_landmarks",
]
