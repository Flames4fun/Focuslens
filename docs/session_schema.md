# Session Schema

Updated: 2026-05-07

FocusLens stores aggregate session summaries. This document defines the current
schema and the planned versioning path for future reports, MCP tools, and LLM
reflection.

## Current 0.2.0 Shape

FocusLens 0.2.0 writes JSON session files and appends rows to
`sessions/sessions.csv`.

Current fields:

| Field | Type | Unit | Meaning |
| --- | --- | --- | --- |
| `started_at` | string | ISO datetime | Session start time. |
| `ended_at` | string | ISO datetime | Session end time. |
| `total_seconds` | number | seconds | Total tracked duration. |
| `focused_seconds` | number | seconds | Time classified as `FOCUSED`. |
| `away_seconds` | number | seconds | Time classified as `AWAY`. |
| `looking_away_seconds` | number | seconds | Time classified as `LOOKING_AWAY`. |
| `too_close_seconds` | number | seconds | Time classified as `TOO_CLOSE`. |
| `too_far_seconds` | number | seconds | Time classified as `TOO_FAR`. |
| `paused_seconds` | number | seconds | Time manually paused. |
| `unknown_seconds` | number | seconds | Time with unknown orientation. |
| `looking_away_events` | integer | count | Counted looking-away events. |
| `away_events` | integer | count | Counted away events. |
| `focus_score` | number | percent | Focused time divided by active time. |
| `presence_score` | number | percent | Non-away active time divided by active time. |

Privacy note: these fields do not include frames, screenshots, videos, face
images, face embeddings, identity templates, or raw landmarks. They can still
reveal personal work patterns because they include timestamps and duration
signals.

## Planned Schema Version

The next schema should add:

```json
{
  "schema_version": "1.0"
}
```

Rules:

- missing `schema_version` means legacy 0.2.0 format;
- loaders should normalize legacy rows to the current in-memory model;
- dashboard, reports, and MCP tools should read through the same validation
  path;
- schema changes must be documented before release.

## Version 1.0 Requirements

Version 1.0 should preserve all 0.2.0 fields and add only metadata required for
safe compatibility.

Required additions:

- `schema_version`;
- optional `app_version` if available at write time;
- optional `calibration_profile_id` only if calibration ships first.

Do not add:

- frame paths;
- image paths;
- raw landmarks;
- face embeddings;
- device serial numbers;
- account identifiers.

## Validation Rules

- datetimes must be valid ISO strings;
- duration fields must be finite and non-negative;
- event fields must be non-negative integers;
- scores must be between `0` and `100`;
- state duration totals must match `total_seconds` within tolerance;
- `ended_at` must not be earlier than `started_at`.

## Consumers

All consumers should use the same schema contract:

- dashboard;
- local HTML report generator;
- evaluation summaries;
- read-only MCP server;
- optional LLM reflection payload builder.

This prevents each integration from inventing its own CSV parsing behavior.

## Migration Approach

1. Add schema constants and validation helpers.
2. Update JSON writer and CSV writer to include `schema_version`.
3. Update dashboard loader to accept missing schema version as legacy.
4. Update `examples/sample_session.json`.
5. Add tests for legacy and versioned rows.
6. Document the schema in release notes.
