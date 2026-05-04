<div align="center">

<img
  src="https://capsule-render.vercel.app/api?type=waving&height=220&color=0:0B0B0F,55:E50914,100:190006&text=FocusLens&fontColor=FFFFFF&fontSize=64&fontAlignY=38&desc=Privacy-first%20local%20focus%20tracking%20for%20deep%20work&descAlignY=58&animation=fadeIn"
  alt="FocusLens animated red and black banner"
/>

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-E50914?style=for-the-badge&labelColor=0B0B0F&logo=python&logoColor=white)](#tech-stack)
[![OpenCV](https://img.shields.io/badge/OpenCV-Webcam%20Vision-E50914?style=for-the-badge&labelColor=0B0B0F&logo=opencv&logoColor=white)](#tech-stack)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Face%20Landmarks-E50914?style=for-the-badge&labelColor=0B0B0F)](#tech-stack)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-E50914?style=for-the-badge&labelColor=0B0B0F&logo=streamlit&logoColor=white)](#dashboard)
[![MIT](https://img.shields.io/badge/License-MIT-E50914?style=for-the-badge&labelColor=0B0B0F)](LICENSE)

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

FocusLens is in its early open source build phase. The product direction is defined, the package basics are in place, the OpenCV camera boundary exists, the pure attention classifier is tested, the MediaPipe face-tracking boundary exists, the local preview loop is wired through the CLI and overlay renderer, and session metrics plus local JSON/CSV summary storage are integrated into `focuslens run`.

Current local progress, checked on 2026-05-04:

- Created and tested: `focuslens/config.py`, `focuslens/attention.py`, `focuslens/camera.py`, `focuslens/face_tracker.py`, `focuslens/overlay.py`, `focuslens/cli.py`, `focuslens/session.py`, `focuslens/storage.py`, and their current unit tests.
- Verified with the project virtual environment: `131 passed`, `ruff check .` passed, and `ruff format --check .` passed.
- The global `python` currently points to Python 3.14 in this workspace and does not have `pytest` or `ruff`; use `.venv\Scripts\python.exe` or activate `.venv` before running checks.
- Closing `focuslens run` now writes a local JSON summary and appends `sessions.csv`.
- Next: build `dashboard.py`, `docs/privacy.md`, and `.github/workflows/ci.yml`.

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

## Features Planned For V1

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

## Tech Stack

| Layer | Tool | Role |
| --- | --- | --- |
| Language | Python 3.11+ | Application, CLI, tests, and data processing. |
| Vision | OpenCV | Webcam access, frame handling, and overlays. |
| Landmarks | MediaPipe | Local face landmark detection. |
| Dashboard | Streamlit | Local web dashboard for session metrics. |
| Data | pandas | CSV reading, tables, and chart-friendly summaries. |
| Quality | pytest + Ruff | Tests, linting, and formatting. |

## Target Repository Structure

```text
focuslens/
|-- focuslens/
|   |-- camera.py
|   |-- face_tracker.py
|   |-- attention.py
|   |-- session.py
|   |-- storage.py
|   |-- overlay.py
|   |-- config.py
|   `-- cli.py
|-- docs/
|   |-- privacy.md
|   |-- architecture.md
|   `-- roadmap.md
|-- tests/
|-- dashboard.py
|-- pyproject.toml
|-- README.md
`-- LICENSE
```

## Installation

The planned development setup is:

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

## Usage

Current CLI:

```bash
focuslens run
focuslens dashboard
```

`focuslens run` expects a local MediaPipe Face Landmarker model at `assets/face_landmarker.task`, or a path supplied with `--model-path` / `FOCUSLENS_MODEL_PATH`. When the run closes, it tries to save JSON and CSV summaries to `sessions/` by default, even if the preview loop fails. Use `--save-dir` to choose another local directory, or `--no-save` for a temporary session.

Session summaries can be sensitive because they include timestamps, focus metrics, absence time, and pause history. FocusLens warns when you choose a non-default save directory or when summaries are written inside a Git repository. Confirm the directory is ignored before sharing commits, cloud folders, or synced desktops.

During `focuslens run`, press `p` to pause or resume attention analysis. The webcam preview remains open while paused, but FocusLens does not run face tracking for paused frames.

`focuslens dashboard` is already exposed as a command, but it needs `dashboard.py` to exist before it can open Streamlit. Only run trusted local dashboard files; `--path` must point to a `.py` file inside this project unless you explicitly pass `--allow-external-dashboard`.

Development fallback:

```bash
python -m focuslens.cli run
streamlit run dashboard.py
```

## Example Session Summary

```json
{
  "started_at": "2026-04-27T09:00:00",
  "ended_at": "2026-04-27T10:15:32",
  "total_seconds": 4532,
  "focused_seconds": 3130,
  "away_seconds": 520,
  "looking_away_events": 23,
  "focus_score": 74.2,
  "presence_score": 88.5
}
```

## Dashboard

The dashboard is planned as a local Streamlit view for:

- Latest session summary.
- Focus score and presence score.
- Away time and looking-away events.
- Session history table.
- Simple charts for focus, absence, and distractions.

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

## Limitations

FocusLens is intentionally lightweight. It estimates useful signals, not absolute truth.

- Poor lighting can reduce detection quality.
- Face angle and camera position affect classification.
- It is not a medical, fatigue, emotion, or productivity diagnosis tool.
- It should not be used for employee monitoring or remote surveillance.

## Roadmap

| Version | Focus |
| --- | --- |
| `0.1` | Current core: configuration, OpenCV camera boundary, attention classification, MediaPipe face tracker boundary, overlay rendering, session metrics, run CLI, and tests. |
| `0.2` | Current CLI session saving with the existing session metrics and JSON/CSV storage modules. |
| `0.3` | Streamlit dashboard, session history, charts, privacy docs, and CI. |
| `1.0` | Stable UX, calibration polish, demo assets, and contributor-ready docs. |

## Contributing

Contributions are welcome once the first implementation lands. Good starting areas will include tests, dashboard polish, privacy documentation, Windows setup notes, and sample session files.

## License

FocusLens is released under the [MIT License](LICENSE).
