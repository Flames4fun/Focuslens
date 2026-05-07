# Release

FocusLens targets Python 3.14 for the first Windows release.

## Local Windows EXE

Build from the project root:

```powershell
.\scripts\build_windows_exe.ps1
```

The executable and release ZIP are written to:

```text
dist\FocusLens.exe
dist\FocusLens-windows-x64.zip
```

Smoke test the build:

```powershell
.\dist\FocusLens.exe --version
.\dist\FocusLens.exe run
.\dist\FocusLens.exe dashboard
```

The build bundles `assets\face_landmarker.task`, so the default `run` command
does not require a separate model path in the packaged executable.

The same executable also bundles the local Streamlit dashboard:

```powershell
.\FocusLens.exe dashboard
```

The dashboard reads `sessions\sessions.csv` from the user's current FocusLens
working directory. That keeps it aligned with the summaries written by
`FocusLens.exe run`.

The bundled model is the MediaPipe Face Landmarker bundle documented by Google
AI Edge:

```text
https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

## Scope

The Windows EXE supports the local webcam session and dashboard flows:

- `FocusLens.exe run`
- `FocusLens.exe dashboard`
- local frame processing only
- bundled MediaPipe Face Landmarker model
- JSON and CSV session summaries under `sessions\`
