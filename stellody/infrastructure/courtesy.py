"""How Stellody behaves towards a service it is a guest of.

Three services are now asked things: the archive that knows about covers, the
catalogue that knows what an artist released and the one that knows who
resembles whom. They are asked by different modules for different reasons;
every one of them has to identify itself the same way and wait the same gap.

**So the courtesy lives here rather than in each of them.** A user agent
written twice is two user agents the day one is edited; a gap honoured in
one client and forgotten in another is a client that gets the whole
application refused.

Nothing here opens a connection. It says who is asking and when the next ask is
allowed; the modules that hold a socket are named in the offline structural
test and are each granted their permission in front of somebody.
"""

from __future__ import annotations

import time

from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.shared.version import APP_NAME, __version__

# What the terms mean by contact: a URL or an address whoever runs the service
# can reach the author of the application at, sent with every request so a
# misbehaving client can be told about rather than merely blocked. An address
# kept for this, since the project's own site is somewhere to read rather than
# somewhere anyone can be reached. It goes out with every request; it is here
# for that and for nothing else.
CONTACT = "stellody@hotmail.com"
USER_AGENT = f"{APP_NAME}/{__version__} ( {CONTACT} )"
# One request a second is what the terms ask for, at MusicBrainz and at
# ListenBrainz alike. A tenth over it is not generosity; it is the margin that
# stops a clock rounding down into a refusal.
REQUEST_GAP_S = 1.1
TIMEOUT_S = 20
# How long a wait between requests may block before the question is asked
# again. The gaps the terms ask for are seconds long; sitting through one
# after a cancel is the same defect as sitting through a read.
SLEEP_SLICE_S = 0.25
# What a refusal looks like: too many requests, else the service declining to
# answer this one. Both mean ask again rather than tell the listener anything.
REFUSAL_CODES = frozenset({429, 503})


class Waiter:
    """A wait somebody can give up on, taken in slices.

    A wait is as uncancellable as a read when it is taken in one go, while the
    terms ask for gaps of over a second between requests. Sliced, a cancel is
    noticed within a slice rather than at the end of the gap.

    An object rather than a function so the slicing has one home: what a test
    injects here is asked for a whole gap and answers however it likes, which
    keeps the tests about the gaps the terms ask for rather than about how
    this happens to take them.
    """

    def __init__(self, sleeper=time.sleep) -> None:
        self._sleeper = sleeper

    def hold(self, seconds: float, wanted: Wanted) -> bool:
        """Wait that long; False where somebody gave up part way through."""
        left = seconds
        while left > 0:
            if not wanted():
                return False
            take = min(SLEEP_SLICE_S, left)
            self._sleeper(take)
            left -= take
        return wanted()


class Gate:
    """Lets one request through at a time, no faster than the terms allow.

    One gate stands in front of one service. Two services are two gates, since
    a gap owed to one says nothing about the other.
    """

    def __init__(
        self, gap_s: float = REQUEST_GAP_S, waiter: Waiter | None = None
    ) -> None:
        self._gap_s = gap_s
        self._last = 0.0
        self._waiter = waiter if waiter is not None else Waiter()

    def wait(self, wanted: Wanted = always_wanted) -> bool:
        """Hold until this request is allowed to go; False if nobody waits.

        The clock is stamped either way, since the gap is about the service
        rather than about who is listening: a request abandoned during the
        wait still has to leave the next one its full gap.
        """
        due = self._last + self._gap_s - time.monotonic()
        going = self._waiter.hold(due, wanted) if due > 0 else wanted()
        self._last = time.monotonic()
        return going
