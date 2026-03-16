"""PDF import adapter.

Sends the PDF to Google Gemini (gemini-3-flash-preview) as inline bytes and
stores the full Markdown response as a single record.

If Gemini cannot be reached (missing API key, network error, quota, etc.) a
RuntimeError is raised with a human-readable message.  No pdfplumber fallback.
"""

import os
from pathlib import Path

import db


def _user_data_dir() -> Path:
    """Return the platform-appropriate user data directory."""
    import sys
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = base / "JobOpeningsTracker"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _key_file_path() -> Path:
    """Return the path to the key file in the user data folder."""
    return _user_data_dir() / "gemini_api_key.txt"


def _load_api_key() -> str:
    """Return the Gemini API key.

    Checks, in order:
      1. GEMINI_API_KEY environment variable
      2. gemini_api_key.txt in the user data folder
      3. key.env in the app directory (legacy location)
    """
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    key_file = _key_file_path()
    if key_file.exists():
        key = key_file.read_text(encoding="utf-8").strip()
        if key and not key.startswith("#"):
            return key
    # Legacy fallback: key.env in app directory
    legacy = Path(__file__).parent / "key.env"
    if legacy.exists():
        key = legacy.read_text(encoding="utf-8").strip()
        if key and not key.startswith("#"):
            return key
    return ""


def save_api_key(key: str) -> None:
    """Save the Gemini API key to the user data folder."""
    _key_file_path().write_text(key.strip(), encoding="utf-8")


# ---------------------------------------------------------------------------
# Gemini prompt
# ---------------------------------------------------------------------------

_GEMINI_PROMPT = """\
Purpose and Goals:
* Accurately convert the contents of provided files or text into valid Markdown format.
* Ensure the structural hierarchy of the document is maintained according to specific heading constraints.
* Provide a clean, text-only output suitable for documentation or technical use.
Behaviors and Rules:
1) Formatting Standards:
 a) Set 'Heading 3' (###) as the highest heading level. If the source has Title or Heading 1/2 levels, downscale them appropriately so that the document starts at ###.
 b) Do not add citations, references, or footnotes to the content.
 c) Do not include any emojis in the output.
 d) Preserve the original meaning and data of the text without adding commentary or interpretations.
2) Operational Constraints:
 a) Process the request using high-speed processing logic consistent with a 'Fast' model approach, prioritizing efficiency and direct output.
 b) If the input file contains complex elements (like tables or lists), convert them into their standard Markdown equivalents.
Overall Tone:
* Professional, utilitarian, and precise.
* Strictly follow formatting constraints without deviation.\
"""

_GEMINI_MODEL = "gemini-3-flash-preview"


# ---------------------------------------------------------------------------
# Gemini extraction
# ---------------------------------------------------------------------------

def _extract_via_gemini(pdf_path: Path) -> str:
    """Send the PDF to Gemini and return Markdown text.

    Raises RuntimeError with a user-facing message on any failure.
    """
    api_key = _load_api_key()
    if not api_key:
        raise RuntimeError(
            "Gemini API key not found.\n\n"
            "Either:\n"
            "  1. Paste your key into the file 'key.env' in the app folder, or\n"
            "  2. Set the environment variable GEMINI_API_KEY before launching."
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise RuntimeError(
            "The google-genai package is not installed.\n\n"
            "Run:  pip install google-genai"
        )

    try:
        pdf_bytes = pdf_path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"Could not read PDF file:\n{exc}")

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=_GEMINI_MODEL,
            contents=[
                _GEMINI_PROMPT,
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            ],
        )
        text = response.text
        if not text or not text.strip():
            raise RuntimeError(
                f"Gemini ({_GEMINI_MODEL}) returned an empty response.\n\n"
                "The PDF may be image-only, password-protected, or too large."
            )
        return text.strip()
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Gemini API error ({type(exc).__name__}):\n{exc}"
        )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def import_pdf(pdf_path: str | Path) -> tuple[int, str]:
    """Import a PDF via Gemini.

    Returns (job_id, error_message).  If error_message is non-empty the record
    was still inserted but teal_import_raw contains the error text so the user
    can see it in the Resume tab of the detail pane.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    error_msg = ""
    try:
        markdown = _extract_via_gemini(pdf_path)
    except RuntimeError as exc:
        error_msg = str(exc)
        markdown = f"[Import error — Gemini could not convert this PDF]\n\n{error_msg}"

    job_id = db.insert_job(
        teal_import_raw=markdown,
        job_title=None,
        customer_name=None,
    )
    return job_id, error_msg
