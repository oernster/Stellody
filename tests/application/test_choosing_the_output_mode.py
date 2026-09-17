"""Which stream the device is asked for; what a change to it does.

Asked for by Oliver on 2026-09-17. The exclusive path had been built, measured
and tested since the engine was written and nothing ever asked for it: every
stream went out through the mixer, which resamples by definition, so the
player could not deliver what it was written to deliver.

Two rules are held here. The mode reaches the request, since that is the only
way it reaches a device at all. A change to it reopens what is in hand, where
it is and as it was, because a switch whose effect cannot be heard until the
next track reads as a switch that did nothing.

What the transport asks for and what the device grants are different facts and
are kept apart: a refusal is the device's answer, carried in the report,
never quietly changing the choice.
"""

from __future__ import annotations

from recording_player import RecordingPlayer
from transport_support import album_of, track

from stellody.application.transport import Transport
from stellody.domain.playback import (
    OutputMode,
    PlaybackPosition,
    PlaybackState,
)

PART_WAY = 44100
LEAD = 1024
TRACK_FRAMES = 441000
RATE = 44100


def _playing() -> tuple[Transport, RecordingPlayer]:
    """An album playing its first track, with the device part way into it."""
    player = RecordingPlayer()
    transport = Transport(player)
    one, two = track(1), track(2)
    transport.play_album(album_of(one, two), one)
    player.reported = PlaybackPosition(
        frame=PART_WAY + LEAD, frame_count=TRACK_FRAMES, sample_rate=RATE
    )
    player.lead = LEAD
    player.calls.clear()
    return transport, player


class TestWhatTheDeviceIsAskedFor:
    def test_shared_is_where_everything_starts(self) -> None:
        """The mode no device refuses, so nobody meets a silent machine."""
        transport = Transport(RecordingPlayer())
        assert transport.output_mode is OutputMode.SHARED

    def test_the_mode_reaches_every_request(self) -> None:
        """The whole of what was missing: nothing ever asked."""
        transport, player = _playing()
        transport.set_output_mode(OutputMode.EXCLUSIVE)
        assert player.requests[-1].mode is OutputMode.EXCLUSIVE

    def test_the_mode_reaches_the_tracks_that_follow_as_well(self) -> None:
        """A choice, not a one-off: the next track asks for it too."""
        transport, player = _playing()
        transport.set_output_mode(OutputMode.EXCLUSIVE)
        transport.next()
        assert player.requests[-1].mode is OutputMode.EXCLUSIVE

    def test_choosing_the_mode_already_chosen_does_nothing_at_all(self) -> None:
        """Otherwise the poll behind the play button would reopen the stream."""
        transport, player = _playing()
        transport.set_output_mode(OutputMode.SHARED)
        assert player.calls == []


class TestWhatAChangeDoesToWhatIsPlaying:
    def test_it_reopens_the_track_in_hand(self) -> None:
        """A mode belongs to a stream, so only a new stream can carry one."""
        transport, player = _playing()
        transport.set_output_mode(OutputMode.EXCLUSIVE)
        assert "load" in player.calls

    def test_it_lands_back_where_the_listener_was(self) -> None:
        """Loading opens a stream at the beginning, so the position is put back."""
        transport, player = _playing()
        transport.set_output_mode(OutputMode.EXCLUSIVE)
        assert f"seek {PART_WAY + LEAD}" in player.calls

    def test_a_playing_track_is_still_playing(self) -> None:
        transport, player = _playing()
        transport.set_output_mode(OutputMode.EXCLUSIVE)
        assert "play" in player.calls

    def test_a_paused_track_is_still_paused(self) -> None:
        """A switch is not a request to start the music."""
        transport, player = _playing()
        transport.toggle()
        assert transport.state is PlaybackState.PAUSED, "the fixture must be paused"
        player.calls.clear()
        transport.set_output_mode(OutputMode.EXCLUSIVE)
        assert "play" not in player.calls

    def test_a_track_waiting_at_its_start_is_left_waiting_there(self) -> None:
        """Where Back lands. A reopen must not read as having played it."""
        player = RecordingPlayer()
        transport = Transport(player)
        one, two = track(1), track(2)
        transport.play_album(album_of(one, two), one)
        transport.next()
        transport.previous()
        assert transport.waiting_at_the_start, "the fixture must be waiting"
        transport.set_output_mode(OutputMode.EXCLUSIVE)
        assert transport.waiting_at_the_start

    def test_a_track_at_its_very_start_is_not_seeked(self) -> None:
        """A load already opens at nought, so a seek there would be noise."""
        player = RecordingPlayer()
        transport = Transport(player)
        one = track(1)
        transport.play_album(album_of(one), one)
        player.reported = PlaybackPosition(
            frame=0, frame_count=TRACK_FRAMES, sample_rate=RATE
        )
        player.calls.clear()
        transport.set_output_mode(OutputMode.EXCLUSIVE)
        assert not [call for call in player.calls if call.startswith("seek")]

    def test_a_device_reporting_no_position_is_still_reopened(self) -> None:
        """A stream that has not started yet has nowhere to be put back to."""
        player = RecordingPlayer()
        transport = Transport(player)
        one = track(1)
        transport.play_album(album_of(one), one)
        player.reported = None
        player.calls.clear()
        transport.set_output_mode(OutputMode.EXCLUSIVE)
        assert "load" in player.calls
        assert not [call for call in player.calls if call.startswith("seek")]

    def test_nothing_in_hand_means_nothing_to_reopen(self) -> None:
        """The switch is pressable with an empty queue, so it must be safe."""
        player = RecordingPlayer()
        transport = Transport(player)
        transport.set_output_mode(OutputMode.EXCLUSIVE)
        assert player.calls == []
        assert transport.output_mode is OutputMode.EXCLUSIVE


class TestWhatTheDeviceAnswered:
    def test_the_report_is_the_devices_own_word(self) -> None:
        """Passed through rather than remembered, so the two cannot disagree."""
        transport, player = _playing()
        transport.set_output_mode(OutputMode.EXCLUSIVE)
        assert transport.report is player.report
        assert transport.report.mode is OutputMode.EXCLUSIVE

    def test_a_refusal_does_not_change_the_choice(self) -> None:
        """The next track asks again, so it takes the mode when it is free."""
        player = RecordingPlayer()
        player.grants = False
        player.refusal = "the device is in use"
        transport = Transport(player)
        one, two = track(1), track(2)
        transport.play_album(album_of(one, two), one)
        transport.set_output_mode(OutputMode.EXCLUSIVE)
        assert transport.output_mode is OutputMode.EXCLUSIVE
        assert transport.report.mode is OutputMode.SHARED
        assert transport.report.fell_back
        assert transport.report.fallback_reason == "the device is in use"
        transport.next()
        assert player.requests[-1].mode is OutputMode.EXCLUSIVE

    def test_nothing_open_reports_nothing(self) -> None:
        assert Transport(RecordingPlayer()).report is None
