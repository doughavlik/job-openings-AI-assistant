# Database Overview: Job Openings Tracker
**Author:** Doug Havlik | **Date:** March 2, 2026 | **Status:** Draft

> **Note for AI assistants:** Keep this document high-level. Do not add implementation detail, code snippets, or widget-level specifics. Maximum 500 words — check before saving.

---

### What Kind of Database Is This?

The app uses **SQLite** — a lightweight database stored as a single file on your computer. No server, no account, no internet required. Back up by copying the file, or use **File > Export Backup to Excel** to save all data to a single `.xlsx` file (see *Backup to Excel PRD*).

---

### Tables

The database has three tables that work together.

**Relationship:** A job opening can have many people. A person can be linked to many job openings. The `job_opening_people` table sits between them and records each connection.

---

### Table: `job_openings`

Each row is one job opening being tracked.

| Field | Plain-English Name | What It Stores |
|---|---|---|
| `id` | Record ID | Assigned automatically. Uniquely identifies the row and never changes. |
| `teal_import_raw` | Resume | Full resume text, converted to Markdown by Gemini on import. Editable in the Resume tab. |
| `job_title` | Job Title | The title of the role. Editable in the table. |
| `customer_name` | Company | The hiring company name. Editable in the table. |
| `application_url` | Application URL | Link to the job application page. Editable in the table. |
| `job_description_contents` | Job Description | Full text of the job posting, pasted in manually. Editable in the Job Description tab. |
| `job_description_url` | JD URL | Legacy URL field; retained in the database but not exposed in the UI. |
| `archived` | Archived | 0 = active, 1 = archived. Archived rows are hidden from the main table by default. |
| `created_at` | Date Created | Set automatically when the record is created. Never changes. |
| `updated_at` | Last Updated | Updated automatically on every save. |

---

### Table: `people`

Each row is one person. A person is stored once here regardless of how many job openings they are linked to.

| Field | Plain-English Name | What It Stores |
|---|---|---|
| `id` | Record ID | Assigned automatically. |
| `name` | Name | The person's full name. |
| `title` | Title | Their job title (e.g. "VP of Sales"). |
| `details` | Details | Free-form multiline text. Typically holds their LinkedIn URL, a link to their company leadership page bio, and/or notes. |
| `created_at` | Date Created | Set automatically. |
| `updated_at` | Last Updated | Updated automatically on every save. |

---

### Table: `job_opening_people` (link table)

Each row connects one person to one job opening. This table has no fields of its own beyond the two IDs it links.

| Field | What It Stores |
|---|---|
| `job_opening_id` | The `id` of the job opening. |
| `person_id` | The `id` of the person. |

---

### A Note on Markdown

`teal_import_raw` and `job_description_contents` store text in **Markdown**. The app displays and edits it as plain text.

---

### File Location

`job_openings.db` is stored in the user data folder (`%LOCALAPPDATA%\JobOpeningsTracker` on Windows). `config.db` lives in the same folder (copied from the app directory on first run).
