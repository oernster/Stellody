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

import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace

from stellody.application.asking import Pause, asked, waited
from stellody.application.discovery_ports import (
    CatalogueSource,
    GenreMemory,
    NothingRemembered,
    RunCancelled,
    SimilaritySource,
    SourceFailed,
    SourceRefused,
    SourceUnavailable,
)
from stellody.application.passing import PASS_PAUSE_SECONDS, Passes
from stellody.application.ports import CancelledCheck
from stellody.application.remembering import (
    CatalogueMemory,
    Clock,
    NothingKept,
    RememberingCatalogue,
    RememberingSimilarity,
)
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
    albums_missing,
    artists_missing,
    held_by_artist,
    playing_something_ticked,
    source_artists,
    still_to_ask,
)
from stellody.domain.matching import ReleaseMatch

# How many similar artists to ask for. Settled in PLAN.md and confirmed on
# 2026-09-06: it is a decision about how much to put in front of somebody
# rather than a fact about anything, so it is named here and nowhere else.
SIMILAR_WANTED = 10
# Said against an artist the catalogue would not talk about on any pass. Plain
# words rather than a status, since it reaches a person: the discovery file
# treats it as a hole and declines to write, so what somebody sees is the last
# complete answer plus this name.
REFUSED_EVERY_PASS = "the catalogue stayed busy through every pass"
# The two endings that cut a run short, each answered from more than one
# place, so each is named once.
CANCELLED = RunReport(outcome=RunOutcome.CANCELLED)
UNAVAILABLE = RunReport(outcome=RunOutcome.UNAVAILABLE)
# Handed how far a run has got, so a window can say so.
ProgressReport = Callable[[DiscoveryProgress], None]


@dataclass(frozen=True, slots=True)
class Discovery:
    """One discovery run, from the library to a report about it."""

    catalogue: CatalogueSource
    similarity: SimilaritySource
    pause: Pause
    memory: GenreMemory = field(default_factory=NothingRemembered)
    recall: CatalogueMemory = field(default_factory=NothingKept)
    # What a remembered answer's age is measured against. Injected for the
    # reason the pause is: a test standing a month from now must not wait one.
    now: Clock = time.time

    def run(
        self,
        albums: tuple[Album, ...],
        ticked: tuple[str, ...],
        report: ProgressReport,
        cancelled: CancelledCheck,
    ) -> RunReport:
        """Ask about every artist inside the ticked genres; say what was found.

        Asked through what is already remembered rather than of the services
        directly, so a question answered on some earlier day is not asked
        again. That is what makes two runs over one library agree: a run that
        asks everything afresh answers with whatever the service felt like
        that minute, which is the fault reported on 2026-09-08.

        What was learned is written down however the run ends, cancelled runs
        included: an answer already paid for is worth keeping whether or not
        the run it arrived during finished.
        """
        kept = self.recall.remembered()
        try:
            return replace(
                self,
                catalogue=RememberingCatalogue(self.catalogue, kept, self.now),
                similarity=RememberingSimilarity(self.similarity, kept, self.now),
            )._asked(albums, ticked, report, cancelled)
        finally:
            self.recall.remember(kept)

    def _asked(
        self,
        albums: tuple[Album, ...],
        ticked: tuple[str, ...],
        report: ProgressReport,
        cancelled: CancelledCheck,
    ) -> RunReport:
        """The run itself, with the memory already standing in front of it."""
        artists = source_artists(albums, ticked)
        if not artists:
            return RunReport(outcome=RunOutcome.NOTHING_TO_ASK)
        # Read once and handed to both halves. The first half counts the
        # candidates it meets that are NOT in here, since those are exactly
        # what the second half will have to ask about; reading it twice would
        # let the two halves disagree about what is already known.
        known = self.memory.remembered()
        gathered, ending = self._gathered(
            albums, artists, ticked, report, cancelled, known
        )
        if ending is not None:
            return ending
        kept = self._narrowed(gathered.gaps, ticked, report, cancelled, known)
        if kept is None:
            return RunReport(outcome=RunOutcome.CANCELLED)
        return replace(gathered, outcome=RunOutcome.COMPLETED, gaps=kept, ticked=ticked)

    def _gathered(
        self,
        albums: tuple[Album, ...],
        artists: tuple[str, ...],
        ticked: tuple[str, ...],
        report: ProgressReport,
        cancelled: CancelledCheck,
        known: dict[str, tuple[str, ...]],
    ) -> tuple[RunReport, RunReport | None]:
        """Everything the catalogues said, plus an ending where one cut in.

        It counts the distinct candidates it meets as it goes, so a listener
        can be told how long the whole run has left rather than how long this
        half of it has. Only candidates nothing is already known about are
        counted, since those are the ones the second half will pay for.
        """
        held = held_by_artist(albums)
        everyone = tuple(held)
        found: list[Gaps] = []
        unresolved: list[str] = []
        ambiguous: list[Ambiguity] = []
        failed: list[SourceFailure] = []
        met: set[str] = set()
        passes, done = Passes(artists), 0
        while True:
            for artist in passes.pending:
                if cancelled():
                    return self._so_far(found, unresolved, ambiguous, failed, CANCELLED)
                report(
                    DiscoveryProgress(
                        artist=artist,
                        done=done,
                        total=len(artists),
                        candidates=len(met),
                    )
                )
                try:
                    gaps = self._about(
                        artist,
                        held.get(artist, frozenset()),
                        everyone,
                        ticked,
                        cancelled,
                    )
                except RunCancelled:
                    return self._so_far(found, unresolved, ambiguous, failed, CANCELLED)
                except SourceUnavailable:
                    return self._so_far(
                        found, unresolved, ambiguous, failed, UNAVAILABLE
                    )
                except SourceRefused:
                    passes.refuse(artist)
                    continue
                except SourceFailed as failure:
                    failed.append(SourceFailure(artist=artist, reason=str(failure)))
                    done += 1
                    continue
                done += 1
                if gaps is None:
                    unresolved.append(artist)
                elif isinstance(gaps, Ambiguity):
                    ambiguous.append(gaps)
                else:
                    found.append(gaps)
                    met.update(
                        candidate.identifier
                        for candidate in gaps.artists
                        if candidate.identifier and candidate.identifier not in known
                    )
            if not passes.again():
                break
            try:
                waited(PASS_PAUSE_SECONDS, cancelled, self.pause)
            except RunCancelled:
                return self._so_far(found, unresolved, ambiguous, failed, CANCELLED)
        failed.extend(
            SourceFailure(artist=artist, reason=REFUSED_EVERY_PASS)
            for artist in passes.refused
        )
        return self._so_far(found, unresolved, ambiguous, failed)

    @staticmethod
    def _so_far(
        found: list[Gaps],
        unresolved: list[str],
        ambiguous: list[Ambiguity],
        failed: list[SourceFailure],
        ending: RunReport | None = None,
    ) -> tuple[RunReport, RunReport | None]:
        """What has been gathered, beside the ending that cut it short.

        The pair rather than the report alone, since every caller wants both
        and the three that end early would otherwise each build the same tuple
        by hand.
        """
        return (
            RunReport(
                outcome=RunOutcome.COMPLETED,
                gaps=tuple(found),
                unresolved=tuple(unresolved),
                ambiguous=tuple(ambiguous),
                failed=tuple(failed),
            ),
            ending,
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
        identifiers = asked(self.catalogue.identify, cancelled, self.pause, artist)
        if not identifiers:
            return None
        if len(identifiers) > 1:
            return Ambiguity(artist=artist, identifiers=identifiers)
        # Three requests are made about one artist. Each is asked about
        # separately inside `_asked`, so a stop between any two of them is
        # honoured rather than waiting for the artist to be finished with.
        offered = asked(self.catalogue.albums_of, cancelled, self.pause, identifiers[0])
        similar = asked(
            self.similarity.similar_to,
            cancelled,
            self.pause,
            identifiers[0],
            SIMILAR_WANTED,
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
        known: dict[str, tuple[str, ...]],
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
        asking = still_to_ask(gathered, known)
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
            replace(gaps, artists=playing_something_ticked(gaps.artists, known, ticked))
            for gaps in gathered
        )

    def _genres_of(self, identifier: str, cancelled: CancelledCheck) -> tuple[str, ...]:
        """What a candidate plays; nothing where the catalogue would not say.

        It is never asked about a candidate with no identifier: `_to_ask` drops
        those before anything is asked, so an unnamed candidate is never looked
        up and is kept on the same ground as every other undescribed one.
        """
        try:
            return asked(self.catalogue.genres_of, cancelled, self.pause, identifier)
        except SourceFailed:
            return ()
