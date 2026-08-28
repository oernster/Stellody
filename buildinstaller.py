"""Build the Stellody setup program with PyInstaller.

Stages the application bundle as a zipped payload, then wraps the installer UI
into one file at dist-installer/StellodySetup.exe.

Run:  python buildinstaller.py
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent

APP_NAME = "Stellody"
SETUP_NAME = f"{APP_NAME}Setup"
INSTALLER_ENTRY = ROOT / "installer" / "app.py"
ICON = ROOT / "assets" / "stellody.ico"
VERSION_FILE = ROOT / "VERSION"
DEV_VERSION = "0.0.0-dev"

PAYLOAD_DIR = ROOT / "installer" / "payload"
ARCHIVE = PAYLOAD_DIR / "payload.zip"
MANIFEST = PAYLOAD_DIR / "manifest.json"

DIST_DIR = ROOT / "dist-installer"
TEMP_DIST_DIR = ROOT / "dist-installer.build"
WORK_DIR = ROOT / "build" / "installer"
SPEC_FILE = ROOT / f"{SETUP_NAME}.spec"

DATA_FILES: tuple[pathlib.Path, ...] = (
    VERSION_FILE,
    ROOT / "LICENSE",
    ROOT / "LICENSE-GPL-3.0.txt",
    ROOT / "LICENSE-LGPL-3.0.txt",
)

UNLINK_RETRIES = 40
UNLINK_DELAY_SECONDS = 0.25


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
        return VERSION_FILE.read_text(encoding="utf-8").strip() or DEV_VERSION
    except OSError:
        return DEV_VERSION


def stage_payload() -> bool:
    """Zip the built application, aborting when it has not been built."""
    result = subprocess.run(
        [sys.executable, "-m", "installer.build_payload"], cwd=ROOT, check=False
    )
    if result.returncode != 0:
        return False
    missing = [item for item in (ARCHIVE, MANIFEST) if not item.is_file()]
    if missing:
        print(f"payload staging produced nothing at {missing}", file=sys.stderr)
        return False
    return True


def command() -> list[str]:
    """The whole PyInstaller invocation for the setup program."""
    parts = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        f"--name={SETUP_NAME}",
        f"--paths={ROOT}",
        f"--distpath={TEMP_DIST_DIR}",
        f"--workpath={WORK_DIR}",
        f"--specpath={ROOT}",
    ]
    if ICON.exists():
        parts.append(f"--icon={ICON}")
    parts.append(f"--add-data={ARCHIVE}{os.pathsep}installer/payload")
    parts.append(f"--add-data={MANIFEST}{os.pathsep}installer/payload")
    parts.append(f"--add-data={ROOT / 'assets'}{os.pathsep}assets")
    for item in DATA_FILES:
        if item.exists():
            parts.append(f"--add-data={item}{os.pathsep}.")
    parts.append(str(INSTALLER_ENTRY))
    return parts


def move_into_place(built: pathlib.Path, final: pathlib.Path) -> bool:
    """Move the setup file into dist-installer, retrying past file locks.

    Antivirus and Explorer hold a new executable open briefly, so a single
    attempt fails intermittently for reasons that have nothing to do with the
    build. A lock that outlasts the retries is almost always a previous setup
    run still going: a onefile build starts a child process, so closing the
    first window does not always end it.
    """
    final.parent.mkdir(parents=True, exist_ok=True)
    last: OSError | None = None
    for attempt in range(UNLINK_RETRIES):
        try:
            final.unlink(missing_ok=True)
            shutil.move(str(built), str(final))
            return True
        except OSError as error:
            last = error
            time.sleep(UNLINK_DELAY_SECONDS)
    waited = UNLINK_RETRIES * UNLINK_DELAY_SECONDS
    print(f"gave up after {waited:.0f}s: {last}", file=sys.stderr)
    print(
        f"{final.name} is most likely still running. Close it; or run:\n"
        f"    Stop-Process -Name {SETUP_NAME} -Force",
        file=sys.stderr,
    )
    return False


def main() -> int:
    """Stage the payload, build the setup program and place it."""
    require("PyInstaller", "PyInstaller")
    version = read_version()
    print(f"{SETUP_NAME} {version}")
    if not stage_payload():
        return 1
    shutil.rmtree(TEMP_DIST_DIR, ignore_errors=True)
    result = subprocess.run(command(), cwd=ROOT, check=False)
    if result.returncode != 0:
        print("PyInstaller failed", file=sys.stderr)
        return result.returncode
    SPEC_FILE.unlink(missing_ok=True)
    built = TEMP_DIST_DIR / f"{SETUP_NAME}.exe"
    if not built.is_file():
        print(f"expected {built}, which is not there", file=sys.stderr)
        return 1
    final = DIST_DIR / f"{SETUP_NAME}.exe"
    if not move_into_place(built, final):
        print(f"could not move the setup file to {final}", file=sys.stderr)
        return 1
    shutil.rmtree(TEMP_DIST_DIR, ignore_errors=True)
    print(f"built {final}")
    print(f"size {final.stat().st_size / (1024 * 1024):.0f} MiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
