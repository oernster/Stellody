"""Application identity, with the version read from the one file that holds it."""

from __future__ import annotations

import pathlib
import sys

APP_NAME = "Stellody"
APP_TAGLINE = "A calm, local-first FLAC music player."
APP_AUTHOR = "Oliver Ernster"
# Fixed rather than read from the clock. A copyright year that moves with the
# machine's date is a claim about nothing; it would also make two machines
# disagree about the same build.
COPYRIGHT_YEAR = "2026"
COPYRIGHT_NOTICE = f"© {COPYRIGHT_YEAR} {APP_AUTHOR}"
APP_DOMAIN = "stellody.com"
# Where the donate button sends a browser. The only address the application
# knows; it is handed to the desktop rather than fetched, so nothing here ever
# opens a connection of its own.
DONATE_URL = "https://www.paypal.com/ncp/payment/QGC2XK2Z5WNUW"

DEV_VERSION = "0.0.0-dev"
VERSION_FILE = "VERSION"


def _search_roots() -> tuple[pathlib.Path, ...]:
    """Places the VERSION file may sit, in development and once packaged."""
    here = pathlib.Path(__file__).resolve()
    roots = [here.parents[2], here.parents[1], here.parent]
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        roots.append(pathlib.Path(bundled))
    roots.append(pathlib.Path(sys.argv[0]).resolve().parent)
    return tuple(roots)


def read_version() -> str:
    """The version string; a development sentinel when VERSION is absent."""
    for root in _search_roots():
        candidate = root / VERSION_FILE
        try:
            text = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            return text
    return DEV_VERSION


__version__ = read_version()
