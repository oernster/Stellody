"""Reading useful values out of a raw tag mapping.

Rippers disagree about spelling and about how numbers are written, so every
lookup accepts several names and every number tolerates the "3/12" form.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from stellody.domain.text import normalise, split_artists

ALBUM = ("ALBUM",)
ALBUM_ARTIST = ("ALBUMARTIST", "ALBUM ARTIST", "ALBUM_ARTIST")
ARTIST = ("ARTIST", "PERFORMER")
TITLE = ("TITLE",)
DATE = ("DATE", "YEAR", "ORIGINALDATE")
GENRE = ("GENRE",)
DISC = ("DISCNUMBER", "DISC")
TRACK = ("TRACKNUMBER", "TRACK")

_LEADING_INT = re.compile(r"^\s*(\d{1,4})")

TagMap = Mapping[str, tuple[str, ...]]


def values(tags: TagMap, names: tuple[str, ...]) -> tuple[str, ...]:
    """Every value held under the first of these names that is present."""
    for name in names:
        found = tags.get(name)
        if found:
            return tuple(value for value in found if value.strip())
    return ()


def first(tags: TagMap, names: tuple[str, ...]) -> str:
    """The first value under these names, normalised; empty when absent."""
    found = values(tags, names)
    return normalise(found[0]) if found else ""


def number(tags: TagMap, names: tuple[str, ...]) -> int | None:
    """A tag read as a positive integer, tolerating the "3/12" form."""
    raw = first(tags, names)
    match = _LEADING_INT.match(raw)
    if match is None:
        return None
    parsed = int(match.group(1))
    return parsed if parsed > 0 else None


def artists(tags: TagMap) -> tuple[str, ...]:
    """Every credited artist, from repeated fields or a packed single field."""
    found = values(tags, ARTIST)
    if len(found) > 1:
        return tuple(normalise(value) for value in found)
    if not found:
        return ()
    return split_artists(found[0])
