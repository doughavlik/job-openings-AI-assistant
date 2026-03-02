"""Database module: connection, schema creation, and CRUD for all tables."""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent / "job_openings.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_openings (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                teal_import_raw         TEXT,
                job_title               TEXT,
                customer_name           TEXT,
                job_description_url     TEXT,
                application_url         TEXT,
                job_description_contents TEXT,
                archived                INTEGER NOT NULL DEFAULT 0,
                created_at              TEXT NOT NULL,
                updated_at              TEXT NOT NULL
            )
        """)
        # Migrate existing databases that predate the archived column.
        existing = {row[1] for row in conn.execute("PRAGMA table_info(job_openings)")}
        if "archived" not in existing:
            conn.execute("ALTER TABLE job_openings ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS people (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT,
                title      TEXT,
                details    TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_opening_people (
                job_opening_id INTEGER NOT NULL REFERENCES job_openings(id),
                person_id      INTEGER NOT NULL REFERENCES people(id),
                PRIMARY KEY (job_opening_id, person_id)
            )
        """)

        conn.commit()


def insert_job(teal_import_raw: str, job_title: str = None, customer_name: str = None) -> int:
    now = _now()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO job_openings
                (teal_import_raw, job_title, customer_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (teal_import_raw, job_title, customer_name, now, now),
        )
        conn.commit()
        return cur.lastrowid


def archive_job(job_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE job_openings SET archived = 1, updated_at = ? WHERE id = ?",
            (_now(), job_id),
        )
        conn.commit()
        return cur.rowcount > 0


def update_job(job_id: int, **fields) -> bool:
    allowed = {
        "job_title", "customer_name", "job_description_url",
        "application_url", "job_description_contents",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates["updated_at"] = _now()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [job_id]
    with get_connection() as conn:
        cur = conn.execute(
            f"UPDATE job_openings SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
        return cur.rowcount > 0


def get_job(job_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM job_openings WHERE id = ?", (job_id,)
        ).fetchone()


def list_jobs() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, job_title, customer_name, job_description_url, application_url, created_at "
            "FROM job_openings WHERE archived = 0 ORDER BY id"
        ).fetchall()


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

def insert_person(job_opening_id: int, name: str = None, title: str = None,
                  details: str = None) -> int:
    """Create a new person and link them to the given job opening."""
    now = _now()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO people (name, title, details, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (name, title, details, now, now),
        )
        person_id = cur.lastrowid
        conn.execute(
            "INSERT INTO job_opening_people (job_opening_id, person_id) VALUES (?, ?)",
            (job_opening_id, person_id),
        )
        conn.commit()
    return person_id


def update_person(person_id: int, **fields) -> bool:
    allowed = {"name", "title", "details"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates["updated_at"] = _now()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [person_id]
    with get_connection() as conn:
        cur = conn.execute(f"UPDATE people SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return cur.rowcount > 0


def unlink_person(job_opening_id: int, person_id: int) -> bool:
    """Remove the link between a person and a job opening (does not delete the person)."""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM job_opening_people WHERE job_opening_id = ? AND person_id = ?",
            (job_opening_id, person_id),
        )
        conn.commit()
        return cur.rowcount > 0


def get_people_for_job(job_opening_id: int) -> list[sqlite3.Row]:
    """Return all people linked to the given job opening."""
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT p.id, p.name, p.title, p.details
            FROM people p
            JOIN job_opening_people jop ON jop.person_id = p.id
            WHERE jop.job_opening_id = ?
            ORDER BY p.id
            """,
            (job_opening_id,),
        ).fetchall()


def job_has_people(job_opening_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM job_opening_people WHERE job_opening_id = ? LIMIT 1",
            (job_opening_id,),
        ).fetchone()
        return row is not None
