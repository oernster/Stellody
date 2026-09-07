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

**One failure does stop everything; only that one.** No connection at all means
every remaining artist will fail the same way, so continuing is 327 slow ways
of saying the network is down.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import TypeVar

from stellody.application.discovery_ports import (
    CatalogueSource,
    GenreMemory,
    NothingRemembered,
    RateRefused,
    RunCancelled,
    SimilaritySource,
    SourceFailed,
    SourceUnavailable,
)
from stellody.application.ports import CancelledCheck
from stellody.application.values import (
    Ambiguity,
    DiscoveryProgress,
    DiscoveryStage,
    RunOutcome,
    RunReport,
    SourceFailure,
)
from stellody.domain.album import Album
from stellody.domain.discovery import (
    Gaps,
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
# How many times one question is asked before it is given up on; how long to
# wait between asks. The wait lengthens with each attempt, since a host
# refusing twice is asking for more room than one refusing once.
RETRY_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 2.0
# A wait is taken in slices so that stopping is felt rather than merely
# obeyed. Waiting out two refusals is six seconds; a listener who has pressed
# stop and watched nothing happen for six seconds has been told the button
# does not work. Small enough to read as immediate, large enough that a run
# is not spending its time asking whether it should stop.
WAIT_SLICE_SECONDS = 0.2

Answer = TypeVar("Answer")
# Handed a number of seconds to wait out a refusal. Injected rather than
# reached for, so the suite waits for nothing at all.
Pause = Callable[[float], None]
# Handed how far a run has got, so a window can say so.
ProgressReport = Callable[[DiscoveryProgress], None]


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
    memory: GenreMemory = field(default_factory=NothingRemembered)

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
        kept = self._narrowed(gathered.gaps, ticked, report, cancelled)
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
                    artist, held.get(artist, frozenset()), everyone, ticked, cancelled
                )
            except RunCancelled:
                return self._so_far(found, unresolved, ambiguous, failed), RunReport(
                    outcome=RunOutcome.CANCELLED
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
        cancelled: CancelledCheck,
    ) -> Gaps | Ambiguity | None:
        """What one artist turned out to be missing.

        None where the catalogue does not know the name at all; an `Ambiguity`
        where it knows too many, since neither is a gap and both are worth
        telling a listener about.
        """
        identifiers = self._asked(self.catalogue.identify, cancelled, artist)
        if not identifiers:
            return None
        if len(identifiers) > 1:
            return Ambiguity(artist=artist, identifiers=identifiers)
        # Three requests are made about one artist. Each is asked about
        # separately inside `_asked`, so a stop between any two of them is
        # honoured rather than waiting for the artist to be finished with.
        offered = self._asked(self.catalogue.albums_of, cancelled, identifiers[0])
        similar = self._asked(
            self.similarity.similar_to, cancelled, identifiers[0], SIMILAR_WANTED
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
        report: ProgressReport,
        cancelled: CancelledCheck,
    ) -> tuple[Gaps, ...] | None:
        """The same gaps with candidate artists outside the ticks taken out.

        The similarity catalogue names artists without saying what they play,
        so each has to be asked about separately. That is the expensive part of
        a run, which is why an artist is asked about ONCE however many times
        the run met them: the well-connected recur constantly.

        It reports as it goes for the same reason the first half does. This
        half used to say nothing at all; a listener watching a bar that had
        stopped moving had no way to tell a long wait from a hang.
        """
        known = self.memory.remembered()
        asking = self._to_ask(gathered, known)
        for done, (identifier, name) in enumerate(asking):
            # No check of its own here. Every candidate is asked about through
            # `_asked`, which consults the cancel before each request, so a
            # check at the top of this loop only asked the same question a
            # progress report earlier and gave a stop two places to be
            # noticed rather than one.
            report(
                DiscoveryProgress(
                    artist=name,
                    done=done,
                    total=len(asking),
                    stage=DiscoveryStage.NARROWING,
                )
            )
            try:
                known[identifier] = self._genres_of(identifier, cancelled)
            except RunCancelled:
                return None
        self.memory.remember(known)
        return tuple(
            replace(gaps, artists=self._kept(gaps.artists, known, ticked))
            for gaps in gathered
        )

    @staticmethod
    def _to_ask(
        gathered: tuple[Gaps, ...], known: dict[str, tuple[str, ...]]
    ) -> tuple[tuple[str, str], ...]:
        """Every candidate still to ask about, each once, in the order met.

        Counted before any of them is asked, so the total a bar is measured
        against is the truth rather than a guess revised as it goes.
        """
        asking: dict[str, str] = {}
        for gaps in gathered:
            for candidate in gaps.artists:
                if candidate.identifier and candidate.identifier not in known:
                    asking.setdefault(candidate.identifier, candidate.name)
        return tuple(asking.items())

    @staticmethod
    def _kept(
        candidates: tuple[SimilarArtist, ...],
        known: dict[str, tuple[str, ...]],
        ticked: tuple[str, ...],
    ) -> tuple[SimilarArtist, ...]:
        """Those of these candidates playing something that was ticked.

        A candidate nothing is known about is kept rather than dropped, on the
        same ground as every other undescribed one: silence from a catalogue
        is not a statement that somebody plays the wrong thing.
        """
        return tuple(
            candidate
            for candidate in candidates
            if wanted_by(known.get(candidate.identifier, ()), ticked)
        )

    def _genres_of(self, identifier: str, cancelled: CancelledCheck) -> tuple[str, ...]:
        """What a candidate plays; nothing where the catalogue would not say.

        It is never asked about a candidate with no identifier: `_to_ask` drops
        those before anything is asked, so an unnamed candidate is never looked
        up and is kept on the same ground as every other undescribed one.
        """
        try:
            return self._asked(self.catalogue.genres_of, cancelled, identifier)
        except SourceFailed:
            return ()

    def _asked(
        self,
        call: Callable[..., Answer],
        cancelled: CancelledCheck,
        *arguments: object,
    ) -> Answer:
        """Ask a catalogue, waiting out a refusal rather than giving up on it.

        Asked whether it is still wanted before EVERY request rather than once
        per artist. Measured on 2026-09-07: a request may take the full twenty
        second timeout and may be attempted three times, so a run asked once
        an artist could go on for minutes after being told to stop. A request
        already in flight cannot be called back, so one of those is the floor;
        what this removes is every one after it.
        """
        attempts = 0
        while True:
            if cancelled():
                raise RunCancelled("stopped before the next request")
            attempts += 1
            try:
                return call(*arguments)
            except RateRefused:
                if attempts >= RETRY_ATTEMPTS:
                    raise SourceFailed("refused after every attempt")
                self._waited(RETRY_PAUSE_SECONDS * attempts, cancelled)

    def _waited(self, seconds: float, cancelled: CancelledCheck) -> None:
        """Wait that long, in slices, giving up the moment somebody asks.

        The whole wait used to be taken in one go, so a stop pressed at the
        start of a four second pause was not acted on for four seconds. It is
        checked before the first slice as well as after each one, so a stop
        pressed while the request was in flight is honoured without waiting
        at all.
        """
        left = seconds
        while True:
            if cancelled():
                raise RunCancelled("stopped while waiting out a refusal")
            if left <= 0:
                return
            take = min(WAIT_SLICE_SECONDS, left)
            self.pause(take)
            left -= take
