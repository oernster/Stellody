"""A move of the system's sound output pauses the music; play carries on there.

Reported by Oliver on 2026-09-14: headphones connected while a track played and
the track went on through the speakers. A stream stays on the device it was
opened on, so the transport pauses instead and the press that resumes opens the
track again where the output now is. What is asserted is the sequence of
commands given to a device that records them.
"""

from __future__ import annotations

from recording_player import RecordingPlayer
from transport_support import album_of, track

from stellody.application.transport import Transport
from stellody.domain.playback import PlaybackPosition, PlaybackState
from stellody.domain.track import CD_SAMPLE_RATE

DECODED_FRAME = 44_100
LEAD_FRAMES = 4_096
TRACK_FRAMES = 441_000
HEARD_FRAME = DECODED_FRAME - LEAD_FRAMES


def playing() -> tuple[Transport, RecordingPlayer]:
    """A transport part way through the first of two tracks."""
    player = RecordingPlayer()
    transport = Transport(player)
    first = track(1)
    transport.play_album(album_of(first, track(2)), first)
    player.reported = PlaybackPosition(
        frame=DECODED_FRAME, frame_count=TRACK_FRAMES, sample_rate=CD_SAMPLE_RATE
    )
    player.lead = LEAD_FRAMES
    player.calls.clear()
    return transport, player


def interrupted() -> tuple[Transport, RecordingPlayer]:
    """Playing, when the device went away underneath the stream.

    Measured on 2026-09-19 through the shipped engine with headphones switched
    off: the stream's write fails first, 0.29 s before Qt reports the device
    gone. The engine then holds the track paused and says it was interrupted.
    """
    transport, player = playing()
    player.interrupted = True
    player.state = PlaybackState.PAUSED
    return transport, player


class TestADeviceGoneBeneathTheStream:
    """Reported by Oliver on 2026-09-19: switching headphones off skipped to
    the next song, else left the last one back at its start."""

    def test_nothing_moves_on(self) -> None:
        transport, player = interrupted()
        assert transport.advance_if_finished() is False
        assert player.calls == []

    def test_the_move_that_follows_is_said_as_a_pause(self) -> None:
        """Qt's report arrives after the stream stopped; it still stopped it."""
        transport, player = interrupted()
        assert transport.output_moved() is True
        assert player.calls == []

    def test_a_second_signal_for_it_says_nothing_more(self) -> None:
        transport, _player = interrupted()
        transport.output_moved()
        assert transport.output_moved() is False

    def test_play_reopens_where_it_was_heard(self) -> None:
        """Even with no report from Qt: that stream can only be reopened."""
        transport, player = interrupted()
        transport.toggle()
        assert player.calls[0] == "load"
        assert f"seek {HEARD_FRAME}" in player.calls
        assert player.calls[-1] == "play"

    def test_nothing_loaded_is_nothing_to_say(self) -> None:
        player = RecordingPlayer()
        transport = Transport(player)
        player.interrupted = True
        assert transport.output_moved() is False


class TestAMoveWhilePlaying:
    def test_the_music_is_paused(self) -> None:
        """The whole of what this is for."""
        transport, player = playing()
        assert transport.output_moved() is True
        assert player.calls == ["pause"]
        assert transport.state is PlaybackState.PAUSED

    def test_the_pause_is_not_taken_for_an_ending(self) -> None:
        """A held track reports itself as an ended one; it must not move on."""
        transport, player = playing()
        transport.output_moved()
        player.finished = True
        assert transport.advance_if_finished() is False
        assert "load" not in player.calls

    def test_a_second_signal_for_the_same_move_changes_nothing(self) -> None:
        transport, player = playing()
        transport.output_moved()
        assert transport.output_moved() is False
        assert player.calls == ["pause"]


class TestPlayAfterAMove:
    def test_the_track_is_opened_again_where_it_was_heard(self) -> None:
        transport, player = playing()
        held = transport.current
        transport.output_moved()
        transport.toggle()
        assert player.calls == ["pause", "load", f"seek {HEARD_FRAME}", "play"]
        assert player.loaded[-1] == held.source
        assert transport.current is held
        assert transport.state is PlaybackState.PLAYING

    def test_only_the_first_resume_reopens(self) -> None:
        """Once it is open where the output is, a pause is an ordinary pause."""
        transport, player = playing()
        transport.output_moved()
        transport.toggle()
        player.calls.clear()
        transport.toggle()
        transport.toggle()
        assert player.calls == ["pause", "play"]

    def test_with_no_position_it_opens_from_the_start(self) -> None:
        transport, player = playing()
        player.reported = None
        transport.output_moved()
        transport.toggle()
        assert player.calls == ["pause", "load", "play"]


class TestWhatAMoveLeavesAlone:
    def test_an_ordinary_pause_resumes_on_the_open_stream(self) -> None:
        transport, player = playing()
        transport.toggle()
        transport.toggle()
        assert player.calls == ["pause", "play"]

    def test_a_move_while_paused_does_not_pause_again(self) -> None:
        """Still marked: a paused track is open on the device just left."""
        transport, player = playing()
        transport.toggle()
        player.calls.clear()
        assert transport.output_moved() is False
        assert player.calls == []
        transport.toggle()
        assert player.calls == ["load", f"seek {HEARD_FRAME}", "play"]

    def test_a_move_with_nothing_loaded_does_nothing(self) -> None:
        player = RecordingPlayer()
        transport = Transport(player)
        assert transport.output_moved() is False
        assert player.calls == []

    def test_moving_to_another_track_opens_it_where_the_output_is(self) -> None:
        """Any open is made where the output now is, so the move is spent."""
        transport, player = playing()
        transport.output_moved()
        transport.next()
        player.calls.clear()
        transport.toggle()
        assert player.calls == ["play"]
