"""A catalogue that answers slowly is a catalogue that answers.

Reported by Oliver on 2026-09-09: a discovery run over a small library
produced no data at all. Measured against MusicBrainz the same day, ten
identical searches paced at the rate its own terms ask for, the time to the
first byte was 0.15 seconds seven times, then 3.6, 12.7 and 26.3. So the
twenty second wait is exceeded by the service ANSWERING rather than by
anything being wrong, perhaps one ask in five.

A slow answer was recorded against the artist as a failure of its own, which
ends that artist for the run: no later pass ever asks about them again. On a
library of three source artists that was the difference between an answer and
an empty screen. These hold the rule that replaced it.
"""

from __future__ import annotations

from discovery_support import (
    ROCK,
    Catalogue,
    Memory,
    Similarity,
    Waits,
    make_album,
    never,
    nothing,
)
from test_discovery import make_run

from stellody.application.discovering import Discovery
from stellody.application.discovery_ports import SourceTooSlow
from stellody.application.gathering import TOO_SLOW_EVERY_PASS
from stellody.application.values import RunOutcome
from stellody.domain.discovery import SimilarArtist


def test_a_slow_answer_is_asked_about_again() -> None:
    """The defect itself: the artist goes round again and is answered.

    One slow search used to end that artist for the whole run, so a library
    small enough for one artist to matter came back holding nothing.
    """
    catalogue = Catalogue(too_slow=1)
    run, source, _, _ = make_run(catalogue)
    albums = (make_album("AC/DC", "Back In Black"), make_album("Eagles", "Desperado"))
    report = run.run(albums, ROCK, nothing, never)
    assert report.outcome is RunOutcome.COMPLETED
    assert report.failed == (), "nothing was written off"
    assert [gaps.artist for gaps in report.gaps] == ["Eagles", "AC/DC"]
    assert source.identified == ["AC/DC", "Eagles", "AC/DC"], "it came back"


def test_a_slow_answer_does_not_end_the_run() -> None:
    """A service under load is not a connection that has gone.

    Enough slow answers in a row to trip the silence rule, were they counted
    as silence: the socket was open and the host was talking, so they are not.
    """
    catalogue = Catalogue(too_slow=1)
    run, _, _, _ = make_run(catalogue)
    report = run.run((make_album("One", "A"),), ROCK, nothing, never)
    assert report.outcome is RunOutcome.COMPLETED
    assert len(report.gaps) == 1


def test_too_slow_on_every_pass_says_so_in_its_own_words() -> None:
    """Not that the catalogue was busy, which is a different thing to be told.

    A busy service says so in its own answer; a slow one says nothing at all
    and is still there. Somebody reading the results should be able to tell
    which happened to an artist they expected to see.
    """
    catalogue = Catalogue(raises=SourceTooSlow("no answer inside 20 seconds"))
    run, _, _, _ = make_run(catalogue)
    report = run.run((make_album("One", "A"),), ROCK, nothing, never)
    assert report.outcome is RunOutcome.COMPLETED
    assert [failure.reason for failure in report.failed] == [TOO_SLOW_EVERY_PASS]


def _narrowing_run(memory: Memory) -> Discovery:
    """A run whose one artist resembles one other, asked about too slowly."""
    catalogue = Catalogue(
        genre_trouble=SourceTooSlow("no answer inside 20 seconds"),
    )
    similar = Similarity((SimilarArtist(name="Robert Cray", identifier="cray"),))
    return Discovery(
        catalogue=catalogue,
        similarity=similar,
        pause=Waits(),
        memory=memory,
    )


def test_a_slow_answer_about_a_candidate_is_not_remembered_as_silence() -> None:
    """A question that never came back is not an answer of "plays nothing".

    What the second half learns is kept between runs, so writing a slow answer
    down settles that candidate for every later run as well as for this one.
    """
    memory = Memory()
    report = _narrowing_run(memory).run(
        (make_album("Muddy Waters", "Electric Mud", "Blues"),),
        ("Blues",),
        nothing,
        never,
    )
    assert report.outcome is RunOutcome.COMPLETED
    assert memory.noted == [], "nothing was learned, so nothing was written down"
    assert memory.kept == [{}], "and the whole recollection says the same"
