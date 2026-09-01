"""What a band covers, what a magnitude means and how a bar falls.

All of it arithmetic, so all of it checkable with nothing installed and no
device in the room, which is the whole reason this half is split from the
transform that feeds it.
"""

from __future__ import annotations

import itertools
import math

from stellody.domain.equalising import BAND_COUNT, BAND_FREQUENCIES
from stellody.domain.spectrum import (
    BAR_COUNT,
    BARS_PER_FILTER,
    CEILING_DB,
    EMPTY,
    FALL_PER_SECOND,
    FLOOR_DB,
    FULL,
    SILENT_BANDS,
    as_decibels,
    as_height,
    band_edges,
    fallen,
    heights,
)

CD_RATE = 44100
# A reference of one means a magnitude reads as its own ratio, which keeps the
# decibel arithmetic legible in a test without a window function in the way.
UNIT = 1.0
# Half of full scale, which is 20 log10 of a half. Written out rather than
# rounded to six, since the test would then be checking the rounding.
HALF_STEP_DB = -6.0206


class TestWhatABandCovers:
    def test_there_are_two_bars_for_each_band_the_equalizer_has(self) -> None:
        """The point of the whole thing: a slider owns a pair of bars."""
        assert BAR_COUNT == BAND_COUNT * BARS_PER_FILTER
        assert len(band_edges(CD_RATE)) == BAR_COUNT
        assert len(SILENT_BANDS) == BAR_COUNT

    def test_each_pair_covers_exactly_the_octave_its_filter_acts_on(self) -> None:
        """Split in half at the filter's own centre, so nothing is invented."""
        edges = band_edges(CD_RATE)
        for band, centre in enumerate(BAND_FREQUENCIES[:-1]):
            low, split = edges[band * BARS_PER_FILTER]
            again, high = edges[band * BARS_PER_FILTER + 1]
            assert math.isclose(split, centre, rel_tol=1e-9), "split at the centre"
            assert math.isclose(again, centre, rel_tol=1e-9), "and taken up there"
            assert math.isclose(high / low, 2.0, rel_tol=1e-9), "an octave in all"

    def test_no_edge_exists_that_the_equalizer_does_not_have(self) -> None:
        """Every split point is a frequency a slider is already named for."""
        centres = set(BAND_FREQUENCIES)
        splits = {
            round(high) for _low, high in band_edges(CD_RATE)[:-BARS_PER_FILTER:2]
        }
        assert splits <= centres

    def test_neighbours_meet_rather_than_leaving_a_gap(self) -> None:
        """Bands an octave wide about centres an octave apart share their edges.

        Within the rounding of the ISO centres themselves, which are not exact
        doublings: 62 doubles to 124 while the next centre is named 125. So the
        edges land within a percent of each other rather than on each other,
        which is a seam nothing can fall through and not a claim of exactness.
        """
        edges = band_edges(CD_RATE)
        for (_, high), (low, _) in itertools.pairwise(edges):
            assert math.isclose(high, low, rel_tol=0.01)

    def test_the_bars_run_low_to_high(self) -> None:
        """Drawn left to right in that order, so they must arrive in it."""
        edges = band_edges(CD_RATE)
        assert [low for low, _high in edges] == sorted(low for low, _high in edges)

    def test_the_top_band_stops_at_the_nyquist_frequency(self) -> None:
        """There is no content above it, so a band reaching past it reads noise."""
        limit = CD_RATE / 2
        for _low, high in band_edges(CD_RATE):
            assert high <= limit
        assert band_edges(CD_RATE)[-1][1] == limit

    def test_a_band_wholly_above_the_limit_collapses_rather_than_inverting(
        self,
    ) -> None:
        """At a low sample rate the top bands have nothing left to cover.

        Clamped to their own low edge rather than to something beneath it: a
        band whose high edge fell below its low one would ask a transform for
        a range that runs backwards.
        """
        for low, high in band_edges(8000):
            assert high >= low


class TestWhatAMagnitudeMeans:
    def test_full_scale_is_the_ceiling(self) -> None:
        assert as_decibels(UNIT, UNIT) == CEILING_DB
        assert as_height(CEILING_DB) == FULL

    def test_half_scale_is_six_decibels_down(self) -> None:
        assert math.isclose(as_decibels(0.5, UNIT), HALF_STEP_DB, abs_tol=0.01)

    def test_silence_is_the_floor_rather_than_an_error(self) -> None:
        """The logarithm of nothing is undefined; digital silence is nothing."""
        assert as_decibels(0.0, UNIT) == FLOOR_DB
        assert as_height(FLOOR_DB) == EMPTY

    def test_a_reference_of_nothing_is_the_floor_too(self) -> None:
        """Dividing by it would be the error this exists to avoid."""
        assert as_decibels(UNIT, 0.0) == FLOOR_DB

    def test_anything_below_the_floor_is_silence_rather_than_negative(self) -> None:
        """A bar cannot be drawn shorter than empty."""
        assert as_decibels(1e-9, UNIT) == FLOOR_DB
        assert as_height(FLOOR_DB - 20) == EMPTY

    def test_anything_above_the_ceiling_is_full_rather_than_over(self) -> None:
        """A bar cannot be drawn taller than the strip."""
        assert as_height(CEILING_DB + 6) == FULL

    def test_the_middle_of_the_range_is_the_middle_of_the_strip(self) -> None:
        assert math.isclose(as_height(FLOOR_DB / 2), 0.5, abs_tol=1e-9)

    def test_every_band_is_converted_at_once(self) -> None:
        got = heights((UNIT, 0.0), UNIT)
        assert got == (FULL, EMPTY)


class TestHowABarFalls:
    def test_a_bar_rises_to_whatever_it_is_given_at_once(self) -> None:
        """The transient is the thing worth seeing, so nothing eases up to it."""
        assert fallen((EMPTY,), (FULL,), 1.0) == (FULL,)

    def test_a_bar_falls_at_the_stated_rate(self) -> None:
        one_second = fallen((FULL,), (EMPTY,), 1.0)[0]
        assert math.isclose(one_second, FULL - FALL_PER_SECOND, abs_tol=1e-9) or (
            one_second == EMPTY
        )
        half = fallen((FULL,), (EMPTY,), 0.5)[0]
        assert half > one_second or half == EMPTY

    def test_a_bar_never_falls_past_what_was_measured(self) -> None:
        """It is falling TOWARDS the measurement, not through it."""
        assert fallen((FULL,), (0.9,), 10.0) == (0.9,)

    def test_no_time_passing_moves_nothing_down(self) -> None:
        assert fallen((FULL,), (EMPTY,), 0.0) == (FULL,)

    def test_time_running_backwards_moves_nothing_down_either(self) -> None:
        """A clock is never read here, so this can only be a caller's mistake.

        Treated as no time at all rather than as a rise: a bar that grew
        because a number arrived negative would be showing something that was
        never measured.
        """
        assert fallen((FULL,), (EMPTY,), -1.0) == (FULL,)

    def test_every_bar_falls_on_its_own(self) -> None:
        got = fallen((FULL, EMPTY), (EMPTY, FULL), 0.1)
        assert got[0] < FULL
        assert got[1] == FULL
