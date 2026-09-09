"""What the first half of a run has gathered; when to stop gathering.

Split out of `discovering.py` on 2026-09-09, when the rule below took that
module over the line cap. The seam is the ordinary one: the loop that asks is
one concern; the bookkeeping of what has come back, who still owes an answer
and whether the connection itself is still there is another.

**A source that answers nothing at all is not a source saying no.** A refusal
arrives with the service's own words in it, so the connection is plainly alive
and the artist is worth another pass. Nothing arriving at all could be either
a connection that has gone or one dropped socket among hundreds.

**One dropped socket is not a dead connection, so it no longer ends a run.**
Reported by Oliver on 2026-09-09. A run of fifty minutes ended on its first
`SourceUnavailable`, which was a single ListenBrainz request closed after 64
milliseconds; measured from the diary of that night, it was the ONLY one in
7252 lines. Everything the run had gathered went with it. An artist nothing
answered about now goes round again exactly as a refused one does.

**What a dead connection actually looks like is a run of them.** So the run
gives up on the connection only after `SILENCE_MEANS_GONE` questions in a row
have been met with nothing at all; any answer whatsoever ends that silence, be
it a description, a refusal or a failure. That keeps the original judgement
that continuing with no network is many slow ways of saying the same thing,
without letting one unlucky socket claim to be the network.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from stellody.application.passing import Passes
from stellody.application.values import (
    Ambiguity,
    RunOutcome,
    RunReport,
    SourceFailure,
)
from stellody.domain.discovery import Gaps

# Said against an artist the catalogue would not talk about on any pass. Plain
# words rather than a status, since it reaches a person: the discovery file
# treats it as a hole and declines to write, so what somebody sees is the last
# complete answer plus this name.
REFUSED_EVERY_PASS = "the catalogue stayed busy through every pass"
# Said against an artist nothing answered about on any pass. Its own words
# rather than the ones above, for the reason a busy source and an unreachable
# one are distinct kinds at all: one is worth trying again in a moment, the
# other is worth looking at the connection over.
NEVER_ANSWERED = "nothing answered about this artist on any pass"
# How many questions in a row may be met with nothing at all before the run
# gives up on the connection itself. Five rather than one, since one is what a
# single dropped socket costs and that is measured to happen: once in 7252
# diary lines. Five in a row, with nothing answering in between, is not luck.
# It is also cheap to be sure: the run paces itself at about a second a
# question, so being wrong five times over costs seconds.
SILENCE_MEANS_GONE = 5


@dataclass(slots=True)
class Silence:
    """How many questions in a row have been met with nothing at all.

    One of these stands for a whole run rather than for a half of it, since
    the connection is one thing: five silent questions mean the same whichever
    stage was asking them.
    """

    running: int = 0

    def deepened(self) -> bool:
        """Count one more; whether the connection itself is now in doubt."""
        self.running += 1
        return self.running >= SILENCE_MEANS_GONE

    def ended(self) -> None:
        """Something arrived, so whatever silence there was is over."""
        self.running = 0


@dataclass(slots=True)
class Gathering:
    """Everything the catalogues have said so far; who still owes an answer.

    Mutable by intention, like the recollection a run fills as it goes: it is
    the state of one run in flight. What it holds is turned into a report at
    whatever moment the run ends, however it ends.
    """

    passes: Passes
    # What is already known about candidate artists, read once by the run and
    # handed here so the count below can leave out the candidates that will
    # cost the second half nothing.
    known: dict[str, tuple[str, ...]]
    found: list[Gaps] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    ambiguous: list[Ambiguity] = field(default_factory=list)
    failed: list[SourceFailure] = field(default_factory=list)
    met: set[str] = field(default_factory=set)
    # Artists whose last go was met with nothing at all, so that whoever is
    # never reached can be told apart from whoever was refused.
    silent: set[str] = field(default_factory=set)

    def answered(self, gaps: Gaps) -> None:
        """An artist the catalogue described, with what it named beside them.

        The candidates are counted as they are met, so a listener can be told
        how long the WHOLE run has left rather than how long this half has.
        Only candidates nothing is already known about are counted, since
        those are the ones the second half will pay for.
        """
        self.found.append(gaps)
        self.met.update(
            candidate.identifier
            for candidate in gaps.artists
            if candidate.identifier and candidate.identifier not in self.known
        )

    def unknown(self, artist: str) -> None:
        """A name the catalogue reached nobody under."""
        self.unresolved.append(artist)

    def several(self, ambiguity: Ambiguity) -> None:
        """A name the catalogue reached more than one artist under."""
        self.ambiguous.append(ambiguity)

    def broke(self, artist: str, reason: str) -> None:
        """One artist's question failed for a reason of its own."""
        self.failed.append(SourceFailure(artist=artist, reason=reason))

    def busy(self, artist: str) -> None:
        """The catalogue asked to be asked again, so it will be."""
        self.silent.discard(artist)
        self.passes.refuse(artist)

    def unheard(self, artist: str) -> None:
        """Nothing answered about this artist, so it goes round again too."""
        self.silent.add(artist)
        self.passes.refuse(artist)

    def owed(self) -> None:
        """Write down everyone still owed an answer once the passes ran out.

        Each in the words of what actually happened to it, which is why the
        two sets are kept apart: an artist a busy service would not discuss
        and an artist nothing answered about are different things to be told.
        """
        self.failed.extend(
            SourceFailure(
                artist=artist,
                reason=NEVER_ANSWERED if artist in self.silent else REFUSED_EVERY_PASS,
            )
            for artist in self.passes.refused
        )

    def report(
        self, ending: RunReport | None = None
    ) -> tuple[RunReport, RunReport | None]:
        """What has been gathered, beside the ending that cut it short.

        The pair rather than the report alone, since every caller wants both
        and the endings would otherwise each build the same thing by hand.
        """
        return (
            RunReport(
                outcome=RunOutcome.COMPLETED,
                gaps=tuple(self.found),
                unresolved=tuple(self.unresolved),
                ambiguous=tuple(self.ambiguous),
                failed=tuple(self.failed),
            ),
            ending,
        )
