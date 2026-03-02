# UI Design Requirements: Job Openings Tracker v2
**Author:** Doug Havlik | **Date:** February 28, 2026 | **Status:** Draft

---

### Overview
Replace the CLI with a desktop GUI centered on a single editable table. Each row represents one active job opening; users edit fields directly in the table without navigating to separate screens.

---

### Layout

A single window with three zones:
1. **Toolbar** — buttons for Import PDF and Add Row, plus a search/filter input.
2. **Job Table** — the primary workspace, occupying most of the window.
3. **Detail Pane** — a collapsible panel below or beside the table showing the full resume Markdown and job description text for the selected row.

---

### Job Table

**Columns (in order):** ID · Company · Job Title · JD (indicator) · Resume (indicator) · Application URL · Created · Actions

- All text columns are **inline-editable** on single click.
- **JD** and **Resume** columns show a filled dot when content exists, empty dot when not.
- The **Actions** column contains a single Archive button per row (with a confirmation tooltip on hover, no modal).
- Archived rows are hidden by default; a **Show Archived** toggle in the toolbar reveals them grayed out.
- Rows are sortable by any column header click.

---

### Detail Pane

- Opens when a row is selected.
- Two tab panels: **Resume** and **Job Description**.
- Each tab shows the full Markdown text in a scrollable, read-only monospace field.
- An **Edit** button per tab replaces the field with an editable textarea; **Save** commits the change.

---

### Tech
`PySide6`
