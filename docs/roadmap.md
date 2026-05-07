# Roadmap

Updated: 2026-05-07

FocusLens 0.2.0 is the first functional release line: local webcam loop,
MediaPipe landmarks, attention states, session summaries, local dashboard,
Windows executable build, and CI.

The next roadmap is intentionally trust-first. FocusLens should become more
measurable and safer before it becomes more agentic.

## Current Local State

- Core package modules exist for configuration, camera access, face tracking,
  attention classification, overlay rendering, session metrics, storage, CLI,
  and dashboard.
- Local checks pass with `.venv\Scripts\python.exe` on Python 3.14.4:
  `153 passed`, `ruff check .`, `ruff format --check .`, `pip check`,
  OpenCV import, MediaPipe import, and a blank-frame MediaPipe model load.
- CI is configured to run Ruff and pytest on Python 3.14.
- Session summaries save to local JSON and CSV.
- The dashboard reads only `sessions/sessions.csv`.
- The default MediaPipe Face Landmarker model is present at
  `assets/face_landmarker.task`.
- Privacy documentation, release notes, sample data, and a static demo SVG are
  present.
- A Windows EXE build script and GitHub Actions workflow are present.
- The packaged EXE supports both `run` and `dashboard`.
- Looking-away classification uses normalized horizontal head-turn scoring.
- `dist\FocusLens.exe --version` returns `FocusLens 0.2.0`.
- Real webcam smoke test passed in a camera-enabled Windows session. The app
  opened the camera and updated `FOCUSED`, `LOOKING_AWAY`, `AWAY`, and pause
  states as expected.
- Known classifier limitation from smoke testing: a low camera looking upward at
  the face can make state sensitivity noisier. Front-facing placement or a
  slightly elevated camera looking downward works better in `0.2.0`.

## Immediate Post-Release Validation

These items keep the published 0.2.0 release honest and easier to trust:

1. Record a privacy-safe demo that hides or masks the real face.
2. Create initial GitHub issues from this roadmap.
3. Track the low-camera-angle sensitivity issue for calibration and evaluation.
4. Cover `FOCUSED`, `LOOKING_AWAY`, `AWAY`, `PAUSED`, quit/save, and dashboard
   review.

Acceptance criteria:

- `focuslens run` opens the real camera in a camera-enabled Windows session;
- the overlay updates across the expected states;
- low-camera-angle sensitivity is documented as a known limitation;
- quitting writes JSON and CSV when save is enabled;
- `focuslens dashboard` reads the saved CSV;
- the demo does not expose raw face footage.

## Post-0.2.0 Strategy

The best next engineering sequence is:

```text
calibrate -> evaluate -> version schema -> report locally -> expose read-only MCP
```

LLM reflection comes after that, and only over aggregate summaries with explicit
opt-in.

Detailed strategy lives in [MCP and Safety Strategy](mcp_safety_strategy.md).

## Release Plan

| Release | Theme | Estimated Effort | Why It Matters |
| --- | --- | --- | --- |
| `0.3.0` | Calibration, evaluation harness, session schema v1 | 2 to 4 focused days | Improves classifier trust before adding higher-level features. |
| `0.4.0` | Local HTML reports, retention controls, delete/export commands | 2 to 3 focused days | Makes session history useful and manageable without cloud services. |
| `0.5.0` | Read-only MCP server for aggregate summaries | 3 to 5 focused days | Lets assistants query FocusLens safely without camera access. |
| `0.6.0` | Optional LLM reflection over summaries only | 3 to 5 focused days | Adds narrative insight with explicit consent and payload preview. |
| `0.7.0` | Checksums, SBOM, dependency review, release trust | 2 to 4 focused days | Builds trust around a Windows app that uses a webcam. |

Estimates assume one engineer who already knows the codebase. They include
implementation, tests, docs, and local verification, but not long community beta
cycles.

## 0.3.0 Deliverables

### Calibration

Add a `focuslens calibrate` flow that helps users tune thresholds for camera
position, lighting, and face distance.

Deliverables:

- local calibration command;
- calibration profile with derived values only;
- no frame, video, or raw landmark persistence;
- suggested `min_face_ratio`, `max_face_ratio`, and
  `looking_away_threshold`;
- guidance for tricky positions such as a low camera looking upward;
- tests for calibration math and invalid samples.

Acceptance criteria:

- calibration runs without writing images;
- defaults still work if no profile exists;
- generated values are valid `FocusLensConfig` values;
- docs explain how to reset or ignore calibration.

### Evaluation Harness

Add privacy-safe fixtures and metrics for classifier regressions.

Deliverables:

- `tests/fixtures/attention_eval.jsonl`;
- `focuslens/evaluation.py` or equivalent test helper;
- per-state accuracy and failure reporting;
- regression cases for known camera-position scenarios, including low
  bottom-up camera angles;
- docs in [Evaluation Plan](evaluation.md).

Acceptance criteria:

- CI can run evaluation without camera access;
- fixtures contain only derived or synthetic data;
- failures show exact case IDs and expected states;
- tests cover `FOCUSED`, `LOOKING_AWAY`, `AWAY`, `TOO_CLOSE`, `TOO_FAR`, and
  `UNKNOWN`.

### Session Schema v1

Version the summary data model before report, MCP, or LLM consumers depend on
it.

Deliverables:

- `schema_version` in JSON and CSV outputs;
- schema constants and validation helpers;
- backward-compatible loading for 0.2.0 summaries;
- updated sample session file;
- docs in [Session Schema](session_schema.md).

Acceptance criteria:

- new sessions include `schema_version`;
- legacy 0.2.0 data still loads;
- dashboard uses shared validation;
- every field has type, unit, and privacy notes.

## 0.4.0 Deliverables

### Local HTML Reports

Add deterministic reports generated from aggregate summaries only.

Deliverables:

- `focuslens report --format html`;
- optional date range filters;
- validated output path;
- escaped HTML output;
- empty-history report state.

Acceptance criteria:

- report generation works offline;
- report includes no frames, images, video, landmarks, or secrets;
- tests cover malformed CSV and HTML escaping;
- docs explain where the report is written.

### Local Data Controls

Make session history easier to manage.

Deliverables:

- delete or prune command for local summaries;
- export command for a date range;
- retention notes in privacy docs;
- dry-run mode before deletion.

Acceptance criteria:

- destructive actions require explicit confirmation or dry-run first;
- commands stay inside the session directory;
- tests cover path traversal and empty history.

## 0.5.0 Deliverables

### Read-Only MCP Server

Expose aggregate FocusLens history to MCP clients without camera access.

Deliverables:

- `focuslens mcp` command or documented MCP entry point;
- read-only tools: `list_sessions`, `summarize_sessions`, `compare_periods`,
  `get_focus_trends`, and `read_privacy_contract`;
- path allowlist restricted to the session root;
- tests for malformed data and path traversal;
- docs in [Agentic Safety](agentic_safety.md).

Acceptance criteria:

- MCP cannot start the camera;
- MCP cannot read arbitrary local files;
- MCP cannot write or delete data in the first release;
- MCP returns aggregate summaries only;
- every tool has documented input, output, and privacy impact.

## 0.6.0 Deliverables

### Optional LLM Reflection

Add a separate, opt-in command for narrative insight over summaries only.

Deliverables:

- `focuslens reflect`;
- provider selection with local/off/external distinction;
- exact payload preview before any external request;
- prompt with explicit non-goals;
- redaction and date-range options.

Acceptance criteria:

- no external LLM call happens by default;
- payload never includes frames, images, video, landmarks, arbitrary files, or
  secrets;
- user can cancel before sending;
- output avoids medical, emotional, identity, or employment judgments.

## 0.7.0 Deliverables

### Release Trust

Strengthen confidence in packaged artifacts.

Deliverables:

- SHA256 checksums for release ZIPs;
- SBOM artifact;
- dependency review workflow;
- Windows camera troubleshooting guide;
- release verification instructions.

Acceptance criteria:

- release page links checksums;
- workflow uploads checksums and SBOM;
- docs explain how users verify the ZIP;
- permissions and data boundaries remain visible.

## Deferred Ideas

These are valuable but lower priority than trust infrastructure:

- Pomodoro mode;
- desktop notifications;
- OBS or streamer mode;
- desktop app packaging;
- richer dashboard charts;
- YAML configuration after schema and calibration are stable.

These are intentionally out of scope:

- identity recognition;
- emotion detection;
- fatigue or medical diagnosis;
- cloud sync;
- accounts;
- employee monitoring;
- LLM analysis of webcam frames;
- write-capable MCP tools.
