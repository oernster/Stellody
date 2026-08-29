"""The transport: what the buttons mean, without a device in the room.

The player is a hand-written fake recording what it was asked to do, so what
is asserted is the sequence of commands the transport issues.
"""

from __future__ import annotations

from stellody.application.transport import Transport
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.playback import (
    OutputMode,
    OutputReport,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
)
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource


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
