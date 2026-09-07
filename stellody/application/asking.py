"""Asking a catalogue something, with the patience its terms ask for.

Split out of `discovering.py` on 2026-09-07, when a second caller appeared. A
run asks about every artist in the library; expanding a candidate artist asks
about one, on demand. Both meet the same refusals from the same hosts, so both
wait them out the same way; a retry written twice is two retries the day one of
them is tuned.

**A refusal is an ordinary answer here, not a failure.** Measured against
MusicBrainz on 2026-08-31: at the rate its own terms ask for, it refused 6 of 10
asks about the same release. Giving up on the first refusal would report an
artist as having nothing missing more often than not.

Nothing here opens a connection or reads a clock. The waiting is done by a
`Pause` handed in, so the suite waits for nothing at all.
"""

from __future__ import annotations

from collections.abc import Callable

from stellody.application.discovery_ports import (
    RateRefused,
    RunCancelled,
    SourceFailed,
)
from stellody.application.ports import CancelledCheck

# Handed a number of seconds to wait out a refusal. Injected rather than
# reached for, so the suite waits for nothing at all.
Pause = Callable[[float], None]

# How many times one question is asked before it is given up on; how long to
# wait between asks. The wait lengthens with each attempt, since a host
# refusing twice is asking for more room than one refusing once.
RETRY_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 2.0
# A wait is taken in slices so that stopping is felt rather than merely
# obeyed. Waiting out two refusals is six seconds; somebody who has pressed
# stop and watched nothing happen for six seconds has been told the button
# does not work. Small enough to read as immediate, large enough that a run
# is not spending its time asking whether it should stop.
WAIT_SLICE_SECONDS = 0.2


def asked[Answer](
    call: Callable[..., Answer],
    cancelled: CancelledCheck,
    pause: Pause,
    *arguments: object,
) -> Answer:
    """Ask a catalogue, waiting out a refusal rather than giving up on it.

    Asked whether it is still wanted before EVERY request rather than once per
    artist. Measured on 2026-09-07: a request may take the full timeout and may
    be attempted three times, so a run consulted once an artist could go on for
    minutes after being told to stop.

    The same question goes down WITH the request, phrased the way a client
    wants it. A request in flight used to be the floor on how quickly a stop
    could be felt, since nothing could reach a thread waiting on a socket; the
    catalogue clients now drop one part way through, so the floor is gone
    rather than merely lowered.
    """

    def wanted() -> bool:
        """Whether the answer to this is still worth waiting for."""
        return not cancelled()

    attempts = 0
    while True:
        if cancelled():
            raise RunCancelled("stopped before the next request")
        attempts += 1
        try:
            return call(*arguments, wanted=wanted)
        except RateRefused:
            if attempts >= RETRY_ATTEMPTS:
                raise SourceFailed("refused after every attempt")
            waited(RETRY_PAUSE_SECONDS * attempts, cancelled, pause)


def waited(seconds: float, cancelled: CancelledCheck, pause: Pause) -> None:
    """Wait that long, in slices, giving up the moment somebody asks.

    The whole wait used to be taken in one go, so a stop pressed at the start
    of a four second pause was not acted on for four seconds. It is checked
    before the first slice as well as after each one, so a stop pressed while
    the request was in flight is honoured without waiting at all.
    """
    left = seconds
    while True:
        if cancelled():
            raise RunCancelled("stopped while waiting out a refusal")
        if left <= 0:
            return
        take = min(WAIT_SLICE_SECONDS, left)
        pause(take)
        left -= take
