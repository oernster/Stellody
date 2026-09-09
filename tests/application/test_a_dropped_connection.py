"""One dropped connection is not the network being down.

Reported by Oliver on 2026-09-09, having left a run going over his whole
library while he slept. It ended after fifty minutes on its first answer of
nothing at all, which was one ListenBrainz request closed after 64
milliseconds; measured from that night's diary, the only one in 7252 lines.
Everything the run had gathered went with it.

The judgement that a run with no network is many slow ways of saying so was
never in doubt. What was wrong was the evidence it acted on: one sample. So
these hold both halves of the rule, since a fix that simply never gives up
would be the opposite mistake.
"""

from __future__ import annotations

from discovery_support import ROCK, Catalogue, make_album, never, nothing
from test_discovery import make_run

from stellody.application.discovery_ports import RateRefused, SourceUnavailable
from stellody.application.gathering import (
    NEVER_ANSWERED,
    REFUSED_EVERY_PASS,
    SILENCE_MEANS_GONE,
)
from stellody.application.values import RunOutcome


def _a_library_of(many: int) -> tuple:
    """A library of this many artists, each with one album."""
    return tuple(make_album(f"Artist {number}", "A") for number in range(many))


def test_one_dropped_connection_does_not_end_a_run() -> None:
    """The defect itself: an artist nothing answered about goes round again,
    exactly as a refused one does."""
    catalogue = Catalogue(unheard=1)
    run, source, _, _ = make_run(catalogue)
    albums = (make_album("One", "A"), make_album("Two", "B"))
    report = run.run(albums, ROCK, nothing, never)
    assert report.outcome is RunOutcome.COMPLETED
    assert report.failed == (), "nothing was given up on"
    assert [gaps.artist for gaps in report.gaps] == ["Two", "One"]
    assert source.identified == ["One", "Two", "One"], "it came back to the first"


def test_a_connection_that_has_gone_still_ends_the_run() -> None:
    """Continuing with no network is many slow ways of saying it once.

    The count is what changed rather than the judgement: it takes a run of
    questions met with nothing, not one of them.
    """
    catalogue = Catalogue(raises=SourceUnavailable("nothing answered"))
    run, source, _, _ = make_run(catalogue)
    report = run.run(_a_library_of(SILENCE_MEANS_GONE + 1), ROCK, nothing, never)
    assert report.outcome is RunOutcome.UNAVAILABLE
    assert not report.is_writable
    assert len(source.identified) == SILENCE_MEANS_GONE


def test_an_answer_between_two_silences_starts_the_count_over() -> None:
    """A silence is a RUN of them, so anything answering breaks it."""
    catalogue = Catalogue(unheard=SILENCE_MEANS_GONE - 1)
    run, _, _, _ = make_run(catalogue)
    report = run.run(_a_library_of(SILENCE_MEANS_GONE + 1), ROCK, nothing, never)
    assert report.outcome is RunOutcome.COMPLETED
    assert len(report.gaps) == SILENCE_MEANS_GONE + 1, "every artist answered"


def test_an_artist_nothing_ever_answered_about_says_that() -> None:
    """Not that the catalogue was busy, which would be a different fact."""
    catalogue = Catalogue(raises=SourceUnavailable("nothing answered"))
    run, _, _, _ = make_run(catalogue)
    report = run.run((make_album("One", "A"),), ROCK, nothing, never)
    assert report.outcome is RunOutcome.COMPLETED
    assert [failure.reason for failure in report.failed] == [NEVER_ANSWERED]


def test_an_artist_refused_after_a_silence_is_reported_as_refused() -> None:
    """Whichever happened last is what somebody is told about."""
    catalogue = Catalogue(unheard=1, refusals=0, raises=RateRefused("busy"))
    run, _, _, _ = make_run(catalogue)
    report = run.run((make_album("One", "A"),), ROCK, nothing, never)
    assert [failure.reason for failure in report.failed] == [REFUSED_EVERY_PASS]
