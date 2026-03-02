"""Database module: connection, schema creation, and CRUD for job_openings."""

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
