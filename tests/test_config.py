import pytest

from focuslens.config import FocusLensConfig


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"min_face_ratio": -1}, "min_face_ratio must be between 0 and 1"),
        ({"min_face_ratio": True}, "min_face_ratio must be a number"),
        ({"min_face_ratio": "0.1"}, "min_face_ratio must be a number"),
        ({"min_face_ratio": float("inf")}, "min_face_ratio must be finite"),
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
        ({"window_title": ""}, "window_title must not be empty"),
        ({"window_title": None}, "window_title must be a string"),
        ({"save_dir": None}, "save_dir must be a path-like value"),
        ({"save_dir": " "}, "save_dir must not be empty"),
        ({"camera_index": True}, "camera_index must be a non-negative integer"),
        ({"camera_index": -1}, "camera_index must be non-negative"),
    ],
)
def test_config_rejects_invalid_values(kwargs, message):
    with pytest.raises(ValueError, match=message):
        FocusLensConfig(**kwargs)


def test_config_accepts_valid_boundary_ratios():
    config = FocusLensConfig(min_face_ratio=0, max_face_ratio=1)

    assert config.min_face_ratio == 0.0
    assert config.max_face_ratio == 1.0


def test_config_normalizes_numeric_values_and_save_dir(tmp_path):
    config = FocusLensConfig(
        min_face_ratio=0,
        max_face_ratio=1,
        looking_away_threshold=1,
        min_event_duration_seconds=2,
        event_cooldown_seconds=3,
        save_dir=tmp_path,
    )

    assert config.looking_away_threshold == 1.0
    assert config.min_event_duration_seconds == 2.0
    assert config.event_cooldown_seconds == 3.0
    assert config.save_dir == tmp_path
