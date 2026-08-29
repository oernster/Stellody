"""Build the Stellody application with Nuitka.

Onefile by default, which is what ships. Pass --standalone for a directory
bundle instead, which is quicker to inspect when something is wrong.

Run:  python buildexe.py
      python buildexe.py --standalone
"""

from __future__ import annotations

import importlib.util
import itertools
import os
import pathlib
import shutil
import subprocess
import sys

# The copyright notice comes from the package rather than being written
# here as well: the exe's file properties and the About box have to say
# the same thing, so they read the same constant.
from stellody.shared.version import COPYRIGHT_NOTICE

ROOT = pathlib.Path(__file__).resolve().parent

APP_DISPLAY_NAME = "Stellody"
APP_DESCRIPTION = "A calm, local-first FLAC music player."
APP_AUTHOR = "Oliver Ernster"
EXE_NAME = "Stellody"
ENTRY_SCRIPT = ROOT / "main.py"
ICON_FILE = ROOT / "assets" / "stellody.ico"
VERSION_FILE = ROOT / "VERSION"
DEV_VERSION = "0.0.0-dev"

PAYLOAD_DIR = ROOT / "installer" / "payload"
BUNDLE_DIR = PAYLOAD_DIR / APP_DISPLAY_NAME
NUITKA_DIST_DIR = PAYLOAD_DIR / "main.dist"
ONEFILE_EXE = PAYLOAD_DIR / f"{EXE_NAME}.exe"

# Directories shipped whole, as (source, destination inside the bundle).
DATA_DIRS: tuple[tuple[pathlib.Path, str], ...] = ((ROOT / "assets", "assets"),)

# Loose files shipped at the bundle root.
DATA_FILES: tuple[pathlib.Path, ...] = (
    VERSION_FILE,
    ROOT / "LICENSE",
    ROOT / "LICENSE-GPL-3.0.txt",
    ROOT / "LICENSE-LGPL-3.0.txt",
)

PE_VERSION_PARTS = 4
CONSOLE_MODE_RELEASE = "disable"
CONSOLE_MODE_DEBUG = "attach"
DEBUG_ENV = "STELLODY_DEBUG"
STANDALONE_FLAG = "--standalone"
BYTES_PER_MIB = 1024 * 1024


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


def pe_version(version: str) -> str:
    """A four part numeric version, which is all Windows PE metadata accepts.

    Anything that is not a digit is dropped from each dotted segment, so a
    version like 0.2.0-rc1 becomes 0.2.0.0.
    """
    parts = [
        "".join(itertools.takewhile(str.isdigit, part)) for part in version.split(".")
    ]
    numbers = [part for part in parts if part][:PE_VERSION_PARTS]
    while len(numbers) < PE_VERSION_PARTS:
        numbers.append("0")
    return ".".join(numbers)


def console_mode() -> str:
    """Show a console only when a debug build is asked for."""
    return CONSOLE_MODE_DEBUG if os.environ.get(DEBUG_ENV) else CONSOLE_MODE_RELEASE


def jobs() -> int:
    """Compile on every core the machine has."""
    return os.cpu_count() or 1


def clean() -> None:
    """Remove previous output so nothing stale survives into this build."""
    for path in (NUITKA_DIST_DIR, BUNDLE_DIR):
        shutil.rmtree(path, ignore_errors=True)
    ONEFILE_EXE.unlink(missing_ok=True)
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)


def command(version: str, onefile: bool) -> list[str]:
    """The whole Nuitka invocation."""
    numeric = pe_version(version)
    parts = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile" if onefile else "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        f"--jobs={jobs()}",
        f"--windows-console-mode={console_mode()}",
        f"--output-dir={PAYLOAD_DIR}",
        f"--output-filename={EXE_NAME}.exe",
        f"--company-name={APP_AUTHOR}",
        f"--product-name={APP_DISPLAY_NAME}",
        f"--file-version={numeric}",
        f"--product-version={numeric}",
        f"--file-description={APP_DESCRIPTION}",
        f"--copyright={COPYRIGHT_NOTICE}",
    ]
    if ICON_FILE.exists():
        parts.append(f"--windows-icon-from-ico={ICON_FILE}")
    for source, destination in DATA_DIRS:
        if source.is_dir():
            parts.append(f"--include-data-dir={source}={destination}")
    for item in DATA_FILES:
        if item.is_file():
            parts.append(f"--include-data-file={item}={item.name}")
    parts.append(str(ENTRY_SCRIPT))
    return parts


def settle_standalone() -> pathlib.Path | None:
    """Move Nuitka's main.dist output to a directory named after the app."""
    if not NUITKA_DIST_DIR.is_dir():
        return None
    shutil.rmtree(BUNDLE_DIR, ignore_errors=True)
    NUITKA_DIST_DIR.rename(BUNDLE_DIR)
    return BUNDLE_DIR / f"{EXE_NAME}.exe"


def report(target: pathlib.Path) -> None:
    """Say what was produced and how large it is."""
    if target.is_dir():
        size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
    else:
        size = target.stat().st_size
    print(f"built {target}")
    print(f"size {size / BYTES_PER_MIB:.0f} MiB")


def main(argv: list[str] | None = None) -> int:
    """Build the application and report where it landed."""
    arguments = sys.argv[1:] if argv is None else argv
    onefile = STANDALONE_FLAG not in arguments
    require("nuitka", "Nuitka")
    version = read_version()
    shape = "onefile" if onefile else "standalone"
    print(f"{APP_DISPLAY_NAME} {version} ({shape}, {jobs()} jobs)")
    clean()
    result = subprocess.run(command(version, onefile), cwd=ROOT, check=False)
    if result.returncode != 0:
        print("Nuitka failed", file=sys.stderr)
        return result.returncode
    produced = ONEFILE_EXE if onefile else settle_standalone()
    if produced is None or not produced.exists():
        print("the build produced nothing where it was expected", file=sys.stderr)
        return 1
    report(ONEFILE_EXE if onefile else BUNDLE_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
