"""What a finished run is said to have been, in words; what to open for it.

Split from `discovering.py`, which was one line short of the danger band below
the line cap when a run gained the choice of including compilations. A run that
found nothing, one nobody could reach, one somebody stopped and one whose file
would not write are four different things. Each ending has its own sentence;
this is the one place that decides which of them a report is.
"""

from __future__ import annotations

from collections.abc import Callable

from stellody.application.carrying_over import carried_over
from stellody.application.discovery_ports import DiscoveryResults
from stellody.application.values import RunOutcome, RunReport
from stellody.ui import shortfall

# Handed a finished run; answers where it was written. Raises where it could
# not be, which is reported rather than swallowed.
WriteDiscovery = Callable[[RunReport], object]

FOUND = (
    "Found {albums} albums and {artists} artists you do not hold. Written to {where}."
)
FOUND_NOTHING = "Nothing missing was found in those genres."
NOTHING_TO_ASK = (
    "Nothing in the library carries those genres, so there was nobody to ask about."
)
STOPPED = "Stopped. Nothing was written; any earlier answer is untouched."
UNREACHABLE = "Nothing answered. Check the connection, then try again."
COULD_NOT_WRITE = (
    "The answer could not be written: {reason}. Any earlier one is untouched."
)


def _counted(report: RunReport) -> tuple[int, int]:
    """How many albums and how many artists a run turned up."""
    albums = sum(len(gaps.albums) for gaps in report.gaps)
    artists = sum(len(gaps.artists) for gaps in report.gaps)
    return albums, artists


class SettlingDiscovery:
    """Deciding what a finished run is said to have been."""

    _write_discovery: WriteDiscovery | None
    _discovery_results: DiscoveryResults | None

    def _carried(self, report: RunReport) -> RunReport:
        """The report as the file will hold it, once earlier answers carry over.

        The writer keeps an earlier answer for an artist this run could not
        reach and records no failure for that artist. FR-D46. The counts and
        the shortfall are read from the same thing, since otherwise the
        sentence and the button name artists the results screen shows an
        answer for. FR-D42, FR-D43.

        A run that will not be written is said as it stands. So is one whose
        file cannot be read back, since there is nothing to carry from.
        """
        if (
            not report.is_writable
            or self._write_discovery is None
            or self._discovery_results is None
        ):
            return report
        return carried_over(report, self._discovery_results.last_run().gaps)

    def _settled(self, report: RunReport) -> tuple[str, bool, bool]:
        """What to tell somebody about a run that ended; what to open for it.

        Three answers, none inferred from another. The message; whether there
        are results worth opening; whether this ending PRESENTS AN ANSWER, so
        the shortfall belongs beside it.

        Only a run that WROTE a file has results worth opening: a stopped or
        unreachable run leaves the previous run's file exactly where it was,
        so showing "the file" after one would put a stale answer on screen as
        though it were this run's.

        The third is answered here rather than worked out again by the caller,
        so the sentence and the button can never disagree about which endings
        carry a shortfall.
        """
        if report.outcome is RunOutcome.NOTHING_TO_ASK:
            return NOTHING_TO_ASK, False, False
        if report.outcome is RunOutcome.CANCELLED:
            return STOPPED, False, False
        if report.outcome is RunOutcome.UNAVAILABLE:
            return UNREACHABLE, False, False
        # Only the two endings that PRESENT AN ANSWER carry the shortfall
        # sentence. A stopped or unreachable run has already said that its
        # answer is incomplete, so naming a count there would be saying it
        # twice; the ones that read as complete are the ones that mislead.
        short_by = shortfall.sentence(report)
        albums, artists = _counted(report)
        if self._write_discovery is None:
            return FOUND_NOTHING + short_by, False, True
        try:
            where = self._write_discovery(report)
        except (OSError, ValueError) as trouble:
            # An answer that could not be kept is not an answer presented,
            # so it carries neither the sentence nor the button.
            return COULD_NOT_WRITE.format(reason=trouble), False, False
        # A run that found nothing missing still opens its screen. Ruled by
        # Oliver on 2026-09-09, after two whole-library runs in one night
        # ended with nothing in front of him: an empty screen is a poor
        # screen, while an hour of work reporting into a strip nobody is
        # watching is worse. It says what it looked in and what it could not
        # answer about, which is more than the sentence alone carries.
        if not albums and not artists:
            return FOUND_NOTHING + short_by, True, True
        # Written first, then shown from what was written: the file is what a
        # later day would be shown from too, so showing anything else now
        # would be showing something nothing else can reproduce. FR-D28.
        return (
            FOUND.format(albums=albums, artists=artists, where=where) + short_by,
            True,
            True,
        )
