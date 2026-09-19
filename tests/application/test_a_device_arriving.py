"""A device arriving carries the music on; one leaving still pauses it.

`OUTPUTS.md` Amendment 5, ruled by Oliver on 2026-09-19 after testing the
installed build with his Px7 S3 headphones. While System default is the
choice, the system's default moving to a device while the one it left is still
listed moves the track in hand there, where it was: playing plays on, paused
stays paused. Everything else keeps the pause of 2026-09-14, since nothing may
send the music to a device the listener never chose.
"""

from __future__ import annotations

from recording_player import RecordingPlayer
from transport_support import album_of, track

from stellody.application.transport import Transport
from stellody.domain.outputs import OutputChoice, OutputDevice
from stellody.domain.playback import PlaybackPosition, PlaybackState
from stellody.domain.track import CD_SAMPLE_RATE

DECODED_FRAME = 44_100
LEAD_FRAMES = 4_096
TRACK_FRAMES = 441_000
REASON = "Device unavailable [PaErrorCode -9985]"

SPEAKERS = OutputDevice(identity="{speakers}", name="Speakers (Realtek)")
FOCUSRITE = OutputDevice(identity="{focusrite}", name="Speakers (Focusrite)")
BATHYS = OutputDevice(identity="{bathys}", name="Headphones (Focal Bathys)")
LISTED = (SPEAKERS, FOCUSRITE)


def chose(device: OutputDevice) -> OutputChoice:
    """The choice a listener makes by picking this device."""
    return OutputChoice(identity=device.identity, name=device.name)


def playing() -> tuple[Transport, RecordingPlayer]:
    """On the system default, part way through the first of two tracks."""
    player = RecordingPlayer()
    transport = Transport(player)
    transport.outputs_listed(LISTED)
    first = track(1)
    transport.play_album(album_of(first, track(2)), first)
    player.reported = PlaybackPosition(
        frame=DECODED_FRAME, frame_count=TRACK_FRAMES, sample_rate=CD_SAMPLE_RATE
    )
    player.lead = LEAD_FRAMES
    player.calls.clear()
    return transport, player


class TestOnTheSystemDefault:
    def test_playing_music_moves_and_plays_on(self) -> None:
        """The whole of the ruling: no pause, no press."""
        transport, player = playing()
        assert transport.output_switched() is False
        assert "pause" not in player.calls
        assert player.calls[0] == "load"
        assert f"seek {DECODED_FRAME}" in player.calls
        assert "play" in player.calls
        assert transport.state is PlaybackState.PLAYING

    def test_the_same_track_carries_on(self) -> None:
        transport, player = playing()
        held = transport.current
        transport.output_switched()
        assert player.loaded[-1] == held.source
        assert transport.current is held

    def test_a_paused_track_moves_and_stays_paused(self) -> None:
        transport, player = playing()
        transport.toggle()
        player.calls.clear()
        assert transport.output_switched() is False
        assert "load" in player.calls
        assert "play" not in player.calls
        assert transport.state is PlaybackState.PAUSED

    def test_play_after_it_is_an_ordinary_resume(self) -> None:
        """It is already open where the output is, so nothing is left owed."""
        transport, player = playing()
        transport.toggle()
        transport.output_switched()
        player.calls.clear()
        transport.toggle()
        assert player.calls == ["play"]

    def test_nothing_loaded_is_nothing_to_move(self) -> None:
        player = RecordingPlayer()
        transport = Transport(player)
        assert transport.output_switched() is False
        assert player.calls == []


class TestWhatStillPauses:
    def test_an_interrupted_stream_keeps_its_pause(self) -> None:
        """Rule 3: the device went from beneath the stream; that is a loss."""
        transport, player = playing()
        player.interrupted = True
        player.state = PlaybackState.PAUSED
        assert transport.output_switched() is True
        assert "load" not in player.calls

    def test_a_missing_choice_is_not_carried_to_a_stranger(self) -> None:
        """Rule 4: the music is on the default only while its device is away."""
        transport, player = playing()
        transport.choose_output(chose(BATHYS))
        player.calls.clear()
        assert transport.output_switched() is True
        assert player.calls == ["pause"]

    def test_a_refused_choice_is_not_carried_to_a_stranger(self) -> None:
        """Rule 4 again, for the choice whose device answered no."""
        transport, player = playing()
        player.refuses = {FOCUSRITE.identity: REASON}
        transport.choose_output(chose(FOCUSRITE))
        player.calls.clear()
        assert transport.output_switched() is True
        assert player.calls == ["pause"]

    def test_a_named_device_in_use_ignores_it(self) -> None:
        """Amendment 3 stands: the music is not on the default at all."""
        transport, player = playing()
        transport.choose_output(chose(FOCUSRITE))
        player.calls.clear()
        assert transport.output_switched() is False
        assert player.calls == []
