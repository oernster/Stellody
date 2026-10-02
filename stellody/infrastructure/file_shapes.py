"""How the discovery files carry an album, a candidate, years and choices.

Split out of `discovery_file.py` on 2026-10-02 when FR-D85 took it over the
line cap. Both directions of each shape live together, one home apiece, since
the discovery file and the catalogue memory both carry albums and candidates
and a shape written twice is two shapes the day one is changed.
"""

from __future__ import annotations

from stellody.domain.discovery import ReleaseGroup, SimilarArtist
from stellody.domain.including import OWN_ALBUMS, Including
from stellody.domain.matching import ReleaseKind
from stellody.domain.release_years import ANY_YEAR, ReleaseYears

# Where an album's first release date is kept. Its absence from an entry is
# itself information: the entry was written before dates were. FR-D67.
RELEASED = "released"
# Where a run's years are kept, beside its genres. FR-D64.
YEARS = "years"
EARLIEST = "earliest"
LATEST = "latest"
# Whether an entry names a series rather than an artist. FR-D74. Also the
# series choice under `INCLUDING`, where it means the same thing.
SERIES = "series"
# What a run widened to, beside its years. FR-D85.
INCLUDING = "including"
CREDITS = "credits"
MIXES = "mixes"


def album_as(group: ReleaseGroup) -> dict:
    """One album in the shape every file here carries it.

    One home for the shape, since the discovery file and the catalogue memory
    both hold albums and a shape written twice is two shapes the day one is
    changed.
    """
    return {
        "title": group.title,
        "kinds": [str(kind) for kind in group.kinds],
        "genres": list(group.genres),
        RELEASED: group.released,
    }


def artist_as(artist: SimilarArtist) -> dict:
    """One candidate artist in the shape every file here carries it."""
    return {"name": artist.name, "identifier": artist.identifier}


def _listed(entry: dict, key: str) -> list:
    """The list under this key; empty where it is anything else."""
    found = entry.get(key)
    return found if isinstance(found, list) else []


def _kind_of(name: str) -> ReleaseKind:
    """The kind this name means; OTHER for one this version does not know.

    The same rule the catalogue client applies on the way in, so a file
    written by a later Stellody is read by an earlier one without a kind it
    has never heard of being mistaken for a plain album.
    """
    try:
        return ReleaseKind(name)
    except ValueError:
        return ReleaseKind.OTHER


def album_from(entry: object) -> ReleaseGroup | None:
    """One album as the file carries it; None where it carries nothing usable.

    A title is required rather than defaulted, since the domain refuses an
    album without one and a record nobody can name is not one to offer.
    """
    if not isinstance(entry, dict):
        return None
    title = str(entry.get("title") or "").strip()
    if not title:
        return None
    return ReleaseGroup(
        title=title,
        kinds=tuple(_kind_of(str(kind)) for kind in _listed(entry, "kinds")),
        genres=tuple(str(genre) for genre in _listed(entry, "genres")),
        released=str(entry.get(RELEASED) or ""),
    )


def _bound(held: dict, key: str) -> int | None:
    """One bound of the years a file names; None where it names none.

    Anything else there is refused rather than skipped, so a damaged pair is
    never read as half of itself: a range narrowed on one side only is a
    question nobody asked.
    """
    found = held.get(key)
    if found is None:
        return None
    if isinstance(found, int) and not isinstance(found, bool):
        return found
    raise ValueError(f"{key} is not a year")


def years_from(held: object) -> ReleaseYears:
    """The years a file says its run was asked for; every year where none.

    A file written before years were recorded names none, which is what that
    run asked for. Neither a bound that is not a year nor a pair the wrong way
    round can have been written by a run, so either reads as no years rather
    than failing the whole file.
    """
    if not isinstance(held, dict):
        return ANY_YEAR
    stated = held.get(YEARS)
    if not isinstance(stated, dict):
        return ANY_YEAR
    try:
        return ReleaseYears(_bound(stated, EARLIEST), _bound(stated, LATEST))
    except ValueError:
        return ANY_YEAR


def including_from(held: object) -> Including:
    """What a file says its run widened to; the defaults where it says nothing.

    A file written before the choices were recorded names none, so it reads as
    the defaults: the artists' own albums with DJ mixes offered. That is not
    quite what such a run did, since no run before FR-D80 offered mixes; an
    older answer expanded now can offer mixes its run never looked at. Each
    choice is read on its own, so one that is not a yes or no falls back alone
    rather than taking the others with it. FR-D85.
    """
    stated = held.get(INCLUDING) if isinstance(held, dict) else None
    if not isinstance(stated, dict):
        return OWN_ALBUMS

    def choice(key: str, otherwise: bool) -> bool:
        found = stated.get(key)
        return found if isinstance(found, bool) else otherwise

    return Including(
        credits=choice(CREDITS, OWN_ALBUMS.credits),
        series=choice(SERIES, OWN_ALBUMS.series),
        mixes=choice(MIXES, OWN_ALBUMS.mixes),
    )


def artist_from(entry: object) -> SimilarArtist | None:
    """One candidate artist as the file carries it; None where unusable."""
    if not isinstance(entry, dict):
        return None
    name = str(entry.get("name") or "").strip()
    if not name:
        return None
    return SimilarArtist(name=name, identifier=str(entry.get("identifier") or ""))
