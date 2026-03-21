# UI Design Requirements: Job Openings Tracker v2
**Author:** Doug Havlik | **Date:** March 2, 2026 | **Status:** Draft

> **Note for AI assistants:** Keep this document high-level. Do not add implementation detail, code snippets, or widget-level specifics. Maximum 500 words — check before saving.

---

### Overview
A desktop GUI centered on a single editable table. Each row represents one active job opening; users edit fields directly in the table without navigating to separate screens. A detail pane below the table shows long-form content and the people associated with the selected opening.

---

### Layout

A single window with three zones:
1. **Toolbar** — buttons for Import PDF and Add Row, plus a search/filter input and a Show Archived toggle.
2. **Job Table** — the primary workspace, occupying the upper portion of the window.
3. **Detail Pane** — a collapsible panel below the table, revealed when a row is selected.

---

### Job Table

**Columns (in order):** ID · Company · Job Title · JD (indicator) · Resume (indicator) · People (indicator) · Application URL · Created · Actions

- Company, Job Title, and Application URL are **inline-editable** on double-click; changes save immediately.
- **JD**, **Resume**, and **People** columns show a filled dot (●) when content exists, empty dot (○) when not.
- The **Actions** column contains a single Archive button per row; clicking asks for confirmation before archiving.
- Archived rows are hidden by default; the **Show Archived** toggle in the toolbar reveals them grayed out.
- Rows are sortable by any column header click.

---

### Detail Pane

Opens when a row is selected. Contains three tabs:

**Tab 1 — Resume**
- Scrollable, read-only monospace text field showing the full resume Markdown.
- Edit / Save / Cancel buttons to modify the content.

**Tab 2 — Job Description**
- Scrollable, read-only monospace text field showing the full job description text.
- Edit / Save / Cancel buttons to modify the content.

**Tab 3 — People**
- A small inline table with columns: **Name · Title · Details · Actions**.
- **Details** is a multiline text field; it typically holds a LinkedIn URL, a company leadership page URL, and/or free-form notes.
- An **Add Person** button above the table inserts a new blank row for editing.
- The **Actions** column per row contains a **Remove** button (with confirmation) that unlinks the person from this job opening. It does not delete the person from the database.
- Name and Title are inline-editable. Details opens a small expandable text area on click.
- The People dot indicator in the main table updates immediately when people are added or removed.

---

### Menu Bar

**File** menu contains **Export Backup to Excel...** (see *Backup to Excel PRD*). **Edit** menu contains **Settings** and **Gemini API Key**.

---

### Tech
`PySide6`
