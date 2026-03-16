"""Database module: connection, schema creation, and CRUD for all tables."""

import os
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone


def _user_data_dir() -> Path:
    """Return the platform-appropriate user data directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = base / "JobOpeningsTracker"
    d.mkdir(parents=True, exist_ok=True)
    return d


# Legacy path (next to the app) — checked for migration on first run.
_LEGACY_DB_PATH = Path(__file__).parent / "job_openings.db"

DB_PATH = _user_data_dir() / "job_openings.db"


def _migrate_legacy_db() -> None:
    """If a DB exists at the legacy location but not at the new location, move it."""
    if _LEGACY_DB_PATH.exists() and not DB_PATH.exists():
        import shutil
        shutil.move(str(_LEGACY_DB_PATH), str(DB_PATH))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    _migrate_legacy_db()
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

    _seed_sample_data()


def _seed_sample_data() -> None:
    """Insert sample data so the app isn't empty on first launch.

    Only runs once — checks whether any rows already exist.
    """
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM job_openings").fetchone()[0]
        if count > 0:
            return

        now = _now()

        # --- Sample job opening ---
        conn.execute(
            """
            INSERT INTO job_openings
                (teal_import_raw, job_title, customer_name, application_url,
                 job_description_contents, archived, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                _SAMPLE_RESUME,
                "Senior Software Engineer",
                "Acme Corp",
                "https://example.com/apply/senior-swe",
                _SAMPLE_JOB_DESCRIPTION,
                now, now,
            ),
        )
        job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # --- Sample person linked to the job ---
        conn.execute(
            "INSERT INTO people (name, title, details, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("Jane Smith", "VP of Engineering", "LinkedIn: https://linkedin.com/in/example\nWill be conducting the technical interview.", now, now),
        )
        person_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO job_opening_people (job_opening_id, person_id) VALUES (?, ?)",
            (job_id, person_id),
        )
        conn.commit()


_SAMPLE_RESUME = """\
### Alex Johnson
**Software Engineer | Python, JavaScript, Cloud Infrastructure**

### Summary
Experienced software engineer with 6+ years building web applications and data pipelines. \
Strong background in Python, React, and AWS. Passionate about clean code and developer tooling.

### Experience

**Software Engineer II** - TechStart Inc. (2021 - Present)
- Built and maintained RESTful APIs serving 50K+ daily requests using Python/FastAPI
- Led migration from monolithic architecture to microservices, reducing deploy times by 70%
- Mentored 3 junior engineers through code reviews and pair programming sessions

**Software Engineer** - DataFlow Systems (2018 - 2021)
- Developed ETL pipelines processing 2M+ records daily using Python and Apache Airflow
- Created internal dashboard with React and D3.js for real-time pipeline monitoring
- Reduced data processing costs by 40% through query optimization

### Education
**B.S. Computer Science** - State University (2018)

### Skills
Python, JavaScript/TypeScript, React, FastAPI, PostgreSQL, AWS (EC2, S3, Lambda), Docker, Git\
"""

_SAMPLE_JOB_DESCRIPTION = """\
### Senior Software Engineer - Acme Corp

**Location:** Remote (US)
**Department:** Platform Engineering

### About the Role
We're looking for a Senior Software Engineer to join our Platform team. You'll design and build \
the core services that power Acme's product suite, working closely with product and data teams.

### Responsibilities
- Design, build, and maintain scalable backend services in Python
- Collaborate with cross-functional teams to define technical requirements
- Mentor junior engineers and contribute to engineering best practices
- Participate in on-call rotation for production systems

### Requirements
- 5+ years of professional software engineering experience
- Strong proficiency in Python and at least one web framework (Django, FastAPI, Flask)
- Experience with cloud platforms (AWS, GCP, or Azure)
- Familiarity with containerization (Docker, Kubernetes)
- Excellent communication and collaboration skills

### Nice to Have
- Experience with data pipelines or ML infrastructure
- Contributions to open source projects
- Experience in a startup or high-growth environment\
"""


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
