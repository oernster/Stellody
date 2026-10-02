"""The series stage of a run: the other volumes of each held compilation.

FR-D69 to FR-D73. Runs only while other volumes of series are included
(FR-D85): after the library's own artists have been asked about; before any
candidate is narrowed. What it adds are albums, not artists, so the narrowing
has nothing to do to them.

**A placeholder is found from answers already in hand.** An artist whose
answer offered no album is asked again who they are and what they released;
both questions were answered moments earlier and are remembered, so this costs
no request. One identity with no release group at all is a name used to tag
compilations rather than anybody: measured on 2026-09-29, MusicBrainz says so
of "Global Underground" in as many words.

**So is a compilation filed under an artist.** FR-D82. Measured on
2026-10-02: of the library's electronic albums only 16 are filed under Various
Artists, while Fabric 97, Balance 029 and four numbered Global Underground
mixes are filed under the DJ. The catalogue already said what each of those
artists released, typed, so a held album it calls a compilation is searched
by the catalogue's own title: "#45" never finds "045".

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
from stellody.application.settling import meant
from stellody.application.values import (
    DiscoveryProgress,
    DiscoveryStage,
    RunReport,
    SourceFailure,
)
from stellody.domain.album import Album
from stellody.domain.credit_evidence import evidence_by_artist, evidence_for
from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.domain.release_years import ReleaseYears
from stellody.domain.series import (
    Series,
    SeriesPlace,
    artist_filed,
    catalogued_compilation,
    held_series,
    merged_entries,
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
            catalogued = self._catalogued(albums, ticked, placeholders, cancelled)
        except RunCancelled:
            return CANCELLED
        filed = series_albums(albums, ticked, placeholders)
        # Each title once, in the order met. FR-D82.
        reached = tuple(
            dict.fromkeys((*(a.identity.title for a in filed), *catalogued))
        )
        held = held_series(albums)
        found = _Found()
        for done, title in enumerate(reached):
            report(
                DiscoveryProgress(
                    artist=title,
                    done=done,
                    total=len(reached),
                    stage=DiscoveryStage.SERIES,
                )
            )
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
        """The series this title belongs to, by the catalogue and by stem.

        The stem is searched whether or not the catalogue names a series. With
        none it is the only answer: measured on 2026-09-29, MusicBrainz places
        "Global Underground: Unique" in no series. With one it tops the series
        up: measured on 2026-09-30, the Select series ends at "Select Ten"
        while a search finds #11, ruled worth offering by Oliver. FR-D70.
        """
        found.covered.add(place)
        named = asked(self.source.series_of, cancelled, self.pause, title)
        fresh = tuple(one for one in named if one not in found.asked_for)
        found.asked_for.update(fresh)
        catalogued = tuple(
            asked(self.source.series, cancelled, self.pause, one) for one in fresh
        )
        stem = series_stem(title)
        if stem in found.asked_for:
            return catalogued
        found.asked_for.add(stem)
        groups = asked(self.source.titled, cancelled, self.pause, stem)
        # Filed under the catalogue's name where there is one, so both answers
        # meet under one heading. FR-D70.
        name = catalogued[0].name if catalogued else stem
        return (*catalogued, Series(name=name, entries=sharing_stem(groups, title)))

    def _catalogued(
        self,
        albums: tuple[Album, ...],
        ticked: tuple[str, ...],
        placeholders: frozenset[str],
        cancelled: CancelledCheck,
    ) -> tuple[str, ...]:
        """The catalogue's titles for held compilations filed under an artist.

        FR-D82. Every album artist inside the ticks was asked about earlier
        in this run, so both questions are answered from its recollection. A
        name the library cannot settle gives nothing here; neither does a
        question that fails. The artist stage has already reported either.
        """
        evidence = evidence_by_artist(albums)
        by_artist: dict[str, list[str]] = {}
        for album in artist_filed(albums, ticked, placeholders):
            artist = album.identity.album_artist
            by_artist.setdefault(artist, []).append(album.identity.title)
        found: list[str] = []
        for artist, titles in by_artist.items():
            try:
                identifiers = meant(
                    self.catalogue,
                    artist,
                    evidence_for(evidence, artist),
                    cancelled,
                    self.pause,
                )
                if len(identifiers) != 1:
                    continue
                released = asked(
                    self.catalogue.albums_of, cancelled, self.pause, identifiers[0]
                )
            except (SourceFailed, SourceUnavailable):
                continue
            for title in titles:
                named = catalogued_compilation(title, released)
                if named is not None:
                    found.append(named)
        return tuple(found)

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
    albums = merged_entries(() if earlier is None else earlier.albums, missing)
    found.gaps[series.name] = Gaps(artist=series.name, albums=albums, series=True)
