<div align="center">

<img
  src="https://capsule-render.vercel.app/api?type=waving&height=220&color=0:0B0B0F,55:E50914,100:190006&text=FocusLens&fontColor=FFFFFF&fontSize=64&fontAlignY=38&desc=Privacy-first%20local%20focus%20tracking%20for%20deep%20work&descAlignY=58&animation=fadeIn"
  alt="FocusLens animated red and black banner"
/>

[![Python 3.14](https://img.shields.io/badge/Python-3.14-E50914?style=for-the-badge&labelColor=0B0B0F&logo=python&logoColor=white)](#tech-stack)
[![OpenCV](https://img.shields.io/badge/OpenCV-Webcam%20Vision-E50914?style=for-the-badge&labelColor=0B0B0F&logo=opencv&logoColor=white)](#tech-stack)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Face%20Landmarks-E50914?style=for-the-badge&labelColor=0B0B0F)](#tech-stack)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-E50914?style=for-the-badge&labelColor=0B0B0F&logo=streamlit&logoColor=white)](#dashboard)
[![MIT](https://img.shields.io/badge/License-MIT-E50914?style=for-the-badge&labelColor=0B0B0F)](LICENSE)
[![CI](https://github.com/Flames4fun/Focuslens/actions/workflows/ci.yml/badge.svg)](https://github.com/Flames4fun/Focuslens/actions/workflows/ci.yml)

<br />

<img
  src="https://readme-typing-svg.demolab.com?font=Inter&weight=700&size=22&duration=2400&pause=900&color=E50914&center=true&vCenter=true&width=760&lines=Local-first+webcam+signals.;No+identity+recognition.;No+cloud+upload.;Only+session+summaries."
  alt="Animated FocusLens privacy promises"
/>

</div>

## Overview

**FocusLens** is a privacy-first local focus tracker that uses webcam-based face landmarks to estimate simple work-session signals: presence, attention direction, away time, and camera distance.

It is designed for students, developers, creators, and deep-work sessions where you want useful feedback without turning focus tracking into surveillance.

> FocusLens estimates simple local signals of presence and attention. It does not identify people, diagnose fatigue, or measure productivity with scientific precision.

## Project Status

FocusLens is in publication prep for its first open source release. The product direction is defined, the package basics are in place, the OpenCV camera boundary exists, the pure attention classifier is tested, the MediaPipe face-tracking boundary exists, the local preview loop is wired through the CLI and overlay renderer, session metrics plus local JSON/CSV summary storage are integrated into `focuslens run`, and the local Streamlit dashboard reads the aggregate CSV history.

Current local progress, checked on 2026-05-06:

- Created and tested: `focuslens/config.py`, `focuslens/attention.py`, `focuslens/camera.py`, `focuslens/face_tracker.py`, `focuslens/overlay.py`, `focuslens/cli.py`, `focuslens/session.py`, `focuslens/storage.py`, `focuslens/dashboard.py`, and their current unit tests.
- Verified with `.venv\Scripts\python.exe` on Python 3.14.4: `143 passed`, `ruff check .` passed, `ruff format --check .` passed, `pip check` passed, and OpenCV/MediaPipe imports passed.
- CI validates Python 3.14, matching the local release target.
- Closing `focuslens run` now writes a local JSON summary and appends `sessions.csv`.
- `focuslens dashboard` now launches the local Streamlit dashboard when Streamlit and pandas are installed.
- Added contributor-ready support files: `docs/privacy.md`, `docs/architecture.md`, `docs/roadmap.md`, `docs/release.md`, `.github/workflows/ci.yml`, `.github/workflows/windows-exe.yml`, `examples/sample_session.json`, `assets/demo.svg`, and `CONTRIBUTING.md`.
- `assets/face_landmarker.task` is present and was validated with MediaPipe on a blank in-memory frame.
- Next publication tasks: run the real webcam flow, record a privacy-safe demo, and create the initial GitHub issues after the repository is published.

## Core Signals

| State | Meaning |
| --- | --- |
| `FOCUSED` | A face is visible and appears oriented toward the screen. |
| `LOOKING_AWAY` | A face is visible, but the head or gaze direction appears shifted. |
| `AWAY` | No face is visible in the camera frame. |
| `TOO_CLOSE` | The face is too close to the camera. |
| `TOO_FAR` | The face is too far from the camera. |
| `PAUSED` | The session is manually paused. |
| `UNKNOWN` | A face is visible, but orientation cannot be estimated from available landmarks. |

## Current Features

- Local webcam processing with OpenCV.
- Face landmark detection with MediaPipe.
- Basic attention-state classification.
- Away-from-desk timing and looking-away events.
- Local JSON and CSV session summaries.
- Streamlit dashboard for session history.
- Privacy-first defaults: no image storage, no video storage, no accounts, no cloud upload.
- Focus and presence scores built from transparent formulas.

## How It Works

```mermaid
flowchart LR
  A[Webcam] --> B[OpenCV frame]
  B --> C[MediaPipe face landmarks]
  C --> D[Attention classifier]
  D --> E[Session tracker]
  E --> F[JSON / CSV summaries]
  F --> G[Streamlit dashboard]

  classDef red fill:#E50914,stroke:#7A0000,color:#FFFFFF;
  classDef black fill:#0B0B0F,stroke:#E50914,color:#FFFFFF;
  class A,C,E,G red;
  class B,D,F black;
```

## Demo

![FocusLens local demo storyboard](assets/demo.svg)

The repository includes a static demo storyboard for documentation. A real
webcam demo GIF is still a manual publication task because it should be recorded
from an actual local run.

## Tech Stack

| Layer | Tool | Role |
| --- | --- | --- |
| Language | Python 3.14 | Application, CLI, tests, and data processing. |
| Vision | OpenCV | Webcam access, frame handling, and overlays. |
| Landmarks | MediaPipe | Local face landmark detection. |
| Dashboard | Streamlit | Local web dashboard for session metrics. |
| Data | pandas | CSV reading, tables, and chart-friendly summaries. |
| Quality | pytest + Ruff | Tests, linting, and formatting. |

## Repository Structure

```text
focuslens/
|-- .github/
|   `-- workflows/
|       |-- ci.yml
|       `-- windows-exe.yml
|-- assets/
|   |-- demo.svg
|   `-- face_landmarker.task
|-- docs/
|   |-- architecture.md
|   |-- privacy.md
|   |-- release.md
|   `-- roadmap.md
|-- examples/
|   `-- sample_session.json
|-- scripts/
|   |-- build_windows_exe.ps1
|   `-- focuslens_launcher.py
|-- focuslens/
|   |-- camera.py
|   |-- face_tracker.py
|   |-- attention.py
|   |-- session.py
|   |-- storage.py
|   |-- dashboard.py
|   |-- overlay.py
|   |-- config.py
|   `-- cli.py
|-- tests/
|   |-- test_attention.py
|   |-- test_camera.py
|   |-- test_cli.py
|   |-- test_config.py
|   |-- test_dashboard.py
|   |-- test_examples.py
|   |-- test_face_tracker.py
|   |-- test_overlay.py
|   |-- test_public_api.py
|   |-- test_session.py
|   `-- test_storage.py
|-- dashboard.py
|-- pyproject.toml
|-- README.md
|-- CONTRIBUTING.md
`-- LICENSE
```

## Installation

Use Python 3.14 for local development and release validation.

```bash
git clone https://github.com/Flames4fun/Focuslens.git
cd Focuslens
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
pip install -e ".[dev]"
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

## Windows EXE

Build the first local Windows executable with:

```powershell
.\scripts\build_windows_exe.ps1
```

The build writes `dist\FocusLens.exe` and bundles the default MediaPipe model.
See [docs/release.md](docs/release.md) for release notes and current packaging
scope.

## Usage

Current CLI:

```bash
focuslens run
focuslens dashboard
```

`focuslens run` uses the included local MediaPipe Face Landmarker model at `assets/face_landmarker.task`, or a path supplied with `--model-path` / `FOCUSLENS_MODEL_PATH`. Packaged Windows builds use the bundled model by default. When the run closes, it tries to save JSON and CSV summaries to `sessions/` by default, even if the preview loop fails. Use `--save-dir` to choose another local directory, or `--no-save` for a temporary session.

Session summaries can be sensitive because they include timestamps, focus metrics, absence time, and pause history. FocusLens warns when you choose a non-default save directory or when summaries are written inside a Git repository. Confirm the directory is ignored before sharing commits, cloud folders, or synced desktops.

During `focuslens run`, press `p` to pause or resume attention analysis. The webcam preview remains open while paused, but FocusLens does not run face tracking for paused frames.

`focuslens dashboard` launches the included `dashboard.py` Streamlit app. Only run trusted local dashboard files; `--path` must point to a `.py` file inside this project unless you explicitly pass `--allow-external-dashboard`.

Development fallback:

```bash
python -m focuslens.cli run
streamlit run dashboard.py
```

## Example Session Summary

```json
{
  "away_events": 2,
  "away_seconds": 360.0,
  "ended_at": "2026-04-27T09:45:00+00:00",
  "focus_score": 73.6,
  "focused_seconds": 1965.0,
  "looking_away_events": 5,
  "looking_away_seconds": 210.0,
  "paused_seconds": 30.0,
  "presence_score": 86.52,
  "started_at": "2026-04-27T09:00:00+00:00",
  "too_close_seconds": 45.0,
  "too_far_seconds": 60.0,
  "total_seconds": 2700.0,
  "unknown_seconds": 30.0
}
```

## Dashboard

The dashboard is a local Streamlit view for:

- Weighted focus and presence scores.
- Latest session and best focus score.
- Aggregate state timing and counted events.
- Focus/presence trend charts.
- State distribution and event charts.
- Session history table derived from `sessions/sessions.csv`.

The dashboard reads only `sessions/sessions.csv`. It does not inspect webcam frames, session JSON files, secrets, or external services.

## Privacy

FocusLens is designed around privacy by default:

- Webcam frames are processed locally in memory.
- Images and videos are not saved by default.
- Session files store aggregated metrics only.
- Session summaries can still reveal personal work patterns, so review custom save directories before syncing or sharing them.
- Local `sessions/` output is ignored by Git to reduce accidental sharing of personal session history.
- No account is required.
- No cloud upload is required.
- The project does not identify people.

Read the full privacy contract in [docs/privacy.md](docs/privacy.md).

## Limitations

FocusLens is intentionally lightweight. It estimates useful signals, not absolute truth.

- Poor lighting can reduce detection quality.
- Face angle and camera position affect classification.
- It is not a medical, fatigue, emotion, or productivity diagnosis tool.
- It should not be used for employee monitoring or remote surveillance.

## Roadmap

| Phase | Focus |
| --- | --- |
| Current local build | Core modules, run CLI, session storage, dashboard, privacy docs, tests, and CI are in place. |
| Publication prep | Real webcam smoke test, privacy-safe demo, Windows EXE artifact, and initial issues. |
| `1.0` | Stable UX, calibration polish, documented camera troubleshooting, and a tagged Windows release. |
| Later | Pomodoro mode, YAML config, desktop notifications, HTML reports, and better threshold calibration. |

See [docs/roadmap.md](docs/roadmap.md) for the working release checklist.

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) for setup, checks, privacy guardrails, and good first areas.

## License

FocusLens is released under the [MIT License](LICENSE).
