# Architecture

FocusLens is a local-only webcam pipeline. Runtime code turns in-memory camera
frames into derived attention states, then into aggregate session summaries.
Frames are not serialized by the package.

## Runtime Flow

```text
focuslens run
  -> OpenCV webcam frame
  -> RGB frame passed to MediaPipe Face Landmarker
  -> FaceResult with landmarks and face bounding-box ratio
  -> AttentionAnalysis state
  -> SessionTracker aggregate metrics
  -> OpenCV overlay for local preview
  -> JSON and CSV summaries on close
```

## Module Boundaries

- `focuslens.camera` owns webcam access, BGR/RGB conversion, and frame
  timestamps.
- `focuslens.face_tracker` isolates MediaPipe and returns plain `FaceResult`
  values.
- `focuslens.attention` is pure classification logic for focused, away,
  looking-away, distance, paused, and unknown states. Horizontal head-turn
  scoring normalizes nose offset by visible eye span so `LOOKING_AWAY` remains
  sensitive across different face sizes.
- `focuslens.session` accumulates state durations and event counts without
  receiving frame data.
- `focuslens.storage` writes `SessionSummary` values to local JSON and CSV.
- `focuslens.overlay` renders derived state and aggregate metrics on the local
  OpenCV preview.
- `focuslens.dashboard` reads only the aggregate `sessions/sessions.csv` file.
- `focuslens.cli` wires the runtime together and validates local paths.

## Data Boundaries

The most sensitive object is `CameraFrame`, which contains in-memory BGR/RGB
arrays. It should stay inside the camera, tracker, and overlay runtime path.

The stored data model is `SessionSummary`. It includes timestamps, state
durations, event counts, and focus/presence scores. It does not include raw
frames, screenshots, video clips, face images, face embeddings, or identity
templates.

## Future MCP Boundaries

Future assistant-facing layers must sit after `SessionSummary`, not before it:

```text
SessionSummary
  -> schema validation
  -> local reports
  -> read-only MCP tools
  -> optional LLM reflection
```

Those layers may read aggregate session summaries. They must not receive
`CameraFrame`, raw frames, screenshots, video, face images, face embeddings,
identity labels, or arbitrary local files.

The first MCP server should be read-only and limited to tools such as
`list_sessions`, `summarize_sessions`, `compare_periods`, `get_focus_trends`,
and `read_privacy_contract`. It should not start the camera, write files,
delete history, modify configuration, or call external LLMs.

Detailed boundaries live in:

- [MCP and Safety Strategy](mcp_safety_strategy.md)
- [Session Schema](session_schema.md)
- [Agentic Safety](agentic_safety.md)

## Runtime Requirements

The package targets Python 3.14. CI validates Python 3.14. The Windows release
build bundles OpenCV, MediaPipe, Streamlit, the local dashboard, and
`assets/face_landmarker.task`.
