# Privacy Policy

FocusLens is designed as a local-first focus tracker. It uses webcam frames to
estimate simple session signals, but it does not identify people, record video,
or upload images.

This document describes the privacy contract for the current open source
version of FocusLens.

## Privacy Promises

- Webcam frames are processed locally on your machine.
- Webcam frames are kept in memory only.
- FocusLens does not save images by default.
- FocusLens does not save video by default.
- FocusLens does not upload webcam data to any cloud service.
- FocusLens does not create accounts or use remote identity services.
- FocusLens does not perform face recognition or person identification.
- FocusLens stores only aggregate session summaries such as durations, event
  counts, focus score, and presence score.

## What FocusLens Processes

During `focuslens run`, the app reads webcam frames through OpenCV and passes
RGB frame data to the local face tracker. The face tracker returns derived face
landmark data and an approximate face bounding-box ratio. The attention
classifier converts that derived data into coarse states:

- `FOCUSED`
- `LOOKING_AWAY`
- `AWAY`
- `TOO_CLOSE`
- `TOO_FAR`
- `PAUSED`
- `UNKNOWN`

Those states are then accumulated into session metrics.

## What FocusLens Stores

When saving is enabled, FocusLens writes local JSON and CSV summaries under
`sessions/` by default. The fields are aggregate metrics:

- Session start and end timestamps.
- Total, focused, away, looking-away, too-close, too-far, paused, and unknown
  seconds.
- Looking-away and away event counts.
- Focus and presence scores.

FocusLens does not store raw frames, screenshots, video clips, face images, or
face templates in these session files.

## Score Calculations

FocusLens stores paused time, but paused seconds are excluded from active
scoring. Current score formulas use:

- `active_seconds = total_seconds - paused_seconds`
- `focus_score = focused_seconds / active_seconds * 100`
- `presence_score = (active_seconds - away_seconds) / active_seconds * 100`

When there is no active time, both scores are `0.0` to avoid misleading
percentages.

## Sensitive Local Data

Session summaries can still be personal. Timestamps and focus patterns may
reveal work habits, breaks, or availability. Treat `sessions/` as private local
data unless you intentionally want to share it.

The default `sessions/` directory is ignored by Git in this repository. If you
use `--save-dir`, confirm that the chosen directory is not synced, committed, or
shared accidentally.

## Dashboard Privacy

`focuslens dashboard` opens the local Streamlit dashboard. The dashboard reads
only `sessions/sessions.csv` from the local FocusLens session directory. It does
not inspect webcam frames, session JSON files, environment secrets, or external
URLs.

## User Controls

- Use `--no-save` for a temporary session that does not write JSON or CSV.
- Use `--save-dir <path>` to choose where summaries are written.
- Delete `sessions/` whenever you want to remove local session history.
- Keep the MediaPipe model file local, for example
  `assets/face_landmarker.task`.

## Non Goals

FocusLens is not designed for surveillance, employee monitoring, medical
diagnosis, emotion detection, fatigue detection, or productivity scoring with
scientific precision. It estimates simple local signals for personal feedback.

## Security Notes

FocusLens should not download models at runtime or send webcam frames over the
network. Dependencies are installed by the user through the Python environment.
Review dependency versions and your local environment before using the app with
sensitive workflows.
