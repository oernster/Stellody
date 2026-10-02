"""Settling a name that reaches several artists, from what the library holds.

FR-D09. A catalogue that knows two artists by one name is not told which one
is meant; the library is asked instead. Each title held under that name is put
to the catalogue as "who is credited on this". A namesake credited there
is the one the listener meant: it is on their shelf.

**One namesake credited settles it; two do not.** Two namesakes credited on
the same title is a real ambiguity (measured on 2026-09-27 for The Wash,
Leonardo and Matador); it is reported exactly as it was before. A title
nobody of that name is credited on says nothing, so the next one is tried.

**At most `MOST_EVIDENCE` titles are put.** Each try is a request. Measured on
2026-09-27 over the 36 names a library could not settle: every one that
settled did so on its first or second title. The cap is a bound on cost; what
a longer search would add was not measured.
"""

from __future__ import annotations

from stellody.application.asking import Pause, asked
from stellody.application.discovery_ports import CatalogueSource
from stellody.application.ports import CancelledCheck
from stellody.domain.credit_evidence import Evidence, settled_by

# How many held titles one ambiguous name may be tried against.
MOST_EVIDENCE = 3


def meant(
    catalogue: CatalogueSource,
    name: str,
    evidence: tuple[Evidence, ...],
    cancelled: CancelledCheck,
    pause: Pause,
) -> tuple[str, ...]:
    """Who a held name means: nobody, the one settled, else every namesake.

    One home for the question, since both the artist stage and the series
    stage ask it (FR-D09, FR-D82). Several back means the library's titles
    could not say which.
    """
    identifiers = asked(catalogue.identify, cancelled, pause, name)
    if len(identifiers) > 1:
        one = settled(catalogue, identifiers, evidence, cancelled, pause)
        if one is not None:
            return (one,)
    return identifiers


def settled(
    catalogue: CatalogueSource,
    identifiers: tuple[str, ...],
    evidence: tuple[Evidence, ...],
    cancelled: CancelledCheck,
    pause: Pause,
) -> str | None:
    """The one namesake the library's own titles credit; None where none does.

    Stops at the first title that credits any namesake at all, since that
    title has answered: one credited settles it, two leave it ambiguous.
    """
    for piece in evidence[:MOST_EVIDENCE]:
        credited = asked(catalogue.credited, cancelled, pause, piece)
        found = settled_by(identifiers, credited)
        if found:
            return next(iter(found)) if len(found) == 1 else None
    return None
