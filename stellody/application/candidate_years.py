"""The third stage of a run, only while years are set: when candidates released.

A candidate artist arrives from the similarity catalogue with a name and nothing
else, so without asking, a run over the 1980s would offer artists who released
nothing in them. FR-D63.

**Asked last, about as few as possible.** Only the candidates the genre stage
kept are asked about, each once however many source artists named them. The
question is the one expanding a candidate asks (FR-D31) and goes through the
same catalogue memory, so an answer paid for here makes that expansion free.

**A candidate who cannot be shown to fit is not offered.** One nobody could
ask about, one the catalogue would not answer about and one with no identifier
all leave the range unestablished; offering them would break the range asked
for without saying so. The one exception is the connection itself going,
which ends the run exactly as it does in the other two stages.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from stellody.application.asking import Pause, asked
from stellody.application.candidate_genres import (
    CANCELLED,
    UNAVAILABLE,
    ProgressReport,
)
from stellody.application.discovery_ports import (
    CatalogueSource,
    RunCancelled,
    SourceFailed,
    SourceUnavailable,
)
from stellody.application.gathering import Silence
from stellody.application.ports import CancelledCheck
from stellody.application.values import (
    DiscoveryProgress,
    DiscoveryStage,
    RunReport,
)
from stellody.domain.discovery import Gaps, everything_offered, still_to_ask
from stellody.domain.release_years import ReleaseYears


@dataclass(frozen=True, slots=True)
class CandidateYears:
    """Narrows gathered gaps to the candidates who released inside the years."""

    catalogue: CatalogueSource
    pause: Pause

    def narrowed(
        self,
        gathered: tuple[Gaps, ...],
        years: ReleaseYears,
        report: ProgressReport,
        cancelled: CancelledCheck,
        silence: Silence,
    ) -> tuple[Gaps, ...] | RunReport:
        """The same gaps, keeping only candidates with an album in the years.

        Handed back untouched where no years are set, without a single
        question asked: a run that asked nothing about years costs what it
        always did.
        """
        if not years.is_bounded:
            return gathered
        # Everyone with an identifier, each once. Nothing is known yet, which
        # is what an empty memory says to the rule that picks who to ask.
        asking = still_to_ask(gathered, {})
        fits: set[str] = set()
        for done, (identifier, name) in enumerate(asking):
            report(
                DiscoveryProgress(
                    artist=name,
                    done=done,
                    total=len(asking),
                    stage=DiscoveryStage.DATING,
                )
            )
            try:
                released = asked(
                    self.catalogue.albums_of, cancelled, self.pause, identifier
                )
            except RunCancelled:
                return CANCELLED
            except SourceFailed:
                # Something answered, so the run of silences ends; what it
                # said establishes nothing, so this candidate is not offered.
                silence.ended()
                continue
            except SourceUnavailable:
                if silence.deepened():
                    return UNAVAILABLE
                continue
            silence.ended()
            if everything_offered(released, years):
                fits.add(identifier)
        return tuple(
            replace(
                gaps,
                artists=tuple(
                    candidate
                    for candidate in gaps.artists
                    if candidate.identifier in fits
                ),
            )
            for gaps in gathered
        )
