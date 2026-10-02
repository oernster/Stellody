"""The other volumes of a compilation: which run it belongs to, what is missing.

Pure: no I/O, no framework, no clock. FR-D69 to FR-D72.

**A compilation's neighbours are its other volumes, not its artists.** Reported
by Oliver on 2026-09-29: a run over four house genres answered "Global
Underground (0 albums)". Measured the same day, MusicBrainz files that name as
an artist with no release groups at all, used only to tag the DJ mixes; the
albums themselves are credited to Various Artists and grouped into series.

**A series entry is held on its stem and number, whoever it is filed under.**
The library writes "Global Underground: Select #7 / Unmixed" where the
catalogue writes "Global Underground: Select #7"; it also files one series under
"Various", "Various Artists" and "Global Underground" at once, all measured
from the tags on 2026-09-29. The release key of section 3.5 is kept as a
second test rather than replaced, so nothing it already recognises is lost.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from stellody.domain.album import Album
from stellody.domain.discovery import ReleaseGroup, wanted_by
from stellody.domain.matching import ReleaseMatch, matched
from stellody.domain.narrowing import Narrowing, narrowed_to
from stellody.domain.overrides import AlbumField
from stellody.domain.release_years import ANY_YEAR, ReleaseYears
from stellody.domain.text import comparison_key, is_various_artists, normalise

# Where a title stops naming its series: a bracket, a spaced solidus or a
# spaced dash, whichever comes first. What follows is a mix, a city or an
# edition, as in "Afterhours 4 - Ibiza / Unmixed".
_TAIL = re.compile(r"\s*(?:[(\[]|\s/\s|\s-\s).*$")
# A volume number written as a word. Measured on 2026-09-30: MusicBrainz titles
# the tenth Select "Global Underground: Select Ten" where the library holds
# "Select #10", so the word has to read as the number or the two never meet.
NUMBER_WORDS = {
    word: value
    for value, word in enumerate(
        (
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
            "twenty",
        ),
        start=1,
    )
}
# The volume number ending a series title, with whatever introduced it. Each
# marker word must start a word, so "Techno 2" loses "2" rather than "no 2";
# the number must start one too, so "Mix2" keeps its digit and "Someone" its
# "one".
_NUMBER = re.compile(
    r"[\s:,]*(?:#|\b(?:no|vol|volume|part|pt)\b\.?)?\s*\b"
    r"(?P<number>\d+|" + "|".join(NUMBER_WORDS) + r")$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class SeriesPlace:
    """Where a title sits in a series: its stem, compared; its volume number.

    `number` is None for the volume that states none, which is how the first
    of a series is usually titled: "Global Underground: Adapt".
    """

    stem: str
    number: int | None = None


@dataclass(frozen=True, slots=True)
class Series:
    """A named run of release groups, as a catalogue answered it."""

    name: str
    entries: tuple[ReleaseGroup, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a series needs a name")


def volume_title(title: str) -> str:
    """The title up to its first bracket, spaced solidus or spaced dash.

    What names the series and the volume, without the mix or the city: what a
    catalogue is searched for, as "Global Underground: Select #7" for the
    library's "Global Underground: Select #7 / Unmixed".
    """
    return _TAIL.sub("", normalise(title))


def series_stem(title: str) -> str:
    """The part of a title naming its series, as written; empty for none.

    The volume title with a trailing volume number taken off. A title that is
    only a number has no stem, since "1999" names no series.
    """
    return _NUMBER.sub("", volume_title(title)).strip(" :,")


def series_place(title: str) -> SeriesPlace | None:
    """Where this title sits in its series; None where it names none."""
    stem = series_stem(title)
    if not stem:
        return None
    found = _NUMBER.search(volume_title(title))
    return SeriesPlace(
        stem=comparison_key(stem),
        number=None if found is None else _volume(found.group("number")),
    )


def _volume(written: str) -> int:
    """A volume number as written: digits, else one of the number words."""
    return int(written) if written.isdigit() else NUMBER_WORDS[written.casefold()]


def entry_key(group: ReleaseGroup) -> SeriesPlace | ReleaseMatch:
    """What makes two series entries the same volume.

    Its place where the title names one, else its release key. Not the whole
    record: measured on 2026-09-30, the series and a stem search both answered
    "Select #9", only one of them stating its kinds, so comparing records
    offered it twice.
    """
    return series_place(group.title) or group.match


def merged_entries(
    earlier: tuple[ReleaseGroup, ...], later: tuple[ReleaseGroup, ...]
) -> tuple[ReleaseGroup, ...]:
    """The earlier entries, then each later one that is a volume not yet there.

    Later entries are checked against each other as well, so one answer
    naming a volume twice still offers it once.
    """
    seen = {entry_key(group) for group in earlier}
    found = list(earlier)
    for group in later:
        key = entry_key(group)
        if key not in seen:
            seen.add(key)
            found.append(group)
    return tuple(found)


@dataclass(frozen=True, slots=True)
class HeldSeries:
    """Everything a library holds, as a series entry is compared against it."""

    places: frozenset[SeriesPlace]
    matches: frozenset[ReleaseMatch]

    def holds(self, group: ReleaseGroup) -> bool:
        """Whether this entry is on the shelf, by either test. FR-D71."""
        return group.match in self.matches or series_place(group.title) in self.places


def held_series(albums: tuple[Album, ...]) -> HeldSeries:
    """What the whole library holds, whoever each album is filed under."""
    places = (series_place(album.identity.title) for album in albums)
    return HeldSeries(
        places=frozenset(place for place in places if place is not None),
        matches=frozenset(matched(album.identity.title) for album in albums),
    )


def series_albums(
    albums: tuple[Album, ...],
    ticked: tuple[str, ...],
    placeholders: frozenset[str] = frozenset(),
) -> tuple[Album, ...]:
    """The held albums inside the ticks that are asked about by series.

    A compilation; else an album filed under a placeholder artist: a name the
    catalogue knows as one artist who released nothing. `placeholders` holds
    those names by `comparison_key`. Nothing ticked is nothing to ask about,
    for the reason `source_artists` gives.
    """
    if not ticked:
        return ()
    narrowing = Narrowing(field=AlbumField.GENRE, wanted=ticked)
    return tuple(
        album
        for album in narrowed_to(albums, narrowing)
        if is_various_artists(album.identity.album_artist)
        or comparison_key(album.identity.album_artist) in placeholders
    )


def sharing_stem(
    groups: tuple[ReleaseGroup, ...], title: str
) -> tuple[ReleaseGroup, ...]:
    """The release groups whose series stem is this title's. FR-D70."""
    wanted = series_place(title)
    if wanted is None:
        return ()
    return tuple(
        group
        for group in groups
        if (place := series_place(group.title)) is not None
        and place.stem == wanted.stem
    )


def series_missing(
    series: Series,
    held: HeldSeries,
    ticked: tuple[str, ...],
    years: ReleaseYears = ANY_YEAR,
) -> tuple[ReleaseGroup, ...]:
    """The entries of a series worth offering, each once, in catalogue order.

    Every kind is offered, compilations and DJ mixes included, since a series
    of compilations is made of nothing else. FR-D72. The genres and the years
    still apply, as they do to any album a run offers.
    """
    kept = tuple(
        group
        for group in series.entries
        if not held.holds(group)
        and wanted_by(group.genres, ticked)
        and years.admits(group.year)
    )
    return merged_entries((), kept)
