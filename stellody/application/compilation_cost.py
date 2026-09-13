"""What including compilations would cost a run, before it is asked. FR-D52.

**Priced from the permitted pace, never from a run.** Before a run there is no
pace to measure, so this is the arithmetic NFR-PERF-002 leaves standing: the
requests a name costs at the gap NFR-PERF-001 requires. It is a floor rather
than a forecast; the dialog's words say what makes a real run longer.

**Only what ticking the box adds.** A credit a run would ask about anyway, as an
album artist in the same genres, costs nothing more. Neither does one the
catalogue memory still holds a standing answer for, since the run will not ask
about it again.

**The memory is read once for each dialog.** It is megabytes on disk, while a
sweep of the genre grid moves every box and each asks for a new price.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from stellody.application.remembering import IDENTIFIERS, CatalogueMemory, Clock
from stellody.domain.album import Album
from stellody.domain.discovery import source_artists
from stellody.domain.estimating import REQUESTS_PER_SOURCE_ARTIST


@dataclass(frozen=True, slots=True)
class Cost:
    """How many names ticking the box adds; the seconds asking about them takes."""

    names: int
    seconds: float


@dataclass(frozen=True, slots=True)
class Pricing:
    """One library over one reading of the memory, priced for any ticks."""

    albums: tuple[Album, ...]
    answered: frozenset[str]
    request_gap_s: float

    def of(self, ticked: tuple[str, ...]) -> Cost:
        """What including compilations adds for these ticked genres."""
        already = set(source_artists(self.albums, ticked))
        added = tuple(
            name
            for name in source_artists(self.albums, ticked, compilations=True)
            if name not in already and name not in self.answered
        )
        return Cost(
            names=len(added),
            seconds=len(added) * REQUESTS_PER_SOURCE_ARTIST * self.request_gap_s,
        )


@dataclass(frozen=True, slots=True)
class CompilationCost:
    """Prices including compilations from the memory and the permitted pace."""

    recall: CatalogueMemory
    request_gap_s: float
    now: Clock = time.time

    def pricing(self, albums: tuple[Album, ...]) -> Pricing:
        """A price list for this library, reading the memory exactly once."""
        kept = self.recall.remembered()
        at = self.now()
        answered = frozenset(
            name
            for name in kept.identifiers
            if kept.holds(IDENTIFIERS, name, kept.identifiers, at)
        )
        return Pricing(
            albums=albums, answered=answered, request_gap_s=self.request_gap_s
        )
