# Job Openings AI Assistant

A desktop app I built using vibe coding to solve a real problem in my own job search: managing application context and generating AI-ready prompts for interview prep, outreach, and follow-up.

As a customer success professional, I know that the best tools come from deeply understanding the workflow. I was spending too much time copying between browser tabs, PDFs, and scattered files just to give AI the context it needed to help me. So I built a system that organizes everything in one place and assembles rich, context-aware prompts with a single click.

This project is 100% vibe-coded — designed, architected, and built through AI-assisted development using Claude Code. Every feature, from the database schema to the PyInstaller distribution, was produced through iterative natural-language collaboration. The PRDs in this repo document that process.

## What It Does

- **Tracks job openings** with company, title, job description, resume, application links, and contact people — all in a local SQLite database
- **Imports resumes from PDF** using Google Gemini to convert to structured Markdown
- **AI Prompt Builder** assembles context-rich prompts (resume + JD + company + interviewer details) for actions like interview prep reports, cover letters, and outreach messages — copy to clipboard and paste into any AI tool
- **Configurable actions** stored in a settings database so users can customize prompt templates
- **Excel backup** exports all data to a formatted `.xlsx` with human-readable headers, designed for both disaster recovery and standalone use
- **Fully local and private** — no cloud storage, no accounts, no data leaves your machine (except the optional Gemini API call for PDF import)

## Getting Started (from source)

**Requirements:** Python 3.11+, Windows 10/11

```bash
git clone https://github.com/doughavlik/job-openings-AI-assistant.git
cd job-openings-AI-assistant
pip install -r requirements.txt
python main.py
```

On first launch you'll be prompted for a [Google Gemini API key](https://aistudio.google.com/apikey) (free tier available). The app seeds sample data so you can explore immediately.

## Pre-Built Executable

Download the latest `.zip` from [Releases](https://github.com/doughavlik/job-openings-AI-assistant/releases), unzip, and run `JobOpeningsTracker.exe`. No Python required.

> Windows SmartScreen may warn you since the exe is unsigned. Click **More info** then **Run anyway**.

## Tech Stack

| Layer | Technology |
|---|---|
| GUI | PySide6 (Qt for Python) |
| Database | SQLite (local, zero-config) |
| PDF Import | Google Gemini API |
| Excel Export | openpyxl |
| Distribution | PyInstaller |

## Project Structure

- `main.py` — Entry point
- `gui.py` — PySide6 desktop interface
- `db.py` — SQLite schema and CRUD for openings, people, and links
- `config_db.py` — Prompt action configuration (seed-file pattern)
- `prompt_builder.py` — Context-aware prompt assembly
- `backup_excel.py` — Excel export with formatted multi-sheet output
- `Product Requirements Documents/` — PRDs documenting every feature

## License

Personal project. Feel free to explore the code and approach.
