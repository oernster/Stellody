"""A running account of when Stellody appeared and what asked it to.

A window arriving unbidden is the hardest kind of fault to reason about: by
the time it is noticed, whatever caused it has finished. Two fixes have gone
in against it already and neither has been shown to be the one that mattered,
which is exactly the point at which guessing has to stop and a measurement has
to start.

So every path that can put the window on screen writes down that it did, with
the frames that led there. When it next happens, the log names the cause
rather than leaving us to argue about which of three doors it came through.

It appends rather than overwrites, because the interesting run is the one
before the one being read. It carries the process id too, since more than one
Stellody may be involved and telling them apart is half the question.

Nothing here may raise. A diary that breaks the application it is watching is
worse than no diary at all.
"""

from __future__ import annotations

import datetime
import os
import pathlib
import tempfile

LOG_NAME = "stellody-diary.log"
# Beyond this the file is started again. A player left running for weeks must
# not fill a disk with its own notes.
KEEP_BYTES = 2_000_000


def location() -> pathlib.Path:
    """Where the account is kept, beside the startup log."""
    return pathlib.Path(tempfile.gettempdir()) / LOG_NAME


def note(message: str) -> None:
    """Write down one thing that happened; stay silent if it cannot be."""
    # Local time carrying its offset, so a line can be lined up against
    # the Windows event log without anybody doing arithmetic.
    clock = datetime.datetime.now(datetime.UTC).astimezone()
    stamp = clock.isoformat(sep=" ", timespec="milliseconds")
    line = f"{stamp}  pid {os.getpid():>6}  {message}\n"
    try:
        report = location()
        if report.exists() and report.stat().st_size > KEEP_BYTES:
            report.unlink()
        with report.open("a", encoding="utf-8") as diary:
            diary.write(line)
    except OSError:
        return


def clear() -> None:
    """Start a fresh account, for when a run is being watched deliberately."""
    try:
        location().unlink(missing_ok=True)
    except OSError:
        return
