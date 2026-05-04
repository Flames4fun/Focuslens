import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from focuslens.attention import AttentionState, FaceObservation
from focuslens.cli import (
    CliError,
    RunOptions,
    analyze_frame,
    build_parser,
    default_model_path,
    find_git_repository_root,
    handle_preview_key,
    key_name_from_wait_key,
    main,
    non_negative_int,
    overlay_metrics_from_summary,
    path_is_relative_to,
    process_frame,
    run_dashboard,
    run_session,
    save_finished_session,
    warn_about_save_dir,
)
from focuslens.config import FocusLensConfig
from focuslens.session import SessionSummary, SessionTracker
from focuslens.storage import SessionSaveResult

STARTED_AT = datetime(2026, 4, 30, 9, 0, tzinfo=UTC)
ENDED_AT = datetime(2026, 4, 30, 9, 5, tzinfo=UTC)


@dataclass(frozen=True)
class FakeFrame:
    bgr: object
    rgb: object
    timestamp_ms: int


class StrictFakeClock:
    def __init__(self, *values):
        self.values = list(values)

    def __call__(self):
        if not self.values:
            raise AssertionError("Clock called more times than expected")

        return self.values.pop(0)


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
    def __init__(self, frames, *, error=None):
        self.frames = list(frames)
        self.error = error
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *_):
        self.exited = True

    def read(self):
        if self.error is not None:
            raise self.error

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
    def __init__(self, *, error=None):
        self.calls = []
        self.error = error

    def render(self, frame_bgr, analysis, metrics=None):
        if self.error is not None:
            raise self.error

        self.calls.append((frame_bgr, analysis, metrics))
        return f"rendered-{frame_bgr}"


def test_build_parser_parses_run_arguments(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    save_dir = tmp_path / "sessions"
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
            "--save-dir",
            str(save_dir),
            "--no-save",
            "--max-frames",
            "5",
        ]
    )

    assert args.command == "run"
    assert args.model_path == model_path
    assert args.camera_index == 2
    assert args.window_title == "FocusLens Test"
    assert args.save_dir == save_dir
    assert args.no_save is True
    assert args.max_frames == 5


def test_default_model_path_uses_environment_variable(monkeypatch, tmp_path):
    model_path = tmp_path / "model.task"
    monkeypatch.setenv("FOCUSLENS_MODEL_PATH", str(model_path))

    assert default_model_path() == model_path


def test_run_options_validates_values(tmp_path):
    model_path = tmp_path / "model.task"

    with pytest.raises(ValueError, match="window_title must not be empty"):
        RunOptions(model_path=model_path, window_title=" ")

    with pytest.raises(ValueError, match="window_title must be a string"):
        RunOptions(model_path=model_path, window_title=None)

    with pytest.raises(ValueError, match="camera_index must be"):
        RunOptions(model_path=model_path, camera_index=True)

    with pytest.raises(ValueError, match="save_dir must not be empty"):
        RunOptions(model_path=model_path, save_dir=" ")

    with pytest.raises(ValueError, match="save_dir must be a path-like"):
        RunOptions(model_path=model_path, save_dir=None)

    with pytest.raises(ValueError, match="save_enabled must be a boolean"):
        RunOptions(model_path=model_path, save_enabled="yes")

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


def test_handle_preview_key_toggles_pause_and_stops_on_quit_keys():
    assert handle_preview_key("p", paused=False).paused is True
    assert handle_preview_key("p", paused=True).paused is False
    assert handle_preview_key("q", paused=True).should_stop is True
    assert handle_preview_key(None, paused=True).paused is True


def test_process_frame_records_session_and_returns_rendered_frame():
    camera = FakeCameraContext([FakeFrame(bgr="bgr-1", rgb="rgb-1", timestamp_ms=100)])
    tracker = FakeTrackerContext()
    renderer = FakeRenderer()
    session_tracker = SessionTracker(
        FocusLensConfig(min_event_duration_seconds=0.1),
        clock=StrictFakeClock(0.0),
        wall_clock=lambda: STARTED_AT,
    )

    rendered_frame = process_frame(
        camera,
        tracker,
        renderer,
        config=FocusLensConfig(min_event_duration_seconds=0.1),
        paused=False,
        session_tracker=session_tracker,
        clock=StrictFakeClock(1.0),
    )

    assert rendered_frame == "rendered-bgr-1"
    assert tracker.calls == [("rgb-1", 100)]
    assert renderer.calls[0][1].state == AttentionState.AWAY
    assert renderer.calls[0][2].elapsed_seconds == 1.0
    assert session_tracker.snapshot(at_seconds=1.0).away_seconds == 0.0


def test_run_session_wires_camera_tracker_attention_and_overlay(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    save_dir = tmp_path / "sessions"
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
            save_dir=save_dir,
        ),
        camera_factory=camera_factory,
        tracker_factory=tracker_factory,
        renderer_factory=renderer_factory,
        cv2_module=cv2,
        clock=StrictFakeClock(10.0, 10.5, 11.5, 12.0),
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
    assert [round(call[2].away_seconds, 1) for call in renderer.calls] == [0.0, 1.0]
    assert [call[2].looking_away_events for call in renderer.calls] == [0, 0]
    assert cv2.named_windows == [("FocusLens Test", "WINDOW_NORMAL")]
    assert cv2.imshow_calls == [
        ("FocusLens Test", "rendered-bgr-1"),
        ("FocusLens Test", "rendered-bgr-2"),
    ]
    assert cv2.wait_delays == [1, 1]
    assert cv2.destroyed_windows == ["FocusLens Test"]
    session_files = list(save_dir.glob("session_*.json"))
    assert len(session_files) == 1
    saved_summary = json.loads(session_files[0].read_text(encoding="utf-8"))
    assert saved_summary["total_seconds"] == 2.0
    assert saved_summary["unknown_seconds"] == 0.5
    assert saved_summary["away_seconds"] == 1.0
    assert saved_summary["paused_seconds"] == 0.5
    assert (save_dir / "sessions.csv").is_file()


def test_run_session_can_skip_saving_with_no_save(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    save_dir = tmp_path / "sessions"
    model_path.write_bytes(b"placeholder")
    camera_context = FakeCameraContext([])
    tracker_context = FakeTrackerContext()

    exit_code = run_session(
        RunOptions(
            model_path=model_path,
            save_dir=save_dir,
            save_enabled=False,
            max_frames=0,
        ),
        camera_factory=lambda _index, _cv2: camera_context,
        tracker_factory=lambda _path: tracker_context,
        renderer_factory=lambda _cv2: FakeRenderer(),
        cv2_module=FakeCv2(keys=[]),
        clock=StrictFakeClock(0.0, 0.0),
    )

    assert exit_code == 0
    assert not save_dir.exists()


def test_run_session_saves_empty_session_when_max_frames_is_zero(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    save_dir = tmp_path / "sessions"
    model_path.write_bytes(b"placeholder")

    exit_code = run_session(
        RunOptions(model_path=model_path, save_dir=save_dir, max_frames=0),
        camera_factory=lambda _index, _cv2: FakeCameraContext([]),
        tracker_factory=lambda _path: FakeTrackerContext(),
        renderer_factory=lambda _cv2: FakeRenderer(),
        cv2_module=FakeCv2(keys=[]),
        clock=StrictFakeClock(0.0, 0.0),
    )

    assert exit_code == 0
    session_files = list(save_dir.glob("session_*.json"))
    assert len(session_files) == 1
    data = json.loads(session_files[0].read_text(encoding="utf-8"))
    assert data["total_seconds"] == 0.0


def test_run_session_reports_save_dir_file_error_clearly(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    save_path = tmp_path / "sessions"
    model_path.write_bytes(b"placeholder")
    save_path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(CliError, match="Could not save session summary"):
        run_session(
            RunOptions(model_path=model_path, save_dir=save_path, max_frames=0),
            camera_factory=lambda _index, _cv2: FakeCameraContext([]),
            tracker_factory=lambda _path: FakeTrackerContext(),
            renderer_factory=lambda _cv2: FakeRenderer(),
            cv2_module=FakeCv2(keys=[]),
            clock=StrictFakeClock(0.0, 0.0),
        )


def test_run_session_preserves_loop_error_and_still_attempts_save(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    save_dir = tmp_path / "sessions"
    model_path.write_bytes(b"placeholder")
    read_error = RuntimeError("camera exploded")

    with pytest.raises(RuntimeError, match="camera exploded"):
        run_session(
            RunOptions(model_path=model_path, save_dir=save_dir),
            camera_factory=lambda _index, _cv2: FakeCameraContext([], error=read_error),
            tracker_factory=lambda _path: FakeTrackerContext(),
            renderer_factory=lambda _cv2: FakeRenderer(),
            cv2_module=FakeCv2(keys=[]),
            clock=StrictFakeClock(0.0, 0.2),
        )

    assert len(list(save_dir.glob("session_*.json"))) == 1


def test_run_session_does_not_hide_loop_error_when_final_save_fails(tmp_path, capsys):
    model_path = tmp_path / "face_landmarker.task"
    save_path = tmp_path / "sessions"
    model_path.write_bytes(b"placeholder")
    save_path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(RuntimeError, match="camera exploded"):
        run_session(
            RunOptions(model_path=model_path, save_dir=save_path),
            camera_factory=lambda _index, _cv2: FakeCameraContext(
                [],
                error=RuntimeError("camera exploded"),
            ),
            tracker_factory=lambda _path: FakeTrackerContext(),
            renderer_factory=lambda _cv2: FakeRenderer(),
            cv2_module=FakeCv2(keys=[]),
            clock=StrictFakeClock(0.0, 0.2),
        )

    assert "Warning: Could not save session summary" in capsys.readouterr().err


def test_run_session_closes_window_when_renderer_fails(tmp_path):
    model_path = tmp_path / "face_landmarker.task"
    model_path.write_bytes(b"placeholder")
    cv2 = FakeCv2(keys=[])
    renderer_error = RuntimeError("renderer failed")

    with pytest.raises(RuntimeError, match="renderer failed"):
        run_session(
            RunOptions(model_path=model_path, save_dir=tmp_path / "sessions"),
            camera_factory=lambda _index, _cv2: FakeCameraContext(
                [FakeFrame(bgr="bgr-1", rgb="rgb-1", timestamp_ms=100)]
            ),
            tracker_factory=lambda _path: FakeTrackerContext(),
            renderer_factory=lambda _cv2: FakeRenderer(error=renderer_error),
            cv2_module=cv2,
            clock=StrictFakeClock(0.0, 0.1, 0.2),
        )

    assert cv2.destroyed_windows == ["FocusLens"]


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


def test_overlay_metrics_from_summary_uses_aggregate_session_values():
    summary = SessionSummary(
        started_at=STARTED_AT,
        ended_at=ENDED_AT,
        total_seconds=300.0,
        focused_seconds=210.0,
        away_seconds=45.0,
        looking_away_seconds=30.0,
        too_close_seconds=15.0,
        looking_away_events=2,
        away_events=1,
        focus_score=70.0,
        presence_score=85.0,
    )

    metrics = overlay_metrics_from_summary(summary)

    assert metrics.elapsed_seconds == 300.0
    assert metrics.focused_seconds == 210.0
    assert metrics.away_seconds == 45.0
    assert metrics.looking_away_events == 2
    assert metrics.focus_score == 70.0
    assert metrics.presence_score == 85.0


def test_save_finished_session_persists_summary_and_validates_files(tmp_path):
    tracker = SessionTracker(
        clock=StrictFakeClock(0.0),
        wall_clock=lambda: STARTED_AT,
    )
    tracker.observe(AttentionState.FOCUSED, at_seconds=0.0)
    tracker.observe(AttentionState.AWAY, at_seconds=2.0)

    result = save_finished_session(tracker, tmp_path, at_seconds=3.0)

    assert result.json_path.is_file()
    assert result.csv_path.is_file()
    data = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert data["focused_seconds"] == 2.0
    assert data["away_seconds"] == 1.0


def test_save_finished_session_wraps_expected_storage_errors(tmp_path):
    tracker = SessionTracker(
        clock=StrictFakeClock(0.0),
        wall_clock=lambda: STARTED_AT,
    )

    def failing_saver(summary, save_dir):
        raise PermissionError("read-only output")

    with pytest.raises(CliError, match="Could not save session summary"):
        save_finished_session(
            tracker,
            tmp_path,
            at_seconds=0.0,
            summary_saver=failing_saver,
        )


def test_save_finished_session_rejects_invalid_save_results(tmp_path):
    tracker = SessionTracker(
        clock=StrictFakeClock(0.0),
        wall_clock=lambda: STARTED_AT,
    )

    def missing_file_saver(summary, save_dir):
        return SessionSaveResult(
            json_path=tmp_path / "missing.json",
            csv_path=tmp_path / "missing.csv",
        )

    with pytest.raises(CliError, match="Session JSON was not written"):
        save_finished_session(
            tracker,
            tmp_path,
            at_seconds=0.0,
            summary_saver=missing_file_saver,
        )


def test_save_finished_session_rejects_missing_csv_after_json_exists(tmp_path):
    tracker = SessionTracker(
        clock=StrictFakeClock(0.0),
        wall_clock=lambda: STARTED_AT,
    )
    json_path = tmp_path / "session.json"
    json_path.write_text("{}", encoding="utf-8")

    def missing_csv_saver(summary, save_dir):
        return SessionSaveResult(
            json_path=json_path,
            csv_path=tmp_path / "missing.csv",
        )

    with pytest.raises(CliError, match="Session CSV was not written"):
        save_finished_session(
            tracker,
            tmp_path,
            at_seconds=0.0,
            summary_saver=missing_csv_saver,
        )


def test_save_finished_session_does_not_wrap_programming_type_errors(tmp_path):
    tracker = SessionTracker(
        clock=StrictFakeClock(0.0),
        wall_clock=lambda: STARTED_AT,
    )

    def failing_saver(summary, save_dir):
        raise TypeError("bad saver contract")

    with pytest.raises(TypeError, match="bad saver contract"):
        save_finished_session(
            tracker,
            tmp_path,
            at_seconds=0.0,
            summary_saver=failing_saver,
        )


def test_main_returns_error_code_for_save_failures(monkeypatch, capsys):
    def fake_run_session(options):
        raise CliError("Could not save session summary: read-only")

    monkeypatch.setattr("focuslens.cli.run_session", fake_run_session)

    exit_code = main(["run", "--model-path", "model.task"])

    assert exit_code == 2
    assert "Could not save session summary" in capsys.readouterr().err


def test_warn_about_save_dir_warns_for_non_default_and_git_repo(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    custom_save_dir = project / "exported_sessions"

    warn_about_save_dir(
        custom_save_dir,
        default_save_dir=project / "sessions",
        cwd=project,
    )

    stderr = capsys.readouterr().err
    assert "session summaries include timestamps" in stderr
    assert "inside a Git repository" in stderr


def test_find_git_repository_root_and_relative_path_helpers(tmp_path):
    project = tmp_path / "project"
    nested = project / "nested" / "sessions"
    nested.mkdir(parents=True)
    (project / ".git").mkdir()

    assert find_git_repository_root(nested) == project
    assert path_is_relative_to(nested, project) is True
    assert path_is_relative_to(project, nested) is False


def test_run_dashboard_requires_existing_dashboard_file(tmp_path):
    with pytest.raises(CliError, match="Dashboard entry file not found"):
        run_dashboard(
            tmp_path / "missing_dashboard.py",
            project_root=tmp_path,
        )


def test_run_dashboard_requires_python_file(tmp_path):
    dashboard_path = tmp_path / "dashboard.txt"
    dashboard_path.write_text("not python\n", encoding="utf-8")

    with pytest.raises(CliError, match="must be a Python .py file"):
        run_dashboard(
            dashboard_path,
            project_root=tmp_path,
        )


def test_run_dashboard_rejects_external_path_without_explicit_allow(tmp_path):
    project_root = tmp_path / "project"
    external_dir = tmp_path / "external"
    project_root.mkdir()
    external_dir.mkdir()
    dashboard_path = external_dir / "dashboard.py"
    dashboard_path.write_text("import streamlit as st\n", encoding="utf-8")

    with pytest.raises(CliError, match="inside the project root"):
        run_dashboard(
            dashboard_path,
            project_root=project_root,
        )


def test_run_dashboard_launches_streamlit_without_shell(monkeypatch, tmp_path):
    dashboard_path = tmp_path / "dashboard.py"
    dashboard_path.write_text("import streamlit as st\n", encoding="utf-8")
    calls = []

    def fake_call(command, **kwargs):
        calls.append((command, kwargs))
        return 7

    monkeypatch.setattr("focuslens.cli.subprocess.call", fake_call)

    exit_code = run_dashboard(
        dashboard_path,
        project_root=tmp_path / "project",
        allow_external=True,
    )

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
