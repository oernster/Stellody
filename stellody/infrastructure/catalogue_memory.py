"""What the catalogues have already said, kept between runs.

The file behind `application/remembering.py`. Read once when a run starts and
written whole once when it ends, since a run that rewrote a file of this size
after every answer would write it two hundred times.

**So each answer is also noted on its own, the moment it arrives.** The whole
file being written late is affordable only because nothing waits on it: the
running record beside it (`journal.py`) takes one line an answer and is read
back on top of the file, so a run whose process dies loses nothing. The file
and the record hold the same answers while both exist, which is why writing
the file clears the record.

**Nothing here expires.** An answer stands until the file is removed. That is
the point of it rather than an oversight: a memory with a lifetime answers
differently before and after that lifetime, which is the difference between
two runs this exists to end.

**A memory that cannot be read is an empty memory, never an error.** The same
judgement the rest of this module family makes: an answer nobody can recall
costs a run its requests, while an exception costs the run itself.
"""

from __future__ import annotations

import json
import pathlib

from stellody.application.remembering import (
    ALBUMS,
    IDENTIFIERS,
    SIMILAR,
    Recollection,
)
from stellody.domain.discovery import ReleaseGroup, SimilarArtist
from stellody.infrastructure import journal, paths
from stellody.infrastructure.atomic import written as _written
from stellody.infrastructure.discovery_file import (
    album_as,
    album_from,
    artist_as,
    artist_from,
)

MEMORY_NAME = "catalogue-memory.json"
JOURNAL_NAME = "catalogue-memory.record"


def memory_path() -> pathlib.Path:
    """Where what the catalogues said is kept, whether or not it is there."""
    return paths.data_dir() / MEMORY_NAME


def journal_path() -> pathlib.Path:
    """Where answers are noted as they arrive, until the file catches up."""
    return paths.data_dir() / JOURNAL_NAME


def _mapping(held: object, key: str) -> dict:
    """The mapping under this key; empty where the file holds anything else."""
    if not isinstance(held, dict):
        return {}
    found = held.get(key)
    return found if isinstance(found, dict) else {}


def _listed(found: object) -> list:
    """The list this is; nothing at all where it is anything else."""
    return found if isinstance(found, list) else []


def _identifiers(found: object) -> tuple[str, ...]:
    """One identify answer, out of whatever was written down for it."""
    return tuple(str(one) for one in _listed(found))


def _albums(found: object) -> tuple[ReleaseGroup, ...]:
    """One albums answer, with anything unreadable left out of it."""
    return tuple(
        album
        for album in (album_from(one) for one in _listed(found))
        if album is not None
    )


def _similar(found: object) -> tuple[SimilarArtist, ...]:
    """One similarity answer, with anything unreadable left out of it."""
    return tuple(
        artist
        for artist in (artist_from(one) for one in _listed(found))
        if artist is not None
    )


def _kept(held: object) -> Recollection:
    """A recollection out of whatever the file turned out to hold.

    Every value is checked rather than trusted, since a file half written by
    an older Stellody must cost a run its speed rather than its life. The
    three answer shapes are read by the same three functions the running
    record is read by, so a file and a record cannot come back differently.
    """
    return Recollection(
        identifiers={
            str(name): _identifiers(found)
            for name, found in _mapping(held, IDENTIFIERS).items()
        },
        albums={
            str(identifier): _albums(found)
            for identifier, found in _mapping(held, ALBUMS).items()
        },
        similar={
            str(question): _similar(found)
            for question, found in _mapping(held, SIMILAR).items()
        },
        written_at={
            str(question): float(when)
            for question, when in _mapping(held, "written_at").items()
            if isinstance(when, (int, float))
        },
    )


def _as_written(kept: Recollection) -> dict:
    """The recollection in the shape the file carries it."""
    return {
        IDENTIFIERS: {name: list(found) for name, found in kept.identifiers.items()},
        ALBUMS: {
            identifier: [album_as(album) for album in found]
            for identifier, found in kept.albums.items()
        },
        SIMILAR: {
            question: [artist_as(artist) for artist in found]
            for question, found in kept.similar.items()
        },
        "written_at": dict(kept.written_at),
    }


def _answer_as(kind: str, answer: object) -> list:
    """One answer in the shape the running record carries it.

    The same shapes the file uses, one answer at a time rather than all of
    them, so what the record holds can be read straight back into a
    recollection.
    """
    if kind == ALBUMS:
        return [album_as(album) for album in answer]
    if kind == SIMILAR:
        return [artist_as(artist) for artist in answer]
    return [str(one) for one in answer]


def _put(kept: Recollection, kind: str, key: str, answer: object) -> bool:
    """Put one noted answer back where it came from; whether it went anywhere.

    A kind this Stellody does not know is skipped rather than guessed at,
    which is how a record written by a later version costs a run some
    requests instead of its life.
    """
    if kind == IDENTIFIERS:
        kept.identifiers[key] = _identifiers(answer)
    elif kind == ALBUMS:
        kept.albums[key] = _albums(answer)
    elif kind == SIMILAR:
        kept.similar[key] = _similar(answer)
    else:
        return False
    return True


def _replayed(kept: Recollection, entries: tuple[dict, ...]) -> Recollection:
    """The recollection with everything noted since laid on top of it.

    In the order it was written, so a question answered twice keeps the later
    answer, exactly as it would inside the run that asked.
    """
    for entry in entries:
        kind, key, when = entry.get("kind"), entry.get("key"), entry.get("when")
        if not isinstance(key, str) or not isinstance(when, (int, float)):
            continue
        if _put(kept, str(kind), key, entry.get("answer")):
            kept.written_at[f"{kind}:{key}"] = float(when)
    return kept


def _from_file() -> Recollection:
    """What the file holds; an empty recollection where it holds nothing."""
    where = memory_path()
    try:
        return _kept(json.loads(where.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return Recollection()


def remembered() -> Recollection:
    """Everything already known, the file plus everything noted since it.

    The record is read ON TOP of the file rather than instead of it: a run
    whose process died noted its answers and never reached the file, so the
    two together are what is known and the file alone is not.
    """
    return _replayed(_from_file(), journal.replayed(journal_path()))


def note(kind: str, key: str, answer: object, when: float) -> None:
    """Write one answer down now, so a run that dies still keeps it."""
    journal.note(
        journal_path(),
        {"kind": kind, "key": key, "when": when, "answer": _answer_as(kind, answer)},
    )


def remember(kept: Recollection) -> None:
    """Keep this for the next run; say nothing where it cannot be kept.

    The running record is dropped once the file holds what it held; never
    before. A record cleared beside a file that was never written would throw
    away the very answers it exists to protect.
    """
    try:
        _written(memory_path(), _as_written(kept))
    except OSError:
        return
    journal.cleared(journal_path())


class FileCatalogueMemory:
    """The catalogue memory as a file, for a run to be handed."""

    def remembered(self) -> Recollection:
        """Everything already known; empty where nothing is."""
        return remembered()

    def note(self, kind: str, key: str, answer: object, when: float) -> None:
        """Write this one answer down now."""
        note(kind, key, answer, when)

    def remember(self, kept: Recollection) -> None:
        """Keep it for next time."""
        remember(kept)
