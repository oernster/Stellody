"""The second half of a run: asking what each suggested artist plays.

Its own module because the run tests beside it went over the line cap once
these arrived; also because this half is its own concern: it is the long half,
the half that used to report nothing at all and the only half that remembers
anything between runs.
"""

from __future__ import annotations

from discovery_support import (
    Catalogue,
    Memory,
    Recorder,
    Similarity,
    Waits,
    make_album,
    never,
    nothing,
)

from stellody.application.discovering import Discovery
from stellody.application.values import DiscoveryProgress, DiscoveryStage, RunOutcome
from stellody.domain.album import Album
from stellody.domain.discovery import SimilarArtist


def one_blues_artist() -> tuple[Album, ...]:
    """A library of one artist, in one genre, for the narrowing tests."""
    return (make_album("Muddy Waters", "Electric Mud", "Blues"),)


def narrowing_run(
    memory: Memory | None = None,
) -> tuple[Discovery, Catalogue, Recorder]:
    """A run whose one artist resembles two others nothing is known about."""
    catalogue = Catalogue(genres={"cray": ("Blues",), "wolf": ("Techno",)})
    similar = Similarity(
        (
            SimilarArtist(name="Robert Cray", identifier="cray"),
            SimilarArtist(name="Howlin' Wolf", identifier="wolf"),
        )
    )
    run = Discovery(
        catalogue=catalogue,
        similarity=similar,
        pause=Waits(),
        memory=memory if memory is not None else Memory(),
    )
    return run, catalogue, Recorder()


def test_the_second_half_of_a_run_reports_as_it_goes() -> None:
    """It used to say nothing, which is indistinguishable from a hang.

    A run over four artists spends the first half naming them and the second
    half asking about everyone they resemble, which is the longer half.
    """
    run, _, report = narrowing_run()
    run.run(one_blues_artist(), ("Blues",), report, never)
    narrowing = [seen for seen in report.seen if seen.stage is DiscoveryStage.NARROWING]
    assert [seen.artist for seen in narrowing] == ["Robert Cray", "Howlin' Wolf"]
    assert [seen.done for seen in narrowing] == [0, 1]
    assert {seen.total for seen in narrowing} == {2}


def test_the_first_half_still_says_which_half_it_is() -> None:
    """Both halves are named, so a bar can say which one is moving."""
    run, _, report = narrowing_run()
    run.run(one_blues_artist(), ("Blues",), report, never)
    first = report.seen[0]
    assert first.stage is DiscoveryStage.LOOKING_UP
    assert first.artist == "Muddy Waters"


def test_the_total_is_counted_before_any_of_them_is_asked_about() -> None:
    """A total revised as it goes is a bar that walks backwards."""
    run, _, report = narrowing_run()
    run.run(one_blues_artist(), ("Blues",), report, never)
    narrowing = [seen for seen in report.seen if seen.stage is DiscoveryStage.NARROWING]
    assert narrowing[0].total == len(narrowing)


def test_what_a_candidate_plays_is_kept_for_the_next_run() -> None:
    """Asking costs a second each; what somebody plays does not change."""
    memory = Memory()
    run, _, report = narrowing_run(memory)
    run.run(one_blues_artist(), ("Blues",), report, never)
    assert memory.kept == [{"cray": ("Blues",), "wolf": ("Techno",)}]


def test_what_was_remembered_is_not_asked_about_again() -> None:
    """The whole point of keeping it: a second run over the same ground."""
    memory = Memory({"cray": ("Blues",), "wolf": ("Techno",)})
    run, catalogue, report = narrowing_run(memory)
    run.run(one_blues_artist(), ("Blues",), report, never)
    assert catalogue.genres_asked == [], "it asked about nobody it already knew"
    assert [seen.stage for seen in report.seen] == [DiscoveryStage.LOOKING_UP]


def test_a_remembered_candidate_is_still_judged_by_what_was_ticked() -> None:
    """Remembering must not smuggle a candidate past the genres asked for."""
    memory = Memory({"cray": ("Blues",), "wolf": ("Techno",)})
    run, _, report = narrowing_run(memory)
    found = run.run(one_blues_artist(), ("Blues",), report, never)
    kept = [artist.name for gaps in found.gaps for artist in gaps.artists]
    assert kept == ["Robert Cray"], "the one playing what was ticked"


def test_a_run_given_nowhere_to_remember_still_runs() -> None:
    """The null memory is the default, so a run has one path through it."""
    catalogue = Catalogue(genres={"cray": ("Blues",)})
    similar = Similarity((SimilarArtist(name="Robert Cray", identifier="cray"),))
    run = Discovery(catalogue=catalogue, similarity=similar, pause=Waits())
    found = run.run(one_blues_artist(), ("Blues",), nothing, never)
    assert found.outcome is RunOutcome.COMPLETED
    assert catalogue.genres_asked == ["cray"], "it asked, having remembered nothing"


def test_a_stage_with_nothing_in_it_is_no_percent_of_anything() -> None:
    """A run whose second half has nobody to ask about still draws a bar.

    Everything a run met was already remembered, so the total is zero and the
    division that turns done into a percentage has nothing to divide by.
    """
    assert DiscoveryProgress(artist="", done=0, total=0).percent == 0


def test_the_percentage_counts_work_finished() -> None:
    """One of four done is a quarter, not the quarter that is under way."""
    assert DiscoveryProgress(artist="U2", done=1, total=4).percent == 25
    assert DiscoveryProgress(artist="U2", done=4, total=4).percent == 100
