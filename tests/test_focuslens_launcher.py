import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER_PATH = PROJECT_ROOT / "scripts" / "focuslens_launcher.py"


def load_launcher_module():
    spec = importlib.util.spec_from_file_location("focuslens_launcher", LAUNCHER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launcher_defaults_double_click_to_run_command():
    launcher = load_launcher_module()

    assert launcher.launcher_args(["FocusLens.exe"]) == ["run"]


def test_launcher_preserves_explicit_arguments():
    launcher = load_launcher_module()

    assert launcher.launcher_args(["FocusLens.exe", "--version"]) == ["--version"]
    assert launcher.launcher_args(["FocusLens.exe", "run", "--no-save"]) == [
        "run",
        "--no-save",
    ]
