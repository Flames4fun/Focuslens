"""PyInstaller entry point for the FocusLens Windows executable."""

from focuslens.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
