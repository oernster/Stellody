"""The second stage of a run: asking what each suggested artist plays.

Split from `discovering.py`, which stood one line short of the danger band below
the line cap once a compilation credit could be taken apart mid-run. The stage is
a unit of its own: it takes the gaps the first stage gathered and hands them back
with the candidates outside the ticks taken out, which is the whole of its
conversation with the rest of a run.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from stellody.application.asking import Pause, asked
from stellody.application.discovery_ports import (
    CatalogueSource,
    GenreMemory,
    RunCancelled,
    SourceFailed,
    SourceTooSlow,
    SourceUnavailable,
)
from stellody.application.gathering import Silence
from stellody.application.ports import CancelledCheck
from stellody.application.values import (
    DiscoveryProgress,
    DiscoveryStage,
    RunOutcome,
    RunReport,
)
from stellody.domain.discovery import Gaps, playing_something_ticked, still_to_ask

# The two endings that cut a run short, each answered from more than one
# place, so each is named once.
CANCELLED = RunReport(outcome=RunOutcome.CANCELLED)
UNAVAILABLE = RunReport(outcome=RunOutcome.UNAVAILABLE)
# Handed how far a run has got, so a window can say so.
ProgressReport = Callable[[DiscoveryProgress], None]


@dataclass(frozen=True, slots=True)
class CandidateGenres:
    """Narrows gathered gaps to the candidates who play something ticked."""

    catalogue: CatalogueSource
    pause: Pause
    memory: GenreMemory

    def narrowed(
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
            except SourceTooSlow:
                # Left unknown rather than written down as playing nothing.
                # What is learned here is kept between runs, so a slow answer
                # recorded as silence would drop that candidate from every
                # later run as well as from this one.
                silence.ended()
                continue
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

        A slow answer is let past rather than swallowed here: it is the one
        failure that says nothing about the candidate, so `narrowed` above
        leaves them undescribed instead of remembering them as playing
        nothing.
        """
        try:
            return asked(self.catalogue.genres_of, cancelled, self.pause, identifier)
        except SourceTooSlow:
            raise
        except SourceFailed:
            return ()
