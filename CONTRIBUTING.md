# Contributing to FocusLens

Thanks for considering a contribution. FocusLens is small on purpose: a local
webcam signal becomes a coarse attention state, then a local session summary.
Changes should keep that privacy-first shape clear.

## Ground Rules

- Do not add image or video persistence by default.
- Do not add cloud upload, accounts, remote tracking, or identity recognition.
- Keep camera-frame handling inside the camera, tracker, and overlay boundary.
- Store only derived aggregate metrics unless a future design explicitly
  documents a safer data flow.
- Prefer small, testable changes.

## Development Setup

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

macOS / Linux:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Checks

Run the same checks used by CI:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

Use `python -m ruff format .` to apply formatting before opening a pull
request.

## Good First Areas

- Tests for pure functions and storage edge cases.
- Dashboard polish that still reads only aggregate CSV data.
- Documentation for Windows camera permissions and MediaPipe model setup.
- Sample session data and demo assets.
- Threshold calibration notes.

## Pull Requests

Please describe the behavior change, note any privacy impact, and include the
checks you ran. If a change touches webcam, storage, or dashboard behavior,
explain what data is processed and what data is saved.
