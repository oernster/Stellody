"""FR-D69, FR-D70, FR-D73: a run asks about the other volumes of a compilation.

Driven through a whole run against hand-written catalogues, so what is
asserted is what was offered and which questions were asked.
"""

from __future__ import annotations

import pytest
from discovery_support import (
    Catalogue,
    KeptMemory,
    Recorder,
    Similarity,
    Waits,
    make_album,
    never,
    nothing,
)

from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.application.discovering import Discovery
from stellody.application.discovery_ports import (
    NoSeries,
    RateRefused,
    SourceFailed,
    SourceUnavailable,
)
from stellody.application.values import DiscoveryStage, RunOutcome, RunReport
from stellody.domain.album import Album
from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.domain.including import OWN_ALBUMS, WIDEST, Including
from stellody.domain.matching import ReleaseKind
from stellody.domain.series import Series

HOUSE = ("House",)
ADAPT = "Global Underground: Adapt"
UNIQUE = "Global Underground: Unique"
GU = "Global Underground"
ADAPT_ID = "adapt-series"


class SeriesCatalogue:
    """A series source answering from what it was handed, counting the asks."""

    def __init__(
        self,
        places: dict[str, tuple[str, ...]] | None = None,
        series: dict[str, Series] | None = None,
        titled: tuple[ReleaseGroup, ...] = (),
        raises: Exception | None = None,
    ) -> None:
        self._places = places or {}
        self._series = series or {}
        self._titled = titled
        self._raises = raises
        self.asked: list[tuple[str, str]] = []

    def series_of(self, title: str, wanted: Wanted = always_wanted) -> tuple[str, ...]:
        """The series this title is in, as this fake was told."""
        self.asked.append(("series_of", title))
        if self._raises is not None:
            raise self._raises
        return self._places.get(title, ())

    def series(self, identifier: str, wanted: Wanted = always_wanted) -> Series:
        """One series, as this fake was told."""
        self.asked.append(("series", identifier))
        return self._series[identifier]

    def titled(
        self, stem: str, wanted: Wanted = always_wanted
    ) -> tuple[ReleaseGroup, ...]:
        """What a search for this stem answers."""
        self.asked.append(("titled", stem))
        return self._titled


def adapt(*numbers: int) -> tuple[ReleaseGroup, ...]:
    """The Adapt volumes with these numbers; 1 is the one titled with none."""
    return tuple(
        ReleaseGroup(title=ADAPT if n == 1 else f"{ADAPT} #{n}") for n in numbers
    )


def run_over(
    albums: tuple[Album, ...],
    series: object,
    catalogue: Catalogue | None = None,
    including: Including = WIDEST,
    **more: object,
) -> RunReport:
    """One run over these albums in House, everything taken in by default."""
    service = Discovery(
        catalogue=catalogue or Catalogue(),
        similarity=Similarity(),
        pause=Waits(),
        series=series,
    )
    return service.run(
        albums,
        HOUSE,
        more.get("report", nothing),
        more.get("cancelled", never),
        including=including,
    )


def the_series(report: RunReport) -> dict[str, tuple[str, ...]]:
    """Each series offered, by name, with the titles offered under it."""
    return {
        gaps.artist: tuple(album.title for album in gaps.albums)
        for gaps in report.gaps
        if gaps.series
    }


HELD_ADAPT = (
    make_album("Various Artists", f"{ADAPT} #2", "House"),
    make_album("Various Artists", f"{ADAPT} #6", "House"),
)


def adapt_catalogue() -> SeriesCatalogue:
    """Both held volumes placed in the six-volume Adapt series."""
    return SeriesCatalogue(
        places={f"{ADAPT} #2": (ADAPT_ID,), f"{ADAPT} #6": (ADAPT_ID,)},
        series={ADAPT_ID: Series(ADAPT, adapt(1, 2, 3, 4, 5, 6))},
    )


def test_a_compilation_brings_its_series() -> None:
    """The FR-D69 acceptance: Adapt #2 and #6 held, the other four offered."""
    report = run_over(HELD_ADAPT, adapt_catalogue())
    assert report.outcome is RunOutcome.COMPLETED
    assert the_series(report) == {
        ADAPT: (ADAPT, f"{ADAPT} #3", f"{ADAPT} #4", f"{ADAPT} #5")
    }


def test_one_series_is_asked_about_once() -> None:
    """Adapt #6 is already an entry of the series #2 found, so is not asked."""
    series = adapt_catalogue()
    run_over(HELD_ADAPT, series)
    assert series.asked == [
        ("series_of", f"{ADAPT} #2"),
        ("series", ADAPT_ID),
        ("titled", ADAPT),
    ]


def test_no_series_falls_back_to_the_stem() -> None:
    """The FR-D70 acceptance, reached through the placeholder artist."""
    catalogue = Catalogue(identities={GU: ("gu-tag",)})
    series = SeriesCatalogue(
        titled=(
            ReleaseGroup(title=UNIQUE),
            ReleaseGroup(title=f"{UNIQUE} #2"),
            ReleaseGroup(title=f"{UNIQUE} #3"),
            ReleaseGroup(title="Global Underground: Uniqueness"),
        )
    )
    report = run_over((make_album(GU, f"{UNIQUE} #2", "House"),), series, catalogue)
    assert the_series(report) == {UNIQUE: (UNIQUE, f"{UNIQUE} #3")}
    assert ("titled", UNIQUE) in series.asked


def test_a_person_with_albums_is_no_placeholder() -> None:
    """Somebody the catalogue has albums for is asked about as an artist only."""
    catalogue = Catalogue(albums={"giza djs": (ReleaseGroup(title="Something Cool"),)})
    series = SeriesCatalogue()
    run_over((make_album("Giza Djs", "Something Cool", "House"),), series, catalogue)
    assert series.asked == []


def test_a_name_reaching_several_artists_is_no_placeholder() -> None:
    """Only one identity with nothing released reads as a tag for compilations."""
    catalogue = Catalogue(identities={GU: ("one", "two")})
    series = SeriesCatalogue()
    run_over((make_album(GU, f"{UNIQUE} #2", "House"),), series, catalogue)
    assert series.asked == []


def test_leaving_compilations_out_asks_about_no_series() -> None:
    series = adapt_catalogue()
    run_over((make_album(GU, f"{UNIQUE} #2", "House"),), series, including=OWN_ALBUMS)
    assert series.asked == []


def test_a_refused_series_is_a_failure() -> None:
    """The FR-D73 acceptance: named among the failures; the run completes."""
    series = SeriesCatalogue(raises=RateRefused("busy"))
    report = run_over(HELD_ADAPT[:1], series)
    assert report.outcome is RunOutcome.COMPLETED
    assert [failure.artist for failure in report.failed] == [f"{ADAPT} #2"]


def test_a_failed_series_question_is_a_failure_too() -> None:
    report = run_over(HELD_ADAPT[:1], SeriesCatalogue(raises=SourceFailed("odd")))
    assert [failure.reason for failure in report.failed] == ["odd"]


def test_one_silence_is_a_failure_rather_than_an_ending() -> None:
    report = run_over(HELD_ADAPT[:1], SeriesCatalogue(raises=SourceUnavailable("x")))
    assert report.outcome is RunOutcome.COMPLETED
    assert [failure.artist for failure in report.failed] == [f"{ADAPT} #2"]


def test_a_run_of_silences_ends_the_run() -> None:
    """The connection is one thing; five silences in a row mean it has gone."""
    held = tuple(
        make_album("Various", f"Series {name} #1", "House") for name in "ABCDE"
    )
    report = run_over(held, SeriesCatalogue(raises=SourceUnavailable("gone")))
    assert report.outcome is RunOutcome.UNAVAILABLE


def test_a_stop_during_the_placeholder_check_ends_the_run() -> None:
    """Pressed once the artist half has asked its last question."""
    catalogue, similarity = Catalogue(identities={GU: ("gu-tag",)}), Similarity()
    service = Discovery(
        catalogue=catalogue,
        similarity=similarity,
        pause=Waits(),
        series=SeriesCatalogue(),
    )
    report = service.run(
        (make_album(GU, f"{UNIQUE} #2", "House"),),
        HOUSE,
        nothing,
        lambda: bool(similarity.asked),
        including=WIDEST,
    )
    assert report.outcome is RunOutcome.CANCELLED


def test_a_stop_while_asking_about_a_series_ends_the_run() -> None:
    """Pressed between the question naming the series and the one reading it."""
    series = adapt_catalogue()
    report = run_over(HELD_ADAPT, series, cancelled=lambda: bool(series.asked))
    assert report.outcome is RunOutcome.CANCELLED
    assert series.asked == [("series_of", f"{ADAPT} #2")]


def test_an_artist_with_albums_beside_a_compilation_is_asked_nothing_more() -> None:
    """Only an artist whose answer offered nothing can be a placeholder."""
    catalogue = Catalogue(albums={"giza djs": (ReleaseGroup(title="New One"),)})
    held = (make_album("Giza Djs", "Something Cool", "House"), *HELD_ADAPT)
    run_over(held, adapt_catalogue(), catalogue)
    assert catalogue.identified == ["Giza Djs"]


def test_the_stage_says_how_far_it_has_got() -> None:
    watching = Recorder()
    run_over(HELD_ADAPT, adapt_catalogue(), report=watching)
    named = [progress.artist for progress in watching.seen]
    assert named[-2:] == [f"{ADAPT} #2", f"{ADAPT} #6"]
    # Its own stage, so the first bar does not read as starting over.
    assert {p.stage for p in watching.seen[-2:]} == {DiscoveryStage.SERIES}


def test_nothing_missing_adds_no_heading() -> None:
    series = SeriesCatalogue(
        places={f"{ADAPT} #2": (ADAPT_ID,)},
        series={ADAPT_ID: Series(ADAPT, adapt(2))},
    )
    assert the_series(run_over(HELD_ADAPT[:1], series)) == {}


def test_two_series_of_one_name_are_one_heading() -> None:
    """Two catalogue series sharing a name merge, each entry offered once."""
    series = SeriesCatalogue(
        places={f"{ADAPT} #2": ("a", "b")},
        series={"a": Series(ADAPT, adapt(3)), "b": Series(ADAPT, adapt(3, 4))},
    )
    report = run_over(HELD_ADAPT[:1], series)
    assert the_series(report) == {ADAPT: (f"{ADAPT} #3", f"{ADAPT} #4")}


def test_a_second_run_asks_nothing_it_was_told() -> None:
    """Series answers are remembered with every other catalogue answer."""
    memory, series = KeptMemory(), adapt_catalogue()
    counted = []
    for _ in range(2):
        Discovery(
            catalogue=Catalogue(),
            similarity=Similarity(),
            pause=Waits(),
            recall=memory,
            series=series,
        ).run(HELD_ADAPT, HOUSE, nothing, never, including=WIDEST)
        counted.append(len(series.asked))
    assert counted[0] > 0
    assert counted[1] == counted[0]


def test_a_volume_found_twice_is_offered_once() -> None:
    """Measured on 2026-09-30 from Oliver's run: Select #5 reached the catalogue
    series; Select #10 reached none, since MusicBrainz titles it "Select Ten",
    so its stem search answered too. Both carry one name, so they met under one
    heading and #9 was offered twice: the search states its kinds, the series
    does not. "Select Ten" was offered back although #10 is held."""
    select = "Global Underground: Select"
    series = SeriesCatalogue(
        places={f"{select} #5": ("select",)},
        series={
            "select": Series(
                select,
                (
                    ReleaseGroup(title=f"{select} #9", released="2024-02-21"),
                    ReleaseGroup(title=f"{select} Ten", released="2025-01-30"),
                ),
            )
        },
        titled=(
            ReleaseGroup(
                title=f"{select} #9",
                kinds=(ReleaseKind.COMPILATION,),
                released="2024-02-21",
            ),
            ReleaseGroup(title=f"{select} Ten", released="2025-01-30"),
            ReleaseGroup(title=f"{select} #11", released="2026-01-30"),
        ),
    )
    held = (
        make_album("Global Underground", f"{select} #5", "House"),
        make_album("Various Artists", f"{select} #10", "House"),
    )
    catalogue = Catalogue(identities={"Global Underground": ("gu-tag",)})
    report = run_over(held, series, catalogue)
    assert the_series(report) == {select: (f"{select} #9", f"{select} #11")}


def test_no_series_source_offers_nothing() -> None:
    """The null object answers every question with none."""
    assert the_series(run_over(HELD_ADAPT, NoSeries())) == {}
    with pytest.raises(SourceFailed):
        NoSeries().series("anything")


def test_a_series_heading_is_marked_as_one() -> None:
    report = run_over(HELD_ADAPT, adapt_catalogue())
    heading = next(gaps for gaps in report.gaps if gaps.artist == ADAPT)
    assert heading == Gaps(artist=ADAPT, albums=heading.albums, series=True)
