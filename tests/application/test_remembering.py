"""A run answers the same way twice, because it asks nothing twice.

Reported by Oliver on 2026-09-08, repeatedly and in the strongest terms: two
runs over the same library gave different answers. Sometimes an artist was
there, sometimes not; sometimes an artist's records could be looked up,
sometimes not.

The reason was that a run remembered nothing, so every answer was a property
of how MusicBrainz happened to feel that minute rather than of the library.
Measured that day from a real run: 27 requests in 65 seconds, 21 of them
refused; seven source artists became one.

So what is held here is the promise: given the same library and the same
memory, a second run asks nothing and answers exactly as the first did.
"""

from __future__ import annotations

from discovery_support import (
    Catalogue,
    Memory,
    Similarity,
    Waits,
    make_album,
    never,
    nothing,
)

from stellody.application.carrying_over import carried_over
from stellody.application.discovering import Discovery
from stellody.application.remembering import (
    NothingKept,
    Recollection,
    RememberingCatalogue,
    RememberingSimilarity,
    similar_key,
)
from stellody.application.values import RunOutcome, RunReport, SourceFailure
from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist

ROCK = ("Rock",)
WOLF = "wolf-id"


class Keeping:
    """A catalogue memory that keeps a recollection where a file would."""

    def __init__(self, kept: Recollection | None = None) -> None:
        self.kept = kept if kept is not None else Recollection()
        self.written = 0

    def remembered(self) -> Recollection:
        """What is known so far."""
        return self.kept

    def remember(self, kept: Recollection) -> None:
        """Hold on to it, counting how often it was handed over."""
        self.kept = kept
        self.written += 1


def _run(recall: Keeping, catalogue: Catalogue, similarity: Similarity) -> Discovery:
    """A run over these fakes, remembering into this."""
    return Discovery(
        catalogue=catalogue,
        similarity=similarity,
        pause=Waits(),
        memory=Memory(),
        recall=recall,
    )


class TestTwoRunsOverOneLibrary:
    def test_the_second_run_asks_the_catalogues_nothing(self) -> None:
        """The whole promise, in one assertion."""
        recall, catalogue, similarity = Keeping(), Catalogue(), Similarity()
        albums = (make_album("U2", "The Joshua Tree"),)
        first = _run(recall, catalogue, similarity).run(albums, ROCK, nothing, never)
        asked_once = list(catalogue.identified)
        second = _run(recall, catalogue, similarity).run(albums, ROCK, nothing, never)
        assert catalogue.identified == asked_once, "it asked nothing the second time"
        assert second.gaps == first.gaps, "and answered exactly as before"

    def test_what_was_learned_is_kept_however_the_run_ended(self) -> None:
        """An answer already paid for is worth keeping whatever became of the
        run it arrived during."""
        recall = Keeping()
        albums = (make_album("U2", "The Joshua Tree"),)
        _run(recall, Catalogue(), Similarity()).run(albums, ROCK, nothing, never)
        assert recall.written == 1
        assert recall.kept.identifiers, "the identity was written down"


class TestAskingOnlyWhatIsUnknown:
    def test_an_identity_already_known_is_not_asked_for(self) -> None:
        kept = Recollection(identifiers={"U2": ("u2-id",)})
        catalogue = Catalogue()
        assert RememberingCatalogue(catalogue, kept).identify("U2") == ("u2-id",)
        assert catalogue.identified == []

    def test_an_identity_not_known_is_asked_for_and_kept(self) -> None:
        kept = Recollection()
        catalogue = Catalogue(identities={"U2": ("u2-id",)})
        assert RememberingCatalogue(catalogue, kept).identify("U2") == ("u2-id",)
        assert catalogue.identified == ["U2"]
        assert kept.identifiers == {"U2": ("u2-id",)}

    def test_albums_already_known_are_not_asked_for(self) -> None:
        held = (ReleaseGroup(title="Pop"),)
        kept = Recollection(albums={WOLF: held})
        catalogue = Catalogue()
        assert RememberingCatalogue(catalogue, kept).albums_of(WOLF) == held
        assert catalogue.albums_asked == []

    def test_albums_not_known_are_asked_for_and_kept(self) -> None:
        kept = Recollection()
        catalogue = Catalogue(albums={WOLF: (ReleaseGroup(title="Pop"),)})
        found = RememberingCatalogue(catalogue, kept).albums_of(WOLF)
        assert [group.title for group in found] == ["Pop"]
        assert kept.albums[WOLF] == found

    def test_genres_are_asked_straight_through(self) -> None:
        """The one question a second memory already keeps, so this keeps none."""
        kept = Recollection()
        catalogue = Catalogue(genres={WOLF: ("Blues",)})
        assert RememberingCatalogue(catalogue, kept).genres_of(WOLF) == ("Blues",)

    def test_similar_artists_already_known_are_not_asked_for(self) -> None:
        held = (SimilarArtist(name="Muddy Waters", identifier="mw"),)
        kept = Recollection(similar={similar_key(WOLF, 5): held})
        similarity = Similarity()
        assert RememberingSimilarity(similarity, kept).similar_to(WOLF, 5) == held
        assert similarity.asked == []

    def test_similar_artists_not_known_are_asked_for_and_kept(self) -> None:
        kept = Recollection()
        similarity = Similarity(artists=(SimilarArtist(name="B", identifier="b"),))
        found = RememberingSimilarity(similarity, kept).similar_to(WOLF, 5)
        assert kept.similar[similar_key(WOLF, 5)] == found

    def test_a_different_count_is_a_different_question(self) -> None:
        """Answered with ten, this cannot then answer a request for fifty."""
        assert similar_key(WOLF, 10) != similar_key(WOLF, 50)


class TestAMemoryThatKeepsNothing:
    def test_it_recalls_nothing(self) -> None:
        assert NothingKept().remembered() == Recollection()

    def test_it_takes_what_it_is_given_and_drops_it(self) -> None:
        memory = NothingKept()
        memory.remember(Recollection(identifiers={"U2": ("u2-id",)}))
        assert memory.remembered() == Recollection()


class TestCarryingAnAnswerOver:
    """A run may add to what is known and may correct it. It may not take it
    away because a service said no."""

    def test_a_run_that_failed_at_nothing_is_left_alone(self) -> None:
        report = RunReport(outcome=RunOutcome.COMPLETED, gaps=(Gaps(artist="U2"),))
        assert carried_over(report, (Gaps(artist="Elbow"),)) is report

    def test_an_artist_that_failed_keeps_what_was_known_about_it(self) -> None:
        known = Gaps(artist="U2", albums=(ReleaseGroup(title="Pop"),))
        report = RunReport(
            outcome=RunOutcome.COMPLETED,
            gaps=(Gaps(artist="Elbow"),),
            failed=(SourceFailure(artist="U2", reason="refused"),),
        )
        carried = carried_over(report, (known,))
        assert carried.gaps == (Gaps(artist="Elbow"), known)
        assert carried.failed == (), "there is nothing left to report"

    def test_an_artist_nobody_ever_answered_about_stays_a_failure(self) -> None:
        report = RunReport(
            outcome=RunOutcome.COMPLETED,
            failed=(SourceFailure(artist="U2", reason="refused"),),
        )
        carried = carried_over(report, ())
        assert carried.gaps == ()
        assert [entry.artist for entry in carried.failed] == ["U2"]
