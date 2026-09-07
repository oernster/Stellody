"""What a candidate artist has to offer, asked at the moment somebody asks.

A discovery run names candidate artists without saying what they released. It
could ask; it deliberately does not. A candidate is one the library holds
nothing by, so their whole discography would come back, while asking during the
run costs a paced request for every candidate that survives the genre filter.
Measured on 2026-09-07 against the gap the terms require, that roughly doubles
the second stage, which is already the longer half of a run. Most of those
answers are never looked at. So the cost is paid one artist at a time, by
whoever opens one. FR-D31.

**The same patience as a run.** MusicBrainz refused 6 of 10 asks about the same
release when measured on 2026-08-31, so a single ask that gave up on the first
refusal would fail more often than it answered. This waits a refusal out
through the shared retry rather than through one of its own.

Nothing here opens a connection. It says what to ask and what to keep;
`fetching.py` is the module that holds the socket.
"""

from __future__ import annotations

from dataclasses import dataclass

from stellody.application.asking import Pause, asked
from stellody.application.discovery_ports import CatalogueSource
from stellody.application.ports import CancelledCheck
from stellody.domain.discovery import ReleaseGroup, everything_offered


def never_stopped() -> bool:
    """A caller with nothing to stop, which is the ordinary case here.

    One expansion is one request rather than a run of hundreds, so most callers
    have nothing to cancel. It is still offered, since a window closing while
    an answer is in flight is a stop like any other.
    """
    return False


@dataclass(frozen=True, slots=True)
class Expansion:
    """One question, asked about one candidate artist."""

    catalogue: CatalogueSource
    pause: Pause

    def releases_of(
        self, identifier: str, cancelled: CancelledCheck = never_stopped
    ) -> tuple[ReleaseGroup, ...]:
        """Everything worth showing by an artist the library holds nothing by.

        The offering rule is applied here and nothing else is: there is no held
        set to compare against, while the ticked genres already chose this
        artist rather than choosing which of their records may be seen.

        A refusal after every attempt, a source that cannot be reached and a
        stop all arrive as the exceptions the ports declare. They are not
        caught here, because what to say about one is a decision for whoever
        asked rather than for this. FR-D32.
        """
        return everything_offered(
            asked(self.catalogue.albums_of, cancelled, self.pause, identifier)
        )
