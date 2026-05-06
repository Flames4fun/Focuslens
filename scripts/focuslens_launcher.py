"""PyInstaller entry point for the FocusLens Windows executable."""

import sys

from focuslens.cli import main


def launcher_args(argv: list[str]) -> list[str]:
    """Default the packaged EXE to the webcam run command on double click."""

    if len(argv) == 1:
        return ["run"]

    return argv[1:]


if __name__ == "__main__":
    raise SystemExit(main(launcher_args(sys.argv)))
