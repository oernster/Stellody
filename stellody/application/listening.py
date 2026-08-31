"""Keeping every track's rating and play count, in step with the store.

Held whole in memory rather than asked for a track at a time, because both
numbers are wanted while the library is being drawn: a row that had to ask the
disk what its rating was would ask once per row. The whole of it is one small
query and only tracks somebody has actually listened to or rated are in it, so
a library nobody has touched costs nothing at all.

Every change is written through immediately. There is no save step to forget
and nothing is lost to a crash between one and the next.
"""

from __future__ import annotations

from stellody.application.ports import ListeningStore
from stellody.domain.listening import Listening

NOTHING = Listening()


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
        """Hold it and write it, so the two can never disagree."""
        self._records[handle] = record
        self._store.set_listening(handle, path, record)
        return record
