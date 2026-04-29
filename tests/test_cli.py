import argparse
import sys
from dataclasses import dataclass

import pytest

from focuslens.attention import AttentionState, FaceObservation
from focuslens.cli import (
    CliError,
    RunOptions,
    analyze_frame,
    build_parser,
    default_model_path,
    key_name_from_wait_key,
    non_negative_int,
    run_dashboard,
    run_session,
)


@dataclass(frozen=True)
class FakeFrame:
    bgr: object
    rgb: object
    timestamp_ms: int


class FakeClock:
    def __init__(self, *values):
        self.values = list(values)
        self.last_value = values[-1] if values else 0.0

    def __call__(self):
        if self.values:
            self.last_value = self.values.pop(0)
        return self.last_value


class FakeCv2:
    WINDOW_NORMAL = "WINDOW_NORMAL"

    def __init__(self, keys):
        self.keys = list(keys)
        self.named_windows = []
        self.imshow_calls = []
        self.wait_delays = []
        self.destroyed_windows = []

    def namedWindow(self, title, flag):
        self.named_windows.append((title, flag))

    def imshow(self, title, frame):
        self.imshow_calls.append((title, frame))

    def waitKey(self, delay):
        self.wait_delays.append(delay)
        if self.keys:
            return self.keys.pop(0)
        return ord("q")

    def destroyWindow(self, title):
        self.destroyed_windows.append(title)


class FakeCameraContext:
    def __init__(self, frames):
        self.frames = list(frames)
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *_):
        self.exited = True

    def read(self):
        return self.frames.pop(0)


class FakeTrackerContext:
    def __init__(self):
        self.calls = []
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *_):
        self.exited = True

    def track(self, frame_rgb, timestamp_ms):
        self.calls.append((frame_rgb, timestamp_ms))
        return FaceObservation(detected=False)


class FakeRenderer:
    def __init__(self):
        self.calls = []

    def render(self, frame_bgr, analysis, metrics=None):
        self.calls.append((frame_bgr, analysis, metrics))
        return f"rendered-{frame_bgr}"


def test_build_parser_parses_run_arguments(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    parser = build_parser()

    args = parser.parse_args(
        [
            "run",
            "--model-path",
            str(model_path),
            "--camera-index",
            "2",
            "--window-title",
            "FocusLens Test",
            "--max-frames",
            "5",
        ]
    )

    assert args.command == "run"
    assert args.model_path == model_path
    assert args.camera_index == 2
    assert args.window_title == "FocusLens Test"
    assert args.max_frames == 5


def test_default_model_path_uses_environment_variable(monkeypatch, tmp_path):
    model_path = tmp_path / "model.task"
    monkeypatch.setenv("FOCUSLENS_MODEL_PATH", str(model_path))

    assert default_model_path() == model_path


def test_run_options_validates_values(tmp_path):
    model_path = tmp_path / "model.task"

    with pytest.raises(ValueError, match="window_title must not be empty"):
        RunOptions(model_path=model_path, window_title=" ")

    with pytest.raises(ValueError, match="wait_key_delay_ms must be"):
        RunOptions(model_path=model_path, wait_key_delay_ms=0)


def test_non_negative_int_rejects_negative_values():
    assert non_negative_int("3") == 3

    with pytest.raises(argparse.ArgumentTypeError, match="must be non-negative"):
        non_negative_int("-1")


@pytest.mark.parametrize(
    ("key_code", "expected"),
    [
        (-1, None),
        (ord("q"), "q"),
        (ord("Q"), "q"),
        (ord("p"), "p"),
        (27, "escape"),
        (ord("x"), None),
    ],
)
def test_key_name_from_wait_key_normalizes_supported_keys(key_code, expected):
    assert key_name_from_wait_key(key_code) == expected


def test_run_session_wires_camera_tracker_attention_and_overlay(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    model_path.write_bytes(b"placeholder")
    camera_context = FakeCameraContext(
        [
            FakeFrame(bgr="bgr-1", rgb="rgb-1", timestamp_ms=100),
            FakeFrame(bgr="bgr-2", rgb="rgb-2", timestamp_ms=200),
        ]
    )
    tracker_context = FakeTrackerContext()
    renderer = FakeRenderer()
    cv2 = FakeCv2(keys=[ord("p"), ord("q")])
    camera_factory_calls = []
    tracker_factory_calls = []

    def camera_factory(camera_index, cv2_module):
        camera_factory_calls.append((camera_index, cv2_module))
        return camera_context

    def tracker_factory(path):
        tracker_factory_calls.append(path)
        return tracker_context

    def renderer_factory(cv2_module):
        assert cv2_module is cv2
        return renderer

    exit_code = run_session(
        RunOptions(
            model_path=model_path,
            camera_index=3,
            window_title="FocusLens Test",
        ),
        camera_factory=camera_factory,
        tracker_factory=tracker_factory,
        renderer_factory=renderer_factory,
        cv2_module=cv2,
        clock=FakeClock(10.0, 10.5, 11.5),
    )

    assert exit_code == 0
    assert camera_factory_calls == [(3, cv2)]
    assert tracker_factory_calls == [model_path]
    assert camera_context.entered is True
    assert camera_context.exited is True
    assert tracker_context.entered is True
    assert tracker_context.exited is True
    assert tracker_context.calls == [("rgb-1", 100)]
    assert [call[1].state for call in renderer.calls] == [
        AttentionState.AWAY,
        AttentionState.PAUSED,
    ]
    assert [round(call[2].elapsed_seconds, 1) for call in renderer.calls] == [0.5, 1.5]
    assert cv2.named_windows == [("FocusLens Test", "WINDOW_NORMAL")]
    assert cv2.imshow_calls == [
        ("FocusLens Test", "rendered-bgr-1"),
        ("FocusLens Test", "rendered-bgr-2"),
    ]
    assert cv2.wait_delays == [1, 1]
    assert cv2.destroyed_windows == ["FocusLens Test"]


def test_run_session_requires_local_model_file(tmp_path):
    with pytest.raises(CliError, match="Face Landmarker model not found"):
        run_session(
            RunOptions(model_path=tmp_path / "missing.task"),
            cv2_module=FakeCv2(keys=[]),
        )


def test_analyze_frame_returns_paused_without_calling_tracker():
    tracker = FakeTrackerContext()

    analysis = analyze_frame(tracker, object(), 100, paused=True)

    assert analysis.state == AttentionState.PAUSED
    assert analysis.reason == "manual_pause"
    assert tracker.calls == []


def test_run_dashboard_requires_existing_dashboard_file(tmp_path):
    with pytest.raises(CliError, match="Dashboard entry file not found"):
        run_dashboard(tmp_path / "missing_dashboard.py")


def test_run_dashboard_launches_streamlit_without_shell(monkeypatch, tmp_path):
    dashboard_path = tmp_path / "dashboard.py"
    dashboard_path.write_text("import streamlit as st\n", encoding="utf-8")
    calls = []

    def fake_call(command, **kwargs):
        calls.append((command, kwargs))
        return 7

    monkeypatch.setattr("focuslens.cli.subprocess.call", fake_call)

    exit_code = run_dashboard(dashboard_path)

    assert exit_code == 7
    assert calls == [
        (
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(dashboard_path.resolve()),
            ],
            {"shell": False},
        )
    ]
