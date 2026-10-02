"""What a discovery run takes in beyond each album artist's own albums. FR-D85.

Pure: no I/O, no framework, no clock.

**Three choices, not one.** Ruled by Oliver on 2026-10-02. One box used to
widen a run to compilations, which meant two things at once: asking about the
artists credited on them while finding the other volumes of their series. Each
costs something different and is wanted for different reasons; DJ mixes
(FR-D80) joined them as a third, so they can be left out as well as offered.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Including:
    """The three choices a run is asked to make, as one value."""

    # The artists credited on compilations inside the ticks. FR-D05, FR-D51.
    credits: bool = False
    # The other volumes of the compilations held. FR-D69, FR-D82.
    series: bool = False
    # DJ mixes in an artist's own list. FR-D80. Offered unless left out, since
    # offering them is what FR-D80 asked for.
    mixes: bool = True


# A run that widens to nothing: neither credits nor series, mixes as FR-D80.
OWN_ALBUMS = Including()
# A run that takes in everything there is to take in: what the one box used
# to mean when ticked, plus mixes.
WIDEST = Including(credits=True, series=True)
