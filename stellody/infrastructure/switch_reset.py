"""A note left by the setup program asking for the switches to start off.

A new install and a reinstall start with shuffle and repeat off, while an
update, a downgrade and a repair leave every choice alone. Stellody's own
directory outlives an uninstall unless the user asks for it to go, so without
this a reinstall came back wearing switches somebody set months ago.

It is a file rather than a write into the library database. The setup program
runs at the one moment the database is least safe to touch: it has just ended
the application by force, so a write ahead log may be half applied and the
file may be held by a process that has not finished exiting. Opening it there
hung an install once and left the application unable to start after another.
An empty file has none of those failure modes; the application, which owns the
database, does the writing.
"""

from __future__ import annotations

import pathlib

MARKER_NAME = "reset-switches"


def marker_path(directory: pathlib.Path) -> pathlib.Path:
    """Where the note belongs inside Stellody's own directory."""
    return directory / MARKER_NAME


def leave(directory: pathlib.Path) -> bool:
    """Ask for the switches to start off; False when the note could not be left.

    Nothing is created but the note itself. A machine with no directory yet has
    nothing remembered to clear, so there is nothing to ask for.
    """
    if not directory.is_dir():
        return False
    try:
        marker_path(directory).write_text("", encoding="utf-8")
    except OSError:
        return False
    return True


def take(directory: pathlib.Path) -> bool:
    """Whether a note was waiting, removing it as it is read.

    Read once: a note left behind would turn every launch into a reset.
    """
    marker = marker_path(directory)
    try:
        if not marker.exists():
            return False
        marker.unlink()
    except OSError:
        return False
    return True
