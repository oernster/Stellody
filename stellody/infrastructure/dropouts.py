"""Writing down every block the device ran dry before it was handed.

Reported on 2026-09-16: a few seconds of static during playback while another
program's build held every core, never permanent. The cause is not known. The
suspicion is that the feeder thread is starved of time and the device runs out
of samples before the next block arrives. That is a hypothesis until it is
measured; this is the measurement.

PortAudio says so itself: a write that finds the device already emptied
answers underflowed rather than raising. Each one is noted with a running
count and how long it had been since the write before, which is what tells a
starved feeder (a long gap) from a device that emptied for some other reason
(a gap no longer than a block takes to play).

The note is handed in rather than chosen here, so the engine can be built
without one in a test and the account lands wherever the application keeps
its others.
"""

from __future__ import annotations

import time
from collections.abc import Callable

MILLISECONDS_PER_SECOND = 1000


def _nothing(_message: str) -> None:
    """Where the notes go when nobody asked for them."""


class DropoutWatch:
    """Counts the writes that found the device already empty; notes each one."""

    def __init__(
        self,
        note: Callable[[str], None] = _nothing,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._note = note
        self._clock = clock
        self._last: float | None = None
        self.count = 0

    def started(self) -> None:
        """Forget the last write, so a pause is not reported as a late one."""
        self._last = None

    def wrote(self, underflowed: bool, block_frames: int, sample_rate: int) -> None:
        """Record one write; note it when the device had already run dry."""
        now = self._clock()
        previous = self._last
        self._last = now
        if not underflowed:
            return
        self.count += 1
        gap = "the first write" if previous is None else self._gap(now - previous)
        playing = block_frames * MILLISECONDS_PER_SECOND // max(sample_rate, 1)
        self._note(
            f"playback dropout {self.count}: the device ran dry before a block "
            f"of {block_frames} frames ({playing} ms) arrived; {gap}"
        )

    @staticmethod
    def _gap(seconds: float) -> str:
        """How long the feeder took since the write before, in words."""
        waited = round(seconds * MILLISECONDS_PER_SECOND)
        return f"{waited} ms since the write before"
