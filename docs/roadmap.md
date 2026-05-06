# Roadmap

Updated: 2026-05-06

## Current Local State

- Core package modules exist for configuration, camera access, face tracking,
  attention classification, overlay rendering, session metrics, storage, CLI,
  and dashboard.
- Local checks pass with `.venv\Scripts\python.exe` on Python 3.14.4:
  `143 passed`, `ruff check .`, `ruff format --check .`, `pip check`,
  OpenCV import, MediaPipe import, and a blank-frame MediaPipe model load.
- CI is configured to run Ruff and pytest on Python 3.14.
- Session summaries save to local JSON and CSV.
- The dashboard reads only `sessions/sessions.csv`.
- The default MediaPipe Face Landmarker model is present at
  `assets/face_landmarker.task`.
- Privacy documentation, release notes, sample data, and a static demo SVG are
  present.
- A Windows EXE build script and GitHub Actions workflow are present.

## Next Release Work

1. Run a real webcam smoke test covering focused, looking-away, away, paused,
   save, and dashboard flows.
2. Build `dist\FocusLens.exe` locally with `.\scripts\build_windows_exe.ps1`.
3. Smoke test `.\dist\FocusLens.exe --version` and `.\dist\FocusLens.exe run`.
4. Record a privacy-safe demo from a local session.
5. Publish the repository and create the initial GitHub issues.

## Initial Issue Set

- Add Pomodoro mode.
- Improve head pose estimation.
- Add HTML report export.
- Add desktop notifications.
- Improve dashboard charts.
- Add Windows troubleshooting guide.
- Improve packaged model setup and release notes.
- Add configuration file support.

## Later Ideas

- YAML configuration for thresholds and save paths.
- Better calibration flow for lighting, camera position, and distance.
- Weekly reports from local summaries.
- OBS or streamer mode.
- Streamlit dashboard packaging.
