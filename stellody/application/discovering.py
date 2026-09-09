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

**A connection that has gone does stop everything; nothing else does.** Where
nothing answers at all, every remaining artist will fail the same way, so
continuing is 327 slow ways of saying the network is down. What proves it has
gone is a RUN of questions met with nothing rather than one of them: `Silence`
in `gathering.py` beside this holds that rule and why it is written that way.
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
from stellody.application.gathering import Gathering, Silence
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

        **Twice over; the second time is the one that matters.** The whole
        recollection is kept at the end, as it always was; the memory is also
        handed to the two wrappers, so each answer is written down as it
        arrives. A run that ends reaches the line below. A run whose process
        dies never does; Oliver lost fifty minutes of asking that way on
        2026-09-09.
        """
        kept = self.recall.remembered()
        try:
            return replace(
                self,
                catalogue=RememberingCatalogue(
                    self.catalogue, kept, self.now, self.recall
                ),
                similarity=RememberingSimilarity(
                    self.similarity, kept, self.now, self.recall
                ),
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
        # One silence for the whole run rather than one a half, since the
        # connection is one thing: five questions in a row met with nothing
        # mean the same whichever stage happened to be asking them.
        silence = Silence()
        gathered, ending = self._gathered(
            albums, artists, ticked, report, cancelled, known, silence
        )
        if ending is not None:
            return ending
        kept = self._narrowed(gathered.gaps, ticked, report, cancelled, known, silence)
        if isinstance(kept, RunReport):
            return kept
        return replace(gathered, outcome=RunOutcome.COMPLETED, gaps=kept, ticked=ticked)

    def _gathered(
        self,
        albums: tuple[Album, ...],
        artists: tuple[str, ...],
        ticked: tuple[str, ...],
        report: ProgressReport,
        cancelled: CancelledCheck,
        known: dict[str, tuple[str, ...]],
        silence: Silence,
    ) -> tuple[RunReport, RunReport | None]:
        """Everything the catalogues said, plus an ending where one cut in.

        What comes back is counted by `Gathering` beside this, which also
        decides how somebody never reached is described. The two endings from
        in here are a stop and a connection that has gone; a single question
        nothing answered is neither of those and is asked again on a later
        pass.
        """
        held = held_by_artist(albums)
        everyone = tuple(held)
        gathered = Gathering(passes=Passes(artists), known=known)
        done = 0
        while True:
            for artist in gathered.passes.pending:
                if cancelled():
                    return gathered.report(CANCELLED)
                report(
                    DiscoveryProgress(
                        artist=artist,
                        done=done,
                        total=len(artists),
                        candidates=len(gathered.met),
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
                    return gathered.report(CANCELLED)
                except SourceUnavailable:
                    # One dropped socket is not a dead connection: this artist
                    # goes round again; only a run of them ends anything.
                    if silence.deepened():
                        return gathered.report(UNAVAILABLE)
                    gathered.unheard(artist)
                    continue
                except SourceRefused:
                    silence.ended()
                    gathered.busy(artist)
                    continue
                except SourceFailed as failure:
                    silence.ended()
                    gathered.broke(artist, str(failure))
                    done += 1
                    continue
                silence.ended()
                done += 1
                if gaps is None:
                    gathered.unknown(artist)
                elif isinstance(gaps, Ambiguity):
                    gathered.several(gaps)
                else:
                    gathered.answered(gaps)
            if not gathered.passes.again():
                break
            try:
                waited(PASS_PAUSE_SECONDS, cancelled, self.pause)
            except RunCancelled:
                return gathered.report(CANCELLED)
        gathered.owed()
        return gathered.report()

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
        silence: Silence,
    ) -> tuple[Gaps, ...] | RunReport:
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
                genres = self._genres_of(identifier, cancelled)
            except RunCancelled:
                return CANCELLED
            except SourceUnavailable:
                # Nothing answered about this one candidate. It is left
                # unknown rather than written down as playing nothing, since
                # a question that was never answered is not an answer; the
                # run carries on unless the connection itself has gone.
                if silence.deepened():
                    return UNAVAILABLE
                continue
            silence.ended()
            # Kept in hand and written down in the same breath, for the reason
            # the first half's answers are: this half is the long one, so a
            # run that dies inside it has the most to lose.
            known[identifier] = genres
            self.memory.note(identifier, genres)
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
