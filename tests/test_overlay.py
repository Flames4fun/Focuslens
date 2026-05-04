import pytest

from focuslens.attention import AttentionAnalysis, AttentionState
from focuslens.overlay import (
    OpenCVOverlayRenderer,
    OverlayMetrics,
    OverlayTheme,
    build_overlay_lines,
    format_duration,
    render_overlay,
)


class FakeFrame:
    shape = (480, 640, 3)

    def __init__(self):
        self.copy_count = 0

    def copy(self):
        self.copy_count += 1
        return FakeFrame()


class InvalidFrame:
    shape = (480, 640)


class FakeCv2:
    FILLED = -1
    FONT_HERSHEY_SIMPLEX = "FONT_HERSHEY_SIMPLEX"
    LINE_AA = "LINE_AA"

    def __init__(self):
        self.rectangles = []
        self.texts = []
        self.blends = []

    def getTextSize(self, text, font_face, font_scale, thickness):
        return ((len(text) * 9, 18), 4)

    def rectangle(self, frame, start, end, color, thickness):
        self.rectangles.append(
            {
                "frame": frame,
                "start": start,
                "end": end,
                "color": color,
                "thickness": thickness,
            }
        )

    def addWeighted(self, overlay, alpha, frame, beta, gamma, output):
        self.blends.append(
            {
                "overlay": overlay,
                "alpha": alpha,
                "frame": frame,
                "beta": beta,
                "gamma": gamma,
                "output": output,
            }
        )

    def putText(
        self,
        frame,
        text,
        origin,
        font_face,
        font_scale,
        color,
        thickness,
        line_type,
    ):
        self.texts.append(
            {
                "frame": frame,
                "text": text,
                "origin": origin,
                "font_face": font_face,
                "font_scale": font_scale,
                "color": color,
                "thickness": thickness,
                "line_type": line_type,
            }
        )


def test_format_duration_uses_hours_minutes_and_seconds():
    assert format_duration(3661.9) == "01:01:01"


def test_overlay_metrics_rejects_negative_or_non_finite_values():
    with pytest.raises(ValueError, match="elapsed_seconds must be"):
        OverlayMetrics(elapsed_seconds=-1)

    with pytest.raises(ValueError, match="focused_seconds must be"):
        OverlayMetrics(focused_seconds=float("nan"))

    with pytest.raises(ValueError, match="looking_away_events must be"):
        OverlayMetrics(looking_away_events=-1)

    with pytest.raises(ValueError, match="focus_score must be between 0 and 100"):
        OverlayMetrics(focus_score=101)

    with pytest.raises(ValueError, match="presence_score must be between 0 and 100"):
        OverlayMetrics(presence_score=-1)


def test_overlay_theme_rejects_invalid_visual_settings():
    with pytest.raises(ValueError, match="background_alpha must be between 0 and 1"):
        OverlayTheme(background_alpha=2)

    with pytest.raises(ValueError, match="panel_fill components must be"):
        OverlayTheme(panel_fill=(0, 0, 300))

    with pytest.raises(ValueError, match="panel_fill components must be integers"):
        OverlayTheme(panel_fill=("1", 2, 3))

    with pytest.raises(ValueError, match="panel_fill components must be integers"):
        OverlayTheme(panel_fill=(1, 2.8, 3))

    with pytest.raises(ValueError, match="panel_fill components must be integers"):
        OverlayTheme(panel_fill=(True, 2, 3))


def test_build_overlay_lines_uses_only_safe_derived_values():
    analysis = AttentionAnalysis(
        state=AttentionState.LOOKING_AWAY,
        face_bbox_ratio=0.25,
        head_offset=0.33,
        reason="internal_reason_should_not_be_displayed",
    )
    metrics = OverlayMetrics(
        elapsed_seconds=62,
        focused_seconds=55,
        away_seconds=3,
        looking_away_events=2,
        focus_score=89.4,
        presence_score=95.1,
    )

    lines = build_overlay_lines(analysis, metrics)

    assert lines == (
        "Status: Looking away",
        "Session: 00:01:02",
        "Focused: 00:00:55",
        "Away: 00:00:03",
        "Looking away: 2",
        "Focus score: 89%",
        "Presence: 95%",
    )
    rendered_text = " ".join(lines)
    assert "internal_reason_should_not_be_displayed" not in rendered_text
    assert "0.25" not in rendered_text
    assert "0.33" not in rendered_text


def test_renderer_draws_status_bar_panel_and_text_without_storing_frames():
    frame = FakeFrame()
    cv2 = FakeCv2()
    renderer = OpenCVOverlayRenderer(cv2_module=cv2)
    metrics = OverlayMetrics(
        elapsed_seconds=5,
        looking_away_events=1,
        focus_score=100,
    )

    result = renderer.render(frame, AttentionState.FOCUSED, metrics)

    assert result is frame
    assert frame.copy_count == 1
    assert len(cv2.blends) == 1
    assert len(cv2.rectangles) == 3
    assert [item["text"] for item in cv2.texts] == [
        "Status: Focused",
        "Session: 00:00:05",
        "Looking away: 1",
        "Focus score: 100%",
    ]


def test_renderer_rejects_invalid_frame_shape():
    renderer = OpenCVOverlayRenderer(cv2_module=FakeCv2())

    with pytest.raises(ValueError, match="frame_bgr must be an image array"):
        renderer.render(InvalidFrame(), AttentionState.AWAY)


def test_render_overlay_convenience_function_uses_injected_cv2():
    frame = FakeFrame()
    cv2 = FakeCv2()

    result = render_overlay(frame, AttentionState.PAUSED, cv2_module=cv2)

    assert result is frame
    assert cv2.texts[0]["text"] == "Status: Paused"
