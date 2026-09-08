"""What the catalogues have already said, kept between runs.

The file behind `application/remembering.py`. Read once when a run starts,
written once when it ends, which is the shape the genre cache beside it
already has: a run that wrote after every answer would write one file two
hundred times.

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

from stellody.application.remembering import Recollection
from stellody.infrastructure import paths
from stellody.infrastructure.atomic import written as _written
from stellody.infrastructure.discovery_file import (
    album_as,
    album_from,
    artist_as,
    artist_from,
)

MEMORY_NAME = "catalogue-memory.json"


def memory_path() -> pathlib.Path:
    """Where what the catalogues said is kept, whether or not it is there."""
    return paths.data_dir() / MEMORY_NAME


def _mapping(held: object, key: str) -> dict:
    """The mapping under this key; empty where the file holds anything else."""
    if not isinstance(held, dict):
        return {}
    found = held.get(key)
    return found if isinstance(found, dict) else {}


def _listed(found: object) -> list:
    """The list this is; nothing at all where it is anything else."""
    return found if isinstance(found, list) else []


def _kept(held: object) -> Recollection:
    """A recollection out of whatever the file turned out to hold.

    Every value is checked rather than trusted, since a file half written by
    an older Stellody must cost a run its speed rather than its life.
    """
    return Recollection(
        identifiers={
            str(name): tuple(str(one) for one in _listed(found))
            for name, found in _mapping(held, "identifiers").items()
        },
        albums={
            str(identifier): tuple(
                album
                for album in (album_from(one) for one in _listed(found))
                if album is not None
            )
            for identifier, found in _mapping(held, "albums").items()
        },
        similar={
            str(question): tuple(
                artist
                for artist in (artist_from(one) for one in _listed(found))
                if artist is not None
            )
            for question, found in _mapping(held, "similar").items()
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
        "identifiers": {name: list(found) for name, found in kept.identifiers.items()},
        "albums": {
            identifier: [album_as(album) for album in found]
            for identifier, found in kept.albums.items()
        },
        "similar": {
            question: [artist_as(artist) for artist in found]
            for question, found in kept.similar.items()
        },
        "written_at": dict(kept.written_at),
    }


def remembered() -> Recollection:
    """Everything already known; an empty recollection where nothing is."""
    where = memory_path()
    try:
        return _kept(json.loads(where.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return Recollection()


def remember(kept: Recollection) -> None:
    """Keep this for the next run; say nothing where it cannot be kept."""
    try:
        _written(memory_path(), _as_written(kept))
    except OSError:
        return


class FileCatalogueMemory:
    """The catalogue memory as a file, for a run to be handed."""

    def remembered(self) -> Recollection:
        """Everything already known; empty where nothing is."""
        return remembered()

    def remember(self, kept: Recollection) -> None:
        """Keep it for next time."""
        remember(kept)
