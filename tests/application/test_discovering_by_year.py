"""A run asked for music from some years only. FR-D60 to FR-D63, FR-D65, FR-D66.

The distinction every test here protects: the years decide what a run OFFERS,
never what it learns from. The library is asked about exactly as it always was.
"""

from __future__ import annotations

from dataclasses import replace

from stellody.application.carrying_over import carried_over
from stellody.application.discovering import Discovery
from stellody.application.discovery_ports import SourceFailed, SourceUnavailable
from stellody.application.expanding import Expansion
from stellody.application.values import (
    DiscoveryStage,
    RunOutcome,
    RunReport,
    SourceFailure,
)
from stellody.domain.album import Album
from stellody.domain.discovery import Gaps, LastRun, ReleaseGroup, SimilarArtist
from stellody.domain.release_years import ANY_YEAR, ReleaseYears
from tests.application.discovery_support import (
    ROCK,
    Catalogue,
    Recorder,
    Similarity,
    Waits,
    make_album,
    never,
    nothing,
)

RECENT = ReleaseYears(earliest=2020)
SOURCE = "Kate Bush"
SOURCE_ID = SOURCE.lower()
OLD_ID, NEW_ID = "old-id", "new-id"
OLD = SimilarArtist(name="Old Hand", identifier=OLD_ID)
NEW = SimilarArtist(name="New Voice", identifier=NEW_ID)


def released(title: str, when: str) -> ReleaseGroup:
    """An album first released on this date."""
    return ReleaseGroup(title=title, released=when)


def held_from_1977() -> Album:
    """The source album, released long before any year a test asks about."""
    held = make_album(SOURCE, "The Kick Inside")
    return replace(held, identity=replace(held.identity, date="1977"))


def a_catalogue(**extra: tuple[ReleaseGroup, ...]) -> Catalogue:
    """The source artist's discography, plus one for each candidate named."""
    albums = a_catalogue_albums()
    albums.update(extra)
    return Catalogue(albums=albums)


def a_catalogue_albums() -> dict[str, tuple[ReleaseGroup, ...]]:
    """What the catalogue holds for the source artist and both candidates."""
    return {
        SOURCE_ID: (
            released("The Kick Inside", "1978-01-12"),
            released("Hounds of Love", "1985-07-30"),
            released("Before the Dawn", "2016-11-25"),
            released("Something Recent", "2021"),
            released("Undated Demos", ""),
        ),
        OLD_ID: (released("Their Only Album", "1975"),),
        NEW_ID: (released("Their Debut", "2022"),),
    }


def run(
    catalogue: Catalogue,
    years: ReleaseYears,
    candidates: tuple[SimilarArtist, ...] = (),
    report=nothing,
    cancelled=never,
) -> RunReport:
    """One run over the 1977 album in Rock, for these years."""
    service = Discovery(
        catalogue=catalogue, similarity=Similarity(candidates), pause=Waits()
    )
    return service.run((held_from_1977(),), ROCK, report, cancelled, years=years)


def offered(report: RunReport) -> list[str]:
    """Every album the run offered, by title."""
    return [album.title for gaps in report.gaps for album in gaps.albums]


def candidates_of(report: RunReport) -> list[str]:
    """Every candidate artist the run offered, by name."""
    return [artist.name for gaps in report.gaps for artist in gaps.artists]


class TestTheLibraryStillTeaches:
    def test_an_old_album_leads_to_a_new_one(self) -> None:
        """The regression FR-D60 exists for: source outside, answer inside."""
        catalogue = a_catalogue()
        report = run(catalogue, RECENT)
        assert catalogue.identified == [SOURCE]
        assert offered(report) == ["Something Recent"]

    def test_the_run_records_its_years(self) -> None:
        assert run(a_catalogue(), RECENT).years == RECENT


class TestAlbumsByYear:
    def test_no_years_offers_what_it_always_did(self) -> None:
        report = run(a_catalogue(), ANY_YEAR)
        assert offered(report) == [
            "Hounds of Love",
            "Before the Dawn",
            "Something Recent",
            "Undated Demos",
        ]
        assert report.years == ANY_YEAR

    def test_a_closed_range_keeps_its_boundaries(self) -> None:
        report = run(a_catalogue(), ReleaseYears(1985, 2016))
        assert offered(report) == ["Hounds of Love", "Before the Dawn"]

    def test_an_upper_bound_alone(self) -> None:
        assert offered(run(a_catalogue(), ReleaseYears(latest=1990))) == [
            "Hounds of Love"
        ]

    def test_an_owned_album_is_still_not_offered(self) -> None:
        """The Kick Inside is 1978 and held: inside the years, still not offered."""
        report = run(a_catalogue(), ReleaseYears(latest=1990))
        assert "The Kick Inside" not in offered(report)


class TestCandidatesByYear:
    def test_only_a_candidate_with_something_inside_the_years_is_offered(
        self,
    ) -> None:
        report = run(a_catalogue(), RECENT, (OLD, NEW))
        assert candidates_of(report) == [NEW.name]

    def test_no_years_asks_nothing_about_candidates(self) -> None:
        catalogue = a_catalogue()
        report = run(catalogue, ANY_YEAR, (OLD, NEW))
        assert candidates_of(report) == [OLD.name, NEW.name]
        assert catalogue.albums_asked == [SOURCE_ID]

    def test_each_candidate_is_asked_about_once(self) -> None:
        catalogue = a_catalogue()
        run(catalogue, RECENT, (OLD, NEW, OLD))
        assert catalogue.albums_asked == [SOURCE_ID, OLD_ID, NEW_ID]

    def test_a_candidate_with_no_identifier_cannot_be_shown_to_fit(self) -> None:
        nameless = SimilarArtist(name="Nobody Knows")
        report = run(a_catalogue(), RECENT, (nameless, NEW))
        assert candidates_of(report) == [NEW.name]

    def test_progress_is_reported_as_checking_years(self) -> None:
        seen = Recorder()
        run(a_catalogue(), RECENT, (OLD, NEW), report=seen)
        dating = [p for p in seen.seen if p.stage is DiscoveryStage.DATING]
        assert [(p.artist, p.done, p.total) for p in dating] == [
            (OLD.name, 0, 2),
            (NEW.name, 1, 2),
        ]


class Troubled(Catalogue):
    """A catalogue that meets trouble asking about some candidates' albums."""

    def __init__(self, trouble: Exception, troubled: frozenset[str]) -> None:
        super().__init__(albums=dict(a_catalogue_albums()))
        self._trouble = trouble
        self._troubled = troubled

    def albums_of(self, identifier, wanted=None):
        """The trouble for a troubled candidate; else the ordinary answer."""
        if identifier in self._troubled:
            raise self._trouble
        return super().albums_of(identifier)


# More candidates in a row met with nothing than a connection is given before
# it counts as gone; the threshold is `Silence`'s, so this only needs to pass it.
QUIET = tuple(
    SimilarArtist(name=f"Quiet {n}", identifier=f"quiet-{n}") for n in range(20)
)


class TestWhenACandidateCannotBeDated:
    def test_a_failure_leaves_that_candidate_out_and_the_run_going(self) -> None:
        troubled = Troubled(SourceFailed("broken"), frozenset({OLD_ID}))
        report = run(troubled, RECENT, (OLD, NEW))
        assert report.outcome is RunOutcome.COMPLETED
        assert candidates_of(report) == [NEW.name]

    def test_one_silence_leaves_that_candidate_out_and_the_run_going(self) -> None:
        troubled = Troubled(SourceUnavailable("gone"), frozenset({OLD_ID}))
        report = run(troubled, RECENT, (OLD, NEW))
        assert report.outcome is RunOutcome.COMPLETED
        assert candidates_of(report) == [NEW.name]

    def test_a_run_of_silences_ends_the_run_as_unavailable(self) -> None:
        quiet = frozenset(artist.identifier for artist in QUIET)
        troubled = Troubled(SourceUnavailable("gone"), quiet)
        assert run(troubled, RECENT, QUIET).outcome is RunOutcome.UNAVAILABLE

    def test_a_stop_while_dating_ends_the_run_as_cancelled(self) -> None:
        catalogue = a_catalogue()
        report = run(
            catalogue,
            RECENT,
            (OLD, NEW),
            cancelled=lambda: OLD_ID in catalogue.albums_asked,
        )
        assert report.outcome is RunOutcome.CANCELLED
        assert NEW_ID not in catalogue.albums_asked


class TestExpandingByYear:
    def test_an_expanded_candidate_shows_only_what_is_inside_the_years(
        self,
    ) -> None:
        both = (released("Old One", "1975"), released("New One", "2022"))
        expansion = Expansion(catalogue=a_catalogue(**{NEW_ID: both}), pause=Waits())
        titles = [group.title for group in expansion.releases_of(NEW_ID, years=RECENT)]
        assert titles == ["New One"]


class TestCarryingOverByYear:
    def earlier(self, years: ReleaseYears) -> LastRun:
        """An earlier answer for the source artist, with one candidate."""
        gaps = Gaps(
            artist=SOURCE,
            albums=(released("Old One", "1975"), released("New One", "2022")),
            artists=(NEW,),
        )
        return LastRun(gaps=(gaps,), years=years)

    def failed_run(self, years: ReleaseYears) -> RunReport:
        """A run that could not reach the source artist."""
        return RunReport(
            outcome=RunOutcome.COMPLETED,
            failed=(SourceFailure(artist=SOURCE, reason="refused"),),
            years=years,
        )

    def test_only_albums_inside_this_runs_years_are_carried(self) -> None:
        carried = carried_over(self.failed_run(RECENT), self.earlier(ANY_YEAR))
        assert offered(carried) == ["New One"]

    def test_candidates_carry_only_across_the_same_years(self) -> None:
        other = carried_over(self.failed_run(RECENT), self.earlier(ANY_YEAR))
        same = carried_over(self.failed_run(RECENT), self.earlier(RECENT))
        assert candidates_of(other) == []
        assert candidates_of(same) == [NEW.name]

    def test_no_years_either_side_carries_everything(self) -> None:
        carried = carried_over(self.failed_run(ANY_YEAR), self.earlier(ANY_YEAR))
        assert offered(carried) == ["Old One", "New One"]
        assert candidates_of(carried) == [NEW.name]
