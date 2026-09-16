"""Writing down every moment the output device had nothing to play.

Reported on 2026-09-16: static during playback while a Nuitka build held every
core. The suspicion is that the feeder thread is starved of time and the device
runs out of samples. That is a hypothesis until it is measured; this is the
measurement.

**PortAudio's own answer cannot be trusted for it.** Measured on 2026-09-16 on
a shared WASAPI stream: a write answered "not underflowed" after the device had
been left for 0.2, 0.5 and 1.0 seconds against a 23 ms buffer. It is not read.

A device can run dry in two places, so both are watched.

- **Between writes.** A freshly started stream has its whole buffer free (1036
  frames on that device). While writes kept up the room was measured between
  53 and 815 frames; after every gap it was the whole buffer again. A write
  that finds the whole buffer free follows a device with nothing left to play.
  The time the feeder was away is split into reading, shaping and waiting to
  run, since each points at a different cause.
- **Inside a write.** A write of 4096 frames into a 23 ms buffer is not one
  copy: PortAudio tops the buffer up as it drains, so the thread must be woken
  every twenty milliseconds or so until the block is in. A thread woken late
  there lets the device run dry mid-write, which the check between writes
  cannot see. This is what the first real report looked like: one empty buffer
  with the feeder away 1 ms, while the static went on. It is caught by
  arithmetic rather than by asking: a device cannot play faster than real
  time, so a write taking longer than the samples it carried plus the samples
  already buffered had a silence in it of at least the difference.

The clock is `perf_counter`. `monotonic` moves in 15.6 ms steps on Windows,
which is most of the buffer being measured.
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
    """Counts the moments the device had nothing to play; notes each one."""

    def __init__(
        self,
        note: Callable[[str], None] = _nothing,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._note = note
        self._clock = clock
        self._last: float | None = None
        self._reading_from = 0.0
        self._shaping_from = 0.0
        self._writing_from = 0.0
        self._capacity = 0
        self._buffered = 0
        self._block_frames = 0
        self._frame = 0
        self._sample_rate = 0
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
        since the write itself blocks for most of a block by design.
        """
        now = self._clock()
        self._writing_from = now
        self._buffered = max(0, self._capacity - room)
        self._block_frames = block_frames
        self._frame = frame
        self._sample_rate = sample_rate
        previous = self._last
        if previous is None or self._capacity <= 0 or room < self._capacity:
            return
        away = _milliseconds(now - previous)
        read = _milliseconds(self._shaping_from - self._reading_from)
        shaped = _milliseconds(now - self._shaping_from)
        self._record(
            f"the device's {self._buffered_ms(self._capacity)} ms buffer had run "
            f"dry before a block of {block_frames} frames; the feeder was away "
            f"{away} ms ({read} ms reading, {shaped} ms shaping, "
            f"{away - read - shaped} ms waiting to run)"
        )

    def written(self) -> None:
        """Mark a write returned; note it if it must have held a silence.

        Nothing is judged for a write whose stream has no buffer reading, nor
        for the first write after a start, which fills an empty buffer.
        """
        now = self._clock()
        previous = self._last
        self._last = now
        if previous is None or self._capacity <= 0 or self._sample_rate <= 0:
            return
        took = now - self._writing_from
        carried = self._block_frames + self._buffered
        silent = took - carried / self._sample_rate
        if silent <= 0:
            return
        self._record(
            f"the device ran dry for at least {_milliseconds(silent)} ms inside a "
            f"write of {self._block_frames} frames; the write took "
            f"{_milliseconds(took)} ms with {self._buffered_ms(self._buffered)} ms "
            f"already buffered"
        )

    def _buffered_ms(self, frames: int) -> int:
        """A count of frames at the current rate, in whole milliseconds."""
        return frames * MILLISECONDS_PER_SECOND // self._sample_rate

    def _record(self, what: str) -> None:
        """Count one dropout and write it down with where in the track it was."""
        self.count += 1
        where = clock_text(self._frame, self._sample_rate)
        self._note(f"playback dropout {self.count} at {where}: {what}")
