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
    MEMORY_LIFE_S,
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
# A fixed moment to stand answers at, so nothing here waits for a clock.
NOW = 1_700_000_000.0


def _now() -> float:
    """The moment every test here is standing at."""
    return NOW


def _stamped(kept: Recollection, *questions: str) -> Recollection:
    """The same recollection, with these answers written down just now."""
    for question in questions:
        kept.written_at[question] = NOW
    return kept


class Keeping:
    """A catalogue memory that keeps a recollection where a file would."""

    def __init__(self, kept: Recollection | None = None) -> None:
        self.kept = kept if kept is not None else Recollection()
        self.written = 0
        self.noted: list[tuple[str, str, object, float]] = []

    def remembered(self) -> Recollection:
        """What is known so far."""
        return self.kept

    def note(self, kind: str, key: str, answer: object, when: float) -> None:
        """Record one answer as it arrives, in the order they arrived."""
        self.noted.append((kind, key, answer, when))

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
        kept = _stamped(Recollection(identifiers={"U2": ("u2-id",)}), "identifiers:U2")
        catalogue = Catalogue()
        found = RememberingCatalogue(catalogue, kept, _now).identify("U2")
        assert found == ("u2-id",)
        assert catalogue.identified == []

    def test_an_identity_not_known_is_asked_for_and_kept(self) -> None:
        kept = Recollection()
        catalogue = Catalogue(identities={"U2": ("u2-id",)})
        assert RememberingCatalogue(catalogue, kept).identify("U2") == ("u2-id",)
        assert catalogue.identified == ["U2"]
        assert kept.identifiers == {"U2": ("u2-id",)}

    def test_albums_already_known_are_not_asked_for(self) -> None:
        held = (ReleaseGroup(title="Pop"),)
        kept = _stamped(Recollection(albums={WOLF: held}), f"albums:{WOLF}")
        catalogue = Catalogue()
        assert RememberingCatalogue(catalogue, kept, _now).albums_of(WOLF) == held
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
        kept = _stamped(
            Recollection(similar={similar_key(WOLF, 5): held}),
            f"similar:{similar_key(WOLF, 5)}",
        )
        similarity = Similarity()
        found = RememberingSimilarity(similarity, kept, _now).similar_to(WOLF, 5)
        assert found == held
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

    def test_a_run_that_failed_at_nothing_keeps_its_own_answer(self) -> None:
        report = RunReport(outcome=RunOutcome.COMPLETED, gaps=(Gaps(artist="U2"),))
        carried = carried_over(report, (Gaps(artist="Elbow"),))
        assert carried.gaps == (Gaps(artist="U2"),), "and takes nothing else on"

    def test_the_artists_come_out_in_one_order_however_they_went_in(self) -> None:
        """An artist carried over would otherwise sit where the carrying put
        it, while the same artist answered for directly sits in library order.
        The same content in two orders is two different screens."""
        report = RunReport(
            outcome=RunOutcome.COMPLETED,
            gaps=(Gaps(artist="Wire"), Gaps(artist="Aztec Camera")),
            failed=(SourceFailure(artist="Móż", reason="refused"),),
        )
        carried = carried_over(report, (Gaps(artist="Móż"),))
        assert [gaps.artist for gaps in carried.gaps] == [
            "Aztec Camera",
            "Móż",
            "Wire",
        ]

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


class TestHowLongAnAnswerStands:
    """Oliver's own statement of what is wanted, on 2026-09-08: the same run
    over the same library should differ over days or weeks, because the
    catalogues themselves change; it should not differ over five minutes,
    because they do not.
    """

    def test_an_answer_from_this_month_is_used_rather_than_asked_for(self) -> None:
        kept = _stamped(Recollection(albums={WOLF: ()}), f"albums:{WOLF}")
        catalogue = Catalogue()
        RememberingCatalogue(catalogue, kept, _now).albums_of(WOLF)
        assert catalogue.albums_asked == []

    def test_an_answer_older_than_that_is_asked_about_again(self) -> None:
        """Otherwise a record released since would never be seen."""
        kept = Recollection(albums={WOLF: ()})
        kept.written_at[f"albums:{WOLF}"] = NOW - MEMORY_LIFE_S - 1
        catalogue = Catalogue(albums={WOLF: (ReleaseGroup(title="New One"),)})
        found = RememberingCatalogue(catalogue, kept, _now).albums_of(WOLF)
        assert [group.title for group in found] == ["New One"]
        assert catalogue.albums_asked == [WOLF]

    def test_asking_again_starts_the_month_over(self) -> None:
        kept = Recollection(albums={WOLF: ()})
        kept.written_at[f"albums:{WOLF}"] = NOW - MEMORY_LIFE_S - 1
        RememberingCatalogue(Catalogue(), kept, _now).albums_of(WOLF)
        assert kept.written_at[f"albums:{WOLF}"] == NOW

    def test_an_answer_with_no_age_at_all_is_asked_about_again(self) -> None:
        """Written by a Stellody that kept no ages, so its age is unknown."""
        kept = Recollection(identifiers={"U2": ("u2-id",)})
        catalogue = Catalogue(identities={"U2": ("u2-id",)})
        RememberingCatalogue(catalogue, kept, _now).identify("U2")
        assert catalogue.identified == ["U2"]

    def test_similar_artists_age_the_same_way(self) -> None:
        kept = Recollection(similar={similar_key(WOLF, 5): ()})
        kept.written_at[f"similar:{similar_key(WOLF, 5)}"] = NOW - MEMORY_LIFE_S - 1
        similarity = Similarity()
        RememberingSimilarity(similarity, kept, _now).similar_to(WOLF, 5)
        assert similarity.asked == [(WOLF, 5)]

    def test_a_month_is_what_it_stands_for(self) -> None:
        """Stated rather than read back off the constant, since a test that
        reads it agrees with every value it could hold."""
        assert MEMORY_LIFE_S == 30 * 86400


class TestAnAnswerIsKeptTheMomentItArrives:
    """Reported by Oliver on 2026-09-09, after an overnight run.

    Everything above keeps a recollection in hand and hands it over when the
    run ends. A run whose process dies never ends, so each answer says so as
    it arrives as well; what happens to it then belongs to whoever is keeping
    it, which is why these ask only that it was said.
    """

    def test_an_identity_is_noted_as_it_is_answered(self) -> None:
        keeper = Keeping()
        catalogue = Catalogue(identities={"U2": ("u2-id",)})
        RememberingCatalogue(catalogue, keeper.kept, _now, keeper).identify("U2")
        assert keeper.noted == [("identifiers", "U2", ("u2-id",), NOW)]

    def test_an_albums_answer_is_noted_as_it_is_answered(self) -> None:
        keeper = Keeping()
        held = (ReleaseGroup(title="Moanin'"),)
        catalogue = Catalogue(albums={WOLF: held})
        RememberingCatalogue(catalogue, keeper.kept, _now, keeper).albums_of(WOLF)
        assert keeper.noted == [("albums", WOLF, held, NOW)]

    def test_a_similarity_answer_is_noted_as_it_is_answered(self) -> None:
        keeper = Keeping()
        RememberingSimilarity(Similarity(), keeper.kept, _now, keeper).similar_to(
            WOLF, 5
        )
        assert keeper.noted == [("similar", similar_key(WOLF, 5), (), NOW)]

    def test_an_answer_that_came_from_memory_is_not_noted_again(self) -> None:
        """It is already written down; noting it would say the same thing."""
        keeper = Keeping(
            _stamped(Recollection(identifiers={"U2": ("u2-id",)}), "identifiers:U2")
        )
        RememberingCatalogue(Catalogue(), keeper.kept, _now, keeper).identify("U2")
        assert keeper.noted == []

    def test_a_run_notes_every_answer_it_pays_for(self) -> None:
        """End to end: the run hands its memory down rather than holding it."""
        keeper = Keeping()
        catalogue = Catalogue(identities={"U2": ("u2-id",)})
        _run(keeper, catalogue, Similarity()).run(
            (make_album("U2", "The Joshua Tree"),), ROCK, nothing, never
        )
        assert [kind for kind, _key, _answer, _when in keeper.noted] == [
            "identifiers",
            "albums",
            "similar",
        ]

    def test_a_run_with_nowhere_to_keep_anything_still_runs(self) -> None:
        """The null memory answers `note` by dropping it, like the rest."""
        NothingKept().note("identifiers", "U2", ("u2-id",), NOW)
