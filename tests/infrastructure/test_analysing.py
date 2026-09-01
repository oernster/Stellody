"""The transform, checked against tones whose answer is known in advance.

A synthesised sine at a stated frequency and a stated level is the one signal
where the right answer can be written down rather than eyeballed, so that is
what this measures against: the band it should light, then how tall.

The block is checked for damage in the same breath. A visualiser that altered
a sample would break the bit perfect claim silently, in a way nobody would hear
until they went looking for it.
"""

from __future__ import annotations

import numpy as np

from stellody.domain.equalising import BAND_FREQUENCIES
from stellody.domain.spectrum import BAR_COUNT, BARS_PER_FILTER, EMPTY, SILENT_BANDS
from stellody.infrastructure.analysing import BlockAnalyser, full_scale_of

CD_RATE = 44100
BLOCK = 4096
INT16_FULL = 32767
# Six decibels is a tenth of the sixty decibel range, so halving a tone should
# take its bar down by that much and no more.
HALF_STEP_HEIGHT = 0.1


def tone(hz: float, amplitude: float = 1.0, channels: int = 2) -> np.ndarray:
    """One block of a sine at `hz`, as int16 at the stated fraction of full."""
    steps = np.arange(BLOCK) / CD_RATE
    mono = np.sin(2 * np.pi * hz * steps) * amplitude
    if channels == 1:
        return (mono * INT16_FULL).astype(np.int16)
    return (np.stack([mono] * channels, axis=1) * INT16_FULL).astype(np.int16)


def loudest(heights: tuple[float, ...]) -> int:
    """Which band came out tallest."""
    return max(range(len(heights)), key=lambda band: heights[band])


class TestWhichBandLightsUp:
    def test_a_tone_lights_a_bar_belonging_to_its_own_filter(self) -> None:
        """The claim the whole feature rests on: a slider owns its pair of bars.

        A tone at the filter's own centre lands on the split between its two
        bars, so which of the pair it lights is the transform's business; that
        it is one of THAT filter's pair is the thing that must hold.
        """
        analyser = BlockAnalyser(CD_RATE, BLOCK)
        for band, centre in enumerate(BAND_FREQUENCIES):
            if centre * 2 > CD_RATE:
                continue
            lit = loudest(analyser.measure(tone(centre)))
            assert lit // BARS_PER_FILTER == band, centre

    def test_there_is_one_height_for_each_bar(self) -> None:
        assert len(BlockAnalyser(CD_RATE, BLOCK).measure(tone(1000))) == BAR_COUNT


class TestHowTallItIs:
    def test_a_full_scale_tone_reaches_the_top(self) -> None:
        """If the window reference were wrong every bar would be short."""
        heights = BlockAnalyser(CD_RATE, BLOCK).measure(tone(1000))
        assert max(heights) > 0.99

    def test_halving_a_tone_drops_it_by_a_tenth_of_the_strip(self) -> None:
        """Six decibels of a sixty decibel range, which is what a half is."""
        analyser = BlockAnalyser(CD_RATE, BLOCK)
        full = max(analyser.measure(tone(1000)))
        half = max(analyser.measure(tone(1000, amplitude=0.5)))
        assert abs((full - half) - HALF_STEP_HEIGHT) < 0.01

    def test_digital_silence_reads_as_silence(self) -> None:
        analyser = BlockAnalyser(CD_RATE, BLOCK)
        assert analyser.measure(np.zeros((BLOCK, 2), np.int16)) == SILENT_BANDS


class TestBlocksItIsHandedAnyway:
    def test_a_mono_block_measures_the_same_as_a_stereo_one(self) -> None:
        """A file with one channel is a file, not a fault."""
        analyser = BlockAnalyser(CD_RATE, BLOCK)
        stereo = analyser.measure(tone(1000))
        mono = analyser.measure(tone(1000, channels=1))
        assert loudest(mono) == loudest(stereo)

    def test_a_float_block_is_already_on_the_scale_the_domain_wants(self) -> None:
        analyser = BlockAnalyser(CD_RATE, BLOCK)
        steps = np.arange(BLOCK) / CD_RATE
        floats = np.sin(2 * np.pi * 1000 * steps).astype(np.float32)
        assert max(analyser.measure(floats)) > 0.99

    def test_an_empty_block_is_refused_rather_than_measured(self) -> None:
        """A stream torn down mid-read hands one of these over."""
        analyser = BlockAnalyser(CD_RATE, BLOCK)
        assert analyser.measure(np.zeros((0, 2), np.int16)) is None

    def test_a_short_block_is_refused_rather_than_read_as_silence(self) -> None:
        """Every track ends on one, since the last read is whatever is left.

        Reporting silence for it would blank the display at the end of every
        piece, which is what this was doing before it was measured end to end.
        """
        analyser = BlockAnalyser(CD_RATE, BLOCK)
        assert analyser.measure(np.zeros((100, 2), np.int16)) is None

    def test_full_scale_is_read_from_the_block_rather_than_assumed(self) -> None:
        assert full_scale_of(np.zeros(1, np.int16)) == INT16_FULL
        assert full_scale_of(np.zeros(1, np.int32)) == np.iinfo(np.int32).max
        assert full_scale_of(np.zeros(1, np.float32)) == 1.0


class TestWhatItMustNotDo:
    def test_measuring_leaves_the_block_exactly_as_it_found_it(self) -> None:
        """The bit perfect claim, held here rather than only upstream of it."""
        analyser = BlockAnalyser(CD_RATE, BLOCK)
        block = tone(1000)
        before = block.copy()
        analyser.measure(block)
        assert np.array_equal(block, before)

    def test_a_low_rate_stream_still_reports_every_band(self) -> None:
        """The top bands have no content left, so they read empty, not wrongly.

        A band whose whole octave sits above the Nyquist frequency has nothing
        to measure. What it must not do is report the noise at the very top of
        the transform as though it were music up there.
        """
        analyser = BlockAnalyser(8000, BLOCK)
        heights = analyser.measure(np.zeros((BLOCK, 2), np.int16))
        assert len(heights) == BAR_COUNT
        assert set(heights) == {EMPTY}
