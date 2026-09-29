"""The series stage of a run: the other volumes of each held compilation.

FR-D69 to FR-D73. Runs only while compilations are included: after the
library's own artists have been asked about; before any candidate is narrowed.
what it adds are albums, not artists, so the narrowing has nothing to do to
them.

**A placeholder is found from answers already in hand.** An artist whose
answer offered no album is asked again who they are and what they released;
both questions were answered moments earlier and are remembered, so this costs
no request. One identity with no release group at all is a name used to tag
compilations rather than anybody: measured on 2026-09-29, MusicBrainz says so
of "Global Underground" in as many words.

**One series is asked about once, however many of it are held.** A held album
whose stem and number are already among the entries of a series found is
answered by that series, so six volumes of Adapt cost one search each for the
first only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from stellody.application.asking import Pause, asked
from stellody.application.candidate_genres import (
    CANCELLED,
    UNAVAILABLE,
    ProgressReport,
)
from stellody.application.discovery_ports import (
    CatalogueSource,
    RunCancelled,
    SeriesSource,
    SourceFailed,
    SourceUnavailable,
)
from stellody.application.gathering import Silence
from stellody.application.ports import CancelledCheck
from stellody.application.values import DiscoveryProgress, RunReport, SourceFailure
from stellody.domain.album import Album
from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.domain.release_years import ReleaseYears
from stellody.domain.series import (
    Series,
    SeriesPlace,
    held_series,
    series_albums,
    series_missing,
    series_place,
    series_stem,
    sharing_stem,
)
from stellody.domain.text import comparison_key

# What the stage hands back: the series found, plus the albums nobody could
# answer about. FR-D73.
SeriesAnswer = tuple[tuple[Gaps, ...], tuple[SourceFailure, ...]]


@dataclass(slots=True)
class _Found:
    """What the stage has learned so far. Mutable: one stage in flight."""

    covered: set[SeriesPlace] = field(default_factory=set)
    asked_for: set[str] = field(default_factory=set)
    gaps: dict[str, Gaps] = field(default_factory=dict)
    failed: list[SourceFailure] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SeriesStage:
    """Finds the missing volumes of every series album a run reaches."""

    catalogue: CatalogueSource
    source: SeriesSource
    pause: Pause

    def found(
        self,
        albums: tuple[Album, ...],
        gathered: tuple[Gaps, ...],
        wanted: tuple[tuple[str, ...], ReleaseYears],
        report: ProgressReport,
        cancelled: CancelledCheck,
        silence: Silence,
    ) -> SeriesAnswer | RunReport:
        """Every series with something missing; an ending where one cut in."""
        ticked, years = wanted
        try:
            placeholders = self._placeholders(gathered, cancelled)
        except RunCancelled:
            return CANCELLED
        reached = series_albums(albums, ticked, placeholders)
        held = held_series(albums)
        found = _Found()
        for done, album in enumerate(reached):
            title = album.identity.title
            report(DiscoveryProgress(artist=title, done=done, total=len(reached)))
            place = series_place(title)
            if place is None or place in found.covered:
                continue
            try:
                answered = self._series_for(title, place, found, cancelled)
            except RunCancelled:
                return CANCELLED
            except SourceUnavailable as failure:
                if silence.deepened():
                    return UNAVAILABLE
                found.failed.append(SourceFailure(artist=title, reason=str(failure)))
                continue
            except SourceFailed as failure:
                silence.ended()
                found.failed.append(SourceFailure(artist=title, reason=str(failure)))
                continue
            silence.ended()
            for series in answered:
                _record(found, series, series_missing(series, held, ticked, years))
        return tuple(found.gaps.values()), tuple(found.failed)

    def _series_for(
        self,
        title: str,
        place: SeriesPlace,
        found: _Found,
        cancelled: CancelledCheck,
    ) -> tuple[Series, ...]:
        """The series this title belongs to, by the catalogue else by stem.

        A title in no catalogue series is matched by its stem instead, which
        is how "Global Underground: Unique" is reached: measured on
        2026-09-29, MusicBrainz places it in no series. FR-D70.
        """
        found.covered.add(place)
        named = asked(self.source.series_of, cancelled, self.pause, title)
        if named:
            fresh = tuple(one for one in named if one not in found.asked_for)
            found.asked_for.update(fresh)
            return tuple(
                asked(self.source.series, cancelled, self.pause, one) for one in fresh
            )
        stem = series_stem(title)
        if stem in found.asked_for:
            return ()
        found.asked_for.add(stem)
        groups = asked(self.source.titled, cancelled, self.pause, stem)
        return (Series(name=stem, entries=sharing_stem(groups, title)),)

    def _placeholders(
        self, gathered: tuple[Gaps, ...], cancelled: CancelledCheck
    ) -> frozenset[str]:
        """The names found to be placeholder artists, by `comparison_key`.

        Only an artist whose answer offered no album can be one. Nothing here
        can fail for want of a catalogue: every artist in `gathered` was
        answered earlier in this run, so both questions are answered from the
        run's own recollection. A stop is still honoured between them.
        """
        return frozenset(
            comparison_key(gaps.artist)
            for gaps in gathered
            if not gaps.albums and self._is_placeholder(gaps.artist, cancelled)
        )

    def _is_placeholder(self, name: str, cancelled: CancelledCheck) -> bool:
        """Whether this name is one artist who released no album or EP."""
        identities = asked(self.catalogue.identify, cancelled, self.pause, name)
        if len(identities) != 1:
            return False
        released = asked(self.catalogue.albums_of, cancelled, self.pause, identities[0])
        return not released


def _record(found: _Found, series: Series, missing: tuple[ReleaseGroup, ...]) -> None:
    """Note what a series answered: its places as covered, its gaps if any."""
    found.covered.update(
        place
        for place in (series_place(entry.title) for entry in series.entries)
        if place is not None
    )
    if not missing:
        return
    earlier = found.gaps.get(series.name)
    albums = (
        missing
        if earlier is None
        else earlier.albums
        + tuple(group for group in missing if group not in earlier.albums)
    )
    found.gaps[series.name] = Gaps(artist=series.name, albums=albums, series=True)
