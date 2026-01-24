# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Omni Meeting Recorder.

This spec file configures PyInstaller to build a portable Windows executable.
Use onedir mode for faster startup and easier debugging.

Build command:
    pyinstaller omr.spec

Output:
    dist/omr/omr.exe  - Main executable
    dist/omr/         - All required DLLs and resources
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# Project root directory
project_root = Path(SPECPATH)
src_dir = project_root / "src"

# Analysis configuration
a = Analysis(
    [str(src_dir / "omr" / "cli" / "main.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Core dependencies
        "typer",
        "typer.main",
        "typer.core",
        "click",
        "click.core",
        "rich",
        "rich.console",
        "rich.table",
        "rich.progress",
        "rich.panel",
        "rich.text",
        "rich.live",
        "pydantic",
        "pydantic.fields",
        "pydantic_core",
        # Audio libraries (native extensions)
        "pyaudiowpatch",
        "pyaudio",
        "lameenc",
        "pyaec",
        # Standard library modules that might be missed
        "wave",
        "struct",
        "threading",
        "queue",
        "ctypes",
        "ctypes.wintypes",
        # Windows-specific
        "comtypes",
        "comtypes.client",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        "matplotlib",
        "numpy.testing",
        "scipy",
        "PIL",
        "tkinter",
        "unittest",
        "xml.etree.ElementTree",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Collect native library binaries
# PyAudioWPatch includes PortAudio DLL
try:
    pyaudio_binaries = collect_dynamic_libs("pyaudiowpatch")
    a.binaries += pyaudio_binaries
except Exception:
    pass

# lameenc includes LAME encoder DLL
try:
    lameenc_binaries = collect_dynamic_libs("lameenc")
    a.binaries += lameenc_binaries
except Exception:
    pass

# pyaec includes WebRTC AEC DLL
try:
    pyaec_binaries = collect_dynamic_libs("pyaec")
    a.binaries += pyaec_binaries
except Exception:
    pass

# PYZ archive (compiled Python modules)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Executable configuration
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # For onedir mode
    name="omr",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress with UPX if available
    console=True,  # CLI application needs console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if desired: icon="resources/omr.ico"
)

# Collect all files into a directory (onedir mode)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="omr",
)
