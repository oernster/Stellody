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

**The series are priced as well.** Ticking the box also asks about the other
volumes of each compilation (FR-D69), so a series is counted once where any
held album of it has no standing answer. A placeholder artist is recognised
from the memory; one never asked about until now cannot be, since only the run
itself learns that the name released nothing, so its series are priced from
the second run on.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field

from stellody.application.remembering import (
    ALBUMS,
    IDENTIFIERS,
    SERIES_OF,
    CatalogueMemory,
    Clock,
    Recollection,
)
from stellody.domain.album import Album
from stellody.domain.discovery import ReleaseGroup, names_beyond, source_artists
from stellody.domain.estimating import REQUESTS_PER_SERIES, REQUESTS_PER_SOURCE_ARTIST
from stellody.domain.including import WIDEST, Including
from stellody.domain.series import (
    artist_filed,
    catalogued_compilation,
    series_albums,
    series_place,
)
from stellody.domain.text import comparison_key


@dataclass(frozen=True, slots=True)
class Cost:
    """What ticking the box adds: names, series; the seconds asking takes."""

    names: int
    seconds: float
    series: int = 0


@dataclass(frozen=True, slots=True)
class SeriesCount:
    """How many series a run will have to look up, from one reading of memory.

    One home for the count, since the dialog prices it (FR-D52) and the run
    carries it while looking up so the time said covers it (FR-D84).
    """

    albums: tuple[Album, ...]
    # Names the memory shows to be placeholder artists, by `comparison_key`.
    placeholders: frozenset[str] = frozenset()
    # Titles whose series question has a standing answer.
    placed: frozenset[str] = frozenset()
    # What each album artist released, where the memory settles them to one
    # identity. A name only the library's titles could settle is absent, so
    # its compilations are not counted: a known undercount. FR-D82.
    released: Mapping[str, tuple[ReleaseGroup, ...]] = field(default_factory=dict)

    def of(self, ticked: tuple[str, ...]) -> int:
        """How many series hold an album nobody has asked the series of."""
        titles = [
            album.identity.title
            for album in series_albums(self.albums, ticked, self.placeholders)
        ]
        for album in artist_filed(self.albums, ticked, self.placeholders):
            released = self.released.get(album.identity.album_artist)
            if released is not None:
                named = catalogued_compilation(album.identity.title, released)
                if named is not None:
                    titles.append(named)
        stems = {
            place.stem
            for title in titles
            if title not in self.placed and (place := series_place(title)) is not None
        }
        return len(stems)


@dataclass(frozen=True, slots=True)
class Pricing:
    """One library over one reading of the memory, priced for any ticks."""

    albums: tuple[Album, ...]
    answered: frozenset[str]
    request_gap_s: float
    series: SeriesCount

    def of(self, ticked: tuple[str, ...], including: Including = WIDEST) -> Cost:
        """What the boxes ticked add for these ticked genres. FR-D52, FR-D85.

        The artists only while their box is ticked; the series likewise.
        """
        added = (
            tuple(
                name
                for name in names_beyond(
                    source_artists(self.albums, ticked, compilations=True),
                    source_artists(self.albums, ticked),
                )
                if name not in self.answered
            )
            if including.credits
            else ()
        )
        series = self.series.of(ticked) if including.series else 0
        requests = (
            len(added) * REQUESTS_PER_SOURCE_ARTIST + series * REQUESTS_PER_SERIES
        )
        return Cost(
            names=len(added), seconds=requests * self.request_gap_s, series=series
        )


def series_count(
    kept: Recollection, albums: tuple[Album, ...], at: float
) -> SeriesCount:
    """The series count for this library over this reading of the memory."""
    return SeriesCount(
        albums=albums,
        placeholders=_placeholders(kept, at),
        placed=frozenset(
            title
            for title in kept.series_of
            if kept.holds(SERIES_OF, title, kept.series_of, at)
        ),
        released=_released(kept, albums, at),
    )


def _released(
    kept: Recollection, albums: tuple[Album, ...], at: float
) -> dict[str, tuple[ReleaseGroup, ...]]:
    """What each album artist released, where the memory names one of them."""
    found: dict[str, tuple[ReleaseGroup, ...]] = {}
    for name in {album.identity.album_artist for album in albums}:
        identities = kept.identifiers.get(name)
        if (
            identities is None
            or len(identities) != 1
            or not kept.holds(IDENTIFIERS, name, kept.identifiers, at)
            or not kept.holds(ALBUMS, identities[0], kept.albums, at)
        ):
            continue
        found[name] = kept.albums[identities[0]]
    return found


def _placeholders(kept: Recollection, at: float) -> frozenset[str]:
    """The names remembered as one artist with no album and no EP."""
    return frozenset(
        comparison_key(name)
        for name, identities in kept.identifiers.items()
        if kept.holds(IDENTIFIERS, name, kept.identifiers, at)
        and len(identities) == 1
        and kept.holds(ALBUMS, identities[0], kept.albums, at)
        and not kept.albums[identities[0]]
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
            albums=albums,
            answered=answered,
            request_gap_s=self.request_gap_s,
            series=series_count(kept, albums, at),
        )
