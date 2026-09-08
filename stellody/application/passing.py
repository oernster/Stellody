"""Going round the refused artists again rather than waiting on each one.

Measured on 2026-09-08 from a run over Oliver's whole library: 93 requests in
841 seconds, 45 of the 82 sent to MusicBrainz refused, 9 seconds spent per
request against a pace of 1.1. The run was not asking slowly; it was sitting
still, waiting out one artist's refusal before asking about the next.

MusicBrainz says why, in its own words in the diary: "The MusicBrainz web
server is currently busy. Please try again later." That is not the rate limit,
which says something else entirely, so pacing ourselves more slowly would not
have helped. It is their load; the answer to load is to come back.

**So the waiting is amortised instead.** A refusal ends that artist's turn at
once; the artist joins the queue for another pass. While the run is asking
about the next artist it is already waiting out the last one's refusal, for
nothing. What cost sixty seconds an artist now costs one pass over what is
left, while each pass is smaller than the one before it.

**A pass that achieves nothing twice running is where it stops.** A service
that is down stays down; going round a hundred times to learn that is a
hundred times of somebody's evening. What is left then is reported as refused,
which the discovery file treats as a hole and so declines to write; every
answer that DID arrive is remembered either way, so running it again asks only
for what is missing.

Nothing here asks anything or waits for anything. It is the bookkeeping of
which artists still owe an answer and whether another go is worth making.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# How many times round the library at most. A safety net rather than a plan:
# the passes shrink geometrically, so a run that is getting anywhere is long
# finished before this, while a run that is not has stopped for the reason
# below.
MOST_PASSES = 12
# How many passes in a row may achieve nothing before it is given up on. Two
# rather than one, since a service can be busy for the half minute one pass
# happens to fall in; two says it is not a coincidence.
QUIET_PASSES = 2
# How long to wait before going round again. Long enough that a busy spell has
# a chance to end, short enough that a run with three artists left in it is
# not made into an evening. Where many artists are left the pass itself takes
# minutes, so this hardly signifies.
PASS_PAUSE_SECONDS = 30.0


@dataclass(slots=True)
class Passes:
    """Which artists still owe an answer; whether to go round again."""

    pending: tuple[str, ...]
    refused: list[str] = field(default_factory=list)
    made: int = 1
    quiet: int = 0

    def refuse(self, artist: str) -> None:
        """Put this artist back in the queue for another pass."""
        self.refused.append(artist)

    def again(self) -> bool:
        """Whether to go round again, having set the next pass up if so.

        Answers False with `refused` still holding whoever is owed an answer,
        so the caller can say who was never reached.
        """
        if not self.refused:
            return False
        if self.made >= MOST_PASSES:
            return False
        self.quiet = self.quiet + 1 if len(self.refused) == len(self.pending) else 0
        if self.quiet >= QUIET_PASSES:
            return False
        self.pending = tuple(self.refused)
        self.refused = []
        self.made += 1
        return True
