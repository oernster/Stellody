"""Build the Stellody setup program with Nuitka.

Stages the built application as a zipped payload, then compiles the installer
into one file at dist-installer/StellodySetup.exe.

Run:  python buildinstaller.py
"""

from __future__ import annotations

import importlib.util
import itertools
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent

APP_DISPLAY_NAME = "Stellody"
APP_DESCRIPTION = "A calm, local-first FLAC music player."
APP_AUTHOR = "Oliver Ernster"
SETUP_NAME = f"{APP_DISPLAY_NAME}Setup"
INSTALLER_ENTRY = ROOT / "installer" / "app.py"
ICON_FILE = ROOT / "assets" / "stellody.ico"
VERSION_FILE = ROOT / "VERSION"
DEV_VERSION = "0.0.0-dev"

STAGE_DIR = ROOT / "installer" / "stage"
ARCHIVE = STAGE_DIR / "payload.zip"
MANIFEST = STAGE_DIR / "manifest.json"

DIST_DIR = ROOT / "dist-installer"
TEMP_DIST_DIR = ROOT / "dist-installer.build"

DATA_FILES: tuple[pathlib.Path, ...] = (
    VERSION_FILE,
    ROOT / "LICENSE",
    ROOT / "LICENSE-GPL-3.0.txt",
    ROOT / "LICENSE-LGPL-3.0.txt",
)

PE_VERSION_PARTS = 4
CONSOLE_MODE = "disable"
UNLINK_RETRIES = 40
UNLINK_DELAY_SECONDS = 0.25
BYTES_PER_MIB = 1024 * 1024


def require(module: str, package: str) -> None:
    """Stop with a useful message when a build tool is not installed."""
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


def pe_version(version: str) -> str:
    """A four part numeric version, which is all Windows PE metadata accepts."""
    parts = [
        "".join(itertools.takewhile(str.isdigit, part)) for part in version.split(".")
    ]
    numbers = [part for part in parts if part][:PE_VERSION_PARTS]
    while len(numbers) < PE_VERSION_PARTS:
        numbers.append("0")
    return ".".join(numbers)


def jobs() -> int:
    """Compile on every core the machine has."""
    return os.cpu_count() or 1


def stage_payload() -> bool:
    """Zip the built application, aborting when it has not been built."""
    result = subprocess.run(
        [sys.executable, "-m", "installer.build_payload"], cwd=ROOT, check=False
    )
    if result.returncode != 0:
        return False
    missing = [item.name for item in (ARCHIVE, MANIFEST) if not item.is_file()]
    if missing:
        print(f"payload staging produced no {missing}", file=sys.stderr)
        return False
    return True


def command(version: str) -> list[str]:
    """The whole Nuitka invocation for the setup program."""
    numeric = pe_version(version)
    parts = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        f"--jobs={jobs()}",
        f"--windows-console-mode={CONSOLE_MODE}",
        f"--output-dir={TEMP_DIST_DIR}",
        f"--output-filename={SETUP_NAME}.exe",
        f"--company-name={APP_AUTHOR}",
        f"--product-name={APP_DISPLAY_NAME} Setup",
        f"--file-version={numeric}",
        f"--product-version={numeric}",
        f"--file-description={APP_DESCRIPTION} Installer",
        f"--copyright=Copyright {APP_AUTHOR}",
        f"--include-data-dir={STAGE_DIR}=payload",
    ]
    if ICON_FILE.exists():
        parts.append(f"--windows-icon-from-ico={ICON_FILE}")
    for item in DATA_FILES:
        if item.is_file():
            parts.append(f"--include-data-file={item}={item.name}")
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
    for _ in range(UNLINK_RETRIES):
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
    require("nuitka", "Nuitka")
    version = read_version()
    print(f"{SETUP_NAME} {version} ({jobs()} jobs)")
    if not stage_payload():
        return 1
    shutil.rmtree(TEMP_DIST_DIR, ignore_errors=True)
    result = subprocess.run(command(version), cwd=ROOT, check=False)
    if result.returncode != 0:
        print("Nuitka failed", file=sys.stderr)
        return result.returncode
    built = TEMP_DIST_DIR / f"{SETUP_NAME}.exe"
    if not built.is_file():
        print(f"expected {built}, which is not there", file=sys.stderr)
        return 1
    final = DIST_DIR / f"{SETUP_NAME}.exe"
    if not move_into_place(built, final):
        return 1
    shutil.rmtree(TEMP_DIST_DIR, ignore_errors=True)
    print(f"built {final}")
    print(f"size {final.stat().st_size / BYTES_PER_MIB:.0f} MiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
