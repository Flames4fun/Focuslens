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
  looking-away, distance, paused, and unknown states.
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

## Runtime Requirements

The package targets Python 3.11+. CI validates Python 3.11. The current local
workspace has tests and dashboard dependencies available in `.venv`, but the
real webcam flow still needs `opencv-python`, `mediapipe`, and a local
`assets/face_landmarker.task` model before release validation.
