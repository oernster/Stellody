"""One Stellody at a time, with a way to call the running one to the front.

Closing the window leaves the application in the notification area; a hidden
window has no button on the taskbar. So what a second launch means,
from a pinned shortcut or the Start menu, is almost always "show me the one I
already have" rather than "give me another".

Two pieces, because they answer different questions. A claim says whether this
copy is the one that runs; it is held in shared memory the system reclaims
when the process ends, so a copy that dies badly does not lock the next one
out. A note in Stellody's own directory then asks the running copy to come
forward: it is a file rather than a socket because the running copy is already
watching that directory and a listening port is a thing to be got wrong.
"""

from __future__ import annotations

import pathlib

from PySide6.QtCore import QSharedMemory

# Named for the application rather than the file, since it is a system wide
# name and the user may have the application in more than one place.
CLAIM_KEY = "Stellody.single.instance"
CLAIM_BYTES = 1
ATTENTION_NAME = "show-window"


class Claim:
    """The claim to being the running copy, held for as long as this lives."""

    def __init__(self, key: str = CLAIM_KEY) -> None:
        self._memory = QSharedMemory(key)

    def take(self) -> bool:
        """Whether this copy is the one that runs.

        Attaching first and detaching again clears a segment left behind by a
        copy the system ended without unmapping, which on Linux outlives the
        process. Windows reclaims it, so there the attach simply fails.
        """
        if self._memory.attach():
            self._memory.detach()
        return bool(self._memory.create(CLAIM_BYTES))

    def release(self) -> None:
        """Give the claim up. Safe whether or not it was ever taken."""
        self._memory.detach()


def attention_path(directory: pathlib.Path) -> pathlib.Path:
    """Where the note asking the running copy to come forward belongs."""
    return directory / ATTENTION_NAME


def ask(directory: pathlib.Path) -> bool:
    """Ask the running copy to show itself; False when the note would not go."""
    if not directory.is_dir():
        return False
    try:
        attention_path(directory).write_text("", encoding="utf-8")
    except OSError:
        return False
    return True


def asked(directory: pathlib.Path) -> bool:
    """Whether somebody asked, taking the note as it is read.

    Read once: a note left behind would raise the window on every tick.
    """
    note = attention_path(directory)
    try:
        if not note.exists():
            return False
        note.unlink()
    except OSError:
        return False
    return True
