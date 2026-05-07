"""PyInstaller entry point for the FocusLens dashboard executable."""

import sys

from focuslens.cli import main


def launcher_args(argv: list[str]) -> list[str]:
    """Default the packaged dashboard EXE to the dashboard command."""

    if len(argv) == 1:
        return ["dashboard"]

    args = argv[1:]
    if args[0] == "dashboard":
        return args

    if args[0] in {"--version", "-h", "--help"}:
        return args

    return ["dashboard", *args]


if __name__ == "__main__":
    raise SystemExit(main(launcher_args(sys.argv)))
