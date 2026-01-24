#!/usr/bin/env python3
"""Build script for creating portable Omni Meeting Recorder package.

This script automates the PyInstaller build process and creates a
distributable ZIP file.

Usage:
    python scripts/build-portable.py [--clean] [--no-zip]

Options:
    --clean     Clean build directories before building
    --no-zip    Skip ZIP file creation
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def get_version() -> str:
    """Get version from omr package."""
    # Read version from __init__.py
    init_file = Path(__file__).parent.parent / "src" / "omr" / "__init__.py"
    with open(init_file, encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                # Extract version string
                return line.split("=")[1].strip().strip('"').strip("'")
    return "unknown"


def check_platform() -> None:
    """Check if running on Windows."""
    if sys.platform != "win32":
        print("Warning: This build script is designed for Windows.")
        print("PyAudioWPatch requires Windows WASAPI.")
        print("The build may complete but the executable will not work.")
        response = input("Continue anyway? [y/N]: ")
        if response.lower() != "y":
            sys.exit(1)


def check_pyinstaller() -> None:
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller  # noqa: F401

        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("Error: PyInstaller is not installed.")
        print("Install it with: uv pip install pyinstaller")
        print("Or: uv sync --group build")
        sys.exit(1)


def clean_build_dirs(project_root: Path) -> None:
    """Clean build and dist directories."""
    print("Cleaning build directories...")
    dirs_to_clean = ["build", "dist"]
    for dir_name in dirs_to_clean:
        dir_path = project_root / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  Removed: {dir_path}")


def run_pyinstaller(project_root: Path) -> bool:
    """Run PyInstaller with the spec file."""
    spec_file = project_root / "omr.spec"
    if not spec_file.exists():
        print(f"Error: Spec file not found: {spec_file}")
        return False

    print("Running PyInstaller...")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            str(spec_file),
        ],
        cwd=project_root,
    )
    return result.returncode == 0


def create_zip(project_root: Path, version: str) -> Path | None:
    """Create ZIP file from dist/omr directory."""
    dist_dir = project_root / "dist" / "omr"
    if not dist_dir.exists():
        print(f"Error: Build output not found: {dist_dir}")
        return None

    zip_name = f"omr-{version}-windows-x64"
    zip_path = project_root / "dist" / zip_name

    print(f"Creating ZIP archive: {zip_name}.zip")
    shutil.make_archive(str(zip_path), "zip", dist_dir.parent, "omr")

    return zip_path.with_suffix(".zip")


def verify_build(project_root: Path) -> bool:
    """Verify the build output."""
    exe_path = project_root / "dist" / "omr" / "omr.exe"
    if not exe_path.exists():
        print(f"Error: Executable not found: {exe_path}")
        return False

    print("Verifying build...")
    # Try to run --version
    result = subprocess.run(
        [str(exe_path), "--version"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"  {result.stdout.strip()}")
        return True
    else:
        print(f"  Warning: Version check failed: {result.stderr}")
        return True  # Don't fail build, just warn


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build portable Omni Meeting Recorder package"
    )
    parser.add_argument(
        "--clean", action="store_true", help="Clean build directories before building"
    )
    parser.add_argument(
        "--no-zip", action="store_true", help="Skip ZIP file creation"
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent.resolve()
    print(f"Project root: {project_root}")

    # Check platform
    check_platform()

    # Check PyInstaller
    check_pyinstaller()

    # Get version
    version = get_version()
    print(f"Building version: {version}")

    # Clean if requested
    if args.clean:
        clean_build_dirs(project_root)

    # Run PyInstaller
    if not run_pyinstaller(project_root):
        print("Build failed!")
        return 1

    # Verify build
    if not verify_build(project_root):
        print("Build verification failed!")
        return 1

    # Create ZIP
    if not args.no_zip:
        zip_path = create_zip(project_root, version)
        if zip_path:
            print(f"ZIP created: {zip_path}")
            print(f"ZIP size: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")

    print("\nBuild completed successfully!")
    print(f"Executable: {project_root / 'dist' / 'omr' / 'omr.exe'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
