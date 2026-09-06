"""Running a discovery: asking two catalogues what a library is missing.

The use case, which is to say the decisions. What a gap IS lives in the domain;
how a catalogue is reached lives in infrastructure. This holds the order things
happen in, what is done when one of them fails and when to stop.

**The ports are declared here rather than in `ports.py`.** That file is four
lines short of the danger band below the module cap, so adding to it would
force an unrelated file to be decomposed by a change that has nothing to do
with it. Interfaces belonging to the code that needs them is the ordinary
reading of dependency inversion in any case; it is noted because the house has
one ports module and this is a second place to look.

**A refusal is an ordinary answer, not a failure.** Measured against
MusicBrainz on 2026-08-31 and recorded in `infrastructure/cover_search.py`: at
the rate its own terms ask for, it refused 6 of 10 asks about the same release.
Asking once and reporting the refusal as an absence would tell a listener that
half their library has nothing missing, which is worse than saying nothing.

**Everything else that goes wrong is kept and carried.** An artist a catalogue
does not know, a name that reaches two artists, an error nobody anticipated:
each is recorded against that artist and the run goes on. An artist nobody
could look up is exactly the artist somebody would otherwise assume was
complete.

**One failure does stop everything, and only one.** No connection at all means
every remaining artist will fail the same way, so continuing is 327 slow ways
of saying the network is down.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Protocol, TypeVar

from stellody.application.ports import CancelledCheck
from stellody.application.values import (
    Ambiguity,
    DiscoveryProgress,
    RunOutcome,
    RunReport,
    SourceFailure,
)
from stellody.domain.album import Album
from stellody.domain.discovery import (
    Gaps,
    ReleaseGroup,
    SimilarArtist,
    albums_missing,
    artists_missing,
    source_artists,
    wanted_by,
)
from stellody.domain.matching import ReleaseMatch, matched

# How many similar artists to ask for. Settled in PLAN.md and confirmed on
# 2026-09-06: it is a decision about how much to put in front of somebody
# rather than a fact about anything, so it is named here and nowhere else.
SIMILAR_WANTED = 10
# How many times one question is asked before it is given up on, and how long
# to wait between asks. The wait lengthens with each attempt, since a host
# refusing twice is asking for more room than one refusing once.
RETRY_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 2.0

Answer = TypeVar("Answer")
# Handed a number of seconds to wait out a refusal. Injected rather than
# reached for, so the suite waits for nothing at all.
Pause = Callable[[float], None]
# Handed how far a run has got, so a window can say so.
ProgressReport = Callable[[DiscoveryProgress], None]


class DiscoveryError(RuntimeError):
    """Something went wrong reaching a catalogue."""


class SourceUnavailable(DiscoveryError):
    """Nothing could be reached at all, so no later question will fare better."""


class RateRefused(DiscoveryError):
    """The catalogue asked to be asked again later."""


class SourceFailed(DiscoveryError):
    """One question failed for a reason of its own."""


class CatalogueSource(Protocol):
    """Knows which artist a name means and what that artist released."""

    def identify(self, name: str) -> tuple[str, ...]:
        """Every artist this name reaches; empty where it reaches none.

        More than one is not an error here: it is the answer, and the decision
        about what to do with it belongs above rather than inside a client.
        """
        ...

    def albums_of(self, identifier: str) -> tuple[ReleaseGroup, ...]:
        """Everything this artist released, with each album's stated genres."""
        ...

    def genres_of(self, identifier: str) -> tuple[str, ...]:
        """What this artist is said to play; empty where nothing is said."""
        ...


class SimilaritySource(Protocol):
    """Knows which artists resemble a given one."""

    def similar_to(self, identifier: str, wanted: int) -> tuple[SimilarArtist, ...]:
        """The artists most like this one, at most `wanted` of them."""
        ...


def held_by_artist(albums: tuple[Album, ...]) -> dict[str, frozenset[ReleaseMatch]]:
    """What each album artist is already held to have, ready to compare.

    Built once for a whole run rather than per artist, since an album is read
    the same way however many times it is asked about.
    """
    held: dict[str, set[ReleaseMatch]] = {}
    for album in albums:
        held.setdefault(album.identity.album_artist, set()).add(
            matched(album.identity.title)
        )
    return {artist: frozenset(found) for artist, found in held.items()}


@dataclass(frozen=True, slots=True)
class Discovery:
    """One discovery run, from the library to a report about it."""

    catalogue: CatalogueSource
    similarity: SimilaritySource
    pause: Pause

    def run(
        self,
        albums: tuple[Album, ...],
        ticked: tuple[str, ...],
        report: ProgressReport,
        cancelled: CancelledCheck,
    ) -> RunReport:
        """Ask about every artist inside the ticked genres; say what was found."""
        artists = source_artists(albums, ticked)
        if not artists:
            return RunReport(outcome=RunOutcome.NOTHING_TO_ASK)
        gathered, ending = self._gathered(albums, artists, ticked, report, cancelled)
        if ending is not None:
            return ending
        kept = self._narrowed(gathered.gaps, ticked, cancelled)
        if kept is None:
            return RunReport(outcome=RunOutcome.CANCELLED)
        return replace(gathered, outcome=RunOutcome.COMPLETED, gaps=kept)

    def _gathered(
        self,
        albums: tuple[Album, ...],
        artists: tuple[str, ...],
        ticked: tuple[str, ...],
        report: ProgressReport,
        cancelled: CancelledCheck,
    ) -> tuple[RunReport, RunReport | None]:
        """Everything the catalogues said, plus an ending where one cut in."""
        held = held_by_artist(albums)
        everyone = tuple(held)
        found: list[Gaps] = []
        unresolved: list[str] = []
        ambiguous: list[Ambiguity] = []
        failed: list[SourceFailure] = []
        for done, artist in enumerate(artists):
            if cancelled():
                return self._so_far(found, unresolved, ambiguous, failed), RunReport(
                    outcome=RunOutcome.CANCELLED
                )
            report(DiscoveryProgress(artist=artist, done=done, total=len(artists)))
            try:
                gaps = self._about(
                    artist, held.get(artist, frozenset()), everyone, ticked
                )
            except SourceUnavailable:
                return self._so_far(found, unresolved, ambiguous, failed), RunReport(
                    outcome=RunOutcome.UNAVAILABLE
                )
            except SourceFailed as failure:
                failed.append(SourceFailure(artist=artist, reason=str(failure)))
                continue
            if gaps is None:
                unresolved.append(artist)
            elif isinstance(gaps, Ambiguity):
                ambiguous.append(gaps)
            else:
                found.append(gaps)
        return self._so_far(found, unresolved, ambiguous, failed), None

    @staticmethod
    def _so_far(
        found: list[Gaps],
        unresolved: list[str],
        ambiguous: list[Ambiguity],
        failed: list[SourceFailure],
    ) -> RunReport:
        """What has been gathered, in the shape a report is written in."""
        return RunReport(
            outcome=RunOutcome.COMPLETED,
            gaps=tuple(found),
            unresolved=tuple(unresolved),
            ambiguous=tuple(ambiguous),
            failed=tuple(failed),
        )

    def _about(
        self,
        artist: str,
        held: frozenset[ReleaseMatch],
        everyone: tuple[str, ...],
        ticked: tuple[str, ...],
    ) -> Gaps | Ambiguity | None:
        """What one artist turned out to be missing.

        None where the catalogue does not know the name at all; an `Ambiguity`
        where it knows too many, since neither is a gap and both are worth
        telling a listener about.
        """
        identifiers = self._asked(self.catalogue.identify, artist)
        if not identifiers:
            return None
        if len(identifiers) > 1:
            return Ambiguity(artist=artist, identifiers=identifiers)
        offered = self._asked(self.catalogue.albums_of, identifiers[0])
        similar = self._asked(
            self.similarity.similar_to, identifiers[0], SIMILAR_WANTED
        )
        return Gaps(
            artist=artist,
            albums=albums_missing(held, offered, ticked),
            artists=artists_missing(everyone, similar),
        )

    def _narrowed(
        self,
        gathered: tuple[Gaps, ...],
        ticked: tuple[str, ...],
        cancelled: CancelledCheck,
    ) -> tuple[Gaps, ...] | None:
        """The same gaps with candidate artists outside the ticks taken out.

        The similarity catalogue names artists without saying what they play,
        so each has to be asked about separately. That is the expensive part of
        a run, which is why an artist is asked about ONCE however many times
        the run met them: the well-connected recur constantly.
        """
        known: dict[str, tuple[str, ...]] = {}
        narrowed: list[Gaps] = []
        for gaps in gathered:
            kept: list[SimilarArtist] = []
            for candidate in gaps.artists:
                if cancelled():
                    return None
                if candidate.identifier not in known:
                    known[candidate.identifier] = self._genres_of(candidate.identifier)
                if wanted_by(known[candidate.identifier], ticked):
                    kept.append(candidate)
            narrowed.append(replace(gaps, artists=tuple(kept)))
        return tuple(narrowed)

    def _genres_of(self, identifier: str) -> tuple[str, ...]:
        """What a candidate plays; nothing where there is nobody to ask about.

        An unnamed candidate is treated as one the catalogue could not
        describe, which keeps it rather than dropping it, on the same ground as
        every other undescribed candidate.
        """
        if not identifier:
            return ()
        try:
            return self._asked(self.catalogue.genres_of, identifier)
        except SourceFailed:
            return ()

    def _asked(self, call: Callable[..., Answer], *arguments: object) -> Answer:
        """Ask a catalogue, waiting out a refusal rather than giving up on it."""
        attempts = 0
        while True:
            attempts += 1
            try:
                return call(*arguments)
            except RateRefused:
                if attempts >= RETRY_ATTEMPTS:
                    raise SourceFailed("refused after every attempt")
                self.pause(RETRY_PAUSE_SECONDS * attempts)
