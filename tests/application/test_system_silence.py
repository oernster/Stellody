"""Asking, once per start, whether the system is holding the music silent.

`OUTPUTS.md` FR-O21. Found on 2026-10-25: Windows had the installed Stellody at
nought in its Volume mixer, so nothing was heard while everything Stellody
showed said it was playing. The answer here is handed in, never read off the
machine, so no test depends on which devices exist or how they are set.
"""

from __future__ import annotations

from recording_player import RecordingPlayer
from transport_support import album_of, track

from stellody.application.transport import Transport
from stellody.domain.playback import SILENT_VOLUME, UNITY_VOLUME, SystemVolume

AT_NOUGHT = SystemVolume(level=SILENT_VOLUME, muted=False)
MUTED = SystemVolume(level=UNITY_VOLUME, muted=True)
AUDIBLE = SystemVolume(level=UNITY_VOLUME, muted=False)


class Mixer:
    """The system's answer, fixed, counting how often it is asked."""

    def __init__(self, answer: SystemVolume | None) -> None:
        self.answer = answer
        self.asked = 0

    def __call__(self) -> SystemVolume | None:
        self.asked += 1
        return self.answer


def _transport(mixer: Mixer) -> Transport:
    return Transport(RecordingPlayer(), system_volume=mixer)


def _play(transport: Transport) -> None:
    held = album_of(track(1), track(2))
    transport.play_album(held, held.ordered_tracks()[0])


def test_a_level_of_nought_is_handed_over_once_playing() -> None:
    """The music has started and the system holds it at nought: say so."""
    transport = _transport(Mixer(AT_NOUGHT))
    _play(transport)
    assert transport.take_system_silence() == AT_NOUGHT


def test_a_mute_is_handed_over() -> None:
    """Muted is silent whatever the level beside it."""
    transport = _transport(Mixer(MUTED))
    _play(transport)
    assert transport.take_system_silence() == MUTED


def test_it_is_handed_over_once_per_start() -> None:
    """Said once, then left alone for the rest of that start."""
    mixer = Mixer(AT_NOUGHT)
    transport = _transport(mixer)
    _play(transport)
    transport.take_system_silence()
    assert transport.take_system_silence() is None
    assert mixer.asked == 1


def test_an_audible_level_is_not_handed_over() -> None:
    """Nothing to say when the system lets the music through."""
    transport = _transport(Mixer(AUDIBLE))
    _play(transport)
    assert transport.take_system_silence() is None


def test_a_system_that_cannot_say_claims_nothing() -> None:
    """No answer, as on a platform with no such setting, is not silence."""
    transport = _transport(Mixer(None))
    _play(transport)
    assert transport.take_system_silence() is None


def test_the_default_claims_nothing() -> None:
    """A transport handed no reader asks nothing of the system."""
    transport = Transport(RecordingPlayer())
    _play(transport)
    assert transport.take_system_silence() is None


def test_nothing_is_asked_before_music_starts() -> None:
    """With nothing started there is no session for the system to hold."""
    mixer = Mixer(AT_NOUGHT)
    transport = _transport(mixer)
    assert transport.take_system_silence() is None
    assert mixer.asked == 0


def test_a_pause_before_the_poll_waits_for_the_music() -> None:
    """Paused before it was asked: asked once the music is playing again."""
    mixer = Mixer(AT_NOUGHT)
    transport = _transport(mixer)
    _play(transport)
    transport.toggle()
    assert transport.take_system_silence() is None
    assert mixer.asked == 0
    transport.toggle()
    assert transport.take_system_silence() == AT_NOUGHT


def test_a_resume_asks_again() -> None:
    """The level may have been put wrong while paused."""
    transport = _transport(Mixer(AT_NOUGHT))
    _play(transport)
    transport.take_system_silence()
    transport.toggle()
    transport.toggle()
    assert transport.take_system_silence() == AT_NOUGHT


def test_the_next_track_asks_again() -> None:
    """Every track opened is a new stream for the system to hold."""
    transport = _transport(Mixer(AT_NOUGHT))
    _play(transport)
    transport.take_system_silence()
    transport.next()
    assert transport.take_system_silence() == AT_NOUGHT
