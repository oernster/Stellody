"""What stands in where the window was handed nothing.

A window can be built without a store and without a diary, which is what every
test that is about something else wants. Rather than let those absences reach
the code that uses them, each has a stand-in here that answers the same shape
and keeps nothing. The window then has one kind of collaborator rather than
two, so nothing downstream asks whether it was given a real one.

The trail belongs beside them for the same reason: it exists to make the
diary's account worth reading, saying who asked rather than only what
happened.
"""

from __future__ import annotations

import pathlib
import traceback

# Enough frames to name the door without printing the whole interpreter.
TRAIL_FRAMES = 6


class ForgetfulStore:
    """Stands in where no store was given: it holds nothing and keeps nothing.

    A window built without one still shows the stars, which is what every test
    that is not about ratings wants; what it says is simply never kept.
    """

    def all_listening(self) -> dict:
        """Nothing has ever been kept here."""
        return {}

    def set_listening(self, handle: str, path: str, record) -> None:
        """Take it and forget it."""


def say_nothing(message: str) -> None:
    """The default diary: one that keeps no account at all."""


def trail() -> str:
    """The calling frames, innermost last, on one line.

    Two frames are dropped: this one and the one that asked, neither of which
    tells a reader anything they did not already know from where the line was
    written.
    """
    frames = traceback.extract_stack()[:-2]
    return " <- ".join(
        f"{pathlib.PurePath(frame.filename).name}:{frame.lineno} {frame.name}"
        for frame in frames[-TRAIL_FRAMES:]
    )
