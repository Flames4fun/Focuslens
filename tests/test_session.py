from datetime import UTC, datetime, timedelta, timezone

import pytest

from focuslens.attention import AttentionAnalysis, AttentionState
from focuslens.config import FocusLensConfig
from focuslens.session import SessionSummary, SessionTracker

STARTED_AT = datetime(2026, 4, 30, 9, 0, tzinfo=UTC)
ENDED_AT = datetime(2026, 4, 30, 9, 30, tzinfo=UTC)


def fixed_clock(value=0.0):
    return lambda: value


def fixed_wall_clock(value=STARTED_AT):
    return lambda: value


def make_tracker(config=None):
    return SessionTracker(
        config or FocusLensConfig(),
        clock=fixed_clock(),
        wall_clock=fixed_wall_clock(),
    )


def test_empty_session_summary_does_not_fail():
    tracker = make_tracker()

    summary = tracker.finish(at_seconds=0.0, ended_at=STARTED_AT)

    assert summary.total_seconds == 0.0
    assert summary.focus_score == 0.0
    assert summary.presence_score == 0.0
    assert summary.looking_away_events == 0
    assert summary.away_events == 0


def test_tracker_accumulates_state_durations_scores_and_events():
    tracker = make_tracker()

    tracker.observe(AttentionState.FOCUSED, at_seconds=0.0)
    tracker.observe(AttentionState.LOOKING_AWAY, at_seconds=5.0)
    tracker.observe(AttentionState.AWAY, at_seconds=8.0)
    summary = tracker.finish(at_seconds=10.0, ended_at=ENDED_AT)

    assert summary.total_seconds == 10.0
    assert summary.focused_seconds == 5.0
    assert summary.looking_away_seconds == 3.0
    assert summary.away_seconds == 2.0
    assert summary.focus_score == 50.0
    assert summary.presence_score == 80.0
    assert summary.looking_away_events == 1
    assert summary.away_events == 1
    assert summary.duration_for(AttentionState.FOCUSED) == 5.0


def test_time_before_first_observation_counts_as_unknown():
    tracker = make_tracker()

    tracker.observe(AttentionState.FOCUSED, at_seconds=3.0)
    summary = tracker.finish(at_seconds=5.0, ended_at=ENDED_AT)

    assert summary.unknown_seconds == 3.0
    assert summary.focused_seconds == 2.0


def test_short_event_runs_are_not_counted():
    tracker = make_tracker(FocusLensConfig(min_event_duration_seconds=1.0))

    tracker.observe(AttentionState.LOOKING_AWAY, at_seconds=0.0)
    tracker.observe(AttentionState.FOCUSED, at_seconds=0.5)
    summary = tracker.finish(at_seconds=1.0, ended_at=ENDED_AT)

    assert summary.looking_away_seconds == 0.5
    assert summary.looking_away_events == 0


def test_event_cooldown_prevents_repeated_rapid_events():
    tracker = make_tracker(
        FocusLensConfig(min_event_duration_seconds=0.1, event_cooldown_seconds=2.0)
    )

    tracker.observe(AttentionState.LOOKING_AWAY, at_seconds=0.0)
    tracker.observe(AttentionState.FOCUSED, at_seconds=1.0)
    tracker.observe(AttentionState.LOOKING_AWAY, at_seconds=1.5)
    tracker.observe(AttentionState.FOCUSED, at_seconds=2.0)
    tracker.observe(AttentionState.LOOKING_AWAY, at_seconds=3.5)
    tracker.observe(AttentionState.FOCUSED, at_seconds=4.0)
    summary = tracker.finish(at_seconds=5.0, ended_at=ENDED_AT)

    assert summary.looking_away_events == 2


def test_snapshot_projects_current_event_without_finalizing_or_double_counting():
    tracker = make_tracker(FocusLensConfig(min_event_duration_seconds=1.0))

    tracker.observe(AttentionState.AWAY, at_seconds=0.0)
    first_snapshot = tracker.snapshot(at_seconds=1.2, ended_at=ENDED_AT)
    second_snapshot = tracker.snapshot(at_seconds=1.2, ended_at=ENDED_AT)
    final_summary = tracker.finish(at_seconds=1.2, ended_at=ENDED_AT)

    assert first_snapshot.away_events == 1
    assert second_snapshot.away_events == 1
    assert final_summary.away_events == 1
    assert tracker.finished is True


def test_tracker_accepts_attention_analysis_objects():
    tracker = make_tracker()

    tracker.observe(
        AttentionAnalysis(state=AttentionState.PAUSED, reason="manual_pause"),
        at_seconds=0.0,
    )
    summary = tracker.finish(at_seconds=2.5, ended_at=ENDED_AT)

    assert tracker.current_state == AttentionState.PAUSED
    assert summary.paused_seconds == 2.5
    assert summary.focus_score == 0.0
    assert summary.presence_score == 0.0


def test_scores_ignore_paused_seconds():
    tracker = make_tracker()

    tracker.observe(AttentionState.FOCUSED, at_seconds=0.0)
    tracker.observe(AttentionState.AWAY, at_seconds=8.0)
    tracker.observe(AttentionState.PAUSED, at_seconds=10.0)
    summary = tracker.finish(at_seconds=20.0, ended_at=ENDED_AT)

    assert summary.total_seconds == 20.0
    assert summary.focused_seconds == 8.0
    assert summary.away_seconds == 2.0
    assert summary.paused_seconds == 10.0
    assert summary.focus_score == 80.0
    assert summary.presence_score == 80.0


def test_tracker_rejects_backwards_timestamps_snapshots_and_observations_after_finish():
    tracker = make_tracker()

    tracker.observe(AttentionState.FOCUSED, at_seconds=1.0)
    with pytest.raises(ValueError, match="must not move backwards"):
        tracker.observe(AttentionState.AWAY, at_seconds=0.5)

    with pytest.raises(ValueError, match="must not move backwards"):
        tracker.snapshot(at_seconds=0.5)

    tracker.finish(at_seconds=2.0, ended_at=ENDED_AT)
    with pytest.raises(RuntimeError, match="already been finalized"):
        tracker.observe(AttentionState.AWAY, at_seconds=3.0)


def test_summary_to_dict_is_json_friendly():
    summary = SessionSummary(
        started_at=STARTED_AT,
        ended_at=STARTED_AT + timedelta(seconds=10),
        total_seconds=10.0,
        focused_seconds=7.5,
        away_seconds=2.5,
        away_events=1,
        focus_score=75.0,
        presence_score=75.0,
    )

    data = summary.to_dict()

    assert data["started_at"] == "2026-04-30T09:00:00+00:00"
    assert data["ended_at"] == "2026-04-30T09:00:10+00:00"
    assert data["focused_seconds"] == 7.5
    assert data["away_events"] == 1


def test_summary_rejects_invalid_values():
    with pytest.raises(ValueError, match="total_seconds must be"):
        SessionSummary(
            started_at=STARTED_AT,
            ended_at=ENDED_AT,
            total_seconds=-1,
        )

    with pytest.raises(ValueError, match="ended_at must not be earlier"):
        SessionSummary(
            started_at=ENDED_AT,
            ended_at=STARTED_AT,
            total_seconds=0,
        )

    with pytest.raises(ValueError, match="focus_score must be between 0 and 100"):
        SessionSummary(
            started_at=STARTED_AT,
            ended_at=ENDED_AT,
            total_seconds=0,
            focus_score=101,
        )

    with pytest.raises(ValueError, match="presence_score must be between 0 and 100"):
        SessionSummary(
            started_at=STARTED_AT,
            ended_at=ENDED_AT,
            total_seconds=0,
            presence_score=101,
        )

    with pytest.raises(ValueError, match="state durations must add up"):
        SessionSummary(
            started_at=STARTED_AT,
            ended_at=ENDED_AT,
            total_seconds=10,
            focused_seconds=100,
        )

    with pytest.raises(ValueError, match="state durations must add up"):
        SessionSummary(
            started_at=STARTED_AT,
            ended_at=ENDED_AT,
            total_seconds=10,
            focused_seconds=5,
        )


def test_summary_normalizes_naive_and_aware_datetimes_to_utc():
    local_timezone = timezone(timedelta(hours=-5))
    summary = SessionSummary(
        started_at=datetime(2026, 4, 30, 9, 0),
        ended_at=datetime(2026, 4, 30, 5, 30, tzinfo=local_timezone),
        total_seconds=10.0,
        focused_seconds=10.0,
        focus_score=100.0,
        presence_score=100.0,
    )

    assert summary.started_at == datetime(2026, 4, 30, 9, 0, tzinfo=UTC)
    assert summary.ended_at == datetime(2026, 4, 30, 10, 30, tzinfo=UTC)
