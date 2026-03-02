"""Entry point for the Job Openings Tracker.

Usage:
    python main.py          # launches the GUI
    python main.py --cli    # launches the original CLI
"""

import sys


def _check_dependencies() -> list[str]:
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
