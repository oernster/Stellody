"""Build the Stellody application bundle with PyInstaller.

Produces dist-pyinstaller/Stellody/Stellody.exe together with everything it
needs at runtime. buildinstaller.py then wraps that bundle into one setup file.

Run:  python buildexe.py
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent

APP_NAME = "Stellody"
ENTRYPOINT = ROOT / "main.py"
ICON = ROOT / "assets" / "stellody.ico"
VERSION_FILE = ROOT / "VERSION"
DEV_VERSION = "0.0.0-dev"

DIST_DIR = ROOT / "dist-pyinstaller"
WORK_DIR = ROOT / "build" / "app"
SPEC_FILE = ROOT / f"{APP_NAME}.spec"

# Directories shipped whole, as (source, destination inside the bundle).
DATA_DIRS: tuple[tuple[pathlib.Path, str], ...] = ((ROOT / "assets", "assets"),)

# Loose files shipped at the bundle root.
DATA_FILES: tuple[pathlib.Path, ...] = (
    VERSION_FILE,
    ROOT / "LICENSE",
    ROOT / "LICENSE-GPL-3.0.txt",
    ROOT / "LICENSE-LGPL-3.0.txt",
)

# Imports PyInstaller cannot see statically.
HIDDEN_IMPORTS: tuple[str, ...] = ("mutagen.flac",)


def require(module: str, package: str) -> None:
    """Stop with a useful message when a build tool is not installed.

    Without this the failure is a bare import error naming a module the reader
    has to map back to a package by themselves.
    """
    if importlib.util.find_spec(module) is None:
        print(
            f"{package} is not installed. It is a build dependency:\n"
            "    python -m pip install -r requirements-dev.txt",
            file=sys.stderr,
        )
        raise SystemExit(1)


def read_version() -> str:
    """The one version string, from the one file that holds it."""
    try:
        text = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return DEV_VERSION
    return text or DEV_VERSION


def clean() -> None:
    """Remove the previous build so nothing stale survives into this one."""
    for path in (DIST_DIR, WORK_DIR):
        shutil.rmtree(path, ignore_errors=True)
    SPEC_FILE.unlink(missing_ok=True)


def command() -> list[str]:
    """The whole PyInstaller invocation."""
    parts = [
        sys.executable,
        "-m",
        "PyInstaller",
        f"--name={APP_NAME}",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--distpath={DIST_DIR}",
        f"--workpath={WORK_DIR}",
        f"--specpath={ROOT}",
    ]
    if ICON.exists():
        parts.append(f"--icon={ICON}")
    for source, destination in DATA_DIRS:
        if source.exists():
            parts.append(f"--add-data={source}{os.pathsep}{destination}")
    for item in DATA_FILES:
        if item.exists():
            parts.append(f"--add-data={item}{os.pathsep}.")
    for name in HIDDEN_IMPORTS:
        parts.append(f"--hidden-import={name}")
    parts.append(str(ENTRYPOINT))
    return parts


def main() -> int:
    """Build the bundle and report where it landed."""
    require("PyInstaller", "PyInstaller")
    version = read_version()
    print(f"{APP_NAME} {version}")
    clean()
    result = subprocess.run(command(), cwd=ROOT, check=False)
    if result.returncode != 0:
        print("PyInstaller failed", file=sys.stderr)
        return result.returncode
    SPEC_FILE.unlink(missing_ok=True)
    executable = DIST_DIR / APP_NAME / f"{APP_NAME}.exe"
    if not executable.exists():
        print(f"expected {executable}, which is not there", file=sys.stderr)
        return 1
    size = sum(
        f.stat().st_size for f in (DIST_DIR / APP_NAME).rglob("*") if f.is_file()
    )
    print(f"built {executable}")
    print(f"bundle size {size / (1024 * 1024):.0f} MiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
