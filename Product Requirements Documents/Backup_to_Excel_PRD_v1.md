> **AI Assistant Note:** This document is intentionally high-level and under 500 words. If you are an AI assistant editing this file, preserve that constraint. Do not expand sections into implementation detail, code, or exhaustive field lists.

# Backup to Excel — Product Requirements Document v1

**Author:** Doug Havlik | **Date:** March 21, 2026 | **Status:** Draft

---

## Purpose

Export all tracker and prompt-builder data to a single `.xlsx` file. The export must be human-readable — usable as a reference if the user loses access to the app — while structured enough to support a future "restore from backup" feature.

---

## Trigger

**File > Export Backup to Excel...** in the menu bar opens a system Save dialog defaulting to `JobOpeningsTracker_Backup_YYYY-MM-DD.xlsx` in the user's Documents folder.

---

## Excel File Structure

One worksheet per database table. Each sheet uses the table's plain-English column names as headers (not raw database column names) so a non-technical reader can understand the file without documentation.

### Sheet 1 — Openings

One row per job opening. Includes all fields from the `job_openings` table: ID, Company, Job Title, Resume, Job Description, Application URL, Archived, Date Created, Last Updated. Also includes a **People** column that lists the names of all linked people (comma-separated) so the relationship is visible without cross-referencing sheets.

### Sheet 2 — People

One row per person. Includes all fields from the `people` table: ID, Name, Title, Details, Date Created, Last Updated. Also includes a **Linked Openings** column listing the Company and Job Title of every opening the person is connected to (comma-separated).

### Sheet 3 — Prompt Actions

One row per configured action from the `prompt_actions` table in the config database: ID, Name, Instructions, Use Company, Use Job Description, Use Resume, Use Person, Person Required, Sort Order, Date Created, Last Updated. Boolean flag columns display "Yes" / "No" for readability.

---

## Formatting Guidelines

- **Header row:** Bold, frozen (stays visible when scrolling).
- **Column widths:** Auto-fit to content where practical; long-text columns (Resume, Job Description, Instructions, Details) set to a fixed readable width with word-wrap enabled.
- **ID columns:** Included for restore-compatibility but do not need emphasis — place them in the first column of each sheet.
- **Date columns:** Formatted as human-readable date/time strings, not raw ISO timestamps.
- **No merged cells, hidden columns, or macros** — keep the file simple and portable.

---

## Restore Considerations

The file format is designed so a future restore feature can read back the sheets and recreate records. To support this:

- Every sheet includes the record ID as the first column.
- Relationship sheets (Openings' People column, People's Linked Openings column) are informational — restore would use the IDs and the link table logic, not parsed name strings.
- The file includes data from both databases (`job_openings.db` and `config.db`).

---

## Out of Scope (v1)

- Restore / import from Excel (future).
- Scheduled or automatic backups.
- Selective export (e.g., only active openings).
- Export to formats other than `.xlsx`.
