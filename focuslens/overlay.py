"""Privacy-preserving local video overlay rendering for FocusLens.

This module draws only derived state and aggregate session numbers on frames
already in memory. It does not save images, serialize frames, log camera data,
or perform network I/O.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib import import_module
from math import isfinite
from types import MappingProxyType
from typing import Any, Protocol

from focuslens.attention import AttentionAnalysis, AttentionState
from focuslens.camera import OpenCVUnavailableError

BgrColor = tuple[int, int, int]

DEFAULT_STATE_COLORS: Mapping[AttentionState, BgrColor] = MappingProxyType(
    {
        AttentionState.FOCUSED: (80, 190, 120),
        AttentionState.LOOKING_AWAY: (35, 185, 245),
        AttentionState.AWAY: (190, 190, 190),
        AttentionState.TOO_CLOSE: (75, 95, 245),
        AttentionState.TOO_FAR: (245, 165, 70),
        AttentionState.PAUSED: (230, 180, 80),
        AttentionState.UNKNOWN: (170, 120, 220),
    }
)

DEFAULT_STATE_LABELS: Mapping[AttentionState, str] = MappingProxyType(
    {
        AttentionState.FOCUSED: "Focused",
        AttentionState.LOOKING_AWAY: "Looking away",
        AttentionState.AWAY: "Away",
        AttentionState.TOO_CLOSE: "Too close",
        AttentionState.TOO_FAR: "Too far",
        AttentionState.PAUSED: "Paused",
        AttentionState.UNKNOWN: "Unknown",
    }
)


def _validate_seconds(name: str, value: float) -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a non-negative finite number")


def _validate_count(name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _validate_percentage(name: str, value: float) -> None:
    if not isfinite(value) or not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100")


def _validate_color(name: str, color: BgrColor) -> BgrColor:
    try:
        components = tuple(color)
    except TypeError as exc:
        raise ValueError(f"{name} must contain exactly three BGR components") from exc

    if len(components) != 3:
        raise ValueError(f"{name} must contain exactly three BGR components")

    if any(
        not isinstance(component, int) or isinstance(component, bool)
        for component in components
    ):
        raise ValueError(f"{name} components must be integers")

    if any(component < 0 or component > 255 for component in components):
        raise ValueError(f"{name} components must be between 0 and 255")

    return components


@dataclass(frozen=True, slots=True)
class OverlayMetrics:
    """Aggregate session values safe to display on the local camera overlay."""

    elapsed_seconds: float = 0.0
    focused_seconds: float | None = None
    away_seconds: float | None = None
    looking_away_events: int | None = None
    focus_score: float | None = None
    presence_score: float | None = None

    def __post_init__(self) -> None:
        """Reject misleading values before they reach the visual layer."""

        _validate_seconds("elapsed_seconds", self.elapsed_seconds)

        if self.focused_seconds is not None:
            _validate_seconds("focused_seconds", self.focused_seconds)

        if self.away_seconds is not None:
            _validate_seconds("away_seconds", self.away_seconds)

        if self.looking_away_events is not None:
            _validate_count("looking_away_events", self.looking_away_events)

        if self.focus_score is not None:
            _validate_percentage("focus_score", self.focus_score)

        if self.presence_score is not None:
            _validate_percentage("presence_score", self.presence_score)


@dataclass(frozen=True, slots=True)
class OverlayTheme:
    """Visual settings for the OpenCV overlay."""

    padding: int = 16
    min_panel_width: int = 260
    line_height: int = 26
    status_bar_height: int = 8
    font_scale: float = 0.62
    font_thickness: int = 2
    background_alpha: float = 0.72
    panel_fill: BgrColor = (18, 22, 26)
    panel_outline: BgrColor = (58, 66, 74)
    text_color: BgrColor = (245, 245, 245)
    muted_text_color: BgrColor = (198, 205, 212)
    state_colors: Mapping[AttentionState, BgrColor] = field(
        default_factory=lambda: DEFAULT_STATE_COLORS
    )

    def __post_init__(self) -> None:
        """Validate theme values and freeze mutable mappings."""

        if self.padding < 0:
            raise ValueError("padding must be non-negative")

        if self.min_panel_width <= 0:
            raise ValueError("min_panel_width must be greater than zero")

        if self.line_height <= 0:
            raise ValueError("line_height must be greater than zero")

        if self.status_bar_height < 0:
            raise ValueError("status_bar_height must be non-negative")

        if self.font_scale <= 0:
            raise ValueError("font_scale must be greater than zero")

        if self.font_thickness <= 0:
            raise ValueError("font_thickness must be greater than zero")

        if not 0 <= self.background_alpha <= 1:
            raise ValueError("background_alpha must be between 0 and 1")

        _validate_color("panel_fill", self.panel_fill)
        _validate_color("panel_outline", self.panel_outline)
        _validate_color("text_color", self.text_color)
        _validate_color("muted_text_color", self.muted_text_color)

        state_colors = {
            state: _validate_color(f"state_colors[{state.value}]", color)
            for state, color in self.state_colors.items()
        }
        object.__setattr__(self, "state_colors", MappingProxyType(state_colors))

    def color_for(self, state: AttentionState) -> BgrColor:
        """Return the configured BGR color for an attention state."""

        return self.state_colors.get(
            state,
            DEFAULT_STATE_COLORS[AttentionState.UNKNOWN],
        )


DEFAULT_OVERLAY_THEME = OverlayTheme()


class OverlayRenderer(Protocol):
    """Interface implemented by local frame overlay renderers."""

    def render(
        self,
        frame_bgr: object,
        analysis: AttentionAnalysis | AttentionState,
        metrics: OverlayMetrics | None = None,
    ) -> object:
        """Draw the overlay on a BGR frame and return that same frame."""
        ...


@dataclass(frozen=True, slots=True)
class _PanelRect:
    left: int
    top: int
    right: int
    bottom: int


class OpenCVOverlayRenderer:
    """Draw a minimal local-only overlay on OpenCV BGR frames."""

    def __init__(
        self,
        *,
        theme: OverlayTheme = DEFAULT_OVERLAY_THEME,
        cv2_module: Any | None = None,
    ) -> None:
        self.theme = theme
        self._cv2_module = cv2_module

    def render(
        self,
        frame_bgr: object,
        analysis: AttentionAnalysis | AttentionState,
        metrics: OverlayMetrics | None = None,
    ) -> object:
        """Draw safe session text on a frame without persisting the image."""

        height, width = _frame_dimensions(frame_bgr)
        cv2 = self._cv2_module or _load_cv2()
        metrics = metrics or OverlayMetrics()
        state = _attention_state(analysis)
        lines = build_overlay_lines(analysis, metrics)
        panel = self._panel_rect(cv2, lines, width, height)
        state_color = self.theme.color_for(state)

        self._draw_status_bar(cv2, frame_bgr, width, state_color)
        self._draw_panel_background(cv2, frame_bgr, panel)
        self._draw_lines(cv2, frame_bgr, panel, lines, state_color)
        return frame_bgr

    def _panel_rect(
        self,
        cv2: Any,
        lines: tuple[str, ...],
        frame_width: int,
        frame_height: int,
    ) -> _PanelRect:
        margin = min(
            self.theme.padding,
            max(frame_width // 8, 0),
            max(frame_height // 8, 0),
        )
        available_width = max(1, frame_width - (margin * 2))
        available_height = max(1, frame_height - margin - self.theme.status_bar_height)
        text_width = max(self._text_width(cv2, line) for line in lines)
        panel_width = min(
            available_width,
            max(self.theme.min_panel_width, text_width + (self.theme.padding * 2)),
        )
        panel_height = min(
            available_height,
            self.theme.padding * 2 + self.theme.line_height * len(lines),
        )
        top = margin + self.theme.status_bar_height
        return _PanelRect(
            left=margin,
            top=top,
            right=margin + panel_width,
            bottom=top + panel_height,
        )

    def _text_width(self, cv2: Any, text: str) -> int:
        size, _ = cv2.getTextSize(
            text,
            cv2.FONT_HERSHEY_SIMPLEX,
            self.theme.font_scale,
            self.theme.font_thickness,
        )
        return int(size[0])

    def _draw_status_bar(
        self,
        cv2: Any,
        frame_bgr: object,
        frame_width: int,
        state_color: BgrColor,
    ) -> None:
        if self.theme.status_bar_height == 0:
            return

        cv2.rectangle(
            frame_bgr,
            (0, 0),
            (frame_width, self.theme.status_bar_height),
            state_color,
            cv2.FILLED,
        )

    def _draw_panel_background(
        self,
        cv2: Any,
        frame_bgr: object,
        panel: _PanelRect,
    ) -> None:
        if self.theme.background_alpha < 1 and hasattr(frame_bgr, "copy"):
            overlay = frame_bgr.copy()
            cv2.rectangle(
                overlay,
                (panel.left, panel.top),
                (panel.right, panel.bottom),
                self.theme.panel_fill,
                cv2.FILLED,
            )
            cv2.addWeighted(
                overlay,
                self.theme.background_alpha,
                frame_bgr,
                1 - self.theme.background_alpha,
                0,
                frame_bgr,
            )
        else:
            cv2.rectangle(
                frame_bgr,
                (panel.left, panel.top),
                (panel.right, panel.bottom),
                self.theme.panel_fill,
                cv2.FILLED,
            )

        cv2.rectangle(
            frame_bgr,
            (panel.left, panel.top),
            (panel.right, panel.bottom),
            self.theme.panel_outline,
            1,
        )

    def _draw_lines(
        self,
        cv2: Any,
        frame_bgr: object,
        panel: _PanelRect,
        lines: tuple[str, ...],
        state_color: BgrColor,
    ) -> None:
        max_text_width = max(1, panel.right - panel.left - (self.theme.padding * 2))
        baseline_y = panel.top + self.theme.padding + self.theme.line_height - 7

        for index, line in enumerate(lines):
            text = self._fit_text(cv2, line, max_text_width)
            color = state_color if index == 0 else self.theme.text_color
            cv2.putText(
                frame_bgr,
                text,
                (
                    panel.left + self.theme.padding,
                    baseline_y + index * self.theme.line_height,
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                self.theme.font_scale,
                color,
                self.theme.font_thickness,
                cv2.LINE_AA,
            )

    def _fit_text(self, cv2: Any, text: str, max_width: int) -> str:
        if self._text_width(cv2, text) <= max_width:
            return text

        suffix = "..."
        available = max(0, max_width - self._text_width(cv2, suffix))
        clipped = ""
        for character in text:
            candidate = clipped + character
            if self._text_width(cv2, candidate) > available:
                break
            clipped = candidate

        return f"{clipped}{suffix}" if clipped else suffix


def render_overlay(
    frame_bgr: object,
    analysis: AttentionAnalysis | AttentionState,
    metrics: OverlayMetrics | None = None,
    *,
    theme: OverlayTheme = DEFAULT_OVERLAY_THEME,
    cv2_module: Any | None = None,
) -> object:
    """Render an OpenCV overlay with the default renderer."""

    renderer = OpenCVOverlayRenderer(theme=theme, cv2_module=cv2_module)
    return renderer.render(frame_bgr, analysis, metrics)


def build_overlay_lines(
    analysis: AttentionAnalysis | AttentionState,
    metrics: OverlayMetrics | None = None,
) -> tuple[str, ...]:
    """Build safe human-readable overlay lines from derived session data."""

    metrics = metrics or OverlayMetrics()
    state = _attention_state(analysis)
    lines = [
        f"Status: {DEFAULT_STATE_LABELS[state]}",
        f"Session: {format_duration(metrics.elapsed_seconds)}",
    ]

    if metrics.focused_seconds is not None:
        lines.append(f"Focused: {format_duration(metrics.focused_seconds)}")

    if metrics.away_seconds is not None:
        lines.append(f"Away: {format_duration(metrics.away_seconds)}")

    if metrics.looking_away_events is not None:
        lines.append(f"Looking away: {metrics.looking_away_events}")

    if metrics.focus_score is not None:
        lines.append(f"Focus score: {metrics.focus_score:.0f}%")

    if metrics.presence_score is not None:
        lines.append(f"Presence: {metrics.presence_score:.0f}%")

    return tuple(lines)


def format_duration(seconds: float) -> str:
    """Format a non-negative duration as HH:MM:SS."""

    _validate_seconds("seconds", seconds)
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds_part = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds_part:02}"


def _attention_state(analysis: AttentionAnalysis | AttentionState) -> AttentionState:
    if isinstance(analysis, AttentionState):
        return analysis

    return analysis.state


def _load_cv2() -> Any:
    try:
        return import_module("cv2")
    except ImportError as exc:
        raise OpenCVUnavailableError(
            "OpenCV is required to render FocusLens overlays. "
            'Install it with: python -m pip install "opencv-python>=4.9"'
        ) from exc


def _frame_dimensions(frame_bgr: object) -> tuple[int, int]:
    shape = getattr(frame_bgr, "shape", None)
    if shape is None or len(shape) != 3 or shape[2] != 3:
        raise ValueError("frame_bgr must be an image array shaped (height, width, 3)")

    height = int(shape[0])
    width = int(shape[1])
    if height <= 0 or width <= 0:
        raise ValueError("frame_bgr dimensions must be greater than zero")

    return height, width


__all__ = [
    "BgrColor",
    "DEFAULT_OVERLAY_THEME",
    "DEFAULT_STATE_LABELS",
    "DEFAULT_STATE_COLORS",
    "OpenCVOverlayRenderer",
    "OverlayMetrics",
    "OverlayRenderer",
    "OverlayTheme",
    "build_overlay_lines",
    "format_duration",
    "render_overlay",
]
