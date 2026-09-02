"""Playback states, output honesty and transport position."""

from __future__ import annotations

import pytest

from stellody.domain.playback import (
    OutputMode,
    OutputReport,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
    clock_text,
)
from stellody.domain.track import CD_BIT_DEPTH, CD_SAMPLE_RATE

HIGH_RATE = 96000
HIGH_DEPTH = 24
ONE_SECOND_OF_CD = CD_SAMPLE_RATE


def cd_request(mode: OutputMode = OutputMode.SHARED) -> OutputRequest:
    """A plain CD quality stereo request."""
    return OutputRequest(sample_rate=CD_SAMPLE_RATE, bit_depth=CD_BIT_DEPTH, mode=mode)


def test_only_stopped_is_inactive() -> None:
    assert PlaybackState.STOPPED.is_active is False
    assert PlaybackState.PLAYING.is_active is True
    assert PlaybackState.PAUSED.is_active is True


def test_a_request_defaults_to_shared_stereo() -> None:
    request = cd_request()
    assert request.mode is OutputMode.SHARED
    assert request.channels == 2


def test_a_request_can_be_restated_as_shared() -> None:
    exclusive = cd_request(OutputMode.EXCLUSIVE)
    shared = exclusive.as_shared()
    assert shared.mode is OutputMode.SHARED
    assert shared.sample_rate == exclusive.sample_rate
    assert shared.bit_depth == exclusive.bit_depth
    assert shared.channels == exclusive.channels


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"sample_rate": 0, "bit_depth": CD_BIT_DEPTH}, "sample rate"),
        ({"sample_rate": CD_SAMPLE_RATE, "bit_depth": -1}, "bit depth"),
        (
            {
                "sample_rate": CD_SAMPLE_RATE,
                "bit_depth": CD_BIT_DEPTH,
                "channels": 0,
            },
            "channel count",
        ),
    ],
)
def test_invalid_requests_are_refused(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        OutputRequest(**kwargs)  # type: ignore[arg-type]


def test_a_source_stating_no_bit_depth_is_accepted() -> None:
    """A lossy file has none to state, so nought is an answer rather than a gap.

    Demanding a positive number here would mean inventing a depth on the
    file's behalf, which is the one thing that would make the claim below
    impossible to check.
    """
    request = OutputRequest(sample_rate=CD_SAMPLE_RATE, bit_depth=0)
    assert request.bit_depth == 0
    assert request.states_depth is False


def test_a_source_that_states_a_depth_says_so() -> None:
    assert cd_request(OutputMode.EXCLUSIVE).states_depth is True


def test_a_source_with_no_stated_depth_is_never_bit_perfect() -> None:
    """However well the device opens, a lossy file cannot be delivered intact.

    What comes out of the decoder is already not what went into the encoder,
    so an exclusive stream at the file's own rate still is not bit perfect.
    Without this the comparison would read `device >= 0`, which passes for
    every lossy file ever opened and would put a false claim on screen.
    """
    request = OutputRequest(
        sample_rate=CD_SAMPLE_RATE, bit_depth=0, mode=OutputMode.EXCLUSIVE
    )
    report = OutputReport(
        request=request,
        mode=OutputMode.EXCLUSIVE,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=32,
    )
    assert report.rate_is_native is True
    assert report.depth_is_native is False
    assert report.is_bit_perfect is False


def test_an_exclusive_stream_at_the_native_rate_and_depth_is_bit_perfect() -> None:
    request = cd_request(OutputMode.EXCLUSIVE)
    report = OutputReport(
        request=request,
        mode=OutputMode.EXCLUSIVE,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=CD_BIT_DEPTH,
    )
    assert report.is_bit_perfect is True
    assert report.fell_back is False
    assert report.rate_is_native is True
    assert report.depth_is_native is True


def test_a_deeper_device_is_still_native_depth() -> None:
    request = cd_request(OutputMode.EXCLUSIVE)
    report = OutputReport(
        request=request,
        mode=OutputMode.EXCLUSIVE,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=HIGH_DEPTH,
    )
    assert report.depth_is_native is True
    assert report.is_bit_perfect is True


def test_a_truncating_device_is_not_bit_perfect() -> None:
    """The measured reference case: exclusive at 96 kHz into 16 bit hardware."""
    request = OutputRequest(
        sample_rate=HIGH_RATE, bit_depth=HIGH_DEPTH, mode=OutputMode.EXCLUSIVE
    )
    report = OutputReport(
        request=request,
        mode=OutputMode.EXCLUSIVE,
        sample_rate=HIGH_RATE,
        bit_depth=CD_BIT_DEPTH,
    )
    assert report.rate_is_native is True
    assert report.depth_is_native is False
    assert report.is_bit_perfect is False


def test_a_resampled_exclusive_stream_is_not_bit_perfect() -> None:
    request = OutputRequest(
        sample_rate=HIGH_RATE, bit_depth=CD_BIT_DEPTH, mode=OutputMode.EXCLUSIVE
    )
    report = OutputReport(
        request=request,
        mode=OutputMode.EXCLUSIVE,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=CD_BIT_DEPTH,
    )
    assert report.rate_is_native is False
    assert report.is_bit_perfect is False


def test_shared_mode_is_never_bit_perfect() -> None:
    request = cd_request()
    report = OutputReport(
        request=request,
        mode=OutputMode.SHARED,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=CD_BIT_DEPTH,
    )
    assert report.is_bit_perfect is False
    assert report.fell_back is False


def test_a_refused_exclusive_request_records_the_fallback() -> None:
    request = cd_request(OutputMode.EXCLUSIVE)
    report = OutputReport(
        request=request,
        mode=OutputMode.SHARED,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=CD_BIT_DEPTH,
        fallback_reason="the device is already in use",
    )
    assert report.fell_back is True
    assert report.is_bit_perfect is False
    assert report.fallback_reason


@pytest.mark.parametrize(
    ("sample_rate", "bit_depth", "message"),
    [
        (0, CD_BIT_DEPTH, "sample rate"),
        (CD_SAMPLE_RATE, 0, "bit depth"),
    ],
)
def test_invalid_reports_are_refused(
    sample_rate: int, bit_depth: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        OutputReport(
            request=cd_request(),
            mode=OutputMode.SHARED,
            sample_rate=sample_rate,
            bit_depth=bit_depth,
        )


def test_a_position_reports_elapsed_total_and_remaining() -> None:
    position = PlaybackPosition(
        frame=ONE_SECOND_OF_CD,
        frame_count=ONE_SECOND_OF_CD * 3,
        sample_rate=CD_SAMPLE_RATE,
    )
    assert position.elapsed_ms == 1000
    assert position.total_ms == 3000
    assert position.remaining_ms == 2000
    assert position.is_complete is False


def test_a_position_at_the_end_is_complete_with_nothing_remaining() -> None:
    position = PlaybackPosition(
        frame=ONE_SECOND_OF_CD,
        frame_count=ONE_SECOND_OF_CD,
        sample_rate=CD_SAMPLE_RATE,
    )
    assert position.is_complete is True
    assert position.remaining_ms == 0


def test_a_position_past_the_end_never_reports_negative_remaining() -> None:
    position = PlaybackPosition(
        frame=ONE_SECOND_OF_CD * 2,
        frame_count=ONE_SECOND_OF_CD,
        sample_rate=CD_SAMPLE_RATE,
    )
    assert position.is_complete is True
    assert position.remaining_ms == 0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"frame": -1, "frame_count": 0, "sample_rate": CD_SAMPLE_RATE}, "frame"),
        (
            {"frame": 0, "frame_count": -1, "sample_rate": CD_SAMPLE_RATE},
            "frame count",
        ),
        ({"frame": 0, "frame_count": 0, "sample_rate": 0}, "sample rate"),
    ],
)
def test_invalid_positions_are_refused(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        PlaybackPosition(**kwargs)  # type: ignore[arg-type]


class TestClockText:
    """Minutes and seconds, for a display somebody reads while listening."""

    def test_the_start_of_a_track_reads_as_zero(self) -> None:
        assert clock_text(0, CD_SAMPLE_RATE) == "0:00"

    def test_seconds_are_padded_and_minutes_are_not(self) -> None:
        """A listener reads 3:07, never 03:07."""
        assert clock_text(CD_SAMPLE_RATE * 187, CD_SAMPLE_RATE) == "3:07"

    def test_a_second_is_not_named_until_it_is_reached(self) -> None:
        """Truncated rather than rounded: 2.9 seconds in is still the second."""
        assert clock_text(int(CD_SAMPLE_RATE * 2.9), CD_SAMPLE_RATE) == "0:02"

    def test_a_long_track_keeps_counting_in_minutes(self) -> None:
        assert clock_text(CD_SAMPLE_RATE * 3661, CD_SAMPLE_RATE) == "61:01"

    def test_before_the_beginning_reads_as_the_beginning(self) -> None:
        """Nothing calls it with one; a clock has no negative reading."""
        assert clock_text(-1, CD_SAMPLE_RATE) == "0:00"

    def test_a_rate_of_nothing_is_refused_rather_than_dividing_by_zero(self) -> None:
        with pytest.raises(ValueError):
            clock_text(1, 0)
