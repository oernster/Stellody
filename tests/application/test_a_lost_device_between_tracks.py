"""A device lost at a track boundary holds the music; it never falls through.

Found by the audit of 2026-10-03. Between two tracks that do not join, the
engine has finished and reads as paused until the next poll moves the queue on.
A loss arriving then was not treated as a pause, since nothing was playing, so
the poll opened the next track on the system default and played it: the
headphones switched off and the music went to the speakers without a press,
which OQ-O5 (FR-O11) rules out. A device name gone stale before Qt
noticed did the same, by failing to open and falling back.

Ruled by Oliver on 2026-10-03: a lost chosen device holds the music whatever
the state; an automatic advance never plays on a device other than the one the
music was on. A press then carries on through the default, as FR-O11 says.
"""

from __future__ import annotations

from recording_player import RecordingPlayer
from transport_support import album_of, track

from stellody.application.transport import Transport
from stellody.domain.outputs import OutputChoice, OutputDevice
from stellody.domain.playback import PlaybackState

SPEAKERS = OutputDevice(identity="{speakers}", name="Speakers (Realtek)")
BATHYS = OutputDevice(identity="{bathys}", name="Headphones (Focal Bathys)")
BOTH = (SPEAKERS, BATHYS)
GONE = "Device unavailable [PaErrorCode -9985]"


def _at_a_seam(choice: OutputDevice | None) -> tuple[Transport, RecordingPlayer]:
    """The first of two tracks just played out; the second does not join.

    `choice` is the device chosen, None being System default. The engine's
    own reading at that moment is finished and paused.
    """
    player = RecordingPlayer()
    player.joins = False
    transport = Transport(player)
    transport.outputs_listed(BOTH)
    if choice is not None:
        transport.choose_output(
            OutputChoice(identity=choice.identity, name=choice.name)
        )
    one = track(1)
    transport.play_album(album_of(one, track(2)), one)
    player.finished = True
    player.state = PlaybackState.PAUSED
    player.calls.clear()
    return transport, player


def test_the_loss_reported_first_at_a_seam_holds_the_music() -> None:
    """Qt says the headphones went, then the poll runs: nothing opens."""
    transport, player = _at_a_seam(BATHYS)
    transport.outputs_listed((SPEAKERS,))
    transport.advance_if_finished()
    assert "load" not in player.calls
    assert "play" not in player.calls


def test_a_stale_device_failing_at_a_seam_holds_the_music() -> None:
    """The poll runs before Qt notices; the next track waits, unplayed."""
    transport, player = _at_a_seam(BATHYS)
    player.refuses[BATHYS.identity] = GONE
    transport.advance_if_finished()
    assert "play" not in player.calls
    assert player.state is PlaybackState.PAUSED
    assert transport.current == track(2)
    refusal = transport.take_refusal()
    assert refusal is not None
    assert (refusal.device, refusal.reason) == (BATHYS, GONE)
    assert not transport.playing, "the window says paused from this"


def test_system_default_headphones_lost_at_a_seam_hold_the_music() -> None:
    """The default left the list between tracks; the speakers stay silent."""
    transport, player = _at_a_seam(None)
    assert transport.output_moved() is True
    transport.advance_if_finished()
    assert "load" not in player.calls
    assert "play" not in player.calls


def test_a_press_after_the_hold_carries_on_through_the_default() -> None:
    """FR-O11: the listener's press is what agrees to the speakers."""
    transport, player = _at_a_seam(BATHYS)
    transport.outputs_listed((SPEAKERS,))
    transport.advance_if_finished()
    transport.toggle()
    assert player.device is None
    assert player.calls[-1] == "play"


def test_a_loss_in_the_middle_of_a_track_still_pauses_it() -> None:
    """The control: the case the pause was first written for."""
    player = RecordingPlayer()
    transport = Transport(player)
    transport.outputs_listed(BOTH)
    one = track(1)
    transport.play_album(album_of(one, track(2)), one)
    player.calls.clear()
    assert transport.output_moved() is True
    assert player.calls == ["pause"]


def test_a_seam_on_the_device_the_music_was_on_plays_on() -> None:
    """Nothing lost: the next track opens where the last one played; it plays."""
    transport, player = _at_a_seam(BATHYS)
    transport.advance_if_finished()
    assert player.calls == ["load", "play"]
    assert player.device == BATHYS


def test_music_on_the_default_for_a_missing_choice_plays_on_at_a_seam() -> None:
    """FR-O10: already on the default, so carrying on moves it nowhere new."""
    player = RecordingPlayer()
    player.joins = False
    transport = Transport(player)
    transport.outputs_listed((SPEAKERS,))
    transport.choose_output(OutputChoice(identity=BATHYS.identity, name=BATHYS.name))
    one = track(1)
    transport.play_album(album_of(one, track(2)), one)
    player.finished = True
    player.state = PlaybackState.PAUSED
    player.calls.clear()
    transport.advance_if_finished()
    assert player.calls == ["load", "play"]
