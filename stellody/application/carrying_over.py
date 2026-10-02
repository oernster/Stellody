"""Keeping what the last run knew about an artist this one could not reach.

The second half of making a run answer the same way twice. The first half is
`remembering.py`, which stops the questions being asked again at all; this is
what stands behind it for the artist nothing has ever been learned about, whose
first answer arrives on the day a service happens to be willing.

**A run may add to what is known and may correct it. It may not take it away
because a service said no.** Reported by Oliver on 2026-09-08: a run over two
genres replaced a file holding seven source artists with one holding a single
artist, the other six having been recorded as refused. The old answer was
still true; nothing had learned otherwise.

**Only an artist this run FAILED on is carried over.** An artist the run
reached and found nothing for is a real answer and replaces what was there; an
artist no longer in the library is not in this run's failures either, so it
falls away as it should. That keeps the file a record of the library rather
than a pile everything ever seen sinks into.

**What is carried keeps to this run's years.** FR-D66. An earlier answer was
found under whatever that run asked. Its albums carry their dates, so they are
held to the years now asked for; its candidate artists were checked against
the earlier years alone, so they come across only where those were the same.
"""

from __future__ import annotations

from dataclasses import replace

from stellody.application.values import RunReport
from stellody.domain.discovery import Gaps, LastRun


def _kept_to_years(gaps: Gaps, report: RunReport, previous: LastRun) -> Gaps:
    """An earlier answer as far as this run's years and DJ mixes allow it."""
    return replace(
        gaps,
        albums=tuple(
            album
            for album in gaps.albums
            if report.years.admits(album.year)
            and album.offered_with(report.including.mixes)
        ),
        artists=gaps.artists if previous.years == report.years else (),
    )


def carried_over(report: RunReport, previous: LastRun) -> RunReport:
    """This run's answer, holding on to what the last one knew, in one order.

    An artist that failed and was known before keeps what was known and stops
    being a failure, since there is nothing left to tell anybody about it. One
    that failed and was never known stays a failure, which is what the
    shortfall report is for.

    **Ordered by name rather than by how the answer was arrived at.** An
    artist carried over would otherwise sit wherever the carrying put it,
    while the same artist answered for directly would sit in library order:
    the same content in two orders is two different screens, which is exactly
    what "the same every time" forbids. Sorting by the artist makes the order
    a property of what is in the answer rather than of how it was got.
    """
    known = {gaps.artist: gaps for gaps in previous.gaps}
    return replace(
        report,
        gaps=tuple(
            sorted(
                report.gaps
                + tuple(
                    _kept_to_years(known[entry.artist], report, previous)
                    for entry in report.failed
                    if entry.artist in known
                ),
                key=lambda gaps: gaps.artist,
            )
        ),
        unresolved=tuple(sorted(report.unresolved)),
        ambiguous=tuple(sorted(report.ambiguous, key=lambda entry: entry.artist)),
        failed=tuple(
            sorted(
                (entry for entry in report.failed if entry.artist not in known),
                key=lambda entry: entry.artist,
            )
        ),
    )
