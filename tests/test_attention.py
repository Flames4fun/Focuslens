from focuslens.attention import (
    LEFT_EYE_OUTER_INDEX,
    NOSE_TIP_INDEX,
    RIGHT_EYE_OUTER_INDEX,
    AttentionState,
    FaceObservation,
    analyze_attention,
    calculate_head_offset,
    classify_attention,
    has_orientation_landmarks,
)
from focuslens.config import FocusLensConfig


def make_landmarks(
    *,
    nose_x: float = 0.5,
    left_eye_x: float = 0.4,
    right_eye_x: float = 0.6,
):
    landmarks = [(0.0, 0.0, 0.0) for _ in range(RIGHT_EYE_OUTER_INDEX + 1)]
    landmarks[NOSE_TIP_INDEX] = (nose_x, 0.5, 0.0)
    landmarks[LEFT_EYE_OUTER_INDEX] = (left_eye_x, 0.4, 0.0)
    landmarks[RIGHT_EYE_OUTER_INDEX] = (right_eye_x, 0.4, 0.0)
    return landmarks


def test_classify_attention_returns_paused_when_manually_paused():
    face = FaceObservation(detected=False)

    assert classify_attention(face, paused=True) == AttentionState.PAUSED


def test_classify_attention_returns_away_when_face_is_not_detected():
    face = FaceObservation(detected=False)

    assert classify_attention(face) == AttentionState.AWAY


def test_classify_attention_returns_too_far_for_small_face_ratio():
    config = FocusLensConfig(min_face_ratio=0.10)
    face = FaceObservation(
        detected=True,
        landmarks=make_landmarks(),
        face_bbox_ratio=0.05,
    )

    assert classify_attention(face, config) == AttentionState.TOO_FAR


def test_face_ratio_equal_to_min_is_not_too_far():
    config = FocusLensConfig(min_face_ratio=0.10)
    face = FaceObservation(
        detected=True,
        landmarks=make_landmarks(),
        face_bbox_ratio=0.10,
    )

    assert classify_attention(face, config) == AttentionState.FOCUSED


def test_classify_attention_returns_too_close_for_large_face_ratio():
    config = FocusLensConfig(max_face_ratio=0.40)
    face = FaceObservation(
        detected=True,
        landmarks=make_landmarks(),
        face_bbox_ratio=0.50,
    )

    assert classify_attention(face, config) == AttentionState.TOO_CLOSE


def test_face_ratio_equal_to_max_is_not_too_close():
    config = FocusLensConfig(max_face_ratio=0.40)
    face = FaceObservation(
        detected=True,
        landmarks=make_landmarks(),
        face_bbox_ratio=0.40,
    )

    assert classify_attention(face, config) == AttentionState.FOCUSED


def test_classify_attention_returns_focused_for_centered_face():
    config = FocusLensConfig(looking_away_threshold=0.16)
    face = FaceObservation(
        detected=True,
        landmarks=make_landmarks(nose_x=0.5, left_eye_x=0.4, right_eye_x=0.6),
        face_bbox_ratio=0.20,
    )

    assert classify_attention(face, config) == AttentionState.FOCUSED


def test_head_offset_equal_to_threshold_is_focused():
    config = FocusLensConfig(looking_away_threshold=0.25)
    face = FaceObservation(
        detected=True,
        landmarks=make_landmarks(nose_x=0.75, left_eye_x=0.4, right_eye_x=0.6),
        face_bbox_ratio=0.20,
    )

    assert classify_attention(face, config) == AttentionState.FOCUSED


def test_classify_attention_returns_looking_away_for_shifted_head():
    config = FocusLensConfig(looking_away_threshold=0.16)
    face = FaceObservation(
        detected=True,
        landmarks=make_landmarks(nose_x=0.75, left_eye_x=0.4, right_eye_x=0.6),
        face_bbox_ratio=0.20,
    )

    assert classify_attention(face, config) == AttentionState.LOOKING_AWAY


def test_analyze_attention_includes_reason_and_measurements():
    config = FocusLensConfig(looking_away_threshold=0.16)
    face = FaceObservation(
        detected=True,
        landmarks=make_landmarks(nose_x=0.75, left_eye_x=0.4, right_eye_x=0.6),
        face_bbox_ratio=0.20,
    )

    analysis = analyze_attention(face, config)

    assert analysis.state == AttentionState.LOOKING_AWAY
    assert analysis.face_bbox_ratio == 0.20
    assert analysis.head_offset == 0.25
    assert analysis.reason == "head_offset_over_threshold"


def test_missing_orientation_landmarks_returns_unknown():
    face = FaceObservation(
        detected=True,
        landmarks=[],
        face_bbox_ratio=0.20,
    )

    analysis = analyze_attention(face)

    assert analysis.state == AttentionState.UNKNOWN
    assert analysis.head_offset is None
    assert analysis.reason == "orientation_landmarks_missing"


def test_calculate_head_offset_returns_absolute_nose_distance_from_eye_center():
    landmarks = make_landmarks(nose_x=0.35, left_eye_x=0.4, right_eye_x=0.6)

    assert round(calculate_head_offset(landmarks), 2) == 0.15


def test_calculate_head_offset_returns_none_without_required_landmarks():
    assert calculate_head_offset([]) is None


def test_has_orientation_landmarks_checks_required_indices():
    assert has_orientation_landmarks(make_landmarks()) is True
    incomplete_landmarks = [(0.0, 0.0, 0.0) for _ in range(RIGHT_EYE_OUTER_INDEX)]

    assert has_orientation_landmarks(incomplete_landmarks) is False
