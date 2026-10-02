"""The artist stage of a run: what each source artist made, who resembles them.

Split out of `discovering.py` on 2026-10-02, when FR-D84 and FR-D85 took that
module into the danger band. The seam is the one `series_stage.py` already
follows: the run decides the order of stages, each stage asks its own
questions. FR-D09 to FR-D13, FR-D53.
"""

from __future__ import annotations

from dataclasses import dataclass

from stellody.application.asking import Pause, asked, waited
from stellody.application.candidate_genres import CANCELLED, UNAVAILABLE, ProgressReport
from stellody.application.discovery_ports import (
    CatalogueSource,
    RunCancelled,
    SimilaritySource,
    SourceFailed,
    SourceRefused,
    SourceTooSlow,
    SourceUnavailable,
)
from stellody.application.gathering import Gathering, Silence
from stellody.application.passing import PASS_PAUSE_SECONDS, Passes
from stellody.application.ports import CancelledCheck
from stellody.application.settling import meant
from stellody.application.values import Ambiguity, DiscoveryProgress, RunReport
from stellody.domain.album import Album
from stellody.domain.credit_evidence import Evidence, evidence_by_artist, evidence_for
from stellody.domain.discovery import (
    Gaps,
    albums_missing,
    artists_missing,
    held_by_artist,
    held_for,
)
from stellody.domain.matching import ReleaseMatch
from stellody.domain.release_years import ReleaseYears
from stellody.domain.text import credit_parts, is_various_artists

# How many similar artists to ask for. Settled in PLAN.md and confirmed on
# 2026-09-06: it is a decision about how much to put in front of somebody
# rather than a fact about anything, so it is named here and nowhere else.
SIMILAR_WANTED = 10


@dataclass(frozen=True, slots=True)
class ArtistStage:
    """Asks about every source artist, in passes, until each is answered."""

    catalogue: CatalogueSource
    similarity: SimilaritySource
    pause: Pause

    def gathered(
        self,
        albums: tuple[Album, ...],
        artists: tuple[str, ...],
        wanted: tuple[tuple[str, ...], ReleaseYears, bool],
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

        `wanted` is the ticked genres, the years and whether DJ mixes are
        included: the three things an offered album is held to.
        """
        held = held_by_artist(albums)
        evidence = evidence_by_artist(albums)
        everyone = tuple(held)
        gathered = Gathering(passes=Passes(artists), known=known)
        done = 0
        while True:
            # Read afresh at every step rather than walked as it stood, since a
            # credit taken apart adds its artists to this same pass. FR-D53.
            at = 0
            while at < len(gathered.passes.pending):
                artist = gathered.passes.pending[at]
                at += 1
                if cancelled():
                    return gathered.report(CANCELLED)
                report(
                    DiscoveryProgress(
                        artist=artist,
                        done=done,
                        total=len(gathered.passes.everyone),
                        candidates=len(gathered.met),
                    )
                )
                try:
                    gaps = self._about(
                        artist,
                        (held_for(held, artist), evidence_for(evidence, artist)),
                        everyone,
                        wanted,
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
                except SourceTooSlow:
                    # A service still thinking when the wait ran out is a
                    # service under load, which is the same thing a refusal
                    # says in words. So this artist goes round again rather
                    # than being written off; see `slow` in `gathering.py`
                    # for what was measured on the day that changed.
                    silence.ended()
                    gathered.slow(artist)
                    continue
                except SourceFailed as failure:
                    silence.ended()
                    gathered.broke(artist, str(failure))
                    done += 1
                    continue
                silence.ended()
                done += 1
                if gaps is None:
                    # Any name, album artist or credit, is taken apart once
                    # nobody is found under the whole of it. FR-D53.
                    parts = credit_parts(artist)
                    gathered.unknown(
                        artist, tuple(p for p in parts if not is_various_artists(p))
                    )
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
        holding: tuple[frozenset[ReleaseMatch], tuple[Evidence, ...]],
        everyone: tuple[str, ...],
        wanted: tuple[tuple[str, ...], ReleaseYears, bool],
        cancelled: CancelledCheck,
    ) -> Gaps | Ambiguity | None:
        """What one artist turned out to be missing.

        None where the catalogue does not know the name at all; an `Ambiguity`
        where it knows too many and the library's own titles cannot say which
        is meant, since neither is a gap and both are worth telling a
        listener about. FR-D09.

        `holding` is what the library holds under the name twice over: the
        albums, to leave out of what is offered; the titles, to settle a name
        several artists share.
        """
        held, evidence = holding
        identifiers = meant(self.catalogue, artist, evidence, cancelled, self.pause)
        if not identifiers:
            return None
        if len(identifiers) > 1:
            return Ambiguity(artist=artist, identifiers=identifiers)
        # Three requests are made about one artist, plus up to MOST_EVIDENCE
        # more where its name had to be settled. Each is asked through `asked`
        # on its own, so a stop between any two of them is
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
            albums=albums_missing(held, offered, *wanted),
            artists=artists_missing(everyone, similar),
        )
