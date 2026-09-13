"""A note left by the setup program asking the window to open afresh.

A fresh install, a repair and a reinstall open maximised on the screen setup
was on, whatever size an earlier install left the window at. An update and a
downgrade are the same install carrying on, so they leave no note.

A file rather than a write into the library database, for the reason
`switch_reset` gives: setup runs at the one moment that database is least safe
to touch. Unlike that note this one is left on a machine with no directory yet,
since nothing is remembered there to clear while a screen still has to be named.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

MARKER_NAME = "reset-window"
NAME_KEY = "screen"
X_KEY = "x"
Y_KEY = "y"


@dataclass(frozen=True, slots=True)
class WindowNote:
    """Which screen setup was on: its name and its top left corner.

    Both are optional. A note naming no screen still asks for the window to
    open afresh; it opens maximised wherever it would have opened anyway.
    """

    name: str = ""
    origin: tuple[int, int] | None = None


def marker_path(directory: pathlib.Path) -> pathlib.Path:
    """Where the note belongs inside Stellody's own directory."""
    return directory / MARKER_NAME


def leave(directory: pathlib.Path, note: WindowNote) -> bool:
    """Ask for the window to open afresh; False when the note could not be left."""
    body: dict[str, object] = {NAME_KEY: note.name}
    if note.origin is not None:
        body[X_KEY], body[Y_KEY] = note.origin
    try:
        directory.mkdir(parents=True, exist_ok=True)
        marker_path(directory).write_text(json.dumps(body), encoding="utf-8")
    except OSError:
        return False
    return True


def take(directory: pathlib.Path) -> WindowNote | None:
    """The note waiting, removing it as it is read; None when there is none.

    Read once: a note left behind would open every launch maximised. A note
    that cannot be removed is read as no note for the same reason.
    """
    marker = marker_path(directory)
    try:
        if not marker.exists():
            return None
        text = marker.read_text(encoding="utf-8")
        marker.unlink()
    except OSError:
        return None
    return read(text)


def read(text: str) -> WindowNote:
    """What a note says about the screen; nothing named where it cannot be read."""
    try:
        body = json.loads(text)
    except ValueError:
        return WindowNote()
    if not isinstance(body, dict):
        return WindowNote()
    name = body.get(NAME_KEY)
    x, y = body.get(X_KEY), body.get(Y_KEY)
    # `type` rather than isinstance, since JSON's true is an int to isinstance.
    origin = (x, y) if type(x) is int and type(y) is int else None
    return WindowNote(name=name if isinstance(name, str) else "", origin=origin)
