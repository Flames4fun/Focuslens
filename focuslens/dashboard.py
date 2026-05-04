"""Local Streamlit dashboard for FocusLens session summaries.

The dashboard reads only the aggregate CSV written by ``focuslens.storage``.
It does not read webcam frames, JSON session files, environment secrets, or
external URLs.
"""

from __future__ import annotations

import csv
import html
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module
from math import isfinite
from pathlib import Path
from typing import Any

from focuslens.config import DEFAULT_CONFIG
from focuslens.session import SECONDS_TOLERANCE, SessionSummary
from focuslens.storage import CSV_FIELDNAMES, CSV_FILENAME

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_SESSION_ROOT = PROJECT_ROOT / DEFAULT_CONFIG.save_dir
DEFAULT_SESSION_CSV_PATH = LOCAL_SESSION_ROOT / CSV_FILENAME

SECONDS_FIELDS = (
    "total_seconds",
    "focused_seconds",
    "away_seconds",
    "looking_away_seconds",
    "too_close_seconds",
    "too_far_seconds",
    "paused_seconds",
    "unknown_seconds",
)
EVENT_FIELDS = ("looking_away_events", "away_events")
SCORE_FIELDS = ("focus_score", "presence_score")
STATE_TOTAL_LABELS = (
    ("Focused", "focused_seconds", "#ff2d3d"),
    ("Away", "away_seconds", "#7b1d25"),
    ("Looking away", "looking_away_seconds", "#d72a38"),
    ("Too close", "too_close_seconds", "#ff6b75"),
    ("Too far", "too_far_seconds", "#a8313b"),
    ("Paused", "paused_seconds", "#787f8b"),
    ("Unknown", "unknown_seconds", "#3c414c"),
)


class DashboardDataError(RuntimeError):
    """Raised when local session history cannot be loaded safely."""


@dataclass(frozen=True, slots=True)
class DashboardStats:
    """Aggregate metrics ready for dashboard presentation."""

    session_count: int
    total_seconds: float
    active_seconds: float
    focused_seconds: float
    away_seconds: float
    looking_away_seconds: float
    too_close_seconds: float
    too_far_seconds: float
    paused_seconds: float
    unknown_seconds: float
    looking_away_events: int
    away_events: int
    focus_score: float
    presence_score: float
    average_focus_score: float
    average_presence_score: float
    best_focus_score: float
    focus_delta: float
    presence_delta: float
    latest_summary: SessionSummary | None


def main() -> None:
    """Render the Streamlit app."""

    st = _load_streamlit()
    pd = _load_pandas(st)

    st.set_page_config(
        page_title="FocusLens Dashboard",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _apply_visual_system(st)

    csv_path = DEFAULT_SESSION_CSV_PATH
    file_signature = _file_signature(csv_path)
    if st.button("Refresh", type="secondary"):
        st.cache_data.clear()

    cached_loader = st.cache_data(show_spinner=False)(_load_session_summaries_uncached)
    try:
        summaries = cached_loader(
            str(csv_path),
            str(LOCAL_SESSION_ROOT),
            file_signature,
        )
    except DashboardDataError as exc:
        _render_header(st, session_count=0)
        _render_data_error(st, exc)
        return

    _render_header(st, session_count=len(summaries))
    if not summaries:
        _render_empty_state(st)
        return

    stats = summarize_sessions(summaries)
    _render_score_console(st, stats)
    _render_metric_grid(st, stats)
    _render_charts(st, pd, summaries, stats)
    _render_history_table(st, pd, summaries)
    _render_privacy_footer(st)


def load_session_summaries(
    csv_path: Path | str = DEFAULT_SESSION_CSV_PATH,
    *,
    allowed_root: Path | str | None = LOCAL_SESSION_ROOT,
) -> tuple[SessionSummary, ...]:
    """Load validated session summaries from the local FocusLens CSV file."""

    safe_csv_path = validate_session_csv_path(csv_path, allowed_root=allowed_root)
    if not safe_csv_path.exists():
        return ()

    if safe_csv_path.stat().st_size == 0:
        return ()

    try:
        with safe_csv_path.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            _validate_csv_header(reader.fieldnames)
            summaries = tuple(
                _parse_session_row(row, row_number=row_number)
                for row_number, row in enumerate(reader, start=2)
            )
    except OSError as exc:
        raise DashboardDataError("Could not read local session history.") from exc

    return tuple(sorted(summaries, key=lambda summary: summary.started_at))


def validate_session_csv_path(
    csv_path: Path | str,
    *,
    allowed_root: Path | str | None = LOCAL_SESSION_ROOT,
) -> Path:
    """Resolve the session CSV path without allowing reads outside the safe root."""

    candidate = Path(csv_path).expanduser()
    if allowed_root is None:
        return candidate.resolve(strict=False)

    safe_root = Path(allowed_root).expanduser().resolve(strict=False)
    if not candidate.is_absolute():
        candidate = safe_root / candidate

    resolved = candidate.resolve(strict=False)
    if not _path_is_relative_to(resolved, safe_root):
        raise DashboardDataError("Dashboard can only read FocusLens session history.")

    if candidate.exists() and not candidate.is_file():
        raise DashboardDataError("Session history path is not a CSV file.")

    return candidate


def summarize_sessions(summaries: tuple[SessionSummary, ...]) -> DashboardStats:
    """Build aggregate dashboard metrics from validated session summaries."""

    if not summaries:
        return DashboardStats(
            session_count=0,
            total_seconds=0.0,
            active_seconds=0.0,
            focused_seconds=0.0,
            away_seconds=0.0,
            looking_away_seconds=0.0,
            too_close_seconds=0.0,
            too_far_seconds=0.0,
            paused_seconds=0.0,
            unknown_seconds=0.0,
            looking_away_events=0,
            away_events=0,
            focus_score=0.0,
            presence_score=0.0,
            average_focus_score=0.0,
            average_presence_score=0.0,
            best_focus_score=0.0,
            focus_delta=0.0,
            presence_delta=0.0,
            latest_summary=None,
        )

    total_seconds = _sum_field(summaries, "total_seconds")
    focused_seconds = _sum_field(summaries, "focused_seconds")
    away_seconds = _sum_field(summaries, "away_seconds")
    looking_away_seconds = _sum_field(summaries, "looking_away_seconds")
    too_close_seconds = _sum_field(summaries, "too_close_seconds")
    too_far_seconds = _sum_field(summaries, "too_far_seconds")
    paused_seconds = _sum_field(summaries, "paused_seconds")
    unknown_seconds = _sum_field(summaries, "unknown_seconds")
    active_seconds = max(0.0, total_seconds - paused_seconds)
    latest_summary = summaries[-1]

    return DashboardStats(
        session_count=len(summaries),
        total_seconds=round(total_seconds, 6),
        active_seconds=round(active_seconds, 6),
        focused_seconds=round(focused_seconds, 6),
        away_seconds=round(away_seconds, 6),
        looking_away_seconds=round(looking_away_seconds, 6),
        too_close_seconds=round(too_close_seconds, 6),
        too_far_seconds=round(too_far_seconds, 6),
        paused_seconds=round(paused_seconds, 6),
        unknown_seconds=round(unknown_seconds, 6),
        looking_away_events=sum(summary.looking_away_events for summary in summaries),
        away_events=sum(summary.away_events for summary in summaries),
        focus_score=_percentage(focused_seconds, active_seconds),
        presence_score=_percentage(active_seconds - away_seconds, active_seconds),
        average_focus_score=_average_field(summaries, "focus_score"),
        average_presence_score=_average_field(summaries, "presence_score"),
        best_focus_score=max(summary.focus_score for summary in summaries),
        focus_delta=_score_delta(summaries, "focus_score"),
        presence_delta=_score_delta(summaries, "presence_score"),
        latest_summary=latest_summary,
    )


def build_history_rows(
    summaries: tuple[SessionSummary, ...],
) -> list[dict[str, object]]:
    """Return sanitized table rows for Streamlit display."""

    rows: list[dict[str, object]] = []
    for index, summary in enumerate(summaries, start=1):
        rows.append(
            {
                "Session": index,
                "Started": _format_datetime(summary.started_at),
                "Duration": format_duration(summary.total_seconds),
                "Focus": format_score(summary.focus_score),
                "Presence": format_score(summary.presence_score),
                "Focused": format_duration(summary.focused_seconds),
                "Away": format_duration(summary.away_seconds),
                "Looking away": format_duration(summary.looking_away_seconds),
                "Look events": summary.looking_away_events,
                "Away events": summary.away_events,
                "Paused": format_duration(summary.paused_seconds),
            }
        )

    return rows


def format_duration(seconds: float) -> str:
    """Format seconds as a compact human-readable duration."""

    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds_part = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes:02}m"

    if minutes:
        return f"{minutes}m {seconds_part:02}s"

    return f"{seconds_part}s"


def format_score(score: float) -> str:
    """Format a percentage for the dashboard UI."""

    return f"{score:.1f}%"


def _load_streamlit() -> Any:
    try:
        return import_module("streamlit")
    except ImportError as exc:
        raise RuntimeError(
            "Streamlit is required for the FocusLens dashboard. "
            'Install the project with: python -m pip install -e ".[dev]"'
        ) from exc


def _load_pandas(st: Any) -> Any:
    try:
        return import_module("pandas")
    except ImportError:
        st.error(
            "pandas is required for the FocusLens dashboard. Install with "
            '`python -m pip install -e ".[dev]"`.'
        )
        st.stop()


def _validate_csv_header(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise DashboardDataError("Session history is empty or missing a CSV header.")

    missing_fields = [field for field in CSV_FIELDNAMES if field not in fieldnames]
    if missing_fields:
        raise DashboardDataError("Session history is missing expected columns.")


def _parse_session_row(row: dict[str, str], *, row_number: int) -> SessionSummary:
    try:
        values = {
            "started_at": _parse_datetime(row["started_at"]),
            "ended_at": _parse_datetime(row["ended_at"]),
            **{
                field: _parse_non_negative_float(row[field], field=field)
                for field in SECONDS_FIELDS
            },
            **{
                field: _parse_non_negative_int(row[field], field=field)
                for field in EVENT_FIELDS
            },
            **{
                field: _parse_percentage(row[field], field=field)
                for field in SCORE_FIELDS
            },
        }
        summary = SessionSummary(**values)
    except (KeyError, TypeError, ValueError) as exc:
        raise DashboardDataError(
            f"Session history contains invalid data on row {row_number}."
        ) from exc

    state_total = sum(
        float(values[field]) for field in SECONDS_FIELDS if field != "total_seconds"
    )
    if abs(state_total - summary.total_seconds) > SECONDS_TOLERANCE:
        raise DashboardDataError(
            f"Session history contains invalid state totals on row {row_number}."
        )

    return summary


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(_strip_csv_value(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _parse_non_negative_float(value: str, *, field: str) -> float:
    try:
        parsed = float(_strip_csv_value(value))
    except ValueError as exc:
        raise ValueError(f"{field} must be numeric") from exc

    if not isfinite(parsed) or parsed < 0:
        raise ValueError(f"{field} must be non-negative and finite")

    return parsed


def _parse_non_negative_int(value: str, *, field: str) -> int:
    stripped = _strip_csv_value(value)
    try:
        parsed = int(stripped)
    except ValueError as exc:
        raise ValueError(f"{field} must be an integer") from exc

    if parsed < 0:
        raise ValueError(f"{field} must be non-negative")

    return parsed


def _parse_percentage(value: str, *, field: str) -> float:
    parsed = _parse_non_negative_float(value, field=field)
    if parsed > 100:
        raise ValueError(f"{field} must be at most 100")

    return parsed


def _strip_csv_value(value: str) -> str:
    if value is None:
        raise ValueError("CSV value is missing")

    stripped = str(value).strip()
    if not stripped:
        raise ValueError("CSV value is empty")

    return stripped


def _sum_field(summaries: tuple[SessionSummary, ...], field: str) -> float:
    return sum(float(getattr(summary, field)) for summary in summaries)


def _average_field(summaries: tuple[SessionSummary, ...], field: str) -> float:
    return round(_sum_field(summaries, field) / len(summaries), 2)


def _score_delta(summaries: tuple[SessionSummary, ...], field: str) -> float:
    if len(summaries) < 2:
        return 0.0

    return round(
        float(getattr(summaries[-1], field)) - float(getattr(summaries[-2], field)),
        2,
    )


def _percentage(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0

    return round((numerator / denominator) * 100, 2)


def _file_signature(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False

    return True


def _format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _state_totals(stats: DashboardStats) -> list[dict[str, object]]:
    return [
        {
            "State": label,
            "Minutes": round(float(getattr(stats, field)) / 60, 2),
            "Color": color,
        }
        for label, field, color in STATE_TOTAL_LABELS
        if float(getattr(stats, field)) > 0
    ]


def _session_signal_rows(
    summaries: tuple[SessionSummary, ...],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, summary in enumerate(summaries, start=1):
        session_label = f"S{index}"
        started_at = _format_datetime(summary.started_at)
        rows.extend(
            [
                {
                    "Session": session_label,
                    "Started": started_at,
                    "Signal": "Focus",
                    "Score": summary.focus_score,
                },
                {
                    "Session": session_label,
                    "Started": started_at,
                    "Signal": "Presence",
                    "Score": summary.presence_score,
                },
            ]
        )

    return rows


def _event_rows(stats: DashboardStats) -> list[dict[str, object]]:
    return [
        {"Event": "Looking away", "Count": stats.looking_away_events},
        {"Event": "Away", "Count": stats.away_events},
    ]


def _load_session_summaries_uncached(
    csv_path: str,
    allowed_root: str,
    file_signature: int,
) -> tuple[SessionSummary, ...]:
    del file_signature
    return load_session_summaries(
        Path(csv_path),
        allowed_root=Path(allowed_root),
    )


def _apply_visual_system(st: Any) -> None:
    st.markdown(
        """
        <style>
        :root {
          --fl-bg: #050507;
          --fl-panel: rgba(15, 16, 20, 0.86);
          --fl-panel-strong: rgba(24, 18, 22, 0.94);
          --fl-red: #ff2d3d;
          --fl-red-soft: #d91f31;
          --fl-red-dark: #6d111c;
          --fl-text: #f6f7fb;
          --fl-muted: #a9afbb;
          --fl-line: rgba(255, 45, 61, 0.28);
          --fl-line-soft: rgba(255, 255, 255, 0.08);
          --fl-font: "Space Grotesk", "Inter", "Segoe UI", Arial, sans-serif;
        }

        .stApp {
          background:
            linear-gradient(135deg, rgba(255, 45, 61, 0.08), transparent 32%),
            linear-gradient(225deg, rgba(255, 45, 61, 0.06), transparent 36%),
            linear-gradient(180deg, #050507 0%, #09090d 52%, #050507 100%);
          color: var(--fl-text);
          font-family: var(--fl-font);
        }

        .block-container {
          max-width: 1280px;
          padding-top: 28px;
          padding-bottom: 48px;
        }

        [data-testid="stHeader"] {
          background: transparent;
        }

        div.stButton > button {
          border: 1px solid var(--fl-line);
          background: rgba(8, 8, 12, 0.72);
          color: var(--fl-text);
          border-radius: 8px;
          min-height: 38px;
          transition: transform 160ms ease, border-color 160ms ease,
            background 160ms ease;
        }

        div.stButton > button:hover {
          border-color: rgba(255, 45, 61, 0.78);
          background: rgba(255, 45, 61, 0.12);
          transform: translateY(-1px);
        }

        .focuslens-hero {
          position: relative;
          overflow: hidden;
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 24px;
          align-items: center;
          border: 1px solid var(--fl-line);
          border-radius: 8px;
          background:
            linear-gradient(90deg, rgba(255, 45, 61, 0.15), transparent 42%),
            repeating-linear-gradient(
              90deg,
              rgba(255, 255, 255, 0.03) 0 1px,
              transparent 1px 48px
            ),
            var(--fl-panel);
          padding: 26px;
          box-shadow: 0 22px 64px rgba(0, 0, 0, 0.38);
          animation: cardEnter 520ms ease both;
        }

        .focuslens-hero::before {
          content: "";
          position: absolute;
          inset: 0;
          background: linear-gradient(
            100deg,
            transparent 0%,
            rgba(255, 45, 61, 0.18) 48%,
            transparent 63%
          );
          transform: translateX(-120%);
          animation: lensSweep 5.4s ease-in-out infinite;
          pointer-events: none;
        }

        .focuslens-hero h1 {
          position: relative;
          margin: 0;
          color: var(--fl-text);
          font-family: var(--fl-font);
          font-size: 34px;
          font-weight: 800;
          line-height: 1.08;
          letter-spacing: 0;
        }

        .focuslens-kicker {
          position: relative;
          margin: 0 0 10px;
          color: var(--fl-red);
          font-size: 13px;
          font-weight: 800;
        }

        .focuslens-copy {
          position: relative;
          max-width: 760px;
          margin: 12px 0 0;
          color: var(--fl-muted);
          font-size: 15px;
          line-height: 1.6;
        }

        .focuslens-chiprail {
          position: relative;
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          justify-content: flex-end;
        }

        .focuslens-chip {
          border: 1px solid var(--fl-line);
          border-radius: 999px;
          padding: 7px 10px;
          color: var(--fl-text);
          background: rgba(255, 45, 61, 0.08);
          font-size: 12px;
          font-weight: 700;
        }

        .score-dial {
          position: relative;
          min-height: 248px;
          border: 1px solid var(--fl-line);
          border-radius: 8px;
          background:
            linear-gradient(160deg, rgba(255, 45, 61, 0.14), transparent 45%),
            var(--fl-panel-strong);
          padding: 22px;
          overflow: hidden;
          animation: cardEnter 620ms ease both;
        }

        .score-dial::after {
          content: "";
          position: absolute;
          left: 0;
          right: 0;
          top: 0;
          height: 1px;
          background: linear-gradient(
            90deg,
            transparent,
            var(--fl-red),
            transparent
          );
          animation: pulseRail 2.8s ease-in-out infinite;
        }

        .score-ring {
          width: 138px;
          height: 138px;
          border-radius: 50%;
          display: grid;
          place-items: center;
          background:
            radial-gradient(circle, #101117 0 54%, transparent 55%),
            conic-gradient(
              var(--fl-red) calc(var(--score) * 1%),
              rgba(255, 255, 255, 0.1) 0
            );
          box-shadow:
            0 0 34px rgba(255, 45, 61, 0.22),
            inset 0 0 32px rgba(0, 0, 0, 0.54);
        }

        .score-ring span {
          color: var(--fl-text);
          font-size: 28px;
          font-weight: 900;
        }

        .score-title {
          margin: 18px 0 6px;
          color: var(--fl-text);
          font-size: 18px;
          font-weight: 800;
        }

        .score-detail,
        .metric-caption,
        .section-caption {
          color: var(--fl-muted);
          font-size: 13px;
          line-height: 1.5;
        }

        .score-delta {
          position: absolute;
          right: 18px;
          top: 18px;
          border: 1px solid var(--fl-line);
          border-radius: 999px;
          padding: 6px 9px;
          color: var(--fl-text);
          background: rgba(5, 5, 7, 0.72);
          font-size: 12px;
          font-weight: 800;
        }

        .metric-card {
          min-height: 136px;
          border: 1px solid var(--fl-line-soft);
          border-radius: 8px;
          background: rgba(12, 13, 17, 0.84);
          padding: 18px;
          animation: cardEnter 700ms ease both;
          transition: transform 160ms ease, border-color 160ms ease;
        }

        .metric-card:hover {
          transform: translateY(-2px);
          border-color: rgba(255, 45, 61, 0.55);
        }

        .metric-label {
          margin: 0 0 8px;
          color: var(--fl-muted);
          font-size: 12px;
          font-weight: 800;
        }

        .metric-value {
          margin: 0;
          color: var(--fl-text);
          font-size: 25px;
          font-weight: 900;
          line-height: 1.1;
        }

        .focuslens-section {
          margin-top: 22px;
          border-top: 1px solid var(--fl-line);
          padding-top: 18px;
        }

        .section-title {
          margin: 0 0 4px;
          color: var(--fl-text);
          font-size: 20px;
          font-weight: 850;
          letter-spacing: 0;
        }

        .empty-state,
        .data-alert,
        .privacy-footer {
          border: 1px solid var(--fl-line);
          border-radius: 8px;
          background: rgba(12, 13, 17, 0.9);
          padding: 22px;
          animation: cardEnter 520ms ease both;
        }

        .data-alert {
          border-color: rgba(255, 89, 100, 0.72);
        }

        .privacy-footer {
          margin-top: 26px;
          color: var(--fl-muted);
          font-size: 13px;
        }

        @keyframes lensSweep {
          0%, 48% { transform: translateX(-120%); }
          72%, 100% { transform: translateX(120%); }
        }

        @keyframes pulseRail {
          0%, 100% { opacity: 0.32; }
          50% { opacity: 1; }
        }

        @keyframes cardEnter {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @media (max-width: 760px) {
          .focuslens-hero {
            grid-template-columns: 1fr;
            padding: 20px;
          }

          .focuslens-chiprail {
            justify-content: flex-start;
          }

          .focuslens-hero h1 {
            font-size: 28px;
          }
        }

        @media (prefers-reduced-motion: reduce) {
          *,
          *::before,
          *::after {
            animation: none !important;
            transition: none !important;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header(st: Any, *, session_count: int) -> None:
    st.markdown(
        f"""
        <section class="focuslens-hero">
          <div>
            <p class="focuslens-kicker">FocusLens Dashboard</p>
            <h1>Redline signal console</h1>
            <p class="focuslens-copy">
              Local-only focus telemetry from aggregate session summaries.
              No frames, no video, no cloud sync, no identity layer.
            </p>
          </div>
          <div class="focuslens-chiprail" aria-label="Dashboard status">
            <span class="focuslens-chip">{_escape(session_count)} sessions</span>
            <span class="focuslens-chip">Local CSV</span>
            <span class="focuslens-chip">Private by default</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_empty_state(st: Any) -> None:
    st.markdown(
        """
        <section class="empty-state">
          <p class="section-title">No session history yet</p>
          <p class="section-caption">
            The dashboard is ready for <code>sessions/sessions.csv</code>.
            Once FocusLens records a session, the console will populate with
            scores, state distribution, event patterns, and session history.
          </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_data_error(st: Any, exc: DashboardDataError) -> None:
    st.markdown(
        f"""
        <section class="data-alert">
          <p class="section-title">Session history could not be loaded</p>
          <p class="section-caption">{_escape(exc)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_score_console(st: Any, stats: DashboardStats) -> None:
    focus_col, presence_col, latest_col = st.columns([1, 1, 1])
    with focus_col:
        _render_score_dial(
            st,
            title="Weighted focus",
            score=stats.focus_score,
            delta=stats.focus_delta,
            detail=(
                f"{format_duration(stats.focused_seconds)} focused across "
                f"{format_duration(stats.active_seconds)} active time."
            ),
        )

    with presence_col:
        _render_score_dial(
            st,
            title="Weighted presence",
            score=stats.presence_score,
            delta=stats.presence_delta,
            detail=(
                f"{format_duration(stats.away_seconds)} away across "
                f"{format_duration(stats.active_seconds)} active time."
            ),
        )

    with latest_col:
        latest = stats.latest_summary
        if latest is not None:
            _render_metric_card(
                st,
                "Latest session",
                format_duration(latest.total_seconds),
                (
                    f"{format_score(latest.focus_score)} focus, "
                    f"{format_score(latest.presence_score)} presence."
                ),
            )
            _render_metric_card(
                st,
                "Best focus score",
                format_score(stats.best_focus_score),
                f"Average session focus is {format_score(stats.average_focus_score)}.",
            )


def _render_metric_grid(st: Any, stats: DashboardStats) -> None:
    st.markdown(
        """
        <section class="focuslens-section">
          <p class="section-title">Session pulse</p>
          <p class="section-caption">
            Aggregated timing and event signals from the local CSV history.
          </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(4)
    metrics = (
        (
            "Total focus",
            format_duration(stats.focused_seconds),
            f"{format_score(stats.focus_score)} weighted score.",
        ),
        (
            "Away time",
            format_duration(stats.away_seconds),
            f"{stats.away_events} away events counted.",
        ),
        (
            "Looking away",
            format_duration(stats.looking_away_seconds),
            f"{stats.looking_away_events} looking-away events counted.",
        ),
        (
            "Paused",
            format_duration(stats.paused_seconds),
            "Paused time is excluded from active scoring.",
        ),
    )
    for column, (label, value, caption) in zip(columns, metrics, strict=True):
        with column:
            _render_metric_card(st, label, value, caption)


def _render_charts(
    st: Any,
    pd: Any,
    summaries: tuple[SessionSummary, ...],
    stats: DashboardStats,
) -> None:
    st.markdown(
        """
        <section class="focuslens-section">
          <p class="section-title">Signal history</p>
          <p class="section-caption">
            Focus and presence over time, state distribution, and counted events.
          </p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    timeline_col, state_col = st.columns([1.35, 1])
    alt = _load_altair()

    with timeline_col:
        timeline_frame = pd.DataFrame(_session_signal_rows(summaries))
        if alt is None:
            st.line_chart(
                timeline_frame.pivot(
                    index="Session",
                    columns="Signal",
                    values="Score",
                )
            )
        else:
            chart = (
                alt.Chart(timeline_frame)
                .mark_line(point={"filled": True, "size": 72}, strokeWidth=3)
                .encode(
                    x=alt.X("Session:N", title="Session"),
                    y=alt.Y("Score:Q", title="Score", scale=alt.Scale(domain=[0, 100])),
                    color=alt.Color(
                        "Signal:N",
                        scale=alt.Scale(
                            domain=["Focus", "Presence"],
                            range=["#ff2d3d", "#f6f7fb"],
                        ),
                    ),
                    tooltip=["Session", "Started", "Signal", "Score"],
                )
                .properties(height=280)
                .configure(background="transparent")
                .configure_axis(
                    labelColor="#a9afbb",
                    titleColor="#f6f7fb",
                    gridColor="rgba(255,255,255,0.08)",
                )
                .configure_legend(labelColor="#f6f7fb", titleColor="#f6f7fb")
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(chart, use_container_width=True)

    with state_col:
        state_frame = pd.DataFrame(_state_totals(stats))
        if state_frame.empty:
            st.info("No timed states have been recorded yet.")
        elif alt is None:
            st.bar_chart(state_frame, x="State", y="Minutes")
        else:
            chart = (
                alt.Chart(state_frame)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("State:N", title="State", sort=None),
                    y=alt.Y("Minutes:Q", title="Minutes"),
                    color=alt.Color(
                        "State:N",
                        scale=alt.Scale(
                            domain=state_frame["State"].tolist(),
                            range=state_frame["Color"].tolist(),
                        ),
                        legend=None,
                    ),
                    tooltip=["State", "Minutes"],
                )
                .properties(height=280)
                .configure(background="transparent")
                .configure_axis(
                    labelColor="#a9afbb",
                    titleColor="#f6f7fb",
                    gridColor="rgba(255,255,255,0.08)",
                )
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(chart, use_container_width=True)

    event_frame = pd.DataFrame(_event_rows(stats))
    if alt is None:
        st.bar_chart(event_frame, x="Event", y="Count")
    else:
        chart = (
            alt.Chart(event_frame)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Event:N", title="Event", sort=None),
                y=alt.Y("Count:Q", title="Count"),
                color=alt.value("#ff2d3d"),
                tooltip=["Event", "Count"],
            )
            .properties(height=210)
            .configure(background="transparent")
            .configure_axis(
                labelColor="#a9afbb",
                titleColor="#f6f7fb",
                gridColor="rgba(255,255,255,0.08)",
            )
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(chart, use_container_width=True)


def _render_history_table(
    st: Any,
    pd: Any,
    summaries: tuple[SessionSummary, ...],
) -> None:
    st.markdown(
        """
        <section class="focuslens-section">
          <p class="section-title">Session ledger</p>
          <p class="section-caption">
            Display rows are derived from aggregate CSV metrics only.
          </p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(
        pd.DataFrame(build_history_rows(summaries)),
        hide_index=True,
        use_container_width=True,
    )


def _render_privacy_footer(st: Any) -> None:
    st.markdown(
        """
        <section class="privacy-footer">
          FocusLens dashboard reads <code>sessions/sessions.csv</code> only.
          It does not inspect camera frames, session JSON files, secrets, or
          external services.
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_score_dial(
    st: Any,
    *,
    title: str,
    score: float,
    delta: float,
    detail: str,
) -> None:
    bounded_score = min(max(score, 0.0), 100.0)
    st.markdown(
        f"""
        <section class="score-dial">
          <div class="score-delta">{_escape(_format_delta(delta))}</div>
          <div class="score-ring" style="--score: {bounded_score:.2f}">
            <span>{_escape(round(score))}%</span>
          </div>
          <p class="score-title">{_escape(title)}</p>
          <p class="score-detail">{_escape(detail)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_metric_card(st: Any, label: str, value: str, caption: str) -> None:
    st.markdown(
        f"""
        <section class="metric-card">
          <p class="metric-label">{_escape(label)}</p>
          <p class="metric-value">{_escape(value)}</p>
          <p class="metric-caption">{_escape(caption)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _format_delta(delta: float) -> str:
    if delta > 0:
        return f"+{delta:.1f}"

    return f"{delta:.1f}"


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _load_altair() -> Any | None:
    try:
        return import_module("altair")
    except ImportError:
        return None


__all__ = [
    "DEFAULT_SESSION_CSV_PATH",
    "DashboardDataError",
    "DashboardStats",
    "build_history_rows",
    "format_duration",
    "format_score",
    "load_session_summaries",
    "main",
    "summarize_sessions",
    "validate_session_csv_path",
]
