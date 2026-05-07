# MCP and Safety Strategy

Updated: 2026-05-07

This document defines the post-0.2.0 technical direction for FocusLens as a
local-first project that can safely expose aggregate summaries to assistants.
The goal is not to add an LLM to the webcam loop. The goal is to make the
current vision pipeline measurable, auditable, and safe enough that future MCP
or LLM integrations can read useful summaries without touching camera data.

## Current Baseline

FocusLens 0.2.0 already has the core product surface:

- local OpenCV webcam loop;
- local MediaPipe Face Landmarker model;
- attention states from derived landmarks;
- session metrics in JSON and CSV;
- local Streamlit dashboard;
- Windows executable build;
- CI with Ruff and pytest;
- privacy documentation and local-only data boundaries.

The repository also has strong module boundaries. Runtime frame data stays in
the camera, tracker, and overlay path. Stored summaries are represented by
`SessionSummary`, which contains timestamps, state durations, event counts, and
scores only.

## Strategic Principle

Future assistant and agentic features must operate on aggregate session data,
not on webcam frames.

That means:

- no LLM receives frames, screenshots, video, face landmarks, or face images;
- MCP tools expose read-only summary operations first;
- any external LLM feature is opt-in and previews the exact payload before use;
- local deterministic reports come before generative reflection;
- evaluation and schema stability come before new assistant features.

This preserves the product promise: useful local feedback without identity,
surveillance, medical claims, or cloud dependence.

## Why This Matters

FocusLens sits near sensitive data because it uses a webcam. Even if frames are
not stored, the app can still reveal work habits through timestamps and session
patterns. Adding an agent or LLM too early would increase privacy risk without
improving the underlying measurement quality.

The best next step is trust infrastructure:

- calibration to reduce false classifications;
- evaluation data to measure behavior changes;
- a stable session schema for dashboard, reports, and MCP tools;
- explicit agentic safety boundaries;
- local reports that are useful without cloud services.

## Post-0.2.0 Delivery Order

| Release | Theme | Estimated Effort | Primary Value |
| --- | --- | --- | --- |
| `0.3.0` | Calibration, evaluation harness, session schema v1 | 2 to 4 focused days | Make the classifier measurable and tunable. |
| `0.4.0` | Local HTML reports, retention controls, delete/export commands | 2 to 3 focused days | Make session history more useful and easier to manage. |
| `0.5.0` | Read-only MCP server for aggregate summaries | 3 to 5 focused days | Let assistants query FocusLens safely without camera access. |
| `0.6.0` | Optional LLM reflection over summaries only | 3 to 5 focused days | Add narrative insights with explicit consent and payload preview. |
| `0.7.0` | Supply-chain and release trust | 2 to 4 focused days | Improve confidence in Windows artifacts and dependencies. |

The estimates assume one engineer who already understands the codebase. They
include implementation, tests, documentation, and local verification, but not
long public beta feedback cycles.

## New Deliverables

### 1. Calibration

Add a `focuslens calibrate` flow that helps users tune local thresholds for
their camera position, lighting, and distance.

Deliverables:

- CLI command for calibration;
- derived calibration profile stored locally;
- no image, video, or raw landmark persistence;
- suggested values for face distance and looking-away threshold;
- tests for calibration math and config validation.

Why:

The current classifier is intentionally simple. Calibration is the fastest way
to improve user trust without adding a heavier model or more invasive data.

Acceptance criteria:

- a user can run calibration without saving frames;
- generated thresholds are bounded by `FocusLensConfig`;
- existing default behavior still works when no profile exists;
- tests cover edge cases such as missing face, unstable measurements, and empty
  calibration samples.

### 2. Evaluation Harness

Add a deterministic evaluation layer for attention classification.

Deliverables:

- privacy-safe fixtures with derived values only;
- command or test helper that reports per-state accuracy;
- regression tests for known tricky cases;
- `docs/evaluation.md` as the evaluation contract.

Why:

Future changes to head-pose scoring should be measurable. Without evaluation
fixtures, the project can improve the dashboard while silently making the
classifier worse.

Acceptance criteria:

- fixtures do not contain frames, images, or identity data;
- each fixture records expected state and derived classifier inputs;
- CI can run the eval suite without camera access;
- failures show which state regressed.

### 3. Session Schema v1

Version the stored session data model before building reports, MCP, or LLM
features on top of it.

Deliverables:

- `schema_version` in JSON and CSV outputs;
- schema documentation in `docs/session_schema.md`;
- backward-compatible loader for 0.2.0 summaries;
- validation shared by dashboard, reports, and future MCP tools.

Why:

MCP tools and LLM features need a stable contract. A schema version prevents
future changes from breaking old session history or producing ambiguous
assistant answers.

Acceptance criteria:

- new sessions include a schema version;
- existing 0.2.0 sample sessions still load;
- dashboard displays both old and new summaries safely;
- schema docs define every field, type, unit, and privacy note.

### 4. Local Reports

Add deterministic local reporting before any generative interpretation.

Deliverables:

- `focuslens report --format html`;
- local report generated from aggregate summaries only;
- optional date range filters;
- no external service dependency;
- tests for report data selection and HTML escaping.

Why:

Reports add real user value while staying fully local. They also create a
structured summary surface that future LLM reflection can reuse safely.

Acceptance criteria:

- reports render without internet access;
- generated HTML contains no raw frames, secrets, or arbitrary local files;
- empty history produces a clear report state;
- user-controlled output path is validated.

### 5. Read-Only MCP Server

Expose FocusLens summaries to MCP clients through a constrained local server.

Deliverables:

- `focuslens mcp` command or documented local MCP entry point;
- read-only tools such as `list_sessions`, `summarize_sessions`,
  `compare_periods`, `get_focus_trends`, and `read_privacy_contract`;
- path allowlist restricted to the FocusLens session directory;
- tests for path traversal, empty history, malformed CSV, and read-only
  behavior.

Why:

This is the highest-value assistant-facing feature. It makes FocusLens useful
to assistants while preserving local boundaries. An assistant can answer
questions about focus trends without ever accessing the webcam.

Acceptance criteria:

- MCP tools cannot start the camera;
- MCP tools cannot read arbitrary files;
- MCP tools return aggregate summaries only;
- MCP server has no write actions in the first release;
- docs include example tool calls and privacy constraints.

### 6. Optional LLM Reflection

Add generative insight only after local reports and MCP are safe.

Deliverables:

- explicit opt-in command, for example `focuslens reflect`;
- provider selection with a local/off/external distinction;
- exact payload preview before any external model call;
- redaction and date-range controls;
- clear non-goals for medical, emotional, employment, or identity claims.

Why:

LLMs can help explain patterns, but they must not become a hidden data export.
Reflection should summarize aggregate metrics and suggest habits, not infer
identity, emotions, health, or productivity truth.

Acceptance criteria:

- default behavior does not call an external LLM;
- user sees the payload before sending;
- frames, images, landmarks, and arbitrary files are never included;
- prompts explicitly prohibit diagnosis, identity recognition, and surveillance
  use cases.

### 7. Supply-Chain and Release Trust

Strengthen trust around packaged releases.

Deliverables:

- release checksums;
- SBOM for the Windows ZIP;
- dependency review workflow;
- optional OpenSSF Scorecard documentation;
- clearer Windows camera troubleshooting guide.

Why:

FocusLens distributes an executable that uses a webcam. Users need confidence
that the artifact matches the project promises and that dependencies are
reviewed.

Acceptance criteria:

- release page includes SHA256 checksums;
- build workflow publishes checksums as artifacts;
- documentation explains how to verify the ZIP;
- dependency and permission boundaries remain visible in docs.

## What Not To Build Next

These are intentionally deferred:

- LLM-based webcam interpretation;
- cloud sync;
- accounts;
- employee monitoring features;
- emotion, fatigue, or medical classification;
- identity recognition;
- remote camera control;
- write-capable MCP tools.

Each of those would change the risk profile of the project. They require a much
larger privacy, safety, and consent design than FocusLens needs right now.

## Decision Summary

The next best engineering move is:

```text
calibrate -> evaluate -> version schema -> report locally -> expose read-only MCP
```

Only after that should FocusLens add optional LLM reflection over aggregate
summary data.
