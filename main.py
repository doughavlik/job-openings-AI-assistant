"""Entry point for the Job Openings Tracker.

Usage:
    python main.py          # launches the GUI
    python main.py --cli    # launches the original CLI
"""

import sys


def _setup_frozen_logging() -> None:
    """When running as a PyInstaller bundle, redirect stdout/stderr to a log
    file in the user-data folder so startup errors are always captured and
    can be shared for support."""
    import os
    from pathlib import Path

    data_dir = (
        Path(os.environ["LOCALAPPDATA"]) / "JobOpeningsTracker"
        if sys.platform == "win32"
        else Path.home() / "Library" / "Application Support" / "JobOpeningsTracker"
        if sys.platform == "darwin"
        else Path.home() / ".local" / "share" / "JobOpeningsTracker"
    )
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "startup.log"

    # Open unbuffered (line-buffered text) so the file is readable even if the
    # app crashes mid-startup.
    log_file = open(log_path, "w", buffering=1, encoding="utf-8")  # noqa: WPS515
    sys.stdout = log_file
    sys.stderr = log_file
    print(f"Log file: {log_path}")


def _check_dependencies() -> list[str]:
    """Only meaningful when running from source.  Skipped when frozen."""
    missing = []
    for pkg, import_name in [
        ("pdfplumber", "pdfplumber"),
        ("google-genai", "google.genai"),
        ("PySide6", "PySide6"),
    ]:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
    return missing


def main() -> None:
    # When packaged by PyInstaller all dependencies are bundled — skip the
    # dev-time check and instead write all output to a log file so any
    # crash can be diagnosed without needing a debug build.
    if getattr(sys, "frozen", False):
        _setup_frozen_logging()
    else:
        missing = _check_dependencies()
        if missing:
            print("Missing required packages.  Install them with:")
            print(f"    pip install {' '.join(missing)}")
            print()
            print("Or install all at once:")
            print("    pip install -r requirements.txt")
            sys.exit(1)

    if "--cli" in sys.argv:
        import cli
        cli.run()
    else:
        import gui
        gui.run()


if __name__ == "__main__":
    main()
