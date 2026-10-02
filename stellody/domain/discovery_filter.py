"""Narrowing a finished answer to some of the genres it looked in. FR-D54, FR-D55.

Pure: no I/O, no framework, no clock. Its own module rather than more of
`discovery.py`: a run decides what an answer holds, while this decides what of
a finished answer is shown, which is a question asked long after the run ended
and of nothing but its result.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from stellody.domain.album import Album
from stellody.domain.discovery import (
    Gaps,
    SimilarArtist,
    catalogue_genres,
    source_artists,
)
from stellody.domain.genres import chosen_in
from stellody.domain.narrowing import Narrowing, narrowed_to
from stellody.domain.overrides import AlbumField
from stellody.domain.series import series_place
from stellody.domain.text import comparison_key, credit_parts


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


def _keys_of(names: Iterable[str]) -> set[str]:
    """Each name compared, plus each artist a joint credit names.

    The run asks about every part of a credit no catalogue knows whole (see
    `credit_parts`), so a heading can be one part of a credit the library holds.
    Measured on 2026-10-02: all 43 headings whose candidates were held back for
    want of a genre were such parts, `DJ Tennis` of `Moat, Kyozo, & DJ Tennis`.
    """
    return {
        comparison_key(name)
        for whole in names
        for name in (whole, *credit_parts(whole))
    }


def _held_genres(
    library: tuple[Album, ...],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """The catalogue genres the library holds per artist and per series. FR-D78.

    An album counts for its album artist and for every artist credited on its
    tracks, so a source reached through a compilation credit has a genre too;
    it counts for its series where its title has a stem. Both keyed compared,
    since that is how a heading is matched to the library everywhere else.
    """
    by_artist: dict[str, set[str]] = {}
    by_series: dict[str, set[str]] = {}
    for album in library:
        named = set(chosen_in(album.genre))
        if not named:
            continue
        credited = (album.identity.album_artist, *album.artists)
        for key in _keys_of(credited):
            by_artist.setdefault(key, set()).update(named)
        place = series_place(album.identity.title)
        if place is not None:
            by_series.setdefault(place.stem, set()).update(named)
    return by_artist, by_series


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
    the candidate genre cache records, since they are not in the library at all.

    **A candidate MusicBrainz gives no recognised genre is judged by who it
    was suggested for.** Ruled by Oliver on 2026-10-01 (FR-D78): of 1,996
    similar artists in his whole-library answer, 615 had no genre at all on
    MusicBrainz and were withheld for it. Such a candidate takes the genres
    the library holds for the heading it sits under, judged per heading. Only
    where the heading's albums name no catalogue genre either is it withheld
    and counted, once, as one the filter could not judge.

    A series keeps its albums where a held album inside the picked genres has
    that series' name as its stem, which is how a series reached by its stem
    is named. A catalogue series named otherwise is withheld under a filter.
    """
    if not picked:
        return FilteredAnswer(gaps=gaps)
    wanted = set(picked)
    holding = _keys_of(source_artists(library, picked, compilations=True))
    series = _series_held(library, picked)
    by_artist, by_series = _held_genres(library)
    unjudged: set[str] = set()
    kept: list[Gaps] = []
    for gap in gaps:
        held = (by_series if gap.series else by_artist).get(
            comparison_key(gap.artist), set()
        )
        artists: list[SimilarArtist] = []
        for candidate in gap.artists:
            named = set(catalogue_genres(remembered.get(candidate.identifier, ())))
            judged_by = named or held
            if not judged_by:
                unjudged.add(candidate.identifier or candidate.name)
            elif judged_by & wanted:
                artists.append(candidate)
        keeping = series if gap.series else holding
        albums = gap.albums if comparison_key(gap.artist) in keeping else ()
        if albums or artists:
            kept.append(replace(gap, albums=albums, artists=tuple(artists)))
    return FilteredAnswer(gaps=tuple(kept), unjudged=len(unjudged))
