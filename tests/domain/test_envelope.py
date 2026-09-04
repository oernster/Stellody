"""The shape of a track and the arithmetic that draws part of it.

A cue-sheet album is one file holding many tracks, so a file is measured once
and each track takes its own share. That sharing is the part with edges: a
track at the very end of a file, a track too short to fill a bucket, a window
narrower than the measurement and one wider than it.
"""

from __future__ import annotations

import pytest

from stellody.domain.waveform import (
    LEAST_BUCKETS,
    MOST_BUCKETS,
    Envelope,
    buckets_for,
    envelope_from,
)

SAMPLE_RATE = 44100

WHOLE_FILE_FRAMES = 1000


def _ramp(buckets: int) -> Envelope:
    """An envelope rising from quiet to loud, so a slice is recognisable."""
    return Envelope(levels=tuple(index / buckets for index in range(buckets)))


class TestMaking:
    def test_an_envelope_needs_a_bucket(self) -> None:
        with pytest.raises(ValueError):
            Envelope(levels=())

    @pytest.mark.parametrize("peak", (-0.1, 1.1))
    def test_a_peak_outside_the_scale_is_refused(self, peak: float) -> None:
        with pytest.raises(ValueError):
            Envelope(levels=(peak,))

    def test_measured_levels_beyond_full_scale_are_flattened_to_it(self) -> None:
        """An intersample peak is a fact about the audio, not an error."""
        assert envelope_from((0.5, 1.4, -0.2)).levels == (0.5, 1.0, 0.0)

    def test_it_knows_its_own_size_and_its_loudest_point(self) -> None:
        envelope = Envelope(levels=(0.1, 0.9, 0.4))
        assert envelope.buckets == 3
        assert envelope.loudest == pytest.approx(0.9)


class TestTakingATracksShare:
    def test_the_first_half_of_a_file_is_the_first_half_of_the_shape(self) -> None:
        part = _ramp(10).between(0, WHOLE_FILE_FRAMES // 2, WHOLE_FILE_FRAMES)
        assert part.buckets == 5
        assert part.levels[0] == pytest.approx(0.0)

    def test_the_last_track_of_a_file_reaches_its_end(self) -> None:
        part = _ramp(10).between(
            WHOLE_FILE_FRAMES // 2, WHOLE_FILE_FRAMES, WHOLE_FILE_FRAMES
        )
        assert part.levels[-1] == pytest.approx(0.9)

    def test_a_region_running_past_the_file_stops_at_its_end(self) -> None:
        """A frame count off by a rounding is not a reason to lose the shape."""
        part = _ramp(10).between(0, WHOLE_FILE_FRAMES * 3, WHOLE_FILE_FRAMES)
        assert part.buckets == 10

    def test_a_region_starting_before_the_file_starts_at_its_beginning(self) -> None:
        part = _ramp(10).between(-500, WHOLE_FILE_FRAMES, WHOLE_FILE_FRAMES)
        assert part.buckets == 10

    def test_a_track_too_short_to_fill_a_bucket_still_has_a_shape(self) -> None:
        """A coarse shape beats no shape; the drawing has to put something up."""
        part = _ramp(10).between(0, 1, WHOLE_FILE_FRAMES)
        assert part.buckets == 1

    def test_a_file_covering_no_frames_has_no_shape_to_share_out(self) -> None:
        with pytest.raises(ValueError):
            _ramp(10).between(0, 10, 0)


class TestDrawing:
    def test_a_window_the_size_of_the_measurement_draws_it_as_it_is(self) -> None:
        envelope = Envelope(levels=(0.1, 0.2, 0.3))
        assert envelope.scaled_to(3) == pytest.approx((0.1, 0.2, 0.3))

    def test_a_narrow_window_keeps_the_loudest_of_what_it_covers(self) -> None:
        """Averaging would flatten the transient that makes a shape readable."""
        envelope = Envelope(levels=(0.1, 0.9, 0.2, 0.3))
        assert envelope.scaled_to(2) == pytest.approx((0.9, 0.3))

    def test_a_wide_window_stretches_rather_than_inventing_detail(self) -> None:
        envelope = Envelope(levels=(0.2, 0.8))
        assert envelope.scaled_to(4) == pytest.approx((0.2, 0.2, 0.8, 0.8))

    def test_one_column_is_the_loudest_point_in_the_whole_shape(self) -> None:
        assert Envelope(levels=(0.1, 0.7, 0.3)).scaled_to(1) == pytest.approx((0.7,))

    def test_a_drawing_with_no_columns_is_refused(self) -> None:
        with pytest.raises(ValueError):
            Envelope(levels=(0.5,)).scaled_to(0)


class TestHowFinelyASourceIsMeasured:
    """A cue-sheet album is one file holding a whole record.

    Measured on a real one, BT's Still Life in Motion, 55.7 minutes of nine
    tracks: a fixed two thousand buckets made each of them 1671 milliseconds,
    so the 3:20 opening track took 120 buckets and drew across two thousand
    pixels as blocks seventeen wide. The resolution belongs to the music, so
    the count follows how much music there is.
    """

    def test_a_long_file_is_measured_finely_enough_for_one_track(self) -> None:
        """The whole of what this is for."""
        album = buckets_for(SAMPLE_RATE * 3342, SAMPLE_RATE)
        opening_track = album * 200 // 3342
        assert opening_track >= 1500, (
            "a 3:20 track of a 55.7 minute file gets "
            f"{opening_track} buckets, which draws as blocks"
        )

    def test_a_short_file_is_not_measured_coarsely(self) -> None:
        """A rule stated in time alone would have made these worse."""
        assert buckets_for(SAMPLE_RATE * 30, SAMPLE_RATE) == LEAST_BUCKETS

    def test_the_count_is_bounded(self) -> None:
        """One record cannot run away with the cache."""
        assert buckets_for(SAMPLE_RATE * 60 * 60 * 3, SAMPLE_RATE) == MOST_BUCKETS

    def test_a_source_of_nothing_still_has_a_count(self) -> None:
        """Asked before anything is known, it answers rather than dividing."""
        assert buckets_for(0, SAMPLE_RATE) == LEAST_BUCKETS
        assert buckets_for(SAMPLE_RATE, 0) == LEAST_BUCKETS
