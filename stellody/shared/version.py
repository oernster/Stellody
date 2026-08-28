"""Application identity, with the version read from the one file that holds it."""

from __future__ import annotations

import pathlib

APP_NAME = "Stellody"
APP_TAGLINE = "A calm, local-first FLAC music player."
APP_AUTHOR = "Oliver Ernster"
APP_DOMAIN = "stellody.com"

DEV_VERSION = "0.0.0-dev"
VERSION_FILE = "VERSION"


def _search_roots() -> tuple[pathlib.Path, ...]:
    """Places the VERSION file may sit, in development and once packaged."""
    here = pathlib.Path(__file__).resolve()
    return (here.parents[2], here.parents[1], here.parent)


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
