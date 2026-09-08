"""Running a discovery, with no network anywhere near it.

Every catalogue here is hand written and stands still, so what is being tested
is the order things happen in and what is done when one of them fails, which is
what the application layer is for.
"""

from __future__ import annotations

import pytest
from discovery_support import (
    ROCK,
    Catalogue,
    Similarity,
    Waits,
    make_album,
    never,
    nothing,
)

from stellody.application.asking import (
    RETRY_ATTEMPTS,
    RETRY_PAUSE_SECONDS,
)
from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.application.discovering import (
    SIMILAR_WANTED,
    Discovery,
    held_by_artist,
)
from stellody.application.discovery_ports import SourceFailed, SourceUnavailable
from stellody.application.values import DiscoveryProgress, RunOutcome
from stellody.domain.discovery import ReleaseGroup, SimilarArtist

# How many times the run is allowed to ask whether it should stop before the
# answer becomes yes. Two, so the stop lands inside a wait rather than at the
# boundary before one, which is the case that used to cost seconds.
SLICES_BEFORE_STOP = 2


def make_run(
    catalogue: Catalogue | None = None, similarity: Similarity | None = None
) -> tuple[Discovery, Catalogue, Similarity, Waits]:
    """A service wired to fakes, with each fake handed back to be read."""
    source = catalogue or Catalogue()
    like = similarity or Similarity()
    waits = Waits()
    return (
        Discovery(catalogue=source, similarity=like, pause=waits),
        source,
        like,
        waits,
    )


def test_sources_read_the_resolved_genre() -> None:
    """The genre a listener sees, never the tag underneath it."""
    run, catalogue, _, _ = make_run()
    albums = (make_album("Finley Quaye", "Maverick A Strike", "Reggae"),)
    run.run(albums, ("Reggae",), nothing, never)
    assert catalogue.identified == ["Finley Quaye"]


def test_no_sources_makes_no_request() -> None:
    """Ticking a genre nothing in the library carries asks nobody anything."""
    run, catalogue, similarity, _ = make_run()
    albums = (make_album("AC/DC", "Back In Black", "Rock"),)
    report = run.run(albums, ("Jazz",), nothing, never)
    assert report.outcome is RunOutcome.NOTHING_TO_ASK
    assert not report.is_writable
    assert catalogue.identified == []
    assert similarity.asked == []


def test_identity_is_requested_once() -> None:
    """One artist is one question, however many albums they are held under."""
    run, catalogue, _, _ = make_run()
    albums = (
        make_album("The Script", "The Script"),
        make_album("The Script", "Science & Faith"),
    )
    run.run(albums, ROCK, nothing, never)
    assert catalogue.identified == ["The Script"]


def test_a_completed_run_carries_what_it_was_asked_to_look_in() -> None:
    """The genres travel on the report, so the file can be written from it.

    Asked for on 2026-09-08. The results screen says what the run looked in,
    which it can only do if the answer knows: reading the ticks from whoever
    started the run instead would be a second source to disagree with the file.
    """
    run, _, _, _ = make_run(Catalogue(identities={"Nobody": ()}))
    report = run.run((make_album("Nobody", "A Record"),), ROCK, nothing, never)
    assert report.outcome is RunOutcome.COMPLETED
    assert report.ticked == ROCK


def test_a_run_that_ends_early_claims_no_genres() -> None:
    """Only a completed run is written, so only one needs to carry them.

    The unwanted sibling of the test above: an ending that writes nothing must
    not look like a run that looked somewhere and found nothing there.
    """
    run, _, _, _ = make_run(Catalogue(identities={}))
    report = run.run(
        (make_album("Nobody", "A Record"),), ("Nothing Held",), nothing, never
    )
    assert report.outcome is RunOutcome.NOTHING_TO_ASK
    assert report.ticked == ()


def test_unknown_artist_is_recorded() -> None:
    """A name no catalogue knows is reported rather than passed over."""
    run, _, _, _ = make_run(Catalogue(identities={"Nobody": ()}))
    report = run.run((make_album("Nobody", "A Record"),), ROCK, nothing, never)
    assert report.unresolved == ("Nobody",)
    assert report.outcome is RunOutcome.COMPLETED


def test_ambiguous_name_is_reported() -> None:
    """Two bands of one name is an answer; guessing files one wrongly."""
    catalogue = Catalogue(identities={"Nirvana": ("us-band", "uk-band")})
    run, source, _, _ = make_run(catalogue)
    report = run.run((make_album("Nirvana", "Bleach"),), ROCK, nothing, never)
    assert report.ambiguous[0].artist == "Nirvana"
    assert report.ambiguous[0].identifiers == ("us-band", "uk-band")
    assert source.albums_asked == []


def test_albums_are_requested_with_genres() -> None:
    """The albums question is asked of the artist that was identified."""
    catalogue = Catalogue(
        identities={"U2": ("u2-id",)},
        albums={"u2-id": (ReleaseGroup(title="Achtung Baby", genres=("Rock",)),)},
    )
    run, source, _, _ = make_run(catalogue)
    report = run.run((make_album("U2", "The Joshua Tree"),), ROCK, nothing, never)
    assert source.albums_asked == ["u2-id"]
    assert [group.title for group in report.gaps[0].albums] == ["Achtung Baby"]


def test_similar_artists_are_requested() -> None:
    """Ten of them, which is the figure the plan settled on."""
    run, _, similarity, _ = make_run(Catalogue(identities={"U2": ("u2-id",)}))
    run.run((make_album("U2", "The Joshua Tree"),), ROCK, nothing, never)
    assert similarity.asked == [("u2-id", SIMILAR_WANTED)]


def test_progress_names_the_artist_and_counts_the_rest() -> None:
    """Eleven minutes of spinner is indistinguishable from a hang."""
    seen: list[DiscoveryProgress] = []
    run, _, _, _ = make_run()
    albums = (make_album("One", "A"), make_album("Two", "B"))
    run.run(albums, ROCK, seen.append, never)
    assert [(step.artist, step.done, step.total) for step in seen] == [
        ("One", 0, 2),
        ("Two", 1, 2),
    ]


def test_no_network_stops_the_run() -> None:
    """Continuing is many slow ways of saying the same thing once."""
    catalogue = Catalogue(raises=SourceUnavailable("nothing answered"))
    run, source, _, _ = make_run(catalogue)
    albums = (make_album("One", "A"), make_album("Two", "B"))
    report = run.run(albums, ROCK, nothing, never)
    assert report.outcome is RunOutcome.UNAVAILABLE
    assert not report.is_writable
    assert source.identified == ["One"]


def test_rate_refusal_is_retried() -> None:
    """A refusal is the catalogue asking for patience, not reporting absence."""
    catalogue = Catalogue(identities={"U2": ("u2-id",)}, refusals=1)
    run, source, _, waits = make_run(catalogue)
    report = run.run((make_album("U2", "The Joshua Tree"),), ROCK, nothing, never)
    assert source.identified == ["U2", "U2"]
    # The total owed to the service, not the number of naps it was taken in:
    # the wait is sliced so a stop can be felt part way through it, which is
    # this run's business rather than the catalogue's.
    assert sum(waits.waited) == pytest.approx(RETRY_PAUSE_SECONDS)
    assert report.outcome is RunOutcome.COMPLETED


def test_a_run_does_not_lose_an_artist_to_three_refusals() -> None:
    """The defect Oliver reported on 2026-09-08: a run over two genres came
    back holding one source artist out of seven, the other six each recorded as
    refused after three asks. Its own record showed 21 refusals in 27 requests,
    while the one artist asked with more patience answered on its fourth ask.

    Stated as the count rather than as the constant, for the reason the
    expansion suite states its own.
    """
    catalogue = Catalogue(identities={"U2": ("u2-id",)}, refusals=3)
    run, source, _, _ = make_run(catalogue)
    report = run.run((make_album("U2", "The Joshua Tree"),), ROCK, nothing, never)
    assert report.failed == (), "the artist was kept rather than given up on"
    assert len(source.identified) == 4


def test_a_refusal_that_never_relents_becomes_a_failure() -> None:
    """Patience has an end; what happens then is written down."""
    catalogue = Catalogue(refusals=RETRY_ATTEMPTS)
    run, _, _, waits = make_run(catalogue)
    report = run.run((make_album("U2", "A"),), ROCK, nothing, never)
    assert [failure.artist for failure in report.failed] == ["U2"]
    owed = RETRY_PAUSE_SECONDS * sum(range(1, RETRY_ATTEMPTS))
    assert sum(waits.waited) == pytest.approx(owed)


def test_other_errors_do_not_stop_the_run() -> None:
    """One artist nobody could answer about is not the end of the library."""

    class Awkward(Catalogue):
        """Fails on the first artist and answers about the second."""

        def identify(
            self, name: str, wanted: Wanted = always_wanted
        ) -> tuple[str, ...]:
            """Raise for One; behave for anybody else."""
            if name == "One":
                raise SourceFailed("the catalogue fell over")
            return super().identify(name, wanted)

    run, _, _, _ = make_run(Awkward())
    albums = (make_album("One", "A"), make_album("Two", "B"))
    report = run.run(albums, ROCK, nothing, never)
    assert [failure.reason for failure in report.failed] == ["the catalogue fell over"]
    assert [gaps.artist for gaps in report.gaps] == ["Two"]
    assert report.outcome is RunOutcome.COMPLETED


def test_a_candidate_artist_is_asked_about_once() -> None:
    """The expensive part of a run; the well-connected recur constantly."""
    shared = SimilarArtist(name="Talk Talk", identifier="talk-talk")
    catalogue = Catalogue(genres={"talk-talk": ("Rock",)})
    run, source, _, _ = make_run(catalogue, Similarity((shared,)))
    albums = (make_album("One", "A"), make_album("Two", "B"))
    run.run(albums, ROCK, nothing, never)
    assert source.genres_asked == ["talk-talk"]


def test_a_candidate_outside_the_ticks_is_dropped() -> None:
    """The filter has to work at the end a listener sees, not only the start."""
    catalogue = Catalogue(genres={"comic": ("Comedy",), "rocker": ("Rock",)})
    offered = (
        SimilarArtist(name="A Comedian", identifier="comic"),
        SimilarArtist(name="A Band", identifier="rocker"),
    )
    run, _, _, _ = make_run(catalogue, Similarity(offered))
    report = run.run((make_album("One", "A"),), ROCK, nothing, never)
    assert [artist.name for artist in report.gaps[0].artists] == ["A Band"]


def test_a_candidate_nobody_can_be_asked_about_is_kept() -> None:
    """No identifier is a candidate the catalogue could not describe."""
    offered = (SimilarArtist(name="Someone"),)
    run, source, _, _ = make_run(similarity=Similarity(offered))
    report = run.run((make_album("One", "A"),), ROCK, nothing, never)
    assert [artist.name for artist in report.gaps[0].artists] == ["Someone"]
    assert source.genres_asked == []


def test_a_candidate_whose_genres_cannot_be_read_is_kept() -> None:
    """A failure to describe somebody is not evidence against them."""

    class Silent(Catalogue):
        """Answers about artists and falls over on genres."""

        def genres_of(
            self, identifier: str, wanted: Wanted = always_wanted
        ) -> tuple[str, ...]:
            """Always fails, which must not lose the candidate."""
            raise SourceFailed("no genres today")

    offered = (SimilarArtist(name="Someone", identifier="someone"),)
    run, _, _, _ = make_run(Silent(), Similarity(offered))
    report = run.run((make_album("One", "A"),), ROCK, nothing, never)
    assert [artist.name for artist in report.gaps[0].artists] == ["Someone"]


def test_what_each_artist_is_already_held_to_have() -> None:
    """Built once for a run, since an album reads the same way every time."""
    albums = (make_album("U2", "The Joshua Tree"), make_album("U2", "Achtung Baby"))
    held = held_by_artist(albums)
    assert len(held["U2"]) == 2
