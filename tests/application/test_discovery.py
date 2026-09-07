"""Running a discovery, with no network anywhere near it.

Every catalogue here is hand written and stands still, so what is being tested
is the order things happen in and what is done when one of them fails, which is
what the application layer is for.
"""

from __future__ import annotations

from discovery_support import (
    ROCK,
    Catalogue,
    Similarity,
    Waits,
    make_album,
    never,
    nothing,
)

from stellody.application.discovering import (
    RETRY_ATTEMPTS,
    SIMILAR_WANTED,
    Discovery,
    SourceFailed,
    SourceUnavailable,
    held_by_artist,
)
from stellody.application.values import DiscoveryProgress, RunOutcome
from stellody.domain.discovery import ReleaseGroup, SimilarArtist


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


def test_cancel_stops_before_the_next_request() -> None:
    """Between requests rather than mid-flight, so nothing is half-written."""
    run, catalogue, _, _ = make_run()
    report = run.run((make_album("One", "A"),), ROCK, nothing, lambda: True)
    assert report.outcome is RunOutcome.CANCELLED
    assert not report.is_writable
    assert catalogue.identified == []


def test_closing_stops_the_run() -> None:
    """A close is a cancel expressed differently; it gets the same answer."""
    asked: list[bool] = []

    def once_around() -> bool:
        """False the first time, then True: the window closes mid-run."""
        asked.append(True)
        return len(asked) > 1

    run, catalogue, _, _ = make_run()
    albums = (make_album("One", "A"), make_album("Two", "B"))
    report = run.run(albums, ROCK, nothing, once_around)
    assert report.outcome is RunOutcome.CANCELLED
    assert catalogue.identified == ["One"]


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
    assert len(waits.waited) == 1
    assert report.outcome is RunOutcome.COMPLETED


def test_a_refusal_that_never_relents_becomes_a_failure() -> None:
    """Patience has an end; what happens then is written down."""
    catalogue = Catalogue(refusals=RETRY_ATTEMPTS)
    run, _, _, waits = make_run(catalogue)
    report = run.run((make_album("U2", "A"),), ROCK, nothing, never)
    assert [failure.artist for failure in report.failed] == ["U2"]
    assert len(waits.waited) == RETRY_ATTEMPTS - 1


def test_other_errors_do_not_stop_the_run() -> None:
    """One artist nobody could answer about is not the end of the library."""

    class Awkward(Catalogue):
        """Fails on the first artist and answers about the second."""

        def identify(self, name: str) -> tuple[str, ...]:
            """Raise for One; behave for anybody else."""
            if name == "One":
                raise SourceFailed("the catalogue fell over")
            return super().identify(name)

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

        def genres_of(self, identifier: str) -> tuple[str, ...]:
            """Always fails, which must not lose the candidate."""
            raise SourceFailed("no genres today")

    offered = (SimilarArtist(name="Someone", identifier="someone"),)
    run, _, _, _ = make_run(Silent(), Similarity(offered))
    report = run.run((make_album("One", "A"),), ROCK, nothing, never)
    assert [artist.name for artist in report.gaps[0].artists] == ["Someone"]


def test_cancelling_while_candidates_are_narrowed_writes_nothing() -> None:
    """The second phase is the long one, so it has to be stoppable too."""
    steps: list[bool] = []

    def after_the_first_artist() -> bool:
        """False while artists are gathered, True once narrowing starts."""
        steps.append(True)
        return len(steps) > 1

    offered = (SimilarArtist(name="Someone", identifier="someone"),)
    run, _, _, _ = make_run(similarity=Similarity(offered))
    report = run.run((make_album("One", "A"),), ROCK, nothing, after_the_first_artist)
    assert report.outcome is RunOutcome.CANCELLED


def test_what_each_artist_is_already_held_to_have() -> None:
    """Built once for a run, since an album reads the same way every time."""
    albums = (make_album("U2", "The Joshua Tree"), make_album("U2", "Achtung Baby"))
    held = held_by_artist(albums)
    assert len(held["U2"]) == 2
