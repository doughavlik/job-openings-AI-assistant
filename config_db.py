"""Config database module.

Manages config.db, which stores AI Prompt Builder action definitions.

Seed-file pattern
-----------------
config.db lives in the project directory and is committed to git — this is
the "factory default" file that ships with the app.

On first run, _ensure_user_db() copies it to the user's local data folder
(%LOCALAPPDATA%\\JobOpeningsTracker on Windows, ~/.local/share/JobOpeningsTracker
on macOS/Linux).  All subsequent reads and writes use the local copy, so
user customisations are never overwritten by a git pull.
"""

import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Seed file: ships with the app, committed to git.
SEED_DB_PATH = Path(__file__).parent / "config.db"

def _user_data_dir() -> Path:
    """Return the platform-appropriate user data directory."""
    import os, sys
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = base / "JobOpeningsTracker"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _user_db_path() -> Path:
    return _user_data_dir() / "config.db"

def _ensure_user_db() -> Path:
    """Copy seed DB to user data folder on first run. Returns path to user DB."""
    user_path = _user_db_path()
    if not user_path.exists():
        if SEED_DB_PATH.exists():
            shutil.copy2(SEED_DB_PATH, user_path)
        else:
            # No seed file yet (e.g. fresh dev checkout before init_config_db was run).
            # Create a blank DB — init_config_db() will set up the schema.
            pass
    return user_path

def get_connection() -> sqlite3.Connection:
    path = _ensure_user_db()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def init_config_db() -> None:
    """Create tables in the user DB (idempotent)."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prompt_actions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                name             TEXT NOT NULL,
                instructions     TEXT NOT NULL DEFAULT '',
                use_company      INTEGER NOT NULL DEFAULT 1,
                use_job_desc     INTEGER NOT NULL DEFAULT 1,
                use_resume       INTEGER NOT NULL DEFAULT 1,
                use_person       INTEGER NOT NULL DEFAULT 0,
                person_required  INTEGER NOT NULL DEFAULT 0,
                sort_order       INTEGER NOT NULL DEFAULT 0,
                created_at       TEXT NOT NULL,
                updated_at       TEXT NOT NULL
            )
        """)
        conn.commit()

# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def list_actions() -> list[sqlite3.Row]:
    """Return all actions ordered by sort_order, then id."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM prompt_actions ORDER BY sort_order, id"
        ).fetchall()

def get_action(action_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM prompt_actions WHERE id = ?", (action_id,)
        ).fetchone()

def insert_action(
    name: str,
    instructions: str = "",
    use_company: bool = True,
    use_job_desc: bool = True,
    use_resume: bool = True,
    use_person: bool = False,
    person_required: bool = False,
    sort_order: int = 0,
) -> int:
    now = _now()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO prompt_actions
                (name, instructions, use_company, use_job_desc, use_resume,
                 use_person, person_required, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, instructions, int(use_company), int(use_job_desc), int(use_resume),
             int(use_person), int(person_required), sort_order, now, now),
        )
        conn.commit()
        return cur.lastrowid

def update_action(action_id: int, **fields) -> bool:
    allowed = {
        "name", "instructions", "use_company", "use_job_desc", "use_resume",
        "use_person", "person_required", "sort_order",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    # Coerce booleans to int for SQLite
    for bool_col in ("use_company", "use_job_desc", "use_resume", "use_person", "person_required"):
        if bool_col in updates:
            updates[bool_col] = int(updates[bool_col])
    updates["updated_at"] = _now()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [action_id]
    with get_connection() as conn:
        cur = conn.execute(
            f"UPDATE prompt_actions SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
        return cur.rowcount > 0

def delete_action(action_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM prompt_actions WHERE id = ?", (action_id,))
        conn.commit()
        return cur.rowcount > 0
