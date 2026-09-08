"""Whether a run goes round the refused artists again; when it stops.

Measured on 2026-09-08 over Oliver's whole library: MusicBrainz refused 45 of
82 asks, saying its web server was busy. A run that waited each refusal out
where it stood spent nine seconds a request against a pace of 1.1, which came
to an estimated three hours. Going round again costs a pass; waiting where you
stand costs a minute an artist.

What is held here is the bookkeeping: which artists still owe an answer, then
whether another go is worth making.
"""

from __future__ import annotations

from stellody.application.passing import MOST_PASSES, QUIET_PASSES, Passes


def _refusing(passes: Passes) -> None:
    """A pass that gets nothing out of anybody it asks."""
    for artist in passes.pending:
        passes.refuse(artist)


def test_a_pass_that_refused_nobody_is_the_last_one() -> None:
    assert Passes(("U2", "Elbow")).again() is False


def test_the_refused_are_who_the_next_pass_asks_about() -> None:
    passes = Passes(("U2", "Elbow"))
    passes.refuse("Elbow")
    assert passes.again() is True
    assert passes.pending == ("Elbow",)
    assert passes.refused == [], "and they are no longer owed twice"


def test_a_pass_that_answers_nobody_twice_running_is_the_last() -> None:
    """A service that is busy for a spell is worth another pass; one that is
    down stays down, so going round it a dozen times is somebody's evening."""
    passes = Passes(("U2",))
    for _quiet in range(QUIET_PASSES - 1):
        _refusing(passes)
        assert passes.again() is True
    _refusing(passes)
    assert passes.again() is False
    assert passes.refused == ["U2"], "who is still owed an answer is still said"


def test_a_pass_that_answered_somebody_starts_the_count_again() -> None:
    """Progress is progress, however slow."""
    passes = Passes(("U2", "Elbow"))
    _refusing(passes)
    assert passes.again() is True
    passes.refuse("U2")
    assert passes.again() is True, "one of the two answered, so it is worth another"
    assert passes.quiet == 0


def test_it_stops_going_round_eventually_whatever_happens() -> None:
    """The safety net rather than the plan: passes that are getting anywhere
    shrink geometrically and finish long before this. So the case it catches is
    a run answering about one more artist each time and never finishing."""
    passes = Passes(tuple(f"Artist {n}" for n in range(MOST_PASSES + 2)))
    while True:
        for artist in passes.pending[1:]:
            passes.refuse(artist)
        if not passes.again():
            break
    assert passes.made == MOST_PASSES
    assert passes.quiet == 0, "it was getting somewhere the whole way"
    assert passes.refused, "and there is still somebody owed an answer"
