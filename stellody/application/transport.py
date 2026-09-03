"""Playing a queue through whatever device is behind the playback port.

The window presses buttons; this decides what they mean. It owns the queue and
the rule that ties the queue to the device: loading a track leaves it playing,
because nothing else is what pressing next means. Back is the one exception;
it says why where it is written.

No Qt, no device, no filesystem. The port is the only way out.
"""

from __future__ import annotations

from collections.abc import Callable

from stellody.application.following import Following
from stellody.application.ports import PlaybackPort
from stellody.application.queue_order import QueueOrder, scattered
from stellody.application.sound_settings import SoundSettings
from stellody.domain.album import Album
from stellody.domain.equalising import Equalisation
from stellody.domain.moving import (
    Ordering,
    after_next,
    after_previous,
)
from stellody.domain.playback import (
    Loudness,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
    RepeatMode,
    audible_position,
)
from stellody.domain.queue import Queue, queue_from
from stellody.domain.track import Track

# Told the album and the track that has just played out, so a count of complete
# plays can be kept by somebody who is not the transport. The album comes with
# it because a record is kept against an album's identity and because a track
# that has just ended may already be gone from the library that a rescan
# rebuilt underneath it.
PlayedOut = Callable[[Album, Track], None]


class Transport(SoundSettings, QueueOrder):
    """The transport the window drives: a queue, plus a device to play it on."""

    def __init__(
        self,
        player: PlaybackPort,
        ordering: Ordering = scattered,
        played: PlayedOut = lambda _album, _track: None,
    ) -> None:
        self._player = player
        # What the device has been told to run into next. Gapless
        # transitions happen inside the engine, so this is how the queue
        # finds out where the music already went.
        self._following = Following(player)
        # Told when a track has played out, which is the one thing this class
        # is in a position to know: nothing else can see the difference
        # between a track that ended and one somebody skipped.
        self._played = played
        # Whether back has already been pressed and is waiting at the start of
        # the track. It is what tells a second press to leave the track; it is
        # a state rather than a stopwatch, because two presses timed against
        # each other made the user hammer the button to land two inside the
        # window.
        self._waiting_at_the_start = False
        # Whether the listener is sitting on this track rather than hearing it.
        # A device reports an ending and a hold the same way, since the feeder
        # clears the same flag for both, so the difference is remembered here
        # by the layer that knows which of the two was asked for.
        self._held = False
        self._queue = Queue()
        self._album: Album | None = None
        self._album_order: tuple[Track, ...] = ()
        self._ordering = ordering
        self._loudness = Loudness()
        self._equalisation = Equalisation()
        self._visualising = False
        self._shuffled = False
        self._repeat = RepeatMode.OFF

    def report_plays_to(self, played: PlayedOut) -> None:
        """Say who is told when a track plays out.

        Set rather than injected, which is the one place this application
        does that; ARCHITECTURE.md records why.
        """
        self._played = played

    @property
    def queue(self) -> Queue:
        """What is lined up, plus where in it playback has reached."""
        return self._queue

    @property
    def album(self) -> Album | None:
        """The album the queue was made from; None while nothing is queued."""
        return self._album

    @property
    def current(self) -> Track | None:
        """The track loaded, else the one that would be; None when idle."""
        return self._queue.current

    @property
    def state(self) -> PlaybackState:
        """Where the transport is, as the device reports it."""
        return self._player.state

    @property
    def playing(self) -> bool:
        """Whether sound is being produced right now."""
        return self._player.state is PlaybackState.PLAYING

    def play_album(self, album: Album, first: Track) -> None:
        """Queue an album and start at the track that was activated.

        The album's own order is kept beside the queue, because it is the only
        thing shuffle can be switched back to.
        """
        self._album = album
        self._album_order = album.ordered_tracks()
        self._queue = queue_from(self._album_order, first)
        if self._shuffled:
            self._queue = self._queue.reordered_leading(
                self._ordering(self._album_order)
            )
        self._load_current()

    def toggle(self) -> None:
        """Pause what is playing, resume what is not.

        With nothing loaded there is nothing to toggle. The queue is then what
        would be played rather than what is, so pressing play starts it.
        """
        self._waiting_at_the_start = False
        if self._player.state is PlaybackState.PLAYING:
            self._held = True
            self._player.pause()
            return
        if self._player.state is PlaybackState.PAUSED:
            self._held = False
            self._player.play()
            return
        self._load_current()

    def stop(self) -> None:
        """Give the device back, keeping the queue where it is."""
        self._waiting_at_the_start = False
        self._player.stop()

    @property
    def position(self) -> PlaybackPosition | None:
        """How far playback has reached, as a listener would say it.

        The correction belongs here rather than in the engine because the
        size of the lead is a property of the device the port opened;
        this is the layer that asks the port anything. It is honest to within
        one buffer; it does not model the device's own latency beyond that.
        """
        reported = self._player.position()
        if reported is None:
            return None
        return audible_position(reported, self._player.lead_frames)

    def seek(self, frame: int) -> None:
        """Move within the track in hand, in frames, clamped to it.

        Asked for in the listener's terms, so it is the audible position that
        lands where they asked; the decode is put one buffer further on, which
        is where it has to be for that to be true a moment later.
        """
        if self._player.position() is None:
            return
        self._waiting_at_the_start = False
        self._player.seek(max(0, frame) + self._player.lead_frames)

    def next(self) -> None:
        """Play the following track; what the end does depends on repeat.

        This is the deliberate skip, so it advances under every mode, holding
        one track included. A listener who has asked to move on has asked to
        move on; a repeat that swallowed the request would leave them pressing
        a button that does nothing and no way off the track but the switch.

        Where the move lands is `domain.moving.after_next`; this decides
        only whether landing there means playing.

        Skipping while paused stays paused. Somebody hunting for the track
        they want has said one thing, that they want silence; pressing
        Next is not taking it back, it started playing anyway, which is what
        this passes the state along to prevent.
        """
        self._move_on(playing=self.playing)

    def _move_on(self, playing: bool) -> None:
        """Step to the following track, playing it or waiting on it.

        The one place that decides where Next lands. Whether it plays is
        handed IN rather than read here, because the two callers disagree and
        must: a listener pressing Next keeps whatever state they were in,
        while a track that has played out carries on into the next one. Read
        from the device instead, the second would break, since a device that
        has run out of track reports itself paused exactly as a paused one
        does; the album would then stop dead at every boundary.
        """
        moved = after_next(
            self._queue,
            self._repeat,
            self._shuffled,
            self._album_order,
            self._ordering,
        )
        # Off the end with repeat off there is nowhere to go, so the track
        # in hand is left alone rather than started again.
        if not self._repeat.repeats and moved == self._queue:
            return
        self._restart_at(moved, playing)

    def previous(self) -> None:
        """Return to the start of this track; leave it if already there.

        While a track is playing, back means the beginning of that track: it
        is what somebody who has heard enough of it to reach for the button
        meant by it. It lands there and waits rather than playing on, so the
        moment to carry on belongs to the listener. Pressing back again while
        it waits there means the track before, waiting at ITS beginning.

        What decides between the two is where the transport already is, not
        how quickly the button was pressed twice: a window timed between
        presses made a deliberate second press restart the track instead, so
        going back a track meant hammering the button until two landed inside
        it. `domain.moving.after_previous` holds the rule itself.
        """
        self._open_paused(
            after_previous(
                self._queue,
                self._repeat,
                self._shuffled,
                self._waiting_at_the_start,
            )
        )

    def _restart_at(self, moved: Queue, playing: bool = True) -> None:
        """Take up a position, playing it unless told to wait on it.

        Never counted as waiting at a beginning, whether it plays or not.
        Waiting there is what pressing Back does and it is what a second Back
        reads to mean the track before; arriving somewhere by SKIPPING is not
        that, even when it arrives quietly. Conflating the two made Back after
        a skip jump a track instead of returning to the start of the one in
        hand.
        """
        self._queue = moved
        self._load_current(playing=playing, waiting=False)

    def _open_paused(self, moved: Queue) -> None:
        """Take up a position at its beginning, waiting rather than playing.

        Opening a source leaves the device paused at its first frame, so this
        is the load without the play that every other move makes.
        """
        self._queue = moved
        self._load_current(playing=False)

    def advance_if_finished(self) -> bool:
        """Move on when the track has played out; True when something changed.

        Two different endings arrive through this one door. The device may
        have run into the next track by itself, having had it open and
        decoding before the seam: nothing needs loading there and the only
        work is to move the queue to where the music already is. Otherwise a
        track has simply stopped, which is not reported by the device and so
        is asked about.

        Holding one track is decided HERE rather than in `next`, because the
        two are different questions asked through the same door: an ending is
        what repeat is about, while pressing Next is a listener overruling it.
        Only the first of them replays the track.

        **A track the listener paused is not a track that ended.** The device
        cannot tell the two apart: the feeder clears the same flag whichever
        it is, so a hold reports itself exactly as an ending does.
        Acting on that turned a pause into an ending at the next poll a quarter
        of a second later: on the last track of a queue it gave the device
        back, so the press that should have resumed reloaded the track from its
        beginning instead; in the middle of one it moved silently to the next
        track while the listener was still sitting on this one.
        """
        if self._held:
            return False
        crossed = self._following.crossed()
        if crossed is not None:
            self._report_played()
            self._queue = crossed
            self._waiting_at_the_start = False
            self._line_up()
            return True
        if not self._player.finished:
            return False
        self._report_played()
        if self._repeat is RepeatMode.ONE:
            self._restart_at(self._queue)
            return True
        if not self._queue.has_next and not self._repeat.repeats:
            self._player.stop()
            return True
        # An ending, not a listener: this carries on whatever the device
        # reports about itself.
        self._move_on(playing=True)
        return True

    def _report_played(self) -> None:
        """Say that the track in hand reached its end, to whoever counts."""
        finished = self._queue.current
        album = self._album
        if finished is not None and album is not None:
            self._played(album, finished)

    def _line_up(self) -> None:
        """Tell the device what to run into when the track in hand ends."""
        self._following.line_up(self._queue, self._repeat, self._shuffled)

    def _load_current(self, playing: bool = True, waiting: bool | None = None) -> None:
        """Open the current track and start it. Nothing to open is not a fault.

        A track that will not open raises; the raise is the report. The caller
        has to give the device back and say so on the status line; only the
        caller can do either. Catching it here and telling a listener
        through a callback looked tidier and was worse, because it left the
        press reading as a success: the window then said the track was playing
        and buried the one message saying it was not, with the device still
        held open behind a track that had never started.
        """
        track = self._queue.current
        if track is None:
            return
        # Anything that opens a track and plays it on has left the start
        # behind; anything that opens one and waits is sitting on it. A caller
        # that knows better says so: skipping while paused opens a track
        # without playing it and without sitting at its beginning.
        self._waiting_at_the_start = (not playing) if waiting is None else waiting
        self._held = not playing
        self._player.set_volume(self._loudness.audible)
        self._player.load(
            track.source,
            OutputRequest(sample_rate=track.sample_rate, bit_depth=track.bit_depth),
        )
        self._following.restart()
        self._line_up()
        if playing:
            self._player.play()
