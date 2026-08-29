"""The transport: what the buttons mean, without a device in the room.

The player is a hand-written fake recording what it was asked to do, so what
is asserted is the sequence of commands the transport issues.
"""

from __future__ import annotations

from stellody.application.transport import Transport
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.playback import (
    SILENT_VOLUME,
    UNITY_VOLUME,
    OutputMode,
    OutputReport,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
)
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource

# Any level that is neither silence nor unity, so the two cannot be confused.
HALF_VOLUME = 0.5


def track(number: int) -> Track:
    """One ordinary track of an album."""
    return Track(
        source=TrackSource(path=f"{number}.flac"),
        disc_number=1,
        track_number=number,
        title=f"Track {number}",
        artists=("Holst",),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


def album_of(*tracks: Track) -> Album:
    """An album holding these tracks."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
        tracks=tracks,
    )


class FakePlayer:
    """A playback port that records rather than plays."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.loaded: list[TrackSource] = []
        self.requests: list[OutputRequest] = []
        self.state = PlaybackState.STOPPED
        self.finished = False
        self.volume = UNITY_VOLUME

    def load(self, source: TrackSource, request: OutputRequest) -> OutputReport:
        """Record the load and report a plain shared stream."""
        self.calls.append("load")
        self.loaded.append(source)
        self.requests.append(request)
        self.finished = False
        self.state = PlaybackState.PAUSED
        return OutputReport(
            request=request,
            mode=OutputMode.SHARED,
            sample_rate=request.sample_rate,
            bit_depth=request.bit_depth,
        )

    def play(self) -> None:
        """Record the play."""
        self.calls.append("play")
        self.state = PlaybackState.PLAYING

    def pause(self) -> None:
        """Record the pause."""
        self.calls.append("pause")
        self.state = PlaybackState.PAUSED

    def stop(self) -> None:
        """Record the stop."""
        self.calls.append("stop")
        self.state = PlaybackState.STOPPED

    def seek(self, frame: int) -> None:
        """Record the seek."""
        self.calls.append(f"seek {frame}")

    def position(self) -> PlaybackPosition | None:
        """Nothing to report in these tests."""
        return None

    def set_volume(self, level: float) -> None:
        """Record the level asked for."""
        self.volume = level


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
    one, two, three = track(1), track(2), track(3)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one, two, three), one)
    transport.next()
    assert transport.current is two
    transport.previous()
    assert transport.current is one
    assert player.loaded == [one.source, two.source, one.source]


def test_neither_end_of_the_queue_reloads_what_is_already_playing() -> None:
    one, two = track(1), track(2)
    player = FakePlayer()
    transport = Transport(player)
    transport.play_album(album_of(one, two), one)
    transport.previous()
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


def reversed_order(tracks: tuple[Track, ...]) -> tuple[Track, ...]:
    """A shuffle that is not random, so what it did can be asserted."""
    return tuple(reversed(tracks))


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


def test_shuffling_reorders_the_queue_and_keeps_playing_what_was_playing() -> None:
    one, two, three = track(1), track(2), track(3)
    player = FakePlayer()
    transport = Transport(player, ordering=reversed_order)
    transport.play_album(album_of(one, two, three), two)
    player.calls.clear()
    transport.set_shuffled(True)
    assert transport.shuffled is True
    assert transport.queue.tracks == (three, two, one)
    assert transport.current is two
    assert player.calls == [], "reordering what comes next interrupts nothing"


def test_unshuffling_puts_the_album_back_into_its_own_order() -> None:
    one, two, three = track(1), track(2), track(3)
    transport = Transport(FakePlayer(), ordering=reversed_order)
    transport.play_album(album_of(one, two, three), one)
    transport.set_shuffled(True)
    transport.set_shuffled(False)
    assert transport.queue.tracks == (one, two, three)
    assert transport.current is one


def test_shuffle_chosen_before_anything_plays_applies_to_the_next_album() -> None:
    """The switch is remembered, so it does not have to be pressed twice."""
    one, two = track(1), track(2)
    transport = Transport(FakePlayer(), ordering=reversed_order)
    transport.set_shuffled(True)
    assert transport.queue.tracks == ()
    transport.play_album(album_of(one, two), one)
    assert transport.queue.tracks == (two, one)
    assert transport.current is one


def test_the_default_shuffle_keeps_every_track_and_loses_none() -> None:
    """The real one is random, so what is asserted is what it preserves."""
    tracks = tuple(track(number) for number in range(1, 6))
    transport = Transport(FakePlayer())
    transport.play_album(album_of(*tracks), tracks[0])
    transport.set_shuffled(True)
    assert set(transport.queue.tracks) == set(tracks)
    assert len(transport.queue.tracks) == len(tracks)
    assert transport.current is tracks[0]


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
    assert transport.current is two


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
    assert player.calls == ["load", "play", "load", "play"]


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
