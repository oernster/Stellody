"""Stage the built application bundle as the setup program's payload.

Produces installer/payload/payload.zip plus a manifest. The bundle is zipped
rather than shipped loose because a onefile build strips loose executables and
DLLs out of a bundled data directory, so they would not survive the trip.

Run:  python -m installer.build_payload
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_NAME = "Stellody"
BUILD_DIR = ROOT / "installer" / "payload"
BUNDLE_DIR = BUILD_DIR / APP_NAME
ONEFILE_EXE = BUILD_DIR / f"{APP_NAME}.exe"
STAGE_DIR = ROOT / "installer" / "stage"
ARCHIVE = STAGE_DIR / "payload.zip"
MANIFEST = STAGE_DIR / "manifest.json"
VERSION_FILE = ROOT / "VERSION"
DEV_VERSION = "0.0.0-dev"
DIGEST_CHUNK = 1024 * 1024


def read_version() -> str:
    """The one version string, from the one file that holds it."""
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or DEV_VERSION
    except OSError:
        return DEV_VERSION


def digest(path: pathlib.Path) -> str:
    """A checksum of the archive, so the manifest describes what it ships."""
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(DIGEST_CHUNK), b""):
            hasher.update(block)
    return hasher.hexdigest()


def source() -> pathlib.Path | None:
    """The Nuitka output to ship: a onefile executable, else a bundle dir."""
    if ONEFILE_EXE.is_file():
        return ONEFILE_EXE
    if BUNDLE_DIR.is_dir():
        return BUNDLE_DIR
    return None


def main() -> int:
    """Zip the built application and write a manifest beside it.

    The archive exists because a onefile setup build strips loose executables
    out of a bundled data directory, so the application would not survive the
    trip as loose files.
    """
    built = source()
    if built is None:
        print(f"no application build under {BUILD_DIR}", file=sys.stderr)
        print("run buildexe.py first", file=sys.stderr)
        return 1
    shutil.rmtree(STAGE_DIR, ignore_errors=True)
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    if built.is_dir():
        shutil.make_archive(str(ARCHIVE.with_suffix("")), "zip", root_dir=built)
        files = sum(1 for item in built.rglob("*") if item.is_file())
    else:
        with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(built, built.name)
        files = 1
    MANIFEST.write_text(
        json.dumps(
            {
                "app": APP_NAME,
                "version": read_version(),
                "files": files,
                "archive": ARCHIVE.name,
                "sha256": digest(ARCHIVE),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    size = ARCHIVE.stat().st_size / (1024 * 1024)
    print(f"payload {ARCHIVE} ({size:.0f} MiB, {files} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
