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

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_NAME = "Stellody"
BUNDLE_DIR = ROOT / "dist-pyinstaller" / APP_NAME
PAYLOAD_DIR = ROOT / "installer" / "payload"
ARCHIVE = PAYLOAD_DIR / "payload.zip"
MANIFEST = PAYLOAD_DIR / "manifest.json"
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


def main() -> int:
    """Zip the bundle and write the manifest beside it."""
    if not BUNDLE_DIR.is_dir():
        print(f"no application bundle at {BUNDLE_DIR}", file=sys.stderr)
        print("run buildexe.py first", file=sys.stderr)
        return 1
    shutil.rmtree(PAYLOAD_DIR, ignore_errors=True)
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    shutil.make_archive(str(ARCHIVE.with_suffix("")), "zip", root_dir=BUNDLE_DIR)
    files = sum(1 for item in BUNDLE_DIR.rglob("*") if item.is_file())
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
