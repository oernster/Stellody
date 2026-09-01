"""Running a cascade of biquads over successive blocks of samples.

The domain designs the sections; this applies them and holds their memory,
which is the one thing that has to survive from one block to the next. A filter
restarted at every boundary would tick at every boundary.

**One pass over the samples, every section applied to each in turn.** Walking
the array once per section was measured at 25.4 milliseconds for ten bands
against 6.9 for this, where a block is 92.9 milliseconds of audio: the cost is
the indexing rather than the arithmetic, so the fewer passes over the array the
better. The samples are taken out to a Python list for the same reason, since
reading one element of a numpy array costs several times what reading one
element of a list does.

Nothing here knows what a frequency is. It is handed coefficients and it
multiplies.
"""

from __future__ import annotations

import numpy as np

from stellody.domain.equalising import Biquad

FLOAT_LIMIT = 1.0


class BiquadCascade:
    """A run of second-order sections, plus the memory they carry between blocks."""

    def __init__(self, sections: tuple[Biquad, ...] = ()) -> None:
        self._sections = sections
        self._memory: list[list[tuple[float, float]]] = []
        self._channels = 0

    @property
    def sections(self) -> tuple[Biquad, ...]:
        """The sections being applied; empty when this changes nothing."""
        return self._sections

    def reset(self) -> None:
        """Forget what has been through, which a seek or a new track wants."""
        self._memory = [
            [(0.0, 0.0)] * len(self._sections) for _ in range(self._channels)
        ]

    def _sized_for(self, channels: int) -> None:
        """Give each channel its own memory, once the block says how many."""
        if channels != self._channels:
            self._channels = channels
            self.reset()

    def process(self, block: np.ndarray) -> np.ndarray:
        """The block with every section applied, in one pass over the samples.

        An empty cascade hands the block straight back rather than copying it,
        so a flat equalizer costs nothing at all and an exclusive stream stays
        genuinely bit perfect.
        """
        if not self._sections:
            return block
        self._sized_for(block.shape[1])
        # Gathered in floating point and only then put back into the block's
        # own format: a lift can ask for more than an integer sample holds,
        # and writing it there before clipping overflows rather than clips.
        filtered = np.empty(block.shape, dtype="float64")
        for channel in range(block.shape[1]):
            filtered[:, channel] = self._channel(block[:, channel].tolist(), channel)
        limit = self._limit(block.dtype)
        return np.clip(filtered, -limit, limit).astype(block.dtype)

    def _channel(self, samples: list[float], channel: int) -> list[float]:
        """One channel through every section, transposed direct form two.

        That form is chosen for its memory: two numbers a section, updated as
        each sample leaves rather than a window of the samples themselves, so
        what has to be carried between blocks is a pair of floats and not a
        tail of the music.
        """
        memory = self._memory[channel]
        for position, sample in enumerate(samples):
            for index, section in enumerate(self._sections):
                first, second = memory[index]
                out = section.b0 * sample + first
                memory[index] = (
                    section.b1 * sample - section.a1 * out + second,
                    section.b2 * sample - section.a2 * out,
                )
                sample = out
            samples[position] = sample
        return samples

    @staticmethod
    def _limit(dtype: np.dtype) -> float:
        """The largest sample this format holds, so a boost cannot wrap round.

        A lift can ask for more than the format can carry. Clipping says so
        quietly at the ceiling, where letting an integer overflow would turn a
        loud passage into noise rather than into a loud passage.
        """
        if np.issubdtype(dtype, np.floating):
            return FLOAT_LIMIT
        return float(np.iinfo(dtype).max)
