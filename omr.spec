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
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_all

# Project root directory
project_root = Path(SPECPATH)
src_dir = project_root / "src"

# Find pyaec package directory and collect its DLL
def find_pyaec_dll():
    """Find pyaec DLL and return as binaries list."""
    try:
        import pyaec
        pyaec_dir = Path(pyaec.__file__).parent
        dll_path = pyaec_dir / "aec.dll"
        if dll_path.exists():
            # (dest_path, src_path, typecode)
            return [(str(Path("pyaec") / "aec.dll"), str(dll_path), "BINARY")]
        # Also check for .pyd files
        for f in pyaec_dir.glob("*.pyd"):
            return [(str(Path("pyaec") / f.name), str(f), "BINARY")]
        for f in pyaec_dir.glob("*.dll"):
            return [(str(Path("pyaec") / f.name), str(f), "BINARY")]
    except Exception as e:
        print(f"Warning: Could not find pyaec DLL: {e}")
    return []

pyaec_binaries = find_pyaec_dll()

# Analysis configuration
a = Analysis(
    [str(src_dir / "omr" / "cli" / "main.py")],
    pathex=[str(src_dir)],
    binaries=pyaec_binaries,  # Include pyaec DLL
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
# Filter to ensure proper TOC format (dest_name, src_name, typecode)
def safe_collect_binaries(package_name):
    """Safely collect binaries, filtering invalid entries."""
    try:
        binaries = collect_dynamic_libs(package_name)
        valid_binaries = []
        for entry in binaries:
            if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                if len(entry) == 2:
                    # Add default typecode 'BINARY'
                    valid_binaries.append((entry[0], entry[1], 'BINARY'))
                elif len(entry) >= 3:
                    valid_binaries.append((entry[0], entry[1], entry[2]))
        return valid_binaries
    except Exception as e:
        print(f"Warning: Failed to collect binaries for {package_name}: {e}")
        return []

# PyAudioWPatch includes PortAudio DLL
a.binaries += safe_collect_binaries("pyaudiowpatch")

# lameenc includes LAME encoder DLL
a.binaries += safe_collect_binaries("lameenc")

# pyaec includes WebRTC AEC DLL
a.binaries += safe_collect_binaries("pyaec")

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
