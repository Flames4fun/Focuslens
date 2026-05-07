# Release

FocusLens targets Python 3.14 for the first Windows release.

## Local Windows EXE

Build from the project root:

```powershell
.\scripts\build_windows_exe.ps1
```

The executables and release ZIP are written to:

```text
dist\FocusLens.exe
dist\Dashboard.exe
dist\FocusLens-windows-x64.zip
```

Smoke test the build:

```powershell
.\dist\FocusLens.exe --version
.\dist\FocusLens.exe run
.\dist\FocusLens.exe dashboard
.\dist\Dashboard.exe
```

Current verification note, 2026-05-07:

- `.\dist\FocusLens.exe --version` returned `FocusLens 0.2.0`.
- `focuslens run --no-save --max-frames 30` opened the real camera in a
  camera-enabled Windows session. It exits quickly by design because
  `--max-frames 30` stops after roughly one second at 30 FPS.
- `focuslens run --no-save` stayed open and exercised the expected live states:
  `FOCUSED`, `LOOKING_AWAY`, `AWAY`, and pause/resume.
- Known camera-position note: the current `0.2.0` classifier is more stable
  with a front-facing camera or a slightly elevated camera looking downward. A
  low camera looking upward can make state sensitivity noisier.

The build bundles `assets\face_landmarker.task`, so the default `run` command
does not require a separate model path in the packaged executable.

The main executable bundles the local Streamlit dashboard:

```powershell
.\FocusLens.exe dashboard
```

The ZIP also includes a dedicated dashboard executable for users who want to
open the dashboard without starting the camera:

```powershell
.\Dashboard.exe
```

The dashboard reads `sessions\sessions.csv` from the user's current FocusLens
working directory. That keeps it aligned with the summaries written by
`FocusLens.exe run`.

The bundled model is the MediaPipe Face Landmarker bundle documented by Google:

```text
https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

## Scope

The Windows EXE supports the local webcam session and dashboard flows:

- `FocusLens.exe run`
- `FocusLens.exe dashboard`
- `Dashboard.exe`
- local frame processing only
- bundled MediaPipe Face Landmarker model
- JSON and CSV session summaries under `sessions\`
