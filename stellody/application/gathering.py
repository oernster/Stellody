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

**A slow answer is not a broken one either; it used to be treated as one.**
Reported by Oliver on 2026-09-09: a run produced no data at all. Measured
against MusicBrainz the same day, ten identical searches paced at the rate its
terms ask for, the time to the first byte was 0.15 seconds seven times, 3.6
once, 12.7 once and 26.3 once. So the twenty second wait is exceeded by the
service ANSWERING, perhaps one ask in five. That was recorded against the
artist as a failure nobody would ever ask about again, which on a small
library is the difference between an answer and an empty screen. It goes round
again now, exactly as a refusal does.

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
# Said against an artist the catalogue was still thinking about when the wait
# ran out, on every pass. Its own words again: a service that answers slowly
# is neither busy nor unreachable; the thing to do about it is to ask later
# rather than to look at the connection.
TOO_SLOW_EVERY_PASS = "the catalogue was too slow to answer on every pass"
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
    # What happened to each artist on their last go, in the words they would
    # be told in if the passes ran out with them still owed an answer. One
    # place rather than a set per kind, so a third kind cannot be added and
    # then forgotten in the two the others clear themselves out of.
    last: dict[str, str] = field(default_factory=dict)

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
        self.last[artist] = REFUSED_EVERY_PASS
        self.passes.refuse(artist)

    def unheard(self, artist: str) -> None:
        """Nothing answered about this artist, so it goes round again too."""
        self.last[artist] = NEVER_ANSWERED
        self.passes.refuse(artist)

    def slow(self, artist: str) -> None:
        """The catalogue was still thinking when the wait ran out.

        Another pass rather than a failure. A service under load sheds the
        expensive questions first, which is what a slow answer IS; the artist
        it happened to is exactly the artist a later pass would get. Written
        on 2026-09-09, when a run over five albums reported one of its three
        artists as broken on the strength of one slow search and a second run
        answered about the same artist in a tenth of a second.
        """
        self.last[artist] = TOO_SLOW_EVERY_PASS
        self.passes.refuse(artist)

    def owed(self) -> None:
        """Write down everyone still owed an answer once the passes ran out.

        Each in the words of what actually happened to it on its last go: a
        busy service, a service nothing came back from at all and a service
        that was still thinking are three different things to be told.
        """
        self.failed.extend(
            SourceFailure(
                artist=artist,
                reason=self.last.get(artist, REFUSED_EVERY_PASS),
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
