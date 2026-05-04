import csv
from datetime import UTC, datetime, timedelta

import pytest

from focuslens.dashboard import (
    DashboardDataError,
    build_history_rows,
    format_duration,
    load_session_summaries,
    summarize_sessions,
    validate_session_csv_path,
)
from focuslens.session import SessionSummary
from focuslens.storage import CSV_FIELDNAMES, CSV_FILENAME

STARTED_AT = datetime(2026, 5, 4, 9, 0, tzinfo=UTC)


def make_summary(**overrides):
    values = {
        "started_at": STARTED_AT,
        "ended_at": STARTED_AT + timedelta(minutes=10),
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


def write_csv(path, summaries):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for summary in summaries:
            writer.writerow(summary.to_dict())


def test_load_session_summaries_returns_empty_for_missing_csv(tmp_path):
    csv_path = tmp_path / CSV_FILENAME

    assert load_session_summaries(csv_path, allowed_root=tmp_path) == ()


def test_load_session_summaries_parses_valid_csv_in_started_order(tmp_path):
    csv_path = tmp_path / CSV_FILENAME
    first_started_at = STARTED_AT + timedelta(hours=1)
    first = make_summary(
        started_at=first_started_at,
        ended_at=first_started_at + timedelta(minutes=10),
    )
    second = make_summary(
        started_at=STARTED_AT,
        ended_at=STARTED_AT + timedelta(minutes=10),
    )
    write_csv(csv_path, [first, second])

    summaries = load_session_summaries(csv_path, allowed_root=tmp_path)

    assert [summary.started_at for summary in summaries] == [
        STARTED_AT,
        STARTED_AT + timedelta(hours=1),
    ]


def test_load_session_summaries_rejects_missing_columns(tmp_path):
    csv_path = tmp_path / CSV_FILENAME
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["started_at"])
        writer.writeheader()
        writer.writerow({"started_at": STARTED_AT.isoformat()})

    with pytest.raises(DashboardDataError, match="missing expected columns"):
        load_session_summaries(csv_path, allowed_root=tmp_path)


def test_load_session_summaries_rejects_invalid_row_values(tmp_path):
    csv_path = tmp_path / CSV_FILENAME
    summary = make_summary()
    write_csv(csv_path, [summary])
    content = csv_path.read_text(encoding="utf-8")
    csv_path.write_text(content.replace("73.68", "140.0"), encoding="utf-8")

    with pytest.raises(DashboardDataError, match="invalid data on row 2"):
        load_session_summaries(csv_path, allowed_root=tmp_path)


def test_validate_session_csv_path_rejects_reads_outside_allowed_root(tmp_path):
    allowed_root = tmp_path / "sessions"
    outside_path = tmp_path / "private.csv"

    with pytest.raises(DashboardDataError, match="only read FocusLens"):
        validate_session_csv_path(outside_path, allowed_root=allowed_root)


def test_summarize_sessions_builds_weighted_metrics_and_deltas():
    first = make_summary()
    second = make_summary(
        started_at=STARTED_AT + timedelta(hours=1),
        ended_at=STARTED_AT + timedelta(hours=1, minutes=10),
        focused_seconds=300.0,
        away_seconds=120.0,
        looking_away_seconds=60.0,
        too_close_seconds=30.0,
        too_far_seconds=30.0,
        paused_seconds=60.0,
        focus_score=55.56,
        presence_score=77.78,
    )

    stats = summarize_sessions((first, second))

    assert stats.session_count == 2
    assert stats.total_seconds == 1200.0
    assert stats.focused_seconds == 720.0
    assert stats.away_seconds == 180.0
    assert stats.active_seconds == 1110.0
    assert stats.focus_score == 64.86
    assert stats.presence_score == 83.78
    assert stats.focus_delta == -18.12
    assert stats.presence_delta == -11.69
    assert stats.looking_away_events == 6
    assert stats.away_events == 2


def test_build_history_rows_formats_safe_display_values():
    summary = make_summary()

    rows = build_history_rows((summary,))

    assert rows == [
        {
            "Session": 1,
            "Started": "2026-05-04 09:00 UTC",
            "Duration": "10m 00s",
            "Focus": "73.7%",
            "Presence": "89.5%",
            "Focused": "7m 00s",
            "Away": "1m 00s",
            "Looking away": "45s",
            "Look events": 3,
            "Away events": 1,
            "Paused": "30s",
        }
    ]


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0.0, "0s"),
        (9.4, "9s"),
        (65.0, "1m 05s"),
        (3661.0, "1h 01m"),
    ],
)
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected
