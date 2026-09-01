"""Measuring the blocks on their way out, without getting in their way.

The transform belongs here rather than in the domain for the same reason the
filtering does: it reads the arrays the device is being handed, where numpy
makes reading them cost nothing worth counting. What a magnitude MEANS
once measured is arithmetic over frequencies and lives in `domain/spectrum.py`,
which this calls; the direction is the usual one, infrastructure reaching in.

**It never touches the block.** Every step here produces a new array: taking
the mean across channels, dividing by full scale, multiplying by the window.
The block written to the device is the same object the equalizer handed over,
which is what keeps the bit perfect claim true with the display running.

**It runs after the write, not before it.** The feeder's job is to keep a
device fed; the surest way not to delay that is to be reached only once the
block has gone. A measurement that arrives late is a frame nobody misses; a
block that arrives late is a gap everybody hears.

**Peak within a band, not the average across it.** A band is an octave wide, so
averaging a loud partial with the quiet bins beside it reports a band quieter
than anything actually in it. The waveform module took the same view for the
same reason: an average of a busy thing and a silent thing looks like neither.

**Full scale is the window's, not one.** A Hann window at full scale sums to
half its length rather than to its length, so a full scale sine measures that
much and not more. Getting this wrong does not fail; it draws every bar short
by a fixed amount for ever, which is why it is worked out rather than guessed.
"""

from __future__ import annotations

import numpy as np

from stellody.domain.spectrum import band_edges, heights

# A Hann window sums to half its length, so a full scale sine through it
# measures that. Named rather than written into the arithmetic, since a
# different window would need a different number and nothing else.
_WINDOW_GAIN = 2.0

# The scale a sample of each width reaches. Read from the array rather than
# written down per format: a signed integer of any width runs to one less than
# a power of two, while a float block is already on the scale the domain wants.
_FLOAT_FULL_SCALE = 1.0

_STEREO_AXIS = 1


def full_scale_of(block: np.ndarray) -> float:
    """What counts as the loudest possible sample in a block of this kind."""
    if np.issubdtype(block.dtype, np.integer):
        return float(np.iinfo(block.dtype).max)
    return _FLOAT_FULL_SCALE


class BlockAnalyser:
    """Turns one block of audio into a height for each of the equalizer's bands.

    Built once per stream, because the band edges and the window depend on the
    sample rate and the block size rather than on the music. Rebuilding either
    per block would be the one part of this that cost anything.
    """

    def __init__(self, sample_rate: int, block_frames: int) -> None:
        self._window = np.hanning(block_frames)
        self._reference = float(self._window.sum()) / _WINDOW_GAIN
        self._bins = self._bins_for(sample_rate, block_frames)

    @staticmethod
    def _bins_for(sample_rate: int, block_frames: int) -> tuple[tuple[int, int], ...]:
        """The first and last transform bin belonging to each band.

        Worked out once. A band whose edges fall between two bins takes the one
        bin its centre lands in rather than none, since a band that measures
        nothing draws a bar that is always flat and reads as a broken display.
        """
        spacing = sample_rate / block_frames
        highest = block_frames // 2
        found = []
        for low, high in band_edges(sample_rate):
            first = min(int(low / spacing), highest)
            last = min(int(high / spacing), highest)
            found.append((first, max(first, last)))
        return tuple(found)

    def measure(self, block: np.ndarray) -> tuple[float, ...] | None:
        """One block's bands as heights from 0 to 1; nothing when it cannot.

        A block that is not the length the window was built for is refused
        rather than measured. Every track ends on one of those, since the last
        read is whatever was left over; a track whose final block reported
        silence would blank the display at the end of every piece. Refusing
        leaves the last real measurement standing and lets it fall away on its
        own, which is what the end of a track actually sounds like.

        Padding the short block instead was the other option and is worse: it
        would report a quieter band than the music held, which is a measurement
        that is wrong rather than absent.
        """
        if block.size == 0:
            return None
        mono = block if block.ndim == 1 else block.mean(axis=_STEREO_AXIS)
        scaled = mono.astype(np.float64) / full_scale_of(block)
        if scaled.size != self._window.size:
            return None
        magnitudes = np.abs(np.fft.rfft(scaled * self._window))
        # No emptiness check: `_bins_for` never returns a band with no bin
        # in it, which is the whole reason it takes a max against itself.
        peaks = tuple(
            float(magnitudes[first : last + 1].max()) for first, last in self._bins
        )
        return heights(peaks, self._reference)
