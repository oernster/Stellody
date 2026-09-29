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
from stellody.domain.narrowing import Narrowing, narrowed_to
from stellody.domain.overrides import AlbumField
from stellody.domain.series import series_place
from stellody.domain.text import comparison_key


@dataclass(frozen=True, slots=True)
class FilteredAnswer:
    """What a genre filter leaves of an answer; how many it could not judge."""

    gaps: tuple[Gaps, ...]
    unjudged: int = 0


def worth_showing(gaps: tuple[Gaps, ...]) -> tuple[Gaps, ...]:
    """The headings with something beneath them. FR-D75.

    Ruled by Oliver on 2026-09-29, over "Global Underground (0 albums)": a
    heading with nothing under it says nothing anybody can act on. The file
    still holds it; only the screen leaves it out.
    """
    return tuple(gap for gap in gaps if not gap.is_empty)


def _series_held(library: tuple[Album, ...], picked: tuple[str, ...]) -> set[str]:
    """The series stems of held albums inside the picked genres, compared."""
    narrowing = Narrowing(field=AlbumField.GENRE, wanted=picked)
    places = (series_place(a.identity.title) for a in narrowed_to(library, narrowing))
    return {place.stem for place in places if place is not None}


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

    A series keeps its albums where a held album inside the picked genres has
    that series' name as its stem, which is how a series reached by its stem
    is named. A catalogue series named otherwise is withheld under a filter.
    """
    if not picked:
        return FilteredAnswer(gaps=gaps)
    wanted = set(picked)
    holding = {
        comparison_key(artist)
        for artist in source_artists(library, picked, compilations=True)
    }
    series = _series_held(library, picked)
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
        keeping = series if gap.series else holding
        albums = gap.albums if comparison_key(gap.artist) in keeping else ()
        if albums or artists:
            kept.append(replace(gap, albums=albums, artists=tuple(artists)))
    return FilteredAnswer(gaps=tuple(kept), unjudged=len(unjudged))
