import pytest

from focuslens.config import FocusLensConfig


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"min_face_ratio": -1}, "min_face_ratio must be between 0 and 1"),
        ({"max_face_ratio": 999}, "max_face_ratio must be between 0 and 1"),
        (
            {"min_face_ratio": 0.8, "max_face_ratio": 0.2},
            "min_face_ratio must be lower than max_face_ratio",
        ),
        (
            {"looking_away_threshold": -0.5},
            "looking_away_threshold must be non-negative",
        ),
        (
            {"min_event_duration_seconds": -1},
            "min_event_duration_seconds must be non-negative",
        ),
        (
            {"event_cooldown_seconds": -1},
            "event_cooldown_seconds must be non-negative",
        ),
        ({"camera_index": -1}, "camera_index must be non-negative"),
    ],
)
def test_config_rejects_invalid_values(kwargs, message):
    with pytest.raises(ValueError, match=message):
        FocusLensConfig(**kwargs)


def test_config_accepts_valid_boundary_ratios():
    config = FocusLensConfig(min_face_ratio=0, max_face_ratio=1)

    assert config.min_face_ratio == 0
    assert config.max_face_ratio == 1
