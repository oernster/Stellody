"""Narrowing a finished answer to some of the genres it looked in. FR-D54, FR-D55.

Pure: no I/O, no framework, no clock. Its own module rather than more of
`discovery.py`: a run decides what an answer holds, while this decides what of
a finished answer is shown, which is a question asked long after the run ended
and of nothing but its result.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from stellody.domain.album import Album
from stellody.domain.discovery import (
    Gaps,
    SimilarArtist,
    catalogue_genres,
    source_artists,
)
from stellody.domain.text import comparison_key


@dataclass(frozen=True, slots=True)
class FilteredAnswer:
    """What a genre filter leaves of an answer; how many it could not judge."""

    gaps: tuple[Gaps, ...]
    unjudged: int = 0


def filtered_answer(
    gaps: tuple[Gaps, ...],
    library: tuple[Album, ...],
    remembered: dict[str, tuple[str, ...]],
    picked: tuple[str, ...],
) -> FilteredAnswer:
    """The answer as a genre filter leaves it. FR-D54, FR-D55.

    A source artist is judged by the library, through the same rule that made
    them a source artist: whoever a run over the picked genres would ask about
    keeps their albums. Ruled by Oliver on 2026-09-13, so nobody he holds is
    ever withheld for want of a catalogue genre. A candidate is judged by what
    the candidate genre cache records, since they are not in the library at all;
    one it records nothing for cannot be judged, so it is withheld and counted once.
    """
    if not picked:
        return FilteredAnswer(gaps=gaps)
    wanted = set(picked)
    holding = {
        comparison_key(artist)
        for artist in source_artists(library, picked, compilations=True)
    }
    unjudged: set[str] = set()
    kept: list[Gaps] = []
    for gap in gaps:
        artists: list[SimilarArtist] = []
        for candidate in gap.artists:
            named = set(catalogue_genres(remembered.get(candidate.identifier, ())))
            if not named:
                unjudged.add(candidate.identifier or candidate.name)
            elif named & wanted:
                artists.append(candidate)
        albums = gap.albums if comparison_key(gap.artist) in holding else ()
        if albums or artists:
            kept.append(replace(gap, albums=albums, artists=tuple(artists)))
    return FilteredAnswer(gaps=tuple(kept), unjudged=len(unjudged))
