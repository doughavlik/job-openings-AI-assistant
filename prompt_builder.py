"""Prompt assembly logic for the AI Prompt Builder.

Assembles a prompt in fixed order:
    [Action instructions]
    [Context components: company → job description → resume → person]
    [Additional context / question text]

All functions are pure (no UI, no side effects).
"""

import sqlite3


def assemble_prompt(
    action: sqlite3.Row,
    job: sqlite3.Row,
    person: sqlite3.Row | None = None,
    additional_context: str = "",
) -> str:
    """Return the fully assembled prompt string.

    Parameters
    ----------
    action:
        A row from prompt_actions (config_db).
    job:
        A row from job_openings (db).
    person:
        A row from people (db), or None if no person is required/selected.
    additional_context:
        Free-text entered by the user in Step 2 of the dialog.
    """
    parts: list[str] = []

    # ---- 1. Action-specific instructions --------------------------------
    instructions = (action["instructions"] or "").strip()
    if instructions:
        parts.append(instructions)

    # ---- 2. Context components (fixed order) ----------------------------

    # Company name
    if action["use_company"]:
        company = (job["customer_name"] or "").strip()
        if company:
            parts.append(f"## Company\n{company}")

    # Job description
    if action["use_job_desc"]:
        jd = (job["job_description_contents"] or "").strip()
        if jd:
            parts.append(f"## Job Description\n{jd}")

    # Resume
    if action["use_resume"]:
        resume = (job["teal_import_raw"] or "").strip()
        if resume:
            parts.append(f"## Resume\n{resume}")

    # Person
    if action["use_person"] and person is not None:
        person_parts = []
        if person["name"]:
            person_parts.append(f"**Name:** {person['name']}")
        if person["title"]:
            person_parts.append(f"**Title:** {person['title']}")
        if person["details"]:
            person_parts.append(person["details"].strip())
        if person_parts:
            parts.append("## Interviewer / Contact\n" + "\n".join(person_parts))

    # ---- 3. Additional context / question text --------------------------
    extra = (additional_context or "").strip()
    if extra:
        parts.append(f"## Additional Context\n{extra}")

    return "\n\n---\n\n".join(parts)
