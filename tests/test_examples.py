import json
from datetime import datetime
from pathlib import Path

from focuslens.session import SessionSummary
from focuslens.storage import CSV_FIELDNAMES

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_sample_session_matches_current_summary_schema():
    sample_path = PROJECT_ROOT / "examples" / "sample_session.json"

    data = json.loads(sample_path.read_text(encoding="utf-8"))
    summary = SessionSummary(
        started_at=datetime.fromisoformat(data["started_at"]),
        ended_at=datetime.fromisoformat(data["ended_at"]),
        total_seconds=data["total_seconds"],
        focused_seconds=data["focused_seconds"],
        away_seconds=data["away_seconds"],
        looking_away_seconds=data["looking_away_seconds"],
        too_close_seconds=data["too_close_seconds"],
        too_far_seconds=data["too_far_seconds"],
        paused_seconds=data["paused_seconds"],
        unknown_seconds=data["unknown_seconds"],
        looking_away_events=data["looking_away_events"],
        away_events=data["away_events"],
        focus_score=data["focus_score"],
        presence_score=data["presence_score"],
    )

    assert set(data) == set(CSV_FIELDNAMES)
    assert summary.to_dict() == data
    assert "frame" not in json.dumps(data).lower()
    assert "image" not in json.dumps(data).lower()
