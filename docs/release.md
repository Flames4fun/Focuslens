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
```

The build bundles `assets\face_landmarker.task`, so the default `run` command
does not require a separate model path in the packaged executable.

The bundled model is the MediaPipe Face Landmarker bundle documented by Google
AI Edge:

```text
https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

## Scope

The first EXE is focused on the local webcam session flow:

- `FocusLens.exe run`
- local frame processing only
- bundled MediaPipe Face Landmarker model
- JSON and CSV session summaries under `sessions\`

The Streamlit dashboard remains a source/development command for now:

```powershell
focuslens dashboard
```

Bundling Streamlit into the same EXE is possible later, but it is a larger
packaging task than the first release needs.
