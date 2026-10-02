"""FR-D69 to FR-D72, FR-D75: the other volumes of a compilation, as pure rules.

The titles are the library's own, read from the tags on 2026-09-29.
"""

from __future__ import annotations

import pytest

from stellody.domain.album import Album
from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.domain.discovery_filter import filtered_answer, worth_showing
from stellody.domain.identity import AlbumIdentity
from stellody.domain.matching import ReleaseKind
from stellody.domain.release_years import ReleaseYears
from stellody.domain.series import (
    Series,
    SeriesPlace,
    held_series,
    merged_entries,
    series_albums,
    series_missing,
    series_place,
    series_stem,
    sharing_stem,
    volume_title,
)
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource

HOUSE = ("House",)
ADAPT = "Global Underground: Adapt"
UNIQUE = "Global Underground: Unique"


def held(artist: str, title: str, genre: str = "House") -> Album:
    """A held album, filed under this artist, in this genre."""
    track = Track(
        source=TrackSource(path="a.flac"),
        disc_number=1,
        track_number=1,
        title="A Track",
        artists=(artist,),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )
    return Album(
        identity=AlbumIdentity(album_artist=artist, title=title),
        tracks=(track,),
        genre=genre,
    )


def group(title: str, released: str = "", *kinds: ReleaseKind) -> ReleaseGroup:
    """One release group as a catalogue states it."""
    return ReleaseGroup(title=title, kinds=kinds, released=released)


class TestTheStem:
    """What part of a title names its series, measured against real titles."""

    @pytest.mark.parametrize(
        ("title", "stem", "number"),
        [
            ("Global Underground: Adapt", ADAPT, None),
            ("Global Underground: Adapt #2", ADAPT, 2),
            ("Global Underground: Unique #3", UNIQUE, 3),
            (
                "Global Underground: Select #7 / Unmixed",
                "Global Underground: Select",
                7,
            ),
            (
                "Global Underground: Afterhours 4 - Ibiza / Unmixed",
                "Global Underground: Afterhours",
                4,
            ),
            (
                "Global Underground: Afterhours 9 (Mixed)",
                "Global Underground: Afterhours",
                9,
            ),
            ("Cafe del Mar Vol. 12", "Cafe del Mar", 12),
            ("Hed Kandi No. 3", "Hed Kandi", 3),
            ("Techno 2", "Techno", 2),
            ("Mix2", "Mix2", None),
        ],
    )
    def test_the_stem_and_number(
        self, title: str, stem: str, number: int | None
    ) -> None:
        assert series_stem(title) == stem
        assert series_place(title) == SeriesPlace(stem=stem.casefold(), number=number)

    def test_a_number_written_as_a_word_is_that_number(self) -> None:
        """Measured on 2026-09-30: the catalogue writes "Select Ten"."""
        assert series_place("Global Underground: Select Ten") == series_place(
            "Global Underground: Select #10"
        )

    def test_a_number_word_inside_a_word_is_not_one(self) -> None:
        assert series_place("Someone") == SeriesPlace(stem="someone")

    def test_a_title_that_is_only_a_number_names_no_series(self) -> None:
        assert series_stem("1999") == ""
        assert series_place("1999") is None

    def test_the_volume_title_keeps_the_number(self) -> None:
        assert volume_title("Global Underground: Select #7 / Unmixed") == (
            "Global Underground: Select #7"
        )

    def test_a_series_needs_a_name(self) -> None:
        with pytest.raises(ValueError):
            Series(name=" ")


class TestHeld:
    """FR-D71: held on stem and number; else on the release key."""

    def test_a_suffix_the_catalogue_does_not_write_is_still_held(self) -> None:
        library = held_series(
            (held("Global Underground", "Global Underground: Select #7 / Unmixed"),)
        )
        assert library.holds(group("Global Underground: Select #7"))

    def test_the_release_key_still_holds(self) -> None:
        library = held_series((held("Various Artists", "1999"),))
        assert library.holds(group("1999"))

    def test_another_volume_is_not_held(self) -> None:
        library = held_series((held("Various", ADAPT),))
        assert not library.holds(group(f"{ADAPT} #2"))


class TestMissing:
    """FR-D72: every kind is offered; genres and years still apply."""

    def test_the_volumes_not_held_are_offered_once_in_order(self) -> None:
        library = held_series(
            (
                held("Various Artists", f"{ADAPT} #2"),
                held("Various Artists", f"{ADAPT} #6"),
            )
        )
        entries = tuple(
            group(t) for t in (ADAPT, f"{ADAPT} #2", f"{ADAPT} #3", f"{ADAPT} #3")
        )
        found = series_missing(Series(ADAPT, entries), library, HOUSE)
        assert [g.title for g in found] == [ADAPT, f"{ADAPT} #3"]

    def test_a_compilation_dj_mix_is_offered(self) -> None:
        mix = group(
            f"{ADAPT} #2", "2018-08-31", ReleaseKind.COMPILATION, ReleaseKind.DJ_MIX
        )
        found = series_missing(Series(ADAPT, (mix,)), held_series(()), HOUSE)
        assert found == (mix,)

    def test_the_years_apply(self) -> None:
        old, new = group(ADAPT, "2017-06-30"), group(f"{ADAPT} #6", "2025-08-29")
        years = ReleaseYears(earliest=2020, latest=None)
        found = series_missing(Series(ADAPT, (old, new)), held_series(()), HOUSE, years)
        assert found == (new,)

    def test_the_genres_apply(self) -> None:
        rock = ReleaseGroup(title=ADAPT, genres=("rock",))
        assert series_missing(Series(ADAPT, (rock,)), held_series(()), HOUSE) == ()


class TestOneVolumeOnce:
    """Measured on 2026-09-30: two answers named Select #9, only one with kinds."""

    def test_the_same_volume_from_two_answers_is_kept_once(self) -> None:
        plain = group(f"{ADAPT} #9", "2024-02-21")
        typed = group(f"{ADAPT} #9", "2024-02-21", ReleaseKind.COMPILATION)
        later = (typed, group(f"{ADAPT} #11"), group(f"{ADAPT} #11"))
        found = merged_entries((plain,), later)
        assert [g.title for g in found] == [f"{ADAPT} #9", f"{ADAPT} #11"]

    def test_a_title_naming_no_series_is_kept_once_by_its_release_key(self) -> None:
        assert merged_entries((group("1999"),), (group("1999"),)) == (group("1999"),)

    def test_a_volume_held_as_a_number_is_held_when_offered_as_a_word(self) -> None:
        library = held_series((held("Various Artists", f"{ADAPT} #10"),))
        assert library.holds(group(f"{ADAPT} Ten"))


class TestWhichAlbumsAreSeriesAlbums:
    """A compilation or a placeholder's album, inside the ticks."""

    def test_a_compilation_and_a_placeholder_album(self) -> None:
        va = held("Various", ADAPT)
        gu = held("Global Underground", f"{UNIQUE} #2")
        person = held("Giza Djs", "Something Cool")
        found = series_albums(
            (va, gu, person), HOUSE, frozenset({"global underground"})
        )
        assert found == (va, gu)

    def test_outside_the_ticks_is_not_one(self) -> None:
        assert series_albums((held("Various", ADAPT, "Rock"),), HOUSE) == ()

    def test_nothing_ticked_is_nothing_to_ask_about(self) -> None:
        assert series_albums((held("Various", ADAPT),), ()) == ()


class TestSharingAStem:
    """FR-D70: the fallback keeps exactly the titles sharing a stem."""

    def test_only_the_same_stem_is_kept(self) -> None:
        answered = tuple(
            group(t)
            for t in (
                UNIQUE,
                f"{UNIQUE} #2",
                f"{UNIQUE} #3",
                "Global Underground: Uniqueness",
            )
        )
        found = sharing_stem(answered, f"{UNIQUE} #2")
        assert [g.title for g in found] == [UNIQUE, f"{UNIQUE} #2", f"{UNIQUE} #3"]

    def test_a_title_naming_no_series_shares_nothing(self) -> None:
        assert sharing_stem((group("1999"),), "1999") == ()


class TestOnScreen:
    """FR-D75 and the genre filter's reading of a series."""

    def test_an_empty_heading_is_not_worth_showing(self) -> None:
        empty, full = Gaps(artist="Global Underground"), Gaps("Giza Djs", (group("X"),))
        assert worth_showing((empty, full)) == (full,)

    def test_a_filter_keeps_a_series_held_in_the_picked_genres(self) -> None:
        series = Gaps(artist=UNIQUE, albums=(group(f"{UNIQUE} #3"),), series=True)
        library = (held("Global Underground", f"{UNIQUE} #2"),)
        assert filtered_answer((series,), library, {}, HOUSE).gaps == (series,)

    def test_a_filter_withholds_a_series_held_elsewhere(self) -> None:
        series = Gaps(artist=UNIQUE, albums=(group(f"{UNIQUE} #3"),), series=True)
        library = (held("Global Underground", f"{UNIQUE} #2", "Rock"),)
        assert filtered_answer((series,), library, {}, HOUSE).gaps == ()
