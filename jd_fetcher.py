"""Job description web fetcher.

Fetches a job posting URL, strips navigation/boilerplate, and converts the
main content to Markdown (H3 as top-level heading).

Falls back gracefully: if fetching fails, returns None and prints an
informative message so the user can paste the content manually.
"""

import re
import sys
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None  # type: ignore

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore

try:
    import markdownify as md_lib
except ImportError:
    md_lib = None  # type: ignore


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TIMEOUT = 15  # seconds

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Tags whose content is almost always boilerplate — strip before converting.
_STRIP_TAGS = {"nav", "header", "footer", "aside", "script", "style", "noscript", "iframe"}

# CSS class/id fragments that suggest boilerplate containers.
_BOILERPLATE_PATTERNS = re.compile(
    r"(nav|navbar|footer|header|sidebar|cookie|banner|ad-|advertisement|modal|popup)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# HTML cleaning helpers
# ---------------------------------------------------------------------------

def _strip_boilerplate(soup: "BeautifulSoup") -> None:
    for tag in _STRIP_TAGS:
        for el in soup.find_all(tag):
            el.decompose()

    from bs4 import Tag
    for el in soup.find_all(True):
        if not isinstance(el, Tag) or not el.attrs:
            continue
        classes = " ".join(el.get("class", []))
        el_id = el.get("id", "")
        if _BOILERPLATE_PATTERNS.search(classes) or _BOILERPLATE_PATTERNS.search(el_id):
            el.decompose()


def _find_main_content(soup: "BeautifulSoup") -> "BeautifulSoup":
    """Return the most likely 'main content' element."""
    for selector in ("main", '[role="main"]', "article", "#content", ".content", ".job-description"):
        el = soup.select_one(selector)
        if el:
            return el
    return soup.body or soup


# ---------------------------------------------------------------------------
# Markdown post-processing
# ---------------------------------------------------------------------------

def _promote_headings(markdown: str) -> str:
    """Demote H1/H2 to H3 so H3 is the top-level heading, as per the PRD."""
    lines = []
    for line in markdown.splitlines():
        if line.startswith("# ") and not line.startswith("### "):
            # H1 → H3
            line = "###" + line[1:]
        elif line.startswith("## ") and not line.startswith("### "):
            # H2 → H3
            line = "###" + line[2:]
        lines.append(line)
    return "\n".join(lines)


def _clean_markdown(text: str) -> str:
    # Collapse 3+ blank lines to 2.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def fetch_job_description(url: str) -> str | None:
    """Fetch *url*, convert to Markdown, and return the result.

    Returns ``None`` if the fetch fails (network error, bot-block, etc.).
    The caller should offer the user a manual-paste fallback in that case.
    """
    if requests is None:
        print("  [error] 'requests' package not installed.  Run: pip install requests")
        return None
    if BeautifulSoup is None:
        print("  [error] 'beautifulsoup4' not installed.  Run: pip install beautifulsoup4")
        return None

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        print(f"  [warn] Request timed out after {_TIMEOUT}s: {url}")
        return None
    except requests.exceptions.HTTPError as exc:
        print(f"  [warn] HTTP {exc.response.status_code} for {url}")
        return None
    except requests.exceptions.RequestException as exc:
        print(f"  [warn] Network error: {exc}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    _strip_boilerplate(soup)
    main = _find_main_content(soup)

    if md_lib is not None:
        raw_md = md_lib.markdownify(str(main), heading_style="ATX")
    else:
        # Fallback: extract plain text if markdownify is unavailable.
        raw_md = main.get_text(separator="\n")

    result = _promote_headings(_clean_markdown(raw_md))
    return result if result else None
