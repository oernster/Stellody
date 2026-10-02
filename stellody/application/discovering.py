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
from dataclasses import dataclass, field, replace

from stellody.application.artist_stage import ArtistStage
from stellody.application.asking import Pause
from stellody.application.candidate_genres import (
    CandidateGenres,
    ProgressReport,
)
from stellody.application.candidate_years import CandidateYears
from stellody.application.compilation_cost import series_count
from stellody.application.discovery_ports import (
    CatalogueSource,
    GenreMemory,
    NoSeries,
    NothingRemembered,
    SeriesSource,
    SimilaritySource,
)
from stellody.application.gathering import Silence
from stellody.application.ports import CancelledCheck
from stellody.application.remembering import (
    CatalogueMemory,
    Clock,
    NothingKept,
    RememberingCatalogue,
    RememberingSimilarity,
)
from stellody.application.remembering_series import RememberingSeries
from stellody.application.reporting_ahead import Ahead
from stellody.application.series_stage import SeriesStage
from stellody.application.values import (
    RunOutcome,
    RunReport,
)
from stellody.domain.album import Album
from stellody.domain.discovery import (
    source_artists,
    still_to_ask,
)
from stellody.domain.including import OWN_ALBUMS, Including
from stellody.domain.release_years import ANY_YEAR, ReleaseYears
from stellody.domain.series import series_albums


@dataclass(frozen=True, slots=True)
class Discovery:
    """One discovery run, from the library to a report about it."""

    catalogue: CatalogueSource
    similarity: SimilaritySource
    pause: Pause
    memory: GenreMemory = field(default_factory=NothingRemembered)
    recall: CatalogueMemory = field(default_factory=NothingKept)
    # Asked about the other volumes of a compilation. FR-D69.
    series: SeriesSource = field(default_factory=NoSeries)
    # What a remembered answer's age is measured against. Injected for the
    # reason the pause is: a test standing a month from now must not wait one.
    now: Clock = time.time

    def run(
        self,
        albums: tuple[Album, ...],
        ticked: tuple[str, ...],
        report: ProgressReport,
        cancelled: CancelledCheck,
        including: Including = OWN_ALBUMS,
        years: ReleaseYears = ANY_YEAR,
    ) -> RunReport:
        """Ask about every artist inside the ticked genres; say what was found.

        `including` says what else to take in (FR-D85): the artists credited
        on compilations inside those genres (FR-D05, FR-D51), the other
        volumes of compilations held (FR-D69) and DJ mixes (FR-D80). With
        `years`, only music released inside them is offered; who is asked
        about is unchanged. FR-D58 to FR-D63.

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
        # Counted before anything is asked, so the time said while looking up
        # covers the series stage too. FR-D84.
        counted = series_count(kept, albums, self.now()).of(ticked)
        ahead = counted if including.series else 0
        try:
            return replace(
                self,
                catalogue=RememberingCatalogue(
                    self.catalogue, kept, self.now, self.recall
                ),
                similarity=RememberingSimilarity(
                    self.similarity, kept, self.now, self.recall
                ),
                series=RememberingSeries(self.series, kept, self.now, self.recall),
            )._asked(albums, ticked, Ahead(report, ahead), cancelled, including, years)
        finally:
            self.recall.remember(kept)

    def _asked(
        self,
        albums: tuple[Album, ...],
        ticked: tuple[str, ...],
        report: Ahead,
        cancelled: CancelledCheck,
        including: Including = OWN_ALBUMS,
        years: ReleaseYears = ANY_YEAR,
    ) -> RunReport:
        """The run itself, with the memory already standing in front of it."""
        artists = source_artists(albums, ticked, including.credits)
        # A compilation crediting nobody askable still has its series. FR-D69.
        if not artists and not (including.series and series_albums(albums, ticked)):
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
        gathered, ending = ArtistStage(
            self.catalogue, self.similarity, self.pause
        ).gathered(
            albums,
            artists,
            (ticked, years, including.mixes),
            report,
            cancelled,
            known,
            silence,
        )
        if ending is not None:
            return ending
        if including.series:
            report.candidates = len(still_to_ask(gathered.gaps, known))
            series = SeriesStage(self.catalogue, self.series, self.pause).found(
                albums, gathered.gaps, (ticked, years), report, cancelled, silence
            )
            if isinstance(series, RunReport):
                return series
            gathered = replace(
                gathered,
                gaps=gathered.gaps + series[0],
                failed=gathered.failed + series[1],
            )
        kept = CandidateGenres(self.catalogue, self.pause, self.memory).narrowed(
            gathered.gaps, ticked, report, cancelled, known, silence
        )
        if isinstance(kept, RunReport):
            return kept
        # Last, so only the candidates the genres kept are asked about. FR-D63.
        kept = CandidateYears(self.catalogue, self.pause, including.mixes).narrowed(
            kept, years, report, cancelled, silence
        )
        if isinstance(kept, RunReport):
            return kept
        return replace(
            gathered,
            outcome=RunOutcome.COMPLETED,
            gaps=kept,
            ticked=ticked,
            years=years,
            including=including,
        )
