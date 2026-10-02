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
from stellody.domain.discovery import MIX_KINDS, ReleaseGroup, wanted_by
from stellody.domain.matching import YEAR_LIKE, ReleaseMatch, matched
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
# A volume number inside a title, then a colon and whoever mixed it. FR-D81.
# Measured on 2026-10-02: the library holds "Global Underground #45: Danny
# Tenaglia - Brooklyn" where MusicBrainz writes "Global Underground 045: Danny
# Tenaglia in Brooklyn"; fabric numbers its mixes "Fabric 99: Sasha". Digits
# only, since "One: A Story" names no volume; never a year, since "Sónar 2011:
# Mixed by Agoria" is one mix of that year rather than its 2011th volume.
_INNER = re.compile(
    r"^(?P<stem>.*?)[\s,]*(?:#|\b(?:no|vol|volume|part|pt)\b\.?)?\s*\b"
    r"(?P<number>\d+)\s*:\s*\S",
    re.IGNORECASE,
)
# What a stem needs to name anything: a letter. "2001: A Space Odyssey" has
# none before its colon, so it is read as a title rather than a volume.
_LETTER = re.compile(r"[^\W\d_]")


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


def _split(title: str) -> tuple[str, int | None]:
    """A title's series stem as written, plus its volume number if it has one.

    A number followed by a colon and a name is the volume, whatever follows;
    else a number ending the volume title is. FR-D81.
    """
    volume = volume_title(title)
    inner = _INNER.match(volume)
    if inner is not None:
        stem = inner.group("stem").strip(" :,")
        number = inner.group("number")
        if _LETTER.search(stem) and not YEAR_LIKE.match(number):
            return stem, int(number)
    found = _NUMBER.search(volume)
    stem = _NUMBER.sub("", volume).strip(" :,")
    return stem, None if found is None else _volume(found.group("number"))


def series_stem(title: str) -> str:
    """The part of a title naming its series, as written; empty for none.

    The volume title with its volume number taken off, with whatever follows
    a number inside it. A title that is only a number has no stem, since
    "1999" names no series.
    """
    return _split(title)[0]


def series_place(title: str) -> SeriesPlace | None:
    """Where this title sits in its series; None where it names none."""
    stem, number = _split(title)
    if not stem:
        return None
    return SeriesPlace(stem=comparison_key(stem), number=number)


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
    return tuple(
        album
        for album in _inside(albums, ticked)
        if _filed_under_nobody(album, placeholders)
    )


def artist_filed(
    albums: tuple[Album, ...],
    ticked: tuple[str, ...],
    placeholders: frozenset[str] = frozenset(),
) -> tuple[Album, ...]:
    """The held albums inside the ticks that `series_albums` leaves: those
    filed under somebody. Any of them may still be a compilation. FR-D82."""
    return tuple(
        album
        for album in _inside(albums, ticked)
        if not _filed_under_nobody(album, placeholders)
    )


def _inside(albums: tuple[Album, ...], ticked: tuple[str, ...]) -> tuple[Album, ...]:
    """The held albums inside the ticks; none where nothing is ticked."""
    if not ticked:
        return ()
    return narrowed_to(albums, Narrowing(field=AlbumField.GENRE, wanted=ticked))


def _filed_under_nobody(album: Album, placeholders: frozenset[str]) -> bool:
    """Whether this album's artist is Various Artists or a placeholder."""
    artist = album.identity.album_artist
    return is_various_artists(artist) or comparison_key(artist) in placeholders


def catalogued_compilation(
    title: str, released: tuple[ReleaseGroup, ...]
) -> str | None:
    """The catalogue's title for this held album where it is a compilation.

    FR-D82. `released` is everything the album artist released, as the
    catalogue answered. The album is the release group whose key matches
    its title, kinds aside; else the one in the same numbered place of the
    same series, since "Global Underground #45: Danny Tenaglia - Brooklyn"
    and "Global Underground 045: Danny Tenaglia in Brooklyn" share no key.
    It counts where that group states Compilation or DJ-mix, a hits package
    included: ruled by Oliver on 2026-10-02, since "Back to Mine" is a series
    typed so. None where nothing matches or what matches is no compilation.

    **A plain album of the same title is the album held.** Measured on
    2026-10-02: "Led Zeppelin" and "Metallica" each share their title with a
    compilation of that artist's, which would otherwise send a studio album
    looking for a series.
    """
    key = matched(title).key
    place = series_place(title)
    numbered = place if place is not None and place.number is not None else None
    found: str | None = None
    for group in released:
        compilation = bool(set(group.kinds) & MIX_KINDS)
        if group.match.key == key:
            if not compilation:
                return None
            found = found or group.title
        elif compilation and numbered is not None:
            if series_place(group.title) == numbered:
                found = found or group.title
    return found


def sharing_stem(
    groups: tuple[ReleaseGroup, ...], title: str
) -> tuple[ReleaseGroup, ...]:
    """The volumes of this title's series a stem search answered. FR-D70.

    A volume is a release group of the same stem stating a number. One
    stating none counts only where this title is itself numbered, since it is
    then the series' first volume, as "Global Underground: Unique" is beside
    "Unique #2". Beside an unnumbered title it is merely another album of
    the same name: a search for "The Planets", measured on 2026-10-02,
    answers with every orchestra's recording. FR-D82.

    Kinds cannot tell the two apart: MusicBrainz states none for "Global
    Underground: Unique" and none for Van Halen's "Balance", so the latter
    can still reach the Balance series. A known limit, not a rule.
    """
    wanted = series_place(title)
    if wanted is None:
        return ()
    return tuple(
        group
        for group in groups
        if (place := series_place(group.title)) is not None
        and place.stem == wanted.stem
        and (place.number is not None or wanted.number is not None)
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
