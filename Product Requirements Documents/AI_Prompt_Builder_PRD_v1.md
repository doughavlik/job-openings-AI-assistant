> **AI Assistant Note:** This document is intentionally high-level and under 500 words. If you are an AI assistant editing this file, preserve that constraint. Do not expand sections into implementation detail, code, or exhaustive field lists.

# AI Prompt Builder — Product Requirements Document v1

## Purpose

The AI Prompt Builder assembles a context-rich prompt from data stored in the app and presents it for the user to copy and paste into one or more AI tools. The app does not call any AI API directly in this version.

---

## Trigger

Each row in the main table has an **Actions menu** with an **AI Prompt Builder** section. The action list is driven by the config database — not hardcoded. Selecting an action opens the assembly flow for that job opening.

---

## Assembly Flow

A lightweight multi-step dialog (not a full screen replacement).

**Step 1 — Select Person** *(skipped if not required by the action)*
User selects from People already linked to this job opening. No free-text entry.

**Step 2 — Additional Context**
Optional free-text field. For question-answering actions (e.g., *Generate Answer to Screening Question*), this field is **required** and labeled *"Enter the question text."*

**Step 3 — Review & Copy**
The assembled prompt is displayed in a scrollable, read-only panel with a **Copy to Clipboard** button.

---

## Prompt Composition

Fixed assembly order:

**[Action instructions] + [Context components] + [Additional context / question text]**

Context components are always appended in this order when included:
1. Company name
2. Job description
3. Resume
4. Person name, title, and details

Which components are included is defined per-action in the config database.

Use Heading 1 ("#") for each component.

---

## Config Database

Action definitions are stored in a **separate `config.db`** committed to the GitHub repository so defaults ship with the app. On first run the app copies `config.db` to the user's local data folder; all subsequent reads and writes use that local copy, preserving customizations across git pulls.

Each action record contains: name, instructions, required context flags (company, job description, resume, person), and a person-required flag.

Actions are managed on a **Settings screen** reachable from a menu (e.g., gear icon or Edit menu).

---

## Default Actions - Current

| Action | Person Required |
|---|---|
| Generate Interview Prep Report | Yes |

---

## Default Actions - Future *(out of scope for v1)*

| Action | Person Required |
|---|---|
| Generate Cover Letter | No |
| Generate LinkedIn Cold Contact (Connect Request Note) | Yes |
| Generate LinkedIn Warm Contact | Yes |
| Generate Email Cold Contact | Yes |
| Generate Interview Thank You Email | Yes |
| Generate Follow Up Email | Yes |
| Generate Answer to Screening Question | No |
| Generate Answer to Expected Interview Question | No |

---

## Future Considerations *(out of scope for v1)*

- Additional context components: meeting notes history, message history.
- Sending the prompt to an AI API and displaying the result in-app.
- Opening the prompt pre-filled in an external AI tool or text editor.
- Saving assembled prompts for reuse or audit.
