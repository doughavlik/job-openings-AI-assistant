# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Job Openings Tracker.

Build with:
    pip install pyinstaller
    pyinstaller JobOpeningsTracker.spec

Output goes to %LOCALAPPDATA%\JobOpeningsTracker-builds\JobOpeningsTracker\
That folder is outside OneDrive so rebuilds never cause sync conflicts.
Zip that folder and upload to the GitHub Release for distribution.
"""

import os
from pathlib import Path

# ── Build output location ────────────────────────────────────────────────────
# Use %LOCALAPPDATA% (C:\Users\<you>\AppData\Local) so the dist folder is
# never inside OneDrive.  This prevents OneDrive from creating conflict copies
# when you rebuild and overwrite the exe.
_local_app_data = Path(os.environ.get("LOCALAPPDATA", "C:\\Temp"))
_dist_path = str(_local_app_data / "JobOpeningsTracker-builds")
_work_path = str(_local_app_data / "JobOpeningsTracker-builds" / "build")

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Ship the seed config.db so action defaults are available on first run
        ('config.db', '.'),
    ],
    hiddenimports=[
        # Google Generative AI SDK
        'google.genai',
        'google.genai.types',
        # pdfplumber + its pdfminer.six backend (not always auto-detected)
        'pdfplumber',
        'pdfminer',
        'pdfminer.high_level',
        'pdfminer.layout',
        'pdfminer.pdfinterp',
        'pdfminer.pdfdevice',
        'pdfminer.converter',
        'pdfminer.pdfpage',
        'pdfminer.pdfdocument',
        'pdfminer.pdfparser',
        'pdfminer.pdftypes',
        'pdfminer.utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JobOpeningsTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # windowed — no console window for end users
    icon=None,       # add an .ico path here if you want a custom icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JobOpeningsTracker',
)
