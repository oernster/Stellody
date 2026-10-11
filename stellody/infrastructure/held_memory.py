"""The catalogue memory a session holds, over the file `catalogue_memory.py` keeps.

Split from the file's own format because the two change for different reasons:
what the file holds is a question of shapes, while when it is read and written
is a question of what else is running, above all the thread feeding the sound
device.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import fields

from stellody.application.remembering import Recollection, merged
from stellody.infrastructure import journal
from stellody.infrastructure.catalogue_memory import (
    entry_for,
    journal_path,
    remember,
    remembered,
    replayed_over,
)


class FileCatalogueMemory:
    """The catalogue memory as a file, read once and held, for a run to be handed.

    One is made, then shared by everything that keeps answers, so its lock is
    the one lock: a note landing between a save reading what is known and
    clearing the running record would be cleared without ever reaching the
    file.

    **Read once, written whole only when the application leaves.** Reading the
    file and writing it whole hold Python's interpreter for a tenth of a second
    at a stretch, measured on 2026-10-11 against an 18 MB file, which starves
    the thread feeding the sound device: the diary showed it run dry within
    half a second of opening discovery, starting a run and stopping one. So
    the file is read the first time anything asks and held; every note goes
    into what is held as well as onto the running record. A run's save then
    merges in hand and writes nothing, since every answer it learned is already
    on the record; `keep` writes the file whole once, as the application quits.
    A process that dies first loses nothing, for the reason it never did: the
    record is read on top of the file next time.

    Each caller is handed a copy, since a stopped run still winding down on
    its own thread goes on adding to the one it was given.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._held: Recollection | None = None
        self._unwritten = False

    def _holding(self) -> Recollection:
        """What is known, read from the file the first time it is asked for."""
        if self._held is None:
            self._held = remembered()
        return self._held

    def remembered(self) -> Recollection:
        """Everything already known, as a copy; empty where nothing is."""
        with self._lock:
            held = self._holding()
            return Recollection(
                **{one.name: dict(getattr(held, one.name)) for one in fields(held)}
            )

    def note(self, kind: str, key: str, answer: object, when: float) -> None:
        """Write this one answer down now; put it into what is held too."""
        entry = entry_for(kind, key, answer, when)
        with self._lock:
            journal.note(journal_path(), entry)
            self._held = replayed_over(self._holding(), (entry,))
            self._unwritten = True

    def remember(self, kept: Recollection) -> None:
        """Keep it for this session, over whatever was kept since; write nothing."""
        with self._lock:
            self._held = merged(self._holding(), kept)
            self._unwritten = True

    def keep(self) -> None:
        """Write the file whole and clear the record, if anything is new."""
        with self._lock:
            if self._unwritten:
                remember(self._holding())
                self._unwritten = False


def warm_memory(memory: FileCatalogueMemory, note: Callable[[str], None]) -> None:
    """Read the memory on a thread of its own, now rather than on first use.

    Called as the application opens, while nothing is playing. A failure is
    written down rather than raised: the memory is then read when first asked
    for, which costs a stutter rather than a run.
    """

    def read() -> None:
        try:
            memory.remembered()
        except Exception as error:  # noqa: BLE001 - noted, read again later
            note(f"the catalogue memory could not be read ahead: {error}")

    threading.Thread(target=read, name="catalogue-memory", daemon=True).start()
