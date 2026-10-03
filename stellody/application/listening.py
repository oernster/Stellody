"""Keeping every track's rating and play count, in step with the store.

Held whole in memory rather than asked for a track at a time, because both
numbers are wanted while the library is being drawn: a row that had to ask the
disk what its rating was would ask once per row. The whole of it is one small
query and only tracks somebody has actually listened to or rated are in it, so
a library nobody has touched costs nothing at all.

Every change is written through immediately. There is no save step to forget
and nothing is lost to a crash between one and the next. A change the store
refuses is not held either.
"""

from __future__ import annotations

from stellody.application.ports import ListeningStore
from stellody.domain.listening import Listening

NOTHING = Listening()


class ListeningUnwritable(Exception):
    """The store would not take a rating or a play count, so nothing changed."""


class ListeningLog:
    """What has been rated and what has played out, by track handle."""

    def __init__(self, store: ListeningStore) -> None:
        self._store = store
        self._records: dict[str, Listening] = {}

    def load(self) -> None:
        """Take everything the store holds, replacing what was held before."""
        self._records = dict(self._store.all_listening())

    def of(self, handle: str) -> Listening:
        """One track's record; an empty one where there is nothing yet.

        An absent record and a track rated at nothing read the same, which is
        what lets a rating be taken back without a second kind of emptiness.
        """
        return self._records.get(handle, NOTHING)

    def rate(self, handle: str, path: str, stars: int) -> Listening:
        """Set one track's rating, keeping whatever count it has."""
        return self._write(handle, path, self.of(handle).rated(stars))

    def count_play(self, handle: str, path: str) -> Listening:
        """Record that one track has played out."""
        return self._write(handle, path, self.of(handle).played())

    def _write(self, handle: str, path: str, record: Listening) -> Listening:
        """Write it, then hold it, so the two can never disagree.

        The store goes first. Held first, a write the store refused left the
        window showing a rating the disk never had, which vanished at the next
        start; now a refusal leaves both as they were and reaches whoever
        asked as `ListeningUnwritable`, for them to say so.
        """
        self._store.set_listening(handle, path, record)
        self._records[handle] = record
        return record
