# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Job Openings Tracker.

Build with:
    pip install pyinstaller
    pyinstaller JobOpeningsTracker.spec

Output goes to dist/JobOpeningsTracker/ — zip that folder for distribution.
"""

import os
from pathlib import Path

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Ship the seed config.db so defaults are available
        ('config.db', '.'),
    ],
    hiddenimports=[
        'google.genai',
        'google.genai.types',
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
    console=False,   # windowed app, no console
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
