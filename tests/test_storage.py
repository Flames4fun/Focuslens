import csv
import json
from datetime import UTC, datetime, timedelta

import pytest

from focuslens.session import SessionSummary
from focuslens.storage import (
    CSV_FIELDNAMES,
    CSV_FILENAME,
    append_session_csv,
    ensure_save_dir,
    next_session_json_path,
    save_session_summary,
    write_session_json,
)

STARTED_AT = datetime(2026, 4, 30, 9, 0, tzinfo=UTC)
ENDED_AT = STARTED_AT + timedelta(minutes=10)


def make_summary(**overrides):
    values = {
        "started_at": STARTED_AT,
        "ended_at": ENDED_AT,
        "total_seconds": 600.0,
        "focused_seconds": 420.0,
        "away_seconds": 60.0,
        "looking_away_seconds": 45.0,
        "too_close_seconds": 30.0,
        "too_far_seconds": 15.0,
        "paused_seconds": 30.0,
        "unknown_seconds": 0.0,
        "looking_away_events": 3,
        "away_events": 1,
        "focus_score": 73.68,
        "presence_score": 89.47,
    }
    values.update(overrides)
    return SessionSummary(**values)


def test_ensure_save_dir_creates_directory(tmp_path):
    save_dir = tmp_path / "nested" / "sessions"

    result = ensure_save_dir(save_dir)

    assert result == save_dir.resolve()
    assert save_dir.is_dir()


def test_ensure_save_dir_returns_resolved_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = ensure_save_dir("sessions")

    assert result == (tmp_path / "sessions").resolve()
    assert result.is_absolute()


def test_ensure_save_dir_rejects_existing_file(tmp_path):
    save_path = tmp_path / "sessions"
    save_path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(NotADirectoryError, match="not a directory"):
        ensure_save_dir(save_path)


def test_write_session_json_saves_summary_without_frames(tmp_path):
    summary = make_summary()

    json_path = write_session_json(summary, save_dir=tmp_path)

    assert json_path.name == "session_2026-04-30_09-00-00.json"
    assert json_path.parent == tmp_path
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data == summary.to_dict()
    assert "frame" not in json.dumps(data).lower()
    assert "image" not in json.dumps(data).lower()
    assert not (tmp_path / "session_2026-04-30_09-00-00.json.tmp").exists()


def test_next_session_json_path_uses_suffix_when_file_exists(tmp_path):
    summary = make_summary()
    existing_path = tmp_path / "session_2026-04-30_09-00-00.json"
    existing_path.write_text("{}", encoding="utf-8")

    path = next_session_json_path(summary, save_dir=tmp_path)

    assert path.name == "session_2026-04-30_09-00-00_01.json"


def test_append_session_csv_creates_header_and_appends_rows(tmp_path):
    first_summary = make_summary()
    second_summary = make_summary(
        started_at=STARTED_AT + timedelta(hours=1),
        ended_at=ENDED_AT + timedelta(hours=1),
        focused_seconds=300.0,
        away_seconds=120.0,
        looking_away_seconds=60.0,
        too_close_seconds=30.0,
        too_far_seconds=30.0,
        paused_seconds=60.0,
        focus_score=55.56,
        presence_score=77.78,
    )

    csv_path = append_session_csv(first_summary, save_dir=tmp_path)
    second_csv_path = append_session_csv(second_summary, save_dir=tmp_path)

    assert csv_path == second_csv_path == tmp_path / CSV_FILENAME
    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 2
    assert tuple(rows[0]) == CSV_FIELDNAMES
    assert rows[0]["started_at"] == "2026-04-30T09:00:00+00:00"
    assert rows[0]["focused_seconds"] == "420.0"
    assert rows[1]["focused_seconds"] == "300.0"


def test_append_session_csv_rejects_empty_filename(tmp_path):
    with pytest.raises(ValueError, match="csv_filename must not be empty"):
        append_session_csv(make_summary(), save_dir=tmp_path, csv_filename=" ")


@pytest.mark.parametrize(
    "csv_filename",
    [
        "../other.csv",
        "nested/sessions.csv",
        r"nested\sessions.csv",
        "/tmp/sessions.csv",
    ],
)
def test_append_session_csv_rejects_paths_as_filenames(tmp_path, csv_filename):
    with pytest.raises(ValueError, match="file name, not a path"):
        append_session_csv(make_summary(), save_dir=tmp_path, csv_filename=csv_filename)


def test_storage_rejects_invalid_summary_type(tmp_path):
    with pytest.raises(TypeError, match="summary must be a SessionSummary"):
        save_session_summary({"fake": "data"}, save_dir=tmp_path)

    with pytest.raises(TypeError, match="summary must be a SessionSummary"):
        write_session_json({"fake": "data"}, save_dir=tmp_path)

    with pytest.raises(TypeError, match="summary must be a SessionSummary"):
        append_session_csv({"fake": "data"}, save_dir=tmp_path)

    with pytest.raises(TypeError, match="summary must be a SessionSummary"):
        next_session_json_path({"fake": "data"}, save_dir=tmp_path)


def test_save_session_summary_writes_json_and_csv(tmp_path):
    summary = make_summary()

    result = save_session_summary(summary, save_dir=tmp_path)

    assert result.json_path.is_file()
    assert result.csv_path.is_file()
    assert result.csv_path.name == CSV_FILENAME
    assert json.loads(result.json_path.read_text(encoding="utf-8")) == summary.to_dict()
