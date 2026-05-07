"""Command line interface for FocusLens.

The run command wires the local webcam, face tracker, attention classifier, and
overlay renderer together. Frames stay in memory only and are never saved here.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from time import perf_counter
from typing import Any

from focuslens import __version__
from focuslens.attention import AttentionAnalysis, AttentionState, analyze_attention
from focuslens.camera import (
    Camera,
    CameraOpenError,
    CameraReadError,
    OpenCVUnavailableError,
    WebcamCamera,
)
from focuslens.config import DEFAULT_CONFIG, FocusLensConfig
from focuslens.face_tracker import (
    FaceTracker,
    MediaPipeFaceTracker,
    MediaPipeUnavailableError,
)
from focuslens.overlay import OpenCVOverlayRenderer, OverlayMetrics, OverlayRenderer
from focuslens.session import SessionSummary, SessionTracker
from focuslens.storage import SessionSaveResult, save_session_summary

MODEL_PATH_ENV_VAR = "FOCUSLENS_MODEL_PATH"
DEFAULT_MODEL_PATH = Path("assets") / "face_landmarker.task"
DEFAULT_DASHBOARD_PATH = Path("dashboard.py")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUIT_KEYS = frozenset({"q", "escape"})

CameraFactory = Callable[[int, Any], AbstractContextManager[Camera]]
TrackerFactory = Callable[[Path], AbstractContextManager[FaceTracker]]
RendererFactory = Callable[[Any], OverlayRenderer]
SessionTrackerFactory = Callable[[FocusLensConfig, Callable[[], float]], SessionTracker]
SummarySaver = Callable[[SessionSummary, Path | str], SessionSaveResult]


class CliError(RuntimeError):
    """Raised for expected CLI failures that should not print tracebacks."""


@dataclass(frozen=True, slots=True)
class PreviewKeyResult:
    """Result of handling one preview-window keypress."""

    paused: bool
    should_stop: bool = False


@dataclass(frozen=True, slots=True)
class RunOptions:
    """Validated options for a local FocusLens run session."""

    model_path: Path
    camera_index: int = DEFAULT_CONFIG.camera_index
    window_title: str = DEFAULT_CONFIG.window_title
    save_dir: Path = field(default_factory=lambda: DEFAULT_CONFIG.save_dir)
    save_enabled: bool = True
    max_frames: int | None = None
    wait_key_delay_ms: int = 1

    def __post_init__(self) -> None:
        """Normalize paths and reject values that would make the loop unsafe."""

        if isinstance(self.camera_index, bool) or not isinstance(
            self.camera_index,
            int,
        ):
            raise ValueError("camera_index must be a non-negative integer")

        if not isinstance(self.model_path, (str, os.PathLike)):
            raise ValueError("model_path must be a path-like value")

        if not isinstance(self.window_title, str):
            raise ValueError("window_title must be a string")

        if not isinstance(self.save_dir, (str, os.PathLike)):
            raise ValueError("save_dir must be a path-like value")

        if isinstance(self.save_dir, str) and not self.save_dir.strip():
            raise ValueError("save_dir must not be empty")

        if not isinstance(self.save_enabled, bool):
            raise ValueError("save_enabled must be a boolean")

        object.__setattr__(self, "model_path", Path(self.model_path).expanduser())
        object.__setattr__(self, "save_dir", Path(self.save_dir).expanduser())

        if self.camera_index < 0:
            raise ValueError("camera_index must be non-negative")

        if not self.window_title.strip():
            raise ValueError("window_title must not be empty")

        if self.max_frames is not None and self.max_frames < 0:
            raise ValueError("max_frames must be non-negative")

        if self.wait_key_delay_ms < 1:
            raise ValueError("wait_key_delay_ms must be greater than zero")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the FocusLens CLI and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return int(args.handler(args))
    except KeyboardInterrupt:
        return 130
    except (
        CliError,
        CameraOpenError,
        CameraReadError,
        MediaPipeUnavailableError,
        OpenCVUnavailableError,
        ValueError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""

    parser = argparse.ArgumentParser(
        prog="focuslens",
        description="Privacy-first local focus tracking from webcam landmarks.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"FocusLens {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Start a local webcam focus session.",
        epilog=(
            "Keys while running: p pauses/resumes attention analysis; "
            "the webcam preview remains open. q or Esc quits."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    run_parser.add_argument(
        "--model-path",
        type=Path,
        default=default_model_path(),
        help=(
            "Local MediaPipe Face Landmarker .task file. "
            f"Can also be set with {MODEL_PATH_ENV_VAR}."
        ),
    )
    run_parser.add_argument(
        "--camera-index",
        type=non_negative_int,
        default=DEFAULT_CONFIG.camera_index,
        help="OpenCV camera index to open.",
    )
    run_parser.add_argument(
        "--window-title",
        default=DEFAULT_CONFIG.window_title,
        help="Title for the local OpenCV preview window.",
    )
    run_parser.add_argument(
        "--save-dir",
        type=Path,
        default=DEFAULT_CONFIG.save_dir,
        help="Directory for local JSON/CSV session summaries.",
    )
    run_parser.add_argument(
        "--no-save",
        action="store_true",
        help="Run a temporary session without writing JSON or CSV summaries.",
    )
    run_parser.add_argument(
        "--max-frames",
        type=non_negative_int,
        default=None,
        help="Stop automatically after N frames. Useful for smoke tests.",
    )
    run_parser.set_defaults(handler=handle_run_command)

    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Open the local Streamlit dashboard when dashboard.py exists.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    dashboard_parser.add_argument(
        "--path",
        type=Path,
        default=default_dashboard_path(),
        help="Trusted local Streamlit dashboard .py file to run.",
    )
    dashboard_parser.add_argument(
        "--allow-external-dashboard",
        action="store_true",
        help=(
            "Allow --path outside this project. Only use this for trusted "
            "local dashboard files."
        ),
    )
    dashboard_parser.set_defaults(handler=handle_dashboard_command)

    return parser


def handle_run_command(args: argparse.Namespace) -> int:
    """Execute `focuslens run` from parsed CLI arguments."""

    options = RunOptions(
        model_path=args.model_path,
        camera_index=args.camera_index,
        window_title=args.window_title,
        save_dir=args.save_dir,
        save_enabled=not args.no_save,
        max_frames=args.max_frames,
    )
    return run_session(options)


def handle_dashboard_command(args: argparse.Namespace) -> int:
    """Execute `focuslens dashboard` from parsed CLI arguments."""

    return run_dashboard(
        args.path,
        allow_external=args.allow_external_dashboard,
    )


def run_session(
    options: RunOptions,
    *,
    camera_factory: CameraFactory | None = None,
    tracker_factory: TrackerFactory | None = None,
    renderer_factory: RendererFactory | None = None,
    session_tracker_factory: SessionTrackerFactory | None = None,
    summary_saver: SummarySaver | None = None,
    cv2_module: Any | None = None,
    clock: Callable[[], float] = perf_counter,
) -> int:
    """Run the local webcam loop until the user quits or the frame limit ends."""

    model_path = options.model_path
    if not model_path.is_file():
        raise CliError(
            f"Face Landmarker model not found: {model_path}. "
            "Provide a local .task file with --model-path or "
            f"{MODEL_PATH_ENV_VAR}."
        )

    cv2 = cv2_module or load_cv2()
    camera_factory = camera_factory or _default_camera_factory
    tracker_factory = tracker_factory or _default_tracker_factory
    renderer_factory = renderer_factory or _default_renderer_factory
    session_tracker_factory = (
        session_tracker_factory or _default_session_tracker_factory
    )
    summary_saver = summary_saver or save_session_summary
    config = FocusLensConfig(
        camera_index=options.camera_index,
        save_dir=options.save_dir,
        window_title=options.window_title,
    )
    renderer = renderer_factory(cv2)
    if options.save_enabled:
        warn_about_save_dir(config.save_dir)

    with camera_factory(config.camera_index, cv2) as camera:
        with tracker_factory(model_path) as tracker:
            return run_preview_loop(
                camera,
                tracker,
                renderer,
                cv2,
                options,
                config=config,
                session_tracker_factory=session_tracker_factory,
                summary_saver=summary_saver,
                clock=clock,
            )


def run_preview_loop(
    camera: Camera,
    tracker: FaceTracker,
    renderer: OverlayRenderer,
    cv2: Any,
    options: RunOptions,
    *,
    config: FocusLensConfig = DEFAULT_CONFIG,
    session_tracker_factory: SessionTrackerFactory | None = None,
    summary_saver: SummarySaver | None = None,
    clock: Callable[[], float] = perf_counter,
) -> int:
    """Run the frame-by-frame preview loop for already opened resources."""

    session_tracker_factory = (
        session_tracker_factory or _default_session_tracker_factory
    )
    summary_saver = summary_saver or save_session_summary
    session_tracker = session_tracker_factory(config, clock)
    paused = False
    rendered_frames = 0
    loop_error: BaseException | None = None

    create_window_if_supported(cv2, config.window_title)

    try:
        while options.max_frames is None or rendered_frames < options.max_frames:
            rendered_frame = process_frame(
                camera,
                tracker,
                renderer,
                config=config,
                paused=paused,
                session_tracker=session_tracker,
                clock=clock,
            )
            cv2.imshow(config.window_title, rendered_frame)
            rendered_frames += 1

            key = key_name_from_wait_key(cv2.waitKey(options.wait_key_delay_ms))
            key_result = handle_preview_key(key, paused)
            paused = key_result.paused
            if key_result.should_stop:
                break
    except BaseException as exc:
        loop_error = exc
        raise
    finally:
        finalize_preview_loop(
            cv2,
            config.window_title,
            session_tracker,
            config.save_dir,
            save_enabled=options.save_enabled,
            at_seconds=clock(),
            summary_saver=summary_saver,
            suppress_errors=loop_error is not None,
        )
    return 0


def analyze_frame(
    tracker: FaceTracker,
    frame_rgb: object,
    timestamp_ms: int,
    *,
    config: FocusLensConfig = DEFAULT_CONFIG,
    paused: bool = False,
) -> AttentionAnalysis:
    """Analyze one frame or return a paused state without running tracking."""

    if paused:
        return AttentionAnalysis(state=AttentionState.PAUSED, reason="manual_pause")

    face = tracker.track(frame_rgb, timestamp_ms)
    return analyze_attention(face, config)


def process_frame(
    camera: Camera,
    tracker: FaceTracker,
    renderer: OverlayRenderer,
    *,
    config: FocusLensConfig,
    paused: bool,
    session_tracker: SessionTracker,
    clock: Callable[[], float],
) -> object:
    """Read, analyze, record, and render one preview frame."""

    frame = camera.read()
    analysis = analyze_frame(
        tracker,
        frame.rgb,
        frame.timestamp_ms,
        config=config,
        paused=paused,
    )
    observed_seconds = clock()
    session_tracker.observe(analysis, at_seconds=observed_seconds)
    metrics = overlay_metrics_from_summary(
        session_tracker.snapshot(at_seconds=observed_seconds)
    )
    return renderer.render(frame.bgr, analysis, metrics)


def handle_preview_key(key: str | None, paused: bool) -> PreviewKeyResult:
    """Apply one normalized preview key command."""

    if key in QUIT_KEYS:
        return PreviewKeyResult(paused=paused, should_stop=True)

    if key == "p":
        return PreviewKeyResult(paused=not paused)

    return PreviewKeyResult(paused=paused)


def overlay_metrics_from_summary(summary: SessionSummary) -> OverlayMetrics:
    """Build overlay-safe metrics from a session summary."""

    return OverlayMetrics(
        elapsed_seconds=summary.total_seconds,
        focused_seconds=summary.focused_seconds,
        away_seconds=summary.away_seconds,
        looking_away_events=summary.looking_away_events,
        focus_score=summary.focus_score,
        presence_score=summary.presence_score,
    )


def finalize_preview_loop(
    cv2: Any,
    window_title: str,
    session_tracker: SessionTracker,
    save_dir: Path | str,
    *,
    save_enabled: bool,
    at_seconds: float,
    summary_saver: SummarySaver | None = None,
    suppress_errors: bool = False,
    warning_stream: object | None = None,
) -> SessionSaveResult | None:
    """Close preview resources and persist the session when configured."""

    warning_stream = warning_stream or sys.stderr
    _, close_error = _try_action(
        lambda: destroy_window_if_supported(cv2, window_title),
        warning="Could not close preview window",
        suppress_errors=suppress_errors,
        stream=warning_stream,
    )

    save_result = None
    if save_enabled:
        save_result, _ = _try_action(
            lambda: save_finished_session(
                session_tracker,
                save_dir,
                at_seconds=at_seconds,
                summary_saver=summary_saver,
            ),
            warning="Could not save session summary",
            suppress_errors=suppress_errors or close_error is not None,
            stream=warning_stream,
        )

    if close_error is not None and not suppress_errors:
        raise close_error

    return save_result


def save_finished_session(
    session_tracker: SessionTracker,
    save_dir: Path | str,
    *,
    at_seconds: float | None = None,
    summary_saver: SummarySaver | None = None,
) -> SessionSaveResult:
    """Finalize and persist a session summary without exposing frame data."""

    summary_saver = summary_saver or save_session_summary
    summary = session_tracker.finish(at_seconds=at_seconds)
    try:
        result = summary_saver(summary, save_dir)
    except OSError as exc:
        raise CliError(f"Could not save session summary: {exc}") from exc

    if not isinstance(result, SessionSaveResult):
        raise CliError("Session saver returned an invalid save result.")

    if not result.json_path.is_file():
        raise CliError(f"Session JSON was not written: {result.json_path}")

    if not result.csv_path.is_file():
        raise CliError(f"Session CSV was not written: {result.csv_path}")

    return result


def _try_action(
    action: Callable[[], object],
    *,
    warning: str,
    suppress_errors: bool,
    stream: object,
) -> tuple[object | None, Exception | None]:
    try:
        return action(), None
    except Exception as exc:
        if not suppress_errors:
            raise

        print(f"Warning: {warning}: {exc}", file=stream)
        return None, exc


def run_dashboard(
    dashboard_path: Path,
    *,
    project_root: Path = PROJECT_ROOT,
    allow_external: bool = False,
    streamlit_runner: Callable[[Path], int] | None = None,
) -> int:
    """Launch the local Streamlit dashboard if the entry file exists."""

    dashboard_path = dashboard_path.expanduser().resolve()
    project_root = project_root.expanduser().resolve()
    if dashboard_path.suffix.lower() != ".py":
        raise CliError("Dashboard path must be a Python .py file.")

    if not allow_external and not path_is_relative_to(dashboard_path, project_root):
        raise CliError(
            f"Dashboard path must be inside the project root: {project_root}. "
            "Use --allow-external-dashboard only for trusted local files."
        )

    if not dashboard_path.is_file():
        raise CliError(
            f"Dashboard entry file not found: {dashboard_path}. "
            "Create dashboard.py before running this command."
        )

    if is_frozen_app():
        runner = streamlit_runner or run_streamlit_dashboard_in_process
        return runner(dashboard_path)

    return subprocess.call(
        [sys.executable, "-m", "streamlit", "run", str(dashboard_path)],
        shell=False,
    )


def run_streamlit_dashboard_in_process(dashboard_path: Path) -> int:
    """Run Streamlit from a packaged executable without shelling out."""

    try:
        streamlit_cli = import_module("streamlit.web.cli")
    except ImportError as exc:
        raise CliError(
            "Streamlit is required for the FocusLens dashboard. "
            'Install it with: python -m pip install "streamlit>=1.35"'
        ) from exc

    args = [
        "run",
        str(dashboard_path),
        "--global.developmentMode=false",
        "--browser.gatherUsageStats=false",
    ]
    previous_argv = sys.argv[:]
    sys.argv = ["streamlit", *args]
    try:
        result = streamlit_cli.main.main(
            args=args,
            prog_name="streamlit",
            standalone_mode=False,
        )
    except SystemExit as exc:
        if exc.code is None:
            return 0

        if isinstance(exc.code, int):
            return exc.code

        raise
    finally:
        sys.argv = previous_argv

    if result is None:
        return 0

    if isinstance(result, int):
        return result

    return 0


def is_frozen_app() -> bool:
    """Return whether FocusLens is running from a packaged executable."""

    return bool(getattr(sys, "frozen", False))


def default_dashboard_path() -> Path:
    """Return the default Streamlit dashboard path for source or EXE runs."""

    bundled_dashboard_path = bundled_default_dashboard_path()
    if bundled_dashboard_path is not None:
        return bundled_dashboard_path

    return DEFAULT_DASHBOARD_PATH


def bundled_default_dashboard_path() -> Path | None:
    """Return the PyInstaller-bundled dashboard script path when available."""

    bundle_root = bundled_root_path()
    if bundle_root is None:
        return None

    candidate = bundle_root / DEFAULT_DASHBOARD_PATH
    if candidate.is_file():
        return candidate

    return None


def default_model_path() -> Path:
    """Return the default local face-landmarker model path."""

    env_value = os.environ.get(MODEL_PATH_ENV_VAR)
    if env_value:
        return Path(env_value).expanduser()

    bundled_model_path = bundled_default_model_path()
    if bundled_model_path is not None:
        return bundled_model_path

    return DEFAULT_MODEL_PATH


def bundled_default_model_path() -> Path | None:
    """Return the PyInstaller-bundled model path when running from an EXE."""

    bundle_root = bundled_root_path()
    if bundle_root is None:
        return None

    candidate = Path(bundle_root) / DEFAULT_MODEL_PATH
    if candidate.is_file():
        return candidate

    return None


def bundled_root_path() -> Path | None:
    """Return the PyInstaller bundle root for one-file or one-folder builds."""

    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root is not None:
        return Path(bundle_root)

    if is_frozen_app():
        return Path(sys.executable).resolve().parent

    return None


def warn_about_save_dir(
    save_dir: Path | str,
    *,
    default_save_dir: Path | str = DEFAULT_CONFIG.save_dir,
    cwd: Path | None = None,
    stream: object | None = None,
) -> None:
    """Warn when session summaries may be easy to sync or commit accidentally."""

    stream = stream or sys.stderr
    cwd = (cwd or Path.cwd()).resolve()
    resolved_save_dir = resolve_from_cwd(save_dir, cwd)
    resolved_default_save_dir = resolve_from_cwd(default_save_dir, cwd)

    if resolved_save_dir != resolved_default_save_dir:
        print(
            "Warning: session summaries include timestamps and focus metrics. "
            f"Review this --save-dir before syncing or sharing it: {resolved_save_dir}",
            file=stream,
        )

    git_root = find_git_repository_root(resolved_save_dir)
    if git_root is not None:
        print(
            "Warning: session summaries are being written inside a Git repository. "
            f"Ensure the directory is ignored before committing: {git_root}",
            file=stream,
        )


def resolve_from_cwd(path: Path | str, cwd: Path) -> Path:
    """Resolve a possibly relative path as the storage layer will see it."""

    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = cwd / candidate

    return candidate.resolve(strict=False)


def find_git_repository_root(path: Path) -> Path | None:
    """Return the nearest Git repository containing a path, if any."""

    resolved = path.resolve(strict=False)
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate

    return None


def path_is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether path is contained by parent."""

    try:
        path.relative_to(parent)
    except ValueError:
        return False

    return True


def load_cv2() -> Any:
    """Import OpenCV only when the CLI needs a video window."""

    try:
        return import_module("cv2")
    except ImportError as exc:
        raise OpenCVUnavailableError(
            "OpenCV is required to run FocusLens. "
            'Install it with: python -m pip install "opencv-python>=4.9"'
        ) from exc


def key_name_from_wait_key(key_code: int) -> str | None:
    """Normalize an OpenCV waitKey result into a small command name."""

    if key_code < 0:
        return None

    normalized = key_code & 0xFF
    if normalized == 27:
        return "escape"

    try:
        character = chr(normalized).lower()
    except ValueError:
        return None

    return character if character in {"p", "q"} else None


def non_negative_int(value: str) -> int:
    """Parse a non-negative integer for argparse."""

    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc

    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")

    return parsed


def create_window_if_supported(cv2: Any, window_title: str) -> None:
    """Create a resizable OpenCV window when the backend exposes namedWindow."""

    named_window = getattr(cv2, "namedWindow", None)
    if named_window is None:
        return

    named_window(window_title, getattr(cv2, "WINDOW_NORMAL", 0))


def destroy_window_if_supported(cv2: Any, window_title: str) -> None:
    """Destroy the preview window when the backend exposes destroyWindow."""

    destroy_window = getattr(cv2, "destroyWindow", None)
    if destroy_window is None:
        return

    destroy_window(window_title)


def _default_camera_factory(
    camera_index: int,
    cv2_module: Any,
) -> AbstractContextManager[Camera]:
    return WebcamCamera(camera_index=camera_index, cv2_module=cv2_module)


def _default_tracker_factory(model_path: Path) -> AbstractContextManager[FaceTracker]:
    return MediaPipeFaceTracker(model_path)


def _default_renderer_factory(cv2_module: Any) -> OverlayRenderer:
    return OpenCVOverlayRenderer(cv2_module=cv2_module)


def _default_session_tracker_factory(
    config: FocusLensConfig,
    clock: Callable[[], float],
) -> SessionTracker:
    return SessionTracker(config, clock=clock)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CliError",
    "DEFAULT_DASHBOARD_PATH",
    "DEFAULT_MODEL_PATH",
    "MODEL_PATH_ENV_VAR",
    "PROJECT_ROOT",
    "PreviewKeyResult",
    "RunOptions",
    "analyze_frame",
    "build_parser",
    "bundled_default_dashboard_path",
    "bundled_default_model_path",
    "bundled_root_path",
    "create_window_if_supported",
    "default_model_path",
    "default_dashboard_path",
    "destroy_window_if_supported",
    "finalize_preview_loop",
    "find_git_repository_root",
    "handle_preview_key",
    "handle_dashboard_command",
    "handle_run_command",
    "key_name_from_wait_key",
    "load_cv2",
    "main",
    "non_negative_int",
    "overlay_metrics_from_summary",
    "path_is_relative_to",
    "process_frame",
    "resolve_from_cwd",
    "run_dashboard",
    "run_streamlit_dashboard_in_process",
    "run_preview_loop",
    "run_session",
    "save_finished_session",
    "warn_about_save_dir",
]
