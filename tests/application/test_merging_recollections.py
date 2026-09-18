"""Laying two recollections together keeps the later answer to each question.

What saving the catalogue memory rests on once two users can hold copies of it
at once: see `tests/infrastructure/test_overlapping_memory.py` for the loss
this closes.
"""

from __future__ import annotations

from stellody.application.remembering import (
    ALBUMS,
    IDENTIFIERS,
    SIMILAR,
    Recollection,
    merged,
    stamp_for,
)

EARLY = 1.0
LATE = 2.0


def _holding(key: str, answer: tuple[str, ...], when: float | None) -> Recollection:
    """A recollection knowing one identifier answer, stamped when given."""
    kept = Recollection(identifiers={key: answer})
    if when is not None:
        kept.written_at[stamp_for(IDENTIFIERS, key)] = when
    return kept


def test_a_question_only_one_side_holds_is_kept_from_that_side() -> None:
    """Nothing either knew is lost by laying them together."""
    together = merged(_holding("a", ("id-a",), EARLY), _holding("b", ("id-b",), LATE))
    assert together.identifiers == {"a": ("id-a",), "b": ("id-b",)}
    assert together.written_at == {
        stamp_for(IDENTIFIERS, "a"): EARLY,
        stamp_for(IDENTIFIERS, "b"): LATE,
    }


def test_the_later_answer_wins_whichever_side_it_is_on() -> None:
    """An older copy saved last never puts an older answer back."""
    older, newer = _holding("a", ("old",), EARLY), _holding("a", ("new",), LATE)
    assert merged(older, newer).identifiers == {"a": ("new",)}
    assert merged(newer, older).identifiers == {"a": ("new",)}
    assert merged(newer, older).written_at[stamp_for(IDENTIFIERS, "a")] == LATE


def test_an_unstamped_answer_gives_way_to_a_stamped_one() -> None:
    """No stamp reads as written before anything was."""
    together = merged(
        _holding("a", ("stamped",), EARLY), _holding("a", ("bare",), None)
    )
    assert together.identifiers == {"a": ("stamped",)}


def test_an_unstamped_answer_nobody_else_holds_is_kept_unstamped() -> None:
    """Kept; still asked about again, since nothing says how old it is."""
    together = merged(Recollection(), _holding("a", ("bare",), None))
    assert together.identifiers == {"a": ("bare",)}
    assert together.written_at == {}


def test_every_kind_of_answer_is_laid_together() -> None:
    """Albums and similar artists are merged exactly as identifiers are."""
    kept = Recollection(albums={"x": ()}, similar={"y": ()})
    kept.written_at[stamp_for(ALBUMS, "x")] = EARLY
    kept.written_at[stamp_for(SIMILAR, "y")] = EARLY
    together = merged(Recollection(), kept)
    assert together.albums == {"x": ()}
    assert together.similar == {"y": ()}


def test_neither_side_is_changed() -> None:
    """A copy handed in is read, never written through."""
    standing, kept = _holding("a", ("s",), EARLY), _holding("b", ("k",), LATE)
    merged(standing, kept)
    assert standing.identifiers == {"a": ("s",)}
    assert kept.identifiers == {"b": ("k",)}
