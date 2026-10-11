"""Which artists a run will have to ask about, read off memory beforehand.

The time a run says it has left is measured from these artists alone, since an
answer read from memory costs nothing worth timing. Reported by Oliver on
2026-10-11: a run said less than a minute three to five minutes in, because
remembered artists finishing at once made the network's pace look quick.
"""

from __future__ import annotations

from discovery_support import (
    Catalogue,
    KeptMemory,
    Memory,
    Recorder,
    Similarity,
    Waits,
    make_album,
    never,
)

from stellody.application.artist_stage import SIMILAR_WANTED
from stellody.application.discovering import Discovery
from stellody.application.foreseeing import Foreseen
from stellody.application.remembering import (
    ALBUMS,
    IDENTIFIERS,
    MEMORY_LIFE_S,
    SIMILAR,
    Recollection,
    similar_key,
    stamp_for,
)
from stellody.domain.discovery import ReleaseGroup

ROCK = ("Rock",)
WOLF = "wolf-id"
NOW = 1_700_000_000.0


def _now() -> float:
    return NOW


def _known(identifiers: tuple[str, ...], *, albums=True, similar=True) -> Foreseen:
    """A memory that already knows who Wolf is, plus whichever answers asked."""
    kept = Recollection()
    kept.identifiers["Wolf"] = identifiers
    kept.written_at[stamp_for(IDENTIFIERS, "Wolf")] = NOW
    if albums:
        kept.albums[WOLF] = (ReleaseGroup(title="Howl"),)
        kept.written_at[stamp_for(ALBUMS, WOLF)] = NOW
    if similar:
        key = similar_key(WOLF, SIMILAR_WANTED)
        kept.similar[key] = ()
        kept.written_at[stamp_for(SIMILAR, key)] = NOW
    return Foreseen(kept, _now)


class TestOneArtist:
    def test_a_name_never_asked_about_goes_to_the_network(self) -> None:
        assert Foreseen(Recollection(), _now)("Wolf")

    def test_an_artist_answered_in_full_does_not(self) -> None:
        assert not _known((WOLF,))("Wolf")

    def test_a_missing_answer_about_releases_still_asks(self) -> None:
        assert _known((WOLF,), albums=False)("Wolf")

    def test_a_missing_answer_about_similar_artists_still_asks(self) -> None:
        assert _known((WOLF,), similar=False)("Wolf")

    def test_a_name_known_to_reach_nobody_asks_nothing_more(self) -> None:
        assert not _known(())("Wolf")

    def test_a_name_reaching_several_artists_counts_as_asked(self) -> None:
        """Settling it asks questions of its own; erring long beats short."""
        assert _known((WOLF, "other-id"))("Wolf")

    def test_an_answer_past_its_life_is_asked_again(self) -> None:
        aged = _known((WOLF,))
        later = Foreseen(aged.kept, lambda: NOW + MEMORY_LIFE_S + 1)
        assert later("Wolf")


class TestARun:
    def _run(self, recall: KeptMemory, artists: tuple[str, ...]) -> Recorder:
        seen = Recorder()
        Discovery(
            catalogue=Catalogue(),
            similarity=Similarity(),
            pause=Waits(),
            memory=Memory(),
            recall=recall,
        ).run(
            tuple(make_album(artist, f"{artist} album") for artist in artists),
            ROCK,
            seen,
            never,
        )
        return seen

    def test_with_nothing_remembered_every_artist_is_timed(self) -> None:
        seen = self._run(KeptMemory(), ("Ash", "Birch", "Cedar"))
        looking = [one for one in seen.seen if one.asked is not None]
        assert looking[0].asked == (0, 3)

    def test_only_the_artists_memory_cannot_answer_are_timed(self) -> None:
        """Two remembered, two new: the stage times the two new ones only."""
        recall = KeptMemory()
        self._run(recall, ("Ash", "Birch"))
        seen = self._run(recall, ("Ash", "Birch", "Cedar", "Dogwood"))
        looking = [one for one in seen.seen if one.asked is not None]
        assert looking[0].asked == (0, 2)
        assert {one.asked[1] for one in looking} == {2}
        assert [one.done for one in looking] == [0, 1, 2, 3]
