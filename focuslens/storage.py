"""Local session-summary persistence for FocusLens.

This module writes only derived aggregate metrics from ``SessionSummary``.
It never receives, saves, or serializes webcam frames.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from focuslens.config import DEFAULT_CONFIG
from focuslens.session import SessionSummary

CSV_FILENAME = "sessions.csv"
SESSION_FILENAME_PREFIX = "session"
SESSION_FILENAME_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
CSV_FIELDNAMES = (
    "started_at",
    "ended_at",
    "total_seconds",
    "focused_seconds",
    "away_seconds",
    "looking_away_seconds",
    "too_close_seconds",
    "too_far_seconds",
    "paused_seconds",
    "unknown_seconds",
    "looking_away_events",
    "away_events",
    "focus_score",
    "presence_score",
)


@dataclass(frozen=True, slots=True)
class SessionSaveResult:
    """Paths written when a session summary is persisted locally."""

    json_path: Path
    csv_path: Path


def save_session_summary(
    summary: SessionSummary,
    save_dir: Path | str = DEFAULT_CONFIG.save_dir,
) -> SessionSaveResult:
    """Save one session summary as JSON and append it to the CSV history."""

    _validate_summary(summary)
    save_dir = ensure_save_dir(save_dir)
    json_path = write_session_json(summary, save_dir=save_dir)
    csv_path = append_session_csv(summary, save_dir=save_dir)
    return SessionSaveResult(json_path=json_path, csv_path=csv_path)


def ensure_save_dir(save_dir: Path | str = DEFAULT_CONFIG.save_dir) -> Path:
    """Create and return the directory used for local session summaries."""

    resolved = Path(save_dir).expanduser().resolve()
    if resolved.exists() and not resolved.is_dir():
        raise NotADirectoryError(f"Session save path is not a directory: {resolved}")

    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def write_session_json(
    summary: SessionSummary,
    *,
    save_dir: Path | str = DEFAULT_CONFIG.save_dir,
) -> Path:
    """Write a session summary to a unique JSON file and return its path."""

    _validate_summary(summary)
    save_dir = ensure_save_dir(save_dir)
    json_path = next_session_json_path(summary, save_dir=save_dir)
    content = json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n"
    tmp_path = json_path.with_suffix(f"{json_path.suffix}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(json_path)
    return json_path


def append_session_csv(
    summary: SessionSummary,
    *,
    save_dir: Path | str = DEFAULT_CONFIG.save_dir,
    csv_filename: str = CSV_FILENAME,
) -> Path:
    """Append a session summary row to the local CSV history."""

    _validate_summary(summary)
    csv_filename = _validate_filename("csv_filename", csv_filename)
    save_dir = ensure_save_dir(save_dir)
    csv_path = save_dir / csv_filename
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0

    with csv_path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(_summary_csv_row(summary))

    return csv_path


def next_session_json_path(
    summary: SessionSummary,
    *,
    save_dir: Path | str = DEFAULT_CONFIG.save_dir,
) -> Path:
    """Return a unique JSON path for a session summary."""

    _validate_summary(summary)
    save_dir = ensure_save_dir(save_dir)
    timestamp = summary.started_at.strftime(SESSION_FILENAME_TIMESTAMP_FORMAT)
    base_name = f"{SESSION_FILENAME_PREFIX}_{timestamp}"
    candidate = save_dir / f"{base_name}.json"
    if not candidate.exists():
        return candidate

    suffix = 1
    while True:
        candidate = save_dir / f"{base_name}_{suffix:02}.json"
        if not candidate.exists():
            return candidate
        suffix += 1


def _validate_summary(summary: SessionSummary) -> None:
    if not isinstance(summary, SessionSummary):
        raise TypeError("summary must be a SessionSummary")


def _summary_csv_row(summary: SessionSummary) -> dict[str, object]:
    data = summary.to_dict()
    return {field: data[field] for field in CSV_FIELDNAMES}


def _validate_filename(name: str, filename: str) -> str:
    if not isinstance(filename, str):
        raise TypeError(f"{name} must be a string")

    if not filename.strip():
        raise ValueError(f"{name} must not be empty")

    if "/" in filename or "\\" in filename or Path(filename).name != filename:
        raise ValueError(f"{name} must be a file name, not a path")

    return filename


__all__ = [
    "CSV_FIELDNAMES",
    "CSV_FILENAME",
    "SESSION_FILENAME_PREFIX",
    "SESSION_FILENAME_TIMESTAMP_FORMAT",
    "SessionSaveResult",
    "append_session_csv",
    "ensure_save_dir",
    "next_session_json_path",
    "save_session_summary",
    "write_session_json",
]
