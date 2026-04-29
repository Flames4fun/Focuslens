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
from dataclasses import dataclass
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

MODEL_PATH_ENV_VAR = "FOCUSLENS_MODEL_PATH"
DEFAULT_MODEL_PATH = Path("assets") / "face_landmarker.task"
QUIT_KEYS = frozenset({"q", "escape"})

CameraFactory = Callable[[int, Any], AbstractContextManager[Camera]]
TrackerFactory = Callable[[Path], AbstractContextManager[FaceTracker]]
RendererFactory = Callable[[Any], OverlayRenderer]


class CliError(RuntimeError):
    """Raised for expected CLI failures that should not print tracebacks."""


@dataclass(frozen=True, slots=True)
class RunOptions:
    """Validated options for a local FocusLens run session."""

    model_path: Path
    camera_index: int = DEFAULT_CONFIG.camera_index
    window_title: str = DEFAULT_CONFIG.window_title
    max_frames: int | None = None
    wait_key_delay_ms: int = 1

    def __post_init__(self) -> None:
        """Normalize paths and reject values that would make the loop unsafe."""

        object.__setattr__(self, "model_path", Path(self.model_path).expanduser())

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
        default=Path("dashboard.py"),
        help="Path to the Streamlit dashboard entry file.",
    )
    dashboard_parser.set_defaults(handler=handle_dashboard_command)

    return parser


def handle_run_command(args: argparse.Namespace) -> int:
    """Execute `focuslens run` from parsed CLI arguments."""

    options = RunOptions(
        model_path=args.model_path,
        camera_index=args.camera_index,
        window_title=args.window_title,
        max_frames=args.max_frames,
    )
    return run_session(options)


def handle_dashboard_command(args: argparse.Namespace) -> int:
    """Execute `focuslens dashboard` from parsed CLI arguments."""

    return run_dashboard(args.path)


def run_session(
    options: RunOptions,
    *,
    camera_factory: CameraFactory | None = None,
    tracker_factory: TrackerFactory | None = None,
    renderer_factory: RendererFactory | None = None,
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
    config = FocusLensConfig(
        camera_index=options.camera_index,
        window_title=options.window_title,
    )
    renderer = renderer_factory(cv2)

    with camera_factory(config.camera_index, cv2) as camera:
        with tracker_factory(model_path) as tracker:
            return run_preview_loop(
                camera,
                tracker,
                renderer,
                cv2,
                options,
                config=config,
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
    clock: Callable[[], float] = perf_counter,
) -> int:
    """Run the frame-by-frame preview loop for already opened resources."""

    started_at = clock()
    paused = False
    rendered_frames = 0

    create_window_if_supported(cv2, config.window_title)

    try:
        while options.max_frames is None or rendered_frames < options.max_frames:
            frame = camera.read()
            analysis = analyze_frame(
                tracker,
                frame.rgb,
                frame.timestamp_ms,
                config=config,
                paused=paused,
            )
            metrics = OverlayMetrics(elapsed_seconds=clock() - started_at)
            rendered_frame = renderer.render(frame.bgr, analysis, metrics)
            cv2.imshow(config.window_title, rendered_frame)
            rendered_frames += 1

            key = key_name_from_wait_key(cv2.waitKey(options.wait_key_delay_ms))
            if key in QUIT_KEYS:
                break
            if key == "p":
                paused = not paused
    finally:
        destroy_window_if_supported(cv2, config.window_title)

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


def run_dashboard(dashboard_path: Path) -> int:
    """Launch the local Streamlit dashboard if the entry file exists."""

    dashboard_path = dashboard_path.expanduser().resolve()
    if not dashboard_path.is_file():
        raise CliError(
            f"Dashboard entry file not found: {dashboard_path}. "
            "Create dashboard.py before running this command."
        )

    return subprocess.call(
        [sys.executable, "-m", "streamlit", "run", str(dashboard_path)],
        shell=False,
    )


def default_model_path() -> Path:
    """Return the default local face-landmarker model path."""

    env_value = os.environ.get(MODEL_PATH_ENV_VAR)
    if env_value:
        return Path(env_value).expanduser()

    return DEFAULT_MODEL_PATH


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


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CliError",
    "DEFAULT_MODEL_PATH",
    "MODEL_PATH_ENV_VAR",
    "RunOptions",
    "analyze_frame",
    "build_parser",
    "create_window_if_supported",
    "default_model_path",
    "destroy_window_if_supported",
    "handle_dashboard_command",
    "handle_run_command",
    "key_name_from_wait_key",
    "load_cv2",
    "main",
    "non_negative_int",
    "run_dashboard",
    "run_preview_loop",
    "run_session",
]
