"""The transport: what the buttons mean, without a device in the room.

The player is a hand-written fake recording what it was asked to do, so what
is asserted is the sequence of commands the transport issues.
"""

from __future__ import annotations

from transport_support import FakePlayer, album_of, track

from stellody.application.transport import Transport
from stellody.domain.playback import SILENT_VOLUME, UNITY_VOLUME, PlaybackState

# Any level that is neither silence nor unity, so the two cannot be confused.
HALF_VOLUME = 0.5


def test_activating_a_track_queues_its_album_and_plays_it() -> None:
    one, two = track(1), track(2)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one, two), two)
    assert transport.current is two
    assert player.calls == ["load", "play"]
    assert player.loaded == [two.source]


def test_the_stream_is_asked_for_at_the_track_s_own_rate_and_depth() -> None:
    """Asking for anything else would resample a file nobody asked to alter."""
    one = track(1)
    player = FakePlayer()
    Transport(player).play_album(album_of(one), one)
    request = player.requests[0]
    assert request.sample_rate == one.sample_rate
    assert request.bit_depth == one.bit_depth


def test_the_toggle_pauses_what_is_playing_and_resumes_what_is_not() -> None:
    one = track(1)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one), one)
    transport.toggle()
    assert player.calls[-1] == "pause"
    transport.toggle()
    assert player.calls[-1] == "play"


def test_the_toggle_starts_the_queue_when_nothing_is_loaded() -> None:
    """After a stop the queue is what WOULD play, so play starts it again."""
    one = track(1)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one), one)
    transport.stop()
    player.calls.clear()
    transport.toggle()
    assert player.calls == ["load", "play"]


def test_the_toggle_does_nothing_at_all_with_an_empty_queue() -> None:
    player = FakePlayer()
    Transport(player).toggle()
    assert player.calls == []


def test_next_and_previous_move_through_the_album() -> None:
    """Back twice in quick succession, because one press restarts the track."""
    one, two, three = track(1), track(2), track(3)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one, two, three), one)
    transport.next()
    assert transport.current is two
    transport.previous()
    transport.previous()
    assert transport.current is one
    assert player.loaded == [one.source, two.source, two.source, one.source]


def test_the_end_of_the_queue_does_not_reload_what_is_already_playing() -> None:
    """What back does at the start is its own rule, asserted in test_previous."""
    one, two = track(1), track(2)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one, two), one)
    transport.next()
    transport.next()
    assert transport.current is two
    assert player.calls.count("load") == 2


def test_a_finished_track_moves_the_queue_on() -> None:
    """The device never says a track ended, so the transport asks."""
    one, two = track(1), track(2)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one, two), one)
    assert transport.advance_if_finished() is False
    player.finished = True
    assert transport.advance_if_finished() is True
    assert transport.current is two


def test_a_track_that_plays_out_is_reported_once() -> None:
    """Reaching the end is what counts as a play, so it is the transport that
    says so: nothing else can tell an ending from a track somebody skipped."""
    one, two = track(1), track(2)
    player = FakePlayer()
    played: list = []
    transport = Transport(player, played=lambda _album, track: played.append(track))
    transport.play_album(album_of(one, two), one)
    transport.advance_if_finished()
    assert played == [], "nothing has ended yet"
    player.finished = True
    transport.advance_if_finished()
    assert played == [one], "the one that ended, not the one now playing"


def test_skipping_a_track_is_not_a_play() -> None:
    one, two = track(1), track(2)
    player = FakePlayer()
    played: list = []
    transport = Transport(player, played=lambda _album, track: played.append(track))
    transport.play_album(album_of(one, two), one)
    transport.next()
    assert transport.current is two
    assert played == []


def test_the_last_track_playing_out_still_counts() -> None:
    """It stops rather than advancing, which is not a reason to lose it."""
    one = track(1)
    player = FakePlayer()
    played: list = []
    transport = Transport(player, played=lambda _album, track: played.append(track))
    transport.play_album(album_of(one), one)
    player.finished = True
    transport.advance_if_finished()
    assert played == [one]


def test_a_device_reporting_finished_with_nothing_loaded_counts_nothing() -> None:
    """There is no track to have played out, so there is nothing to record."""
    player = FakePlayer()
    played: list = []
    transport = Transport(player, played=lambda _album, track: played.append(track))
    player.finished = True
    assert transport.advance_if_finished() is True
    assert played == []
    assert player.calls[-1] == "stop"


def test_the_last_track_finishing_stops_rather_than_looping() -> None:
    one = track(1)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one), one)
    player.finished = True
    assert transport.advance_if_finished() is True
    assert player.calls[-1] == "stop"
    assert transport.current is one


def test_the_transport_reports_whether_sound_is_being_made() -> None:
    one = track(1)
    player = FakePlayer()
    transport = Transport(player)
    assert transport.playing is False
    transport.play_album(album_of(one), one)
    assert transport.playing is True
    assert transport.state is PlaybackState.PLAYING


def test_the_queue_is_readable_from_outside() -> None:
    """The window shows what is lined up, so it has to be able to ask."""
    one, two = track(1), track(2)
    transport = Transport(FakePlayer())
    assert transport.queue.current is None
    transport.play_album(album_of(one, two), one)
    assert transport.queue.tracks == (one, two)
    assert transport.queue.has_next is True


def test_the_chosen_volume_is_held_and_re_applied_to_whatever_loads_next() -> None:
    """A level set before anything is loaded still applies to the next track."""
    one = track(1)
    player = FakePlayer()
    transport = Transport(player)
    assert transport.volume == UNITY_VOLUME
    transport.set_volume(SILENT_VOLUME)
    assert transport.volume == SILENT_VOLUME
    assert player.volume == SILENT_VOLUME
    player.volume = UNITY_VOLUME
    transport.play_album(album_of(one), one)
    assert player.volume == SILENT_VOLUME


def test_muting_silences_the_device_without_forgetting_the_level() -> None:
    """Unmuting has to return to the level the listener chose, not to full."""
    player = FakePlayer()
    transport = Transport(player)
    transport.set_volume(HALF_VOLUME)
    transport.set_muted(True)
    assert transport.muted is True
    assert player.volume == SILENT_VOLUME
    assert transport.volume == HALF_VOLUME
    transport.set_muted(False)
    assert player.volume == HALF_VOLUME


def test_a_level_chosen_while_muted_is_stored_without_breaking_the_silence() -> None:
    """Mute is its own switch; nothing but the switch turns it off."""
    player = FakePlayer()
    transport = Transport(player)
    transport.set_muted(True)
    transport.set_volume(HALF_VOLUME)
    assert player.volume == SILENT_VOLUME
    assert transport.volume == HALF_VOLUME
    assert transport.muted is True


def test_a_track_loaded_while_muted_stays_silent() -> None:
    """The level is re-applied on every load, so mute has to survive one."""
    one = track(1)
    player = FakePlayer()
    transport = Transport(player)
    transport.set_muted(True)
    transport.play_album(album_of(one), one)
    assert player.volume == SILENT_VOLUME


def test_repeat_carries_the_end_of_the_queue_round_to_its_start() -> None:
    one, two = track(1), track(2)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one, two), two)
    transport.next()
    assert transport.current is two, "without repeat the end is the end"
    transport.set_repeating(True)
    assert transport.repeating is True
    transport.next()
    assert transport.current is one


def test_repeat_carries_the_start_of_the_queue_round_to_its_end() -> None:
    one, two = track(1), track(2)
    transport = Transport(FakePlayer())
    transport.play_album(album_of(one, two), one)
    transport.set_repeating(True)
    transport.previous()
    transport.previous()
    assert transport.current is two, "the second press is the one that steps"


def test_a_repeating_queue_of_one_track_plays_that_track_again() -> None:
    """Wrapping onto itself means playing again, not standing still."""
    one = track(1)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one), one)
    transport.set_repeating(True)
    player.calls.clear()
    transport.next()
    assert player.calls == ["load", "play"]
    transport.previous()
    assert player.calls == ["load", "play", "load"], "back opens it and waits"


def test_a_finished_last_track_loops_instead_of_stopping_while_repeating() -> None:
    one, two = track(1), track(2)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one, two), two)
    transport.set_repeating(True)
    player.finished = True
    assert transport.advance_if_finished() is True
    assert transport.current is one
    assert "stop" not in player.calls
