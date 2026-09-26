"""One artist, spelled two ways in the library, is one source artist. FR-D05.

Reported by Oliver on 2026-09-26: a run answered for "Dennis De Laat" and for
"Dennis de Laat" as two artists, each asked about separately and each shown
with the same similar artist. Names are the same name wherever discovery
compares them on `comparison_key`; choosing who to ask about has to agree.
"""

from __future__ import annotations

from stellody.domain.discovery import (
    Gaps,
    ReleaseGroup,
    albums_missing,
    held_by_artist,
    held_for,
    names_beyond,
    source_artists,
)
from stellody.domain.discovery_filter import filtered_answer
from stellody.domain.text import comparison_key
from tests.application.discovery_support import make_album, make_compilation

ROCK = ("Rock",)
UPPER, LOWER = "Dennis De Laat", "Dennis de Laat"


def test_two_spellings_are_asked_about_once_under_the_first_met() -> None:
    library = (make_album(UPPER, "First"), make_album(LOWER, "Second"))
    assert source_artists(library, ROCK) == (UPPER,)


def test_a_compilation_credit_is_the_album_artist_it_spells() -> None:
    library = (make_compilation("Rock", LOWER), make_album(UPPER, "First"))
    assert source_artists(library, ROCK, compilations=True) == (LOWER,)


def test_an_album_held_under_either_spelling_is_not_offered_back() -> None:
    library = (make_album(UPPER, "First"), make_album(LOWER, "Second"))
    held = held_for(held_by_artist(library), UPPER)
    offered = (ReleaseGroup(title="First"), ReleaseGroup(title="Second"))
    assert albums_missing(held, offered, ROCK) == ()


def test_the_filter_keeps_an_artist_whichever_spelling_the_run_used() -> None:
    library = (make_album(UPPER, "First"),)
    answer = (Gaps(artist=LOWER, albums=(ReleaseGroup(title="Third"),)),)
    kept = filtered_answer(answer, library, {}, ROCK)
    assert [gap.artist for gap in kept.gaps] == [LOWER]


def test_a_credit_respelling_an_album_artist_is_not_a_credit_of_its_own() -> None:
    """What decides whether a name may be taken apart; also what it costs."""
    assert names_beyond((LOWER, "Somebody Else"), (UPPER,)) == ("Somebody Else",)


def test_the_key_really_is_the_same() -> None:
    """What every assertion above rests on, stated once."""
    assert comparison_key(UPPER) == comparison_key(LOWER)
