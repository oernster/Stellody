"""Writing down every block the device ran dry before it was handed.

Reported on 2026-09-16: static during playback while another program's build
held every core, never permanent. The suspicion is that the feeder thread is
starved of time and the device runs out of samples before the next block
arrives. That is a hypothesis until it is measured; this is the measurement.

**PortAudio's own answer cannot be trusted for it.** A write is supposed to
answer underflowed when the device had already run dry. Measured on
2026-09-16 on a shared WASAPI stream: it answered no after the device had been
left for 0.2, 0.5 and 1.0 seconds, against a buffer holding 23 ms. The first
version of this module trusted that answer and reported nothing through a run
full of static.

**What is read instead is the room in the device's buffer.** Straight after a
stream starts, the room is the whole buffer: nothing has been written yet.
Measured on the same device, the room then moved between 53 and 815 frames
while writes kept up; it came back to the whole buffer, 1036 frames, after
every gap. So a write that finds the whole buffer free follows a device that
had nothing left to play. The underflow answer is not read at all, since it
was measured to say nothing on the path this application plays through.

Each dropout is noted with a running count, where in the track it happened
and how long the feeder was away from the device, split into reading, shaping
and waiting to run; each of the three points at a different cause.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from stellody.domain.playback import clock_text

MILLISECONDS_PER_SECOND = 1000


def _milliseconds(seconds: float) -> int:
    """A span of seconds in whole milliseconds."""
    return round(seconds * MILLISECONDS_PER_SECOND)


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
        self._reading_from = 0.0
        self._shaping_from = 0.0
        self._capacity = 0
        self.count = 0

    def started(self, capacity: int) -> None:
        """Take the room a freshly started stream has: its whole buffer.

        Forgets the last write too, so a pause is not reported as a late one
        and the first write into an empty buffer is not reported at all.
        """
        self._capacity = capacity
        self._last = None

    def reading(self) -> None:
        """Mark the moment the feeder starts reading the next block."""
        self._reading_from = self._clock()

    def shaping(self) -> None:
        """Mark the moment the block is read and the equalizer starts on it."""
        self._shaping_from = self._clock()

    def writing(
        self, room: int, block_frames: int, frame: int, sample_rate: int
    ) -> None:
        """Look at the room just before a write; note it if the buffer was empty.

        The time away is measured from the moment the write before RETURNED,
        since the write itself blocks for most of a block by design. It is
        split three ways, because each points somewhere different: reading is
        the file and the decoder, so a slow disk; shaping is the equalizer; the
        rest is the thread ready to run and not being run.
        """
        previous = self._last
        if previous is None:
            return
        if self._capacity <= 0 or room < self._capacity:
            return
        self.count += 1
        now = self._clock()
        away = _milliseconds(now - previous)
        read = _milliseconds(self._shaping_from - self._reading_from)
        shaped = _milliseconds(now - self._shaping_from)
        buffered = self._capacity * MILLISECONDS_PER_SECOND // sample_rate
        self._note(
            f"playback dropout {self.count} at {clock_text(frame, sample_rate)}: "
            f"the device's {buffered} ms buffer had run dry before a block of "
            f"{block_frames} frames; the feeder was away {away} ms "
            f"({read} ms reading, {shaped} ms shaping, "
            f"{away - read - shaped} ms waiting to run)"
        )

    def written(self) -> None:
        """Mark the moment a write returned, which the next gap is taken from."""
        self._last = self._clock()
