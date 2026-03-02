"""Interactive CLI for the Job Openings Tracker."""

import textwrap
from pathlib import Path

import db
import pdf_importer


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _hr(char: str = "─", width: int = 60) -> str:
    return char * width


def _print_job_row(row: db.sqlite3.Row) -> None:
    title = row["job_title"] or "(no title)"
    company = row["customer_name"] or "(no company)"
    print(f"  [{row['id']:>4}]  {title} @ {company}")
    if row["application_url"]:
        print(f"          Apply  : {row['application_url']}")


def _print_job_detail(row: db.sqlite3.Row) -> None:
    print(_hr())
    print(f"Job #{row['id']}")
    print(_hr())
    print(f"  Title        : {row['job_title'] or '—'}")
    print(f"  Company      : {row['customer_name'] or '—'}")
    print(f"  Apply URL    : {row['application_url'] or '—'}")
    print(f"  Archived     : {'Yes' if row['archived'] else 'No'}")
    print(f"  Created      : {row['created_at']}")
    print(f"  Updated      : {row['updated_at']}")
    print()
    if row["teal_import_raw"]:
        print("--- Teal Import ---")
        print(textwrap.indent(row["teal_import_raw"], "  "))
    if row["job_description_contents"]:
        print()
        print("--- Job Description ---")
        print(textwrap.indent(row["job_description_contents"], "  "))
    print(_hr())


def _prompt(msg: str) -> str:
    return input(f"{msg}: ").strip()


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_import() -> None:
    path_str = _prompt("Path to Teal PDF")
    if not path_str:
        print("  Cancelled.")
        return
    path = Path(path_str.strip('"').strip("'"))
    try:
        count = pdf_importer.import_pdf(path)
        print(f"  Imported {count} record(s).")
    except FileNotFoundError as exc:
        print(f"  Error: {exc}")
    except RuntimeError as exc:
        print(f"  Error: {exc}")


def cmd_list() -> None:
    rows = db.list_jobs()
    if not rows:
        print("  No job openings in the database yet.")
        return
    print(_hr())
    print(f"  {'ID':>4}   Title @ Company")
    print(_hr())
    for row in rows:
        _print_job_row(row)
    print(_hr())
    print(f"  {len(rows)} record(s).")


def cmd_view() -> None:
    job_id_str = _prompt("Job ID to view")
    if not job_id_str.isdigit():
        print("  Invalid ID.")
        return
    row = db.get_job(int(job_id_str))
    if row is None:
        print(f"  No job found with ID {job_id_str}.")
        return
    _print_job_detail(row)


def cmd_edit() -> None:
    job_id_str = _prompt("Job ID to edit")
    if not job_id_str.isdigit():
        print("  Invalid ID.")
        return
    job_id = int(job_id_str)
    row = db.get_job(job_id)
    if row is None:
        print(f"  No job found with ID {job_id}.")
        return

    print(f"  Editing Job #{job_id}: {row['job_title'] or '(no title)'}")
    print("  Press Enter to keep the current value.")

    fields: dict[str, str] = {}

    for field, label in [
        ("job_title", "Job Title"),
        ("customer_name", "Company Name"),
        ("application_url", "Application URL"),
    ]:
        current = row[field] or ""
        val = _prompt(f"  {label} [{current}]")
        if val:
            fields[field] = val

    has_jd = bool(row["job_description_contents"])
    jd_prompt = "  Job Description text (paste; Enter to keep existing)" if has_jd else "  Job Description text (paste; Enter to skip)"
    jd_text = _prompt(jd_prompt)
    if jd_text:
        fields["job_description_contents"] = jd_text

    if fields:
        db.update_job(job_id, **fields)
        print(f"  Job #{job_id} updated.")
    else:
        print("  No changes made.")


def cmd_add() -> None:
    """Manually add a new job opening (no PDF required)."""
    print("  Adding a new job opening manually.")
    job_title = _prompt("  Job Title")
    customer_name = _prompt("  Company Name")
    application_url = _prompt("  Application URL (optional)")
    jd_text = _prompt("  Job Description text (paste; or Enter to skip)")

    job_id = db.insert_job(
        teal_import_raw="",
        job_title=job_title or None,
        customer_name=customer_name or None,
    )

    updates: dict[str, str] = {}
    if application_url:
        updates["application_url"] = application_url
    if jd_text:
        updates["job_description_contents"] = jd_text

    if updates:
        db.update_job(job_id, **updates)

    print(f"  Job #{job_id} created.")


def cmd_archive() -> None:
    job_id_str = _prompt("Job ID to archive")
    if not job_id_str.isdigit():
        print("  Invalid ID.")
        return
    job_id = int(job_id_str)
    row = db.get_job(job_id)
    if row is None:
        print(f"  No job found with ID {job_id}.")
        return
    if row["archived"]:
        print(f"  Job #{job_id} is already archived.")
        return
    title = row["job_title"] or "(no title)"
    company = row["customer_name"] or "(no company)"
    confirm = _prompt(f"  Archive '{title} @ {company}'? [y/N]").lower()
    if confirm == "y":
        db.archive_job(job_id)
        print(f"  Job #{job_id} archived.")
    else:
        print("  Cancelled.")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

MENU = """
╔══════════════════════════════════╗
║   Job Openings Tracker v1        ║
╠══════════════════════════════════╣
║  i  — Import Teal PDF            ║
║  l  — List all jobs              ║
║  v  — View job detail            ║
║  e  — Edit / enrich a job        ║
║  a  — Add job manually           ║
║  x  — Archive a job              ║
║  q  — Quit                       ║
╚══════════════════════════════════╝
"""


def run() -> None:
    db.init_db()
    while True:
        print(MENU)
        choice = input("Choice: ").strip().lower()
        print()
        if choice == "i":
            cmd_import()
        elif choice == "l":
            cmd_list()
        elif choice == "v":
            cmd_view()
        elif choice == "e":
            cmd_edit()
        elif choice == "a":
            cmd_add()
        elif choice == "x":
            cmd_archive()
        elif choice in ("q", "quit", "exit"):
            print("Goodbye.")
            break
        else:
            print("  Unknown option.  Please choose from the menu.")
        print()
