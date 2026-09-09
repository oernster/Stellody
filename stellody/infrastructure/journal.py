"""Writing one answer down the moment it arrives, so nothing can take it away.

Reported by Oliver on 2026-09-09, having left a run going overnight: a run of
fifty minutes ended and everything it had learned would have gone with it had
the process died rather than returned. The memories beside this are written
ONCE, when a run ends; a run that never ends never writes.

So every answer is appended here as it arrives, one line of JSON at a time;
the whole file is still written at the end as it always was. A run that
dies leaves this behind, the next run reads its file, replays these on top of
it and knows everything the dead run knew. What is here is a duplicate of what
is in the file for as long as both exist, which is why consolidating clears it.

**Appended and forced to the disk, never rewritten.** An append cannot damage
what is already written, so the worst a half-written line can cost is that one
line. The force is what makes it survive the machine going down rather than
merely the application: a buffered write is a record only the living process
can see, which is the record nobody needs.

**A line nobody can read is skipped rather than fatal.** The same judgement the
memories make: an answer that cannot be recalled costs a run some requests,
while an exception costs the run itself.
"""

from __future__ import annotations

import json
import os
import pathlib


def note(where: pathlib.Path, entry: dict) -> None:
    """Add one answer to the end of the record; say nothing where it cannot be.

    Failing to write here is not worth failing a run over: what it costs is
    the safety net; the run itself still ends by writing everything down.
    """
    try:
        with where.open("a", encoding="utf-8") as record:
            record.write(json.dumps(entry, ensure_ascii=False) + "\n")
            record.flush()
            os.fsync(record.fileno())
    except OSError:
        return


def replayed(where: pathlib.Path) -> tuple[dict, ...]:
    """Every answer written since the last consolidation, in the order written.

    The order matters: a question answered twice belongs to whichever answer
    came last, exactly as it would inside a run.
    """
    try:
        lines = where.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    return tuple(entry for entry in (_read(line) for line in lines) if entry)


def _read(line: str) -> dict | None:
    """The entry this line holds; nothing where it holds anything else.

    A run that died mid-write leaves a partial last line, which is precisely
    the case this exists for.
    """
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    return entry if isinstance(entry, dict) else None


def cleared(where: pathlib.Path) -> None:
    """Drop the record, once its answers are kept in the file itself."""
    try:
        where.unlink(missing_ok=True)
    except OSError:
        return
