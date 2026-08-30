"""Where playback has reached, said the way a listener would say it.

The port reports what has been DECODED. That runs ahead of what is leaving the
speakers by whatever the device is still holding, so a display fed from it
raw sits ahead of the music and a track appears to end before it has.

The correction lives with the transport rather than in the engine, because the
size of the lead is a property of the device the port opened and this is the
layer that asks the port anything. These pin it against a known lead, which is
what the milestone asked for.
"""

from __future__ import annotations

import pytest
from transport_support import FakePlayer, album_of, track

from stellody.application.transport import Transport
from stellody.domain.playback import PlaybackPosition
from stellody.domain.track import CD_SAMPLE_RATE

ONE_BLOCK = 4096
HALFWAY = 100_000
TRACK_FRAMES = 200_000


@pytest.fixture
def playing() -> tuple[Transport, FakePlayer]:
    """A transport over a device that reports whatever a test puts there."""
    player = FakePlayer()
    transport = Transport(player)
    first, second = track(1), track(2)
    transport.play_album(album_of(first, second), second)
    return transport, player


def _reported(frame: int) -> PlaybackPosition:
    """What the port would say the decode has reached."""
    return PlaybackPosition(
        frame=frame, frame_count=TRACK_FRAMES, sample_rate=CD_SAMPLE_RATE
    )


def test_nothing_loaded_reports_no_position(playing) -> None:
    transport, player = playing
    player.reported = None
    assert transport.position is None


def test_the_reported_position_is_the_decode_less_one_buffer(playing) -> None:
    """The whole correction, against a lead the test chose."""
    transport, player = playing
    player.lead = ONE_BLOCK
    player.reported = _reported(HALFWAY)
    audible = transport.position
    assert audible is not None
    assert audible.frame == HALFWAY - ONE_BLOCK


def test_the_track_it_belongs_to_is_left_alone(playing) -> None:
    """Only where playback has reached moves; the track is the same length."""
    transport, player = playing
    player.lead = ONE_BLOCK
    player.reported = _reported(HALFWAY)
    audible = transport.position
    assert audible is not None
    assert audible.frame_count == TRACK_FRAMES
    assert audible.sample_rate == CD_SAMPLE_RATE


def test_the_first_buffer_of_a_track_reads_as_the_beginning(playing) -> None:
    """Not as a negative position, which is not a place in a track.

    A track opens with the decode already a buffer in, so an uncorrected
    subtraction would put the listener before the start.
    """
    transport, player = playing
    player.lead = ONE_BLOCK
    player.reported = _reported(ONE_BLOCK // 2)
    audible = transport.position
    assert audible is not None
    assert audible.frame == 0


def test_a_device_holding_nothing_needs_no_correction(playing) -> None:
    """Which is what a stand-in reports, so the arithmetic must survive it."""
    transport, player = playing
    player.lead = 0
    player.reported = _reported(HALFWAY)
    audible = transport.position
    assert audible is not None
    assert audible.frame == HALFWAY


def test_seeking_asks_the_device_for_the_frame_a_listener_meant(playing) -> None:
    """Asked in the listener's terms, so the audible position lands there.

    The decode has to go one buffer further on for that to be true a moment
    later, which is the same correction read backwards.
    """
    transport, player = playing
    player.lead = ONE_BLOCK
    player.reported = _reported(0)
    transport.seek(HALFWAY)
    assert f"seek {HALFWAY + ONE_BLOCK}" in player.calls


def test_seeking_before_the_start_lands_at_the_start(playing) -> None:
    transport, player = playing
    player.lead = 0
    player.reported = _reported(0)
    transport.seek(-500)
    assert "seek 0" in player.calls


def test_seeking_with_nothing_loaded_asks_the_device_for_nothing(playing) -> None:
    """There is no track to move within, so there is nothing to say."""
    transport, player = playing
    player.reported = None
    player.calls.clear()
    transport.seek(HALFWAY)
    assert not [call for call in player.calls if call.startswith("seek")]


def test_seeking_ends_the_wait_at_the_start_of_a_track(playing) -> None:
    """Back leaves the transport waiting; moving within the track is a move.

    Left set, the next press of back would leave the track rather than
    returning to the beginning of the one somebody has just moved inside.
    """
    transport, player = playing
    player.reported = _reported(HALFWAY)
    transport.previous()
    assert transport.current is not None
    assert transport.current.track_number == 2, "waiting at the start of this one"
    transport.seek(HALFWAY)
    transport.previous()
    assert transport.current is not None
    assert transport.current.track_number == 2, (
        "back returned to the start of the track somebody had just moved inside, "
        "rather than leaving it for the one before"
    )
