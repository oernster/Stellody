"""Which device the music goes to; what choosing one does. `OUTPUTS.md`.

A choice reopens what is in hand, where it is and as it was, exactly as the
exclusive switch does. A device that will not open is fallen back from rather
than left silent. A choice whose device is missing plays on the system default
while the choice itself is kept.
"""

from __future__ import annotations

import pytest
from recording_player import RecordingPlayer
from transport_support import album_of, track

from stellody.application.output_choosing import OutputChange
from stellody.application.playback_ports import OutputRefused
from stellody.application.transport import Transport
from stellody.domain.outputs import SYSTEM_DEFAULT, OutputChoice, OutputDevice
from stellody.domain.playback import PlaybackPosition, PlaybackState

PART_WAY = 44100
LEAD = 1024
TRACK_FRAMES = 441000
RATE = 44100
REASON = "Device unavailable [PaErrorCode -9985]"

SPEAKERS = OutputDevice(identity="{speakers}", name="Speakers (Realtek)")
FOCUSRITE = OutputDevice(identity="{focusrite}", name="Speakers (Focusrite)")
BATHYS = OutputDevice(identity="{bathys}", name="Headphones (Focal Bathys)")
LISTED = (SPEAKERS, FOCUSRITE)


def chose(device: OutputDevice) -> OutputChoice:
    """The choice a listener makes by picking this device."""
    return OutputChoice(identity=device.identity, name=device.name)


def _listed(devices=LISTED) -> tuple[Transport, RecordingPlayer]:
    """A transport told which devices exist, with nothing loaded."""
    player = RecordingPlayer()
    transport = Transport(player)
    transport.outputs_listed(devices)
    return transport, player


def _playing(devices=LISTED) -> tuple[Transport, RecordingPlayer]:
    """An album playing its first track, the device part way into it."""
    transport, player = _listed(devices)
    one, two = track(1), track(2)
    transport.play_album(album_of(one, two), one)
    player.reported = PlaybackPosition(
        frame=PART_WAY + LEAD, frame_count=TRACK_FRAMES, sample_rate=RATE
    )
    player.lead = LEAD
    player.calls.clear()
    return transport, player


class TestStartingOut:
    def test_the_system_default_is_where_everything_starts(self) -> None:
        """FR-O03: today's behaviour for anybody who never opens the list."""
        transport, player = _listed()
        assert transport.output_choice == SYSTEM_DEFAULT
        assert transport.device_in_use is None
        assert player.device is None

    def test_the_list_is_the_domains_over_what_is_listed(self) -> None:
        """FR-O05, FR-O06: the window reads the list from here."""
        transport, _player = _listed()
        transport.choose_output(chose(FOCUSRITE))
        marked = [entry.choice for entry in transport.output_entries if entry.chosen]
        assert marked == [chose(FOCUSRITE)]
        assert len(transport.output_entries) == len(LISTED) + 1


class TestChoosing:
    def test_choosing_reopens_in_place(self) -> None:
        """FR-O07: a new stream, the same place in the track."""
        transport, player = _playing()
        transport.choose_output(chose(FOCUSRITE))
        assert player.calls[:2] == [f"device {FOCUSRITE.identity}", "load"]
        assert f"seek {PART_WAY + LEAD}" in player.calls
        assert "play" in player.calls

    def test_a_paused_track_stays_paused(self) -> None:
        """FR-O07: a choice is not a request to start the music."""
        transport, player = _playing()
        transport.toggle()
        player.calls.clear()
        transport.choose_output(chose(FOCUSRITE))
        assert "load" in player.calls
        assert "play" not in player.calls

    def test_the_device_is_told_before_anything_opens(self) -> None:
        """With nothing loaded, the next track is what opens there."""
        transport, player = _listed()
        transport.choose_output(chose(FOCUSRITE))
        assert player.device == FOCUSRITE
        assert transport.device_in_use == FOCUSRITE
        assert "load" not in player.calls

    def test_nothing_loaded_opens_nothing(self) -> None:
        """A queue left stopped is not reopened by a choice: that would hold
        the device for a track nobody asked to hear."""
        transport, player = _playing()
        transport.stop()
        player.calls.clear()
        transport.choose_output(chose(FOCUSRITE))
        assert "load" not in player.calls

    def test_choosing_the_choice_already_made_does_nothing(self) -> None:
        """Otherwise a menu opened and closed would put a gap in the music."""
        transport, player = _playing()
        transport.choose_output(SYSTEM_DEFAULT)
        assert player.calls == []

    def test_back_to_the_system_default(self) -> None:
        """FR-O15: the default is a choice like any other."""
        transport, player = _playing()
        transport.choose_output(chose(FOCUSRITE))
        player.calls.clear()
        transport.choose_output(SYSTEM_DEFAULT)
        assert player.calls[:2] == ["device default", "load"]
        assert transport.device_in_use is None


class TestARefusal:
    def test_a_refusal_falls_back_to_the_default(self) -> None:
        """FR-O08: the music plays on the system default rather than not."""
        transport, player = _playing()
        player.refuses = {FOCUSRITE.identity: REASON}
        transport.choose_output(chose(FOCUSRITE))
        assert player.calls.count("load") == 2
        assert player.device is None
        assert "play" in player.calls

    def test_the_refusal_is_kept_for_the_window_once(self) -> None:
        """FR-O08: which device, with the reason it gave, said once."""
        transport, player = _playing()
        player.refuses = {FOCUSRITE.identity: REASON}
        transport.choose_output(chose(FOCUSRITE))
        refusal = transport.take_refusal()
        assert refusal is not None
        assert (refusal.device, refusal.reason) == (FOCUSRITE, REASON)
        assert transport.take_refusal() is None

    def test_the_choice_is_kept(self) -> None:
        """What was asked for is remembered; the device answered no."""
        transport, player = _playing()
        player.refuses = {FOCUSRITE.identity: REASON}
        transport.choose_output(chose(FOCUSRITE))
        assert transport.output_choice == chose(FOCUSRITE)

    def test_the_tick_is_on_the_default_it_plays_on(self) -> None:
        """Amendment 5: the list ticks where the music is going."""
        transport, player = _playing()
        player.refuses = {FOCUSRITE.identity: REASON}
        transport.choose_output(chose(FOCUSRITE))
        marked = [entry.choice for entry in transport.output_entries if entry.chosen]
        assert marked == [SYSTEM_DEFAULT]

    def test_the_next_track_does_not_ask_again(self) -> None:
        """One refusal, one message: not a failed open on every track."""
        transport, player = _playing()
        player.refuses = {FOCUSRITE.identity: REASON}
        transport.choose_output(chose(FOCUSRITE))
        transport.take_refusal()
        player.calls.clear()
        transport.next()
        assert player.calls.count("load") == 1
        assert transport.take_refusal() is None

    def test_choosing_it_again_asks_again(self) -> None:
        """A listener choosing it once more is asking for another try."""
        transport, player = _playing()
        player.refuses = {FOCUSRITE.identity: REASON}
        transport.choose_output(chose(FOCUSRITE))
        player.refuses = {}
        player.calls.clear()
        transport.choose_output(chose(FOCUSRITE))
        assert player.device == FOCUSRITE
        assert transport.device_in_use == FOCUSRITE

    def test_a_default_that_refuses_has_nothing_to_fall_back_to(self) -> None:
        """The refusal is the report, raised as every open failure is."""
        transport, player = _listed()
        player.refuses = {"": REASON}
        one = track(1)
        with pytest.raises(OutputRefused):
            transport.play_album(album_of(one), one)


class TestAMissingChoice:
    def test_a_missing_choice_plays_on_the_default(self) -> None:
        """FR-O10: the Bathys remembered while switched off."""
        transport, player = _listed()
        transport.choose_output(chose(BATHYS))
        assert transport.output_missing
        assert player.device is None
        assert transport.output_choice == chose(BATHYS)

    def test_a_present_choice_is_not_missing(self) -> None:
        transport, _player = _listed()
        transport.choose_output(chose(FOCUSRITE))
        assert not transport.output_missing

    def test_the_default_is_never_missing(self) -> None:
        transport, _player = _listed(())
        assert not transport.output_missing


class TestTheListChanging:
    def test_a_new_device_changes_nothing_in_use(self) -> None:
        """FR-O13: the list grows; the music stays where it is."""
        transport, player = _listed()
        assert transport.outputs_listed((*LISTED, BATHYS)) is OutputChange.NONE
        assert player.device is None

    def test_the_chosen_device_leaving_is_a_loss(self) -> None:
        """FR-O11: later streams open on the default."""
        transport, player = _listed((*LISTED, BATHYS))
        transport.choose_output(chose(BATHYS))
        assert transport.outputs_listed(LISTED) is OutputChange.LOST
        assert player.device is None
        assert transport.output_missing

    def test_the_chosen_device_coming_back_is_a_return(self) -> None:
        """FR-O12: the kept choice finds its device again."""
        transport, player = _listed()
        transport.choose_output(chose(BATHYS))
        assert transport.outputs_listed((*LISTED, BATHYS)) is OutputChange.RETURNED
        assert player.device == BATHYS

    def test_a_refused_device_still_listed_is_not_retried(self) -> None:
        """Any change to the list would otherwise reopen the music into the
        same refusal."""
        transport, player = _playing()
        player.refuses = {FOCUSRITE.identity: REASON}
        transport.choose_output(chose(FOCUSRITE))
        assert transport.outputs_listed((*LISTED, BATHYS)) is OutputChange.NONE
        assert player.device is None

    def test_a_refused_device_that_leaves_and_returns_is_tried_again(self) -> None:
        """Unplugged and plugged back in is a different device session."""
        transport, player = _playing()
        player.refuses = {FOCUSRITE.identity: REASON}
        transport.choose_output(chose(FOCUSRITE))
        transport.outputs_listed((SPEAKERS,))
        player.refuses = {}
        assert transport.outputs_listed(LISTED) is OutputChange.RETURNED
        assert player.device == FOCUSRITE


class TestWhatALossDoesToTheTrackInHand:
    """OQ-O5, ruled by Oliver on 2026-09-18: the 2026-09-14 rule governs.

    Music never jumps to the speakers without a press. The device the
    listener chose takes the music back when it returns.
    """

    def _lost_while_playing(self) -> tuple[Transport, RecordingPlayer]:
        transport, player = _playing((*LISTED, BATHYS))
        transport.choose_output(chose(BATHYS))
        player.calls.clear()
        transport.outputs_listed(LISTED)
        return transport, player

    def test_a_loss_while_playing_pauses(self) -> None:
        """FR-O11: paused where it was, rather than out of the speakers."""
        _transport, player = self._lost_while_playing()
        assert player.calls == ["device default", "pause"]

    def test_play_after_a_loss_opens_on_the_default(self) -> None:
        """FR-O11: the press is the listener agreeing to the speakers."""
        transport, player = self._lost_while_playing()
        player.calls.clear()
        transport.toggle()
        assert player.calls[0] == "load"
        assert player.device is None
        assert player.calls[-1] == "play"

    def test_a_loss_while_paused_starts_nothing(self) -> None:
        transport, player = _playing((*LISTED, BATHYS))
        transport.choose_output(chose(BATHYS))
        transport.toggle()
        player.calls.clear()
        transport.outputs_listed(LISTED)
        assert player.calls == ["device default"]

    def test_play_after_a_loss_while_paused_reopens_rather_than_resumes(
        self,
    ) -> None:
        """The paused stream is open on the device that went; resuming it
        would play into nothing."""
        transport, player = _playing((*LISTED, BATHYS))
        transport.choose_output(chose(BATHYS))
        transport.toggle()
        transport.outputs_listed(LISTED)
        player.calls.clear()
        transport.toggle()
        assert player.calls[0] == "load"

    def test_a_loss_with_nothing_loaded_touches_nothing_else(self) -> None:
        transport, player = _listed((*LISTED, BATHYS))
        transport.choose_output(chose(BATHYS))
        player.calls.clear()
        transport.outputs_listed(LISTED)
        assert player.calls == ["device default"]

    def test_a_return_takes_a_playing_track_back_in_place(self) -> None:
        """FR-O12: the chosen device takes the music back, playing on."""
        transport, player = _playing()
        transport.choose_output(chose(BATHYS))
        player.calls.clear()
        transport.outputs_listed((*LISTED, BATHYS))
        assert player.calls[:2] == [f"device {BATHYS.identity}", "load"]
        assert f"seek {PART_WAY + LEAD}" in player.calls
        assert "play" in player.calls

    def test_a_return_after_a_loss_leaves_the_pause_in_place(self) -> None:
        """FR-O12: moved to the device, still waiting for the press."""
        transport, player = self._lost_while_playing()
        player.calls.clear()
        transport.outputs_listed((*LISTED, BATHYS))
        assert "load" in player.calls
        assert "play" not in player.calls
        assert player.device == BATHYS

    def test_a_return_with_nothing_loaded_opens_nothing(self) -> None:
        transport, player = _listed()
        transport.choose_output(chose(BATHYS))
        player.calls.clear()
        transport.outputs_listed((*LISTED, BATHYS))
        assert player.calls == [f"device {BATHYS.identity}"]


class TestTheSystemMovingItsDefault:
    def test_the_default_is_followed(self) -> None:
        """FR-O15: today's pause for a move, while the default is the choice."""
        transport, _player = _playing()
        assert transport.output_moved()
        assert transport.state is PlaybackState.PAUSED

    def test_a_named_device_in_use_ignores_the_move(self) -> None:
        """The music is not on the default, so its moving is nothing to it."""
        transport, player = _playing()
        transport.choose_output(chose(FOCUSRITE))
        player.calls.clear()
        assert not transport.output_moved()
        assert player.calls == []

    def test_a_missing_choice_follows_the_default_it_plays_on(self) -> None:
        """Playing on the default because the choice is absent is playing on
        the default: its moving matters."""
        transport, _player = _playing()
        transport.choose_output(chose(BATHYS))
        assert transport.output_moved()
