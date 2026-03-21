# Product Requirements Document: Job Openings Tracker v1

**Author:** Doug Havlik | **Date:** February 28, 2026 | **Status:** Draft

---

### Problem Statement

Job seekers rely on AI throughout their search — generating interview-prep briefs, drafting questions to ask, editing thank-you and follow-up emails, reviewing cover letters, crafting cold-contact LinkedIn messages to recruiters or hiring managers, and rehearsing responses to likely interview questions. Good AI output depends on good context: the submitted resume, job description, company background, interviewer profiles (LinkedIn, leadership pages), meeting notes, and message threads. Today, seekers lack a local, private system for converting this content to a usable format, storing it in an organized manner, and recombining relevant context for AI based on the task at hand. Manually copying between browser tabs, PDFs, and scattered files wastes time and introduces errors during an already stressful process.

### Objective

Deliver a local Windows app that tracks the attempt to get hired for a job opening into a queryable SQL database and lets users enrich each record with the submitted resume, job description content, application links, and other details — no cloud dependencies or fees.

### Target User

Mid-career professionals targeting $100K+ SaaS roles who want a private, offline system to manage application context.

### Success Metrics

- Zero cloud dependencies; all data stays on the user's machine.

### Tech Stack

- **Runtime:** Python 3.11+ on Windows 11
- **Database:** SQLite (free, local, zero-config)

### Core Features (v1 Scope)

**1. Resume PDF Import** — Accepts a Resume PDF, converts content to Markdown (H3 as top-level heading) using an LLM via API call, and inserts each record into the `job_openings` table.

**2. Manual Field Entry** — User can add or update: job description, application page URL, company name, and job title.

### Database Schema (job_openings)

| Column | Type | Source |
|---|---|---|
| id | INTEGER PK | Auto |
| teal_import_raw | TEXT | PDF import |
| job_title | TEXT | User |
| customer_name | TEXT | User |
| job_description_url | TEXT | User |
| application_url | TEXT | User |
| job_description_contents | TEXT | Auto-fetched |
| created_at | DATETIME | Auto |
| updated_at | DATETIME | Auto |

### Out of Scope (v1)

Resume tailoring, cover letter generation, status tracking, multi-user support, cloud sync. See *Backup to Excel PRD* for the export/backup feature.