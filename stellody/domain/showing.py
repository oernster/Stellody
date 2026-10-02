"""Which kinds of thing an answer shows: the results filter's "Show:" row. FR-D86.

Pure: no I/O, no framework, no clock.

**By kind, beside the genres.** Ruled by Oliver on 2026-10-02: with series and
DJ mixes offered in number (FR-D80, FR-D82), an answer needs separating by what
each thing is as well as by what it plays. A series heading is shown or hidden
whole; under an artist, a DJ mix answers to its own box and every other album
to the albums box; the similar artists answer to theirs. A heading left with
nothing under it is not shown, for the reason FR-D75 gives.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.domain.matching import ReleaseKind


@dataclass(frozen=True, slots=True)
class Showing:
    """The four boxes of the "Show:" row, all ticked to begin with."""

    albums: bool = True
    mixes: bool = True
    series: bool = True
    artists: bool = True


# Every box ticked: no filter by kind at all.
EVERYTHING = Showing()


def _wanted(album: ReleaseGroup, showing: Showing) -> bool:
    """Whether this album's own box is ticked."""
    return showing.mixes if ReleaseKind.DJ_MIX in album.kinds else showing.albums


def shown(gaps: tuple[Gaps, ...], showing: Showing) -> tuple[Gaps, ...]:
    """The headings and rows these boxes leave, in the order they came."""
    if showing == EVERYTHING:
        return gaps
    kept: list[Gaps] = []
    for gap in gaps:
        if gap.series:
            if showing.series:
                kept.append(gap)
            continue
        albums = tuple(album for album in gap.albums if _wanted(album, showing))
        artists = gap.artists if showing.artists else ()
        if albums or artists:
            kept.append(replace(gap, albums=albums, artists=artists))
    return tuple(kept)
