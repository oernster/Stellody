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
"""

from __future__ import annotations

from dataclasses import replace

from stellody.application.values import RunReport
from stellody.domain.discovery import Gaps


def carried_over(report: RunReport, previous: tuple[Gaps, ...]) -> RunReport:
    """This run's answer, holding on to what the last one knew.

    An artist that failed and was known before keeps what was known and stops
    being a failure, since there is nothing left to tell anybody about it. One
    that failed and was never known stays a failure, which is what the
    shortfall report is for.

    The carried entries follow this run's own, rather than being threaded back
    into the order the library gave: where they sit says nothing, while the
    order being decided by which artists happened to fail would be one more
    thing that differs between two runs.
    """
    if not report.failed:
        return report
    known = {gaps.artist: gaps for gaps in previous}
    return replace(
        report,
        gaps=report.gaps
        + tuple(
            known[entry.artist] for entry in report.failed if entry.artist in known
        ),
        failed=tuple(entry for entry in report.failed if entry.artist not in known),
    )
