"""What the end of a track does: playing out, running on, stopping by itself.

Split out of `transport.py` on 2026-10-03, when two findings of that day's
audit put it into the band below the length a module is allowed. Both are about
the moment one track gives way to the next, which is one concern: the poll
asking whether anything ended and deciding what follows.

A track that stopped by itself is named with its reason and passed over. One
that played out carries on, except onto a device the music was not on: a
device lost at the boundary holds the music rather than letting it fall through
to the speakers (`OUTPUTS.md` OQ-O5, ruled again by Oliver on 2026-10-03).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from stellody.application.following import Following
from stellody.application.playback_ports import PlaybackPort
from stellody.domain.album import Album
from stellody.domain.moving import RepeatMode
from stellody.domain.outputs import OutputDevice
from stellody.domain.queue import Queue
from stellody.domain.track import Track


@dataclass(frozen=True, slots=True)
class Failure:
    """A track that stopped playing by itself, with the reason the device gave.

    The track is None only where nothing was in hand to name, which the window
    words as it words any other failure it cannot attribute.
    """

    track: Track | None
    reason: str


class Ending:
    """The end of a track, as a transport meets it. Mixed into `Transport`."""

    _player: PlaybackPort
    _following: Following
    _queue: Queue
    _repeat: RepeatMode
    _album: Album | None
    _held: bool
    _waiting_at_the_start: bool
    _in_use: OutputDevice | None
    _failure: Failure | None
    _played: Callable[[Album, Track], None]

    def take_failure(self) -> Failure | None:
        """The last track that stopped by itself, once; None after it is taken."""
        failure, self._failure = self._failure, None
        return failure

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

        A failure is asked about first, held or not: its feeder has ended, so
        the track cannot be resumed and there is nothing to sit on.
        """
        reason = self._player.failure
        if reason:
            self._failure = Failure(track=self._queue.current, reason=reason)
            self._onward()
            return True
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
            self._carry_on(lambda: self._restart_at(self._queue, playing=False))
            return True
        self._onward()
        return True

    def _onward(self) -> None:
        """Carry on to the next track; at the end of the queue, let go.

        An ending, not a listener: this carries on whatever the device reports
        about itself. Under repeat one it still moves, which is what keeps a
        track that will not play from being tried again at every poll.
        """
        if not self._queue.has_next and not self._repeat.repeats:
            self._player.stop()
            return
        self._carry_on(lambda: self._move_on(False))

    def _carry_on(self, step: Callable[[], None]) -> None:
        """Take `step`, which opens a track paused; play it where the music was.

        Opened paused, then started only where the device in use is the one
        the music was on before. Found by the audit of 2026-10-03: a chosen
        device whose name had gone stale failed to open at the boundary, the
        open fell back to the system default (FR-O08) and the next track
        played through the speakers without a press. It now waits there,
        paused, for the press FR-O11 asks for; the refusal is still said.
        """
        before = self._in_use
        step()
        if self._in_use != before:
            return
        self._held = False
        self._player.play()

    def _report_played(self) -> None:
        """Say that the track in hand reached its end, to whoever counts."""
        finished = self._queue.current
        album = self._album
        if finished is not None and album is not None:
            self._played(album, finished)
