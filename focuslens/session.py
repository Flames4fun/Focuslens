"""Session metrics for FocusLens.

This module stores only derived attention states and aggregate timings. It does
not receive, persist, or serialize webcam frames.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite
from time import perf_counter
from types import MappingProxyType

from focuslens.attention import AttentionAnalysis, AttentionState
from focuslens.config import DEFAULT_CONFIG, FocusLensConfig

EVENT_STATES = frozenset({AttentionState.AWAY, AttentionState.LOOKING_AWAY})
SECONDS_TOLERANCE = 0.001


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class SessionSummary:
    """Immutable aggregate metrics for one FocusLens session."""

    started_at: datetime
    ended_at: datetime
    total_seconds: float
    focused_seconds: float = 0.0
    away_seconds: float = 0.0
    looking_away_seconds: float = 0.0
    too_close_seconds: float = 0.0
    too_far_seconds: float = 0.0
    paused_seconds: float = 0.0
    unknown_seconds: float = 0.0
    looking_away_events: int = 0
    away_events: int = 0
    focus_score: float = 0.0
    presence_score: float = 0.0

    def __post_init__(self) -> None:
        """Reject negative or impossible summary values."""

        object.__setattr__(self, "started_at", _normalize_datetime(self.started_at))
        object.__setattr__(self, "ended_at", _normalize_datetime(self.ended_at))

        for name in (
            "total_seconds",
            "focused_seconds",
            "away_seconds",
            "looking_away_seconds",
            "too_close_seconds",
            "too_far_seconds",
            "paused_seconds",
            "unknown_seconds",
        ):
            _validate_non_negative_finite(name, getattr(self, name))

        _validate_percentage("focus_score", self.focus_score)
        _validate_percentage("presence_score", self.presence_score)
        _validate_count("looking_away_events", self.looking_away_events)
        _validate_count("away_events", self.away_events)
        self._validate_state_total()

        if self.ended_at < self.started_at:
            raise ValueError("ended_at must not be earlier than started_at")

    def _validate_state_total(self) -> None:
        state_total = (
            self.focused_seconds
            + self.away_seconds
            + self.looking_away_seconds
            + self.too_close_seconds
            + self.too_far_seconds
            + self.paused_seconds
            + self.unknown_seconds
        )
        if abs(state_total - self.total_seconds) > SECONDS_TOLERANCE:
            raise ValueError("state durations must add up to total_seconds")

    def duration_for(self, state: AttentionState) -> float:
        """Return the accumulated duration for a specific attention state."""

        durations = {
            AttentionState.FOCUSED: self.focused_seconds,
            AttentionState.AWAY: self.away_seconds,
            AttentionState.LOOKING_AWAY: self.looking_away_seconds,
            AttentionState.TOO_CLOSE: self.too_close_seconds,
            AttentionState.TOO_FAR: self.too_far_seconds,
            AttentionState.PAUSED: self.paused_seconds,
            AttentionState.UNKNOWN: self.unknown_seconds,
        }
        return durations[state]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly dictionary for local storage."""

        return {
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "total_seconds": self.total_seconds,
            "focused_seconds": self.focused_seconds,
            "away_seconds": self.away_seconds,
            "looking_away_seconds": self.looking_away_seconds,
            "too_close_seconds": self.too_close_seconds,
            "too_far_seconds": self.too_far_seconds,
            "paused_seconds": self.paused_seconds,
            "unknown_seconds": self.unknown_seconds,
            "looking_away_events": self.looking_away_events,
            "away_events": self.away_events,
            "focus_score": self.focus_score,
            "presence_score": self.presence_score,
        }


class SessionTracker:
    """Accumulate attention states into a FocusLens session summary.

    Timing starts when the tracker is created. Time before the first real
    observation is counted as UNKNOWN so startup latency remains visible.
    """

    def __init__(
        self,
        config: FocusLensConfig = DEFAULT_CONFIG,
        *,
        clock: Callable[[], float] = perf_counter,
        wall_clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.config = config
        self._clock = clock
        self._wall_clock = wall_clock
        self.started_at = _normalize_datetime(wall_clock())
        self._started_seconds = _validate_timestamp("started_seconds", clock())
        self._last_observed_seconds = self._started_seconds
        self._current_state = AttentionState.UNKNOWN
        self._current_state_started_seconds = self._started_seconds
        self._current_run_event_counted = False
        self._state_seconds = _empty_state_seconds()
        self._event_counts = {
            AttentionState.AWAY: 0,
            AttentionState.LOOKING_AWAY: 0,
        }
        self._last_event_seconds: dict[AttentionState, float] = {}
        self._finished_summary: SessionSummary | None = None

    @property
    def current_state(self) -> AttentionState:
        """Return the state currently being timed."""

        return self._current_state

    @property
    def finished(self) -> bool:
        """Return whether this tracker has already been finalized."""

        return self._finished_summary is not None

    def observe(
        self,
        observation: AttentionAnalysis | AttentionState,
        *,
        at_seconds: float | None = None,
    ) -> None:
        """Record the current attention state at a monotonic timestamp."""

        self._ensure_open()
        observed_seconds = self._timestamp_or_now(at_seconds)
        self._advance_to(observed_seconds)

        next_state = _state_from_observation(observation)
        if next_state != self._current_state:
            self._current_state = next_state
            self._current_state_started_seconds = observed_seconds
            self._current_run_event_counted = False

    record = observe

    def snapshot(
        self,
        *,
        at_seconds: float | None = None,
        ended_at: datetime | None = None,
    ) -> SessionSummary:
        """Return a non-final summary of the session up to now."""

        if self._finished_summary is not None:
            return self._finished_summary

        snapshot_seconds = self._timestamp_or_now(at_seconds)
        _validate_monotonic_timestamp(snapshot_seconds, self._last_observed_seconds)
        state_seconds = dict(self._state_seconds)
        event_counts = dict(self._event_counts)

        elapsed = snapshot_seconds - self._last_observed_seconds
        state_seconds[self._current_state] += elapsed
        self._project_current_event(snapshot_seconds, event_counts)

        return self._build_summary(
            state_seconds,
            event_counts,
            ended_at=_normalize_datetime(ended_at or self._wall_clock()),
        )

    def finish(
        self,
        *,
        at_seconds: float | None = None,
        ended_at: datetime | None = None,
    ) -> SessionSummary:
        """Finalize the session and return its summary."""

        if self._finished_summary is not None:
            return self._finished_summary

        finished_seconds = self._timestamp_or_now(at_seconds)
        self._advance_to(finished_seconds)
        self._finished_summary = self._build_summary(
            self._state_seconds,
            self._event_counts,
            ended_at=_normalize_datetime(ended_at or self._wall_clock()),
        )
        return self._finished_summary

    def _advance_to(self, timestamp_seconds: float) -> None:
        _validate_monotonic_timestamp(timestamp_seconds, self._last_observed_seconds)

        elapsed = timestamp_seconds - self._last_observed_seconds
        self._state_seconds[self._current_state] += elapsed
        self._last_observed_seconds = timestamp_seconds
        self._maybe_count_current_event(timestamp_seconds)

    def _maybe_count_current_event(self, timestamp_seconds: float) -> None:
        if self._current_run_event_counted:
            return

        if not self._event_should_count(timestamp_seconds):
            return

        self._event_counts[self._current_state] += 1
        self._last_event_seconds[self._current_state] = timestamp_seconds
        self._current_run_event_counted = True

    def _project_current_event(
        self,
        timestamp_seconds: float,
        event_counts: dict[AttentionState, int],
    ) -> None:
        if self._current_run_event_counted:
            return

        if self._event_should_count(timestamp_seconds):
            event_counts[self._current_state] += 1

    def _event_should_count(self, timestamp_seconds: float) -> bool:
        if self._current_state not in EVENT_STATES:
            return False

        run_duration = timestamp_seconds - self._current_state_started_seconds
        if run_duration < self.config.min_event_duration_seconds:
            return False

        last_event_seconds = self._last_event_seconds.get(self._current_state)
        if last_event_seconds is None:
            return True

        return (
            timestamp_seconds - last_event_seconds >= self.config.event_cooldown_seconds
        )

    def _build_summary(
        self,
        state_seconds: Mapping[AttentionState, float],
        event_counts: Mapping[AttentionState, int],
        *,
        ended_at: datetime,
    ) -> SessionSummary:
        durations = MappingProxyType(
            {
                state: _clean_seconds(state_seconds.get(state, 0.0))
                for state in AttentionState
            }
        )
        total_seconds = _clean_seconds(sum(durations.values()))
        focused_seconds = durations[AttentionState.FOCUSED]
        away_seconds = durations[AttentionState.AWAY]
        paused_seconds = durations[AttentionState.PAUSED]
        active_seconds = max(0.0, total_seconds - paused_seconds)

        return SessionSummary(
            started_at=self.started_at,
            ended_at=ended_at,
            total_seconds=total_seconds,
            focused_seconds=focused_seconds,
            away_seconds=away_seconds,
            looking_away_seconds=durations[AttentionState.LOOKING_AWAY],
            too_close_seconds=durations[AttentionState.TOO_CLOSE],
            too_far_seconds=durations[AttentionState.TOO_FAR],
            paused_seconds=paused_seconds,
            unknown_seconds=durations[AttentionState.UNKNOWN],
            looking_away_events=event_counts[AttentionState.LOOKING_AWAY],
            away_events=event_counts[AttentionState.AWAY],
            focus_score=_percentage(focused_seconds, active_seconds),
            presence_score=_percentage(active_seconds - away_seconds, active_seconds),
        )

    def _timestamp_or_now(self, at_seconds: float | None) -> float:
        timestamp_seconds = self._clock() if at_seconds is None else at_seconds
        return _validate_timestamp("at_seconds", timestamp_seconds)

    def _ensure_open(self) -> None:
        if self._finished_summary is not None:
            raise RuntimeError("SessionTracker has already been finalized")


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def _empty_state_seconds() -> dict[AttentionState, float]:
    return {state: 0.0 for state in AttentionState}


def _state_from_observation(
    observation: AttentionAnalysis | AttentionState,
) -> AttentionState:
    if isinstance(observation, AttentionState):
        return observation

    return observation.state


def _validate_timestamp(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a finite number")

    if not isfinite(value):
        raise ValueError(f"{name} must be a finite number")

    return float(value)


def _validate_monotonic_timestamp(value: float, previous_value: float) -> None:
    if value < previous_value:
        raise ValueError("at_seconds must not move backwards")


def _validate_non_negative_finite(name: str, value: float) -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a non-negative finite number")


def _validate_percentage(name: str, value: float) -> None:
    if not isfinite(value) or not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100")


def _validate_count(name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _clean_seconds(value: float) -> float:
    return round(value, 6)


def _percentage(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0

    return round((numerator / denominator) * 100, 2)


__all__ = [
    "EVENT_STATES",
    "SECONDS_TOLERANCE",
    "SessionSummary",
    "SessionTracker",
]
