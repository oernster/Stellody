"""How long a pooled connection is believed in; letting go of it at rest.

**The host lets go at about thirty seconds.** Measured twice from the same
hosts: the diary of 2026-09-08 caught two idle sockets torn down at 29.914 and
29.877 seconds after the last request; on 2026-09-09 the same question asked
three times with the run's between-pass pause in between came back instantly
with GOAWAY and `RemoteHostClosedError` on the ask after each idle.

Half of that is taken as the limit rather than a figure near it, since the cost
of being early is one connection to open and the cost of being late is a lost
request. Lost where it fell, too: the pause is between PASSES, so the dead
socket met the first artist of every pass, which is the same artist each time.
A run could go round twelve times and lose that one artist on every go, which
on a small library is a run that finds nothing. Reported by Oliver on
2026-09-09; the fetcher has thrown such a socket away before asking since.

**Letting go before the host does, rather than after.** Throwing a connection
away at the next ask still left the host to close it first; Qt says so as it
notices: `QIODevice::read (QSslSocket): device not open`. Reported by Oliver
on 2026-10-13, twice in one pause, 29.99 and 29.97 seconds after each host's
last ask. Reproduced the same day against ListenBrainz on a thread resting the
way a run rests: the warning at 30.17 seconds with nothing let go of; none at
all with the connections let go of at fifteen. A run sleeps through its pauses
on its own thread, which is the thread its connections belong to, so the pause
is where they are let go of.
"""

from __future__ import annotations

import time
from typing import Protocol

from stellody.application.asking import Pause

HOST_LETS_GO_AFTER_S = 30.0
IDLE_LIMIT_S = HOST_LETS_GO_AFTER_S / 2


class Idling(Protocol):
    """Something holding connections that can be let go of once idle."""

    def let_go_if_idle(self) -> None:
        """Let go of this thread's connections if they have stood too long."""


def resting(holders: tuple[Idling, ...], sleep: Pause = time.sleep) -> Pause:
    """A run's pause that lets idle connections go before each slice of it.

    Asked on every slice, which is cheap: a holder with nothing idle does
    nothing, so a short wait between refusals is unchanged.
    """

    def rest(seconds: float) -> None:
        """Let go of what has stood too long, then wait."""
        for holder in holders:
            holder.let_go_if_idle()
        sleep(seconds)

    return rest
