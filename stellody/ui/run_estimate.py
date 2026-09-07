"""How long a run has left, in the words a status bar carries.

The arithmetic is the domain's. This holds the two things it cannot: a clock,
plus what to say. A run is measured from the moment each stage begins, so the
stage change resets the reading rather than dragging the first stage's pace
into the second, where a unit costs half as much.

**It says the run is under way rather than naming a wrong time.** FR-D38: a
pace measured over one finished unit is wrong by a factor on a run whose first
request met a refusal; a number that swings is trusted less than an honest
silence. So the words for that case exist deliberately and are not a fallback
nobody thought about.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from stellody.application.values import DiscoveryProgress, DiscoveryStage
from stellody.domain.estimating import (
    SECONDS_PER_MINUTE,
    looking_up_seconds_left,
    narrowing_seconds_left,
    rounded_minutes,
)

# Reads the wall clock. Injected rather than reached for, so a test can drive a
# whole eleven minute run in no time at all.
Clock = Callable[[], float]

# Said while a run is going. The first names no time, for a run too young to
# have a pace worth quoting; the rest name one. FR-D35.
UNDER_WAY = "Looking for music you do not hold."
NOT_LONG = "Looking for music you do not hold. Less than a minute left."
ONE_MINUTE = "Looking for music you do not hold. About a minute left."
MINUTES_LEFT = "Looking for music you do not hold. About {minutes} minutes left."
# A minute reads as "a minute" rather than "1 minutes".
ONE = 1


def how_long(seconds: float) -> str:
    """That many seconds, said the way somebody waiting would say it.

    To the nearest minute, since a listener deciding whether to leave it
    running has no use for a number of seconds that is a projection anyway.
    """
    if seconds < SECONDS_PER_MINUTE:
        return NOT_LONG
    minutes = rounded_minutes(seconds)
    if minutes == ONE:
        return ONE_MINUTE
    return MINUTES_LEFT.format(minutes=minutes)


class RunEstimate:
    """What to say about a run in progress, kept across its reports.

    An object rather than a function because the answer depends on when the
    stage began, which is a fact about this run rather than about this report.
    """

    def __init__(self, now: Clock = time.monotonic) -> None:
        self._now = now
        self._stage: DiscoveryStage | None = None
        self._began = 0.0

    def restart(self) -> None:
        """Forget the last run, so the next is measured from its own start."""
        self._stage = None
        self._began = 0.0

    def said_about(self, progress: DiscoveryProgress) -> str:
        """What to tell somebody, given how far the run has got.

        The clock is read here rather than handed in with the report, because
        a report is a statement about the run and not about the time; the run
        itself is on another thread and has no business reading this one's.
        """
        if progress.stage is not self._stage:
            self._stage = progress.stage
            self._began = self._now()
        left = self._seconds_left(progress, self._now() - self._began)
        return UNDER_WAY if left is None else how_long(left)

    @staticmethod
    def _seconds_left(progress: DiscoveryProgress, elapsed_s: float) -> float | None:
        """The whole run's remaining seconds, read for whichever stage it is in.

        The first stage carries a projection of the second, since that is the
        longer half and its size is not known until the first ends. The second
        needs none: by then the total is a count.
        """
        if progress.stage is DiscoveryStage.LOOKING_UP:
            return looking_up_seconds_left(
                progress.done, progress.total, elapsed_s, progress.candidates
            )
        return narrowing_seconds_left(progress.done, progress.total, elapsed_s)
