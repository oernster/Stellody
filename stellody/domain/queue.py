"""What is lined up to play, plus which of it is playing now.

A queue is a value: every move returns a new one rather than altering this
one, so nothing can change what is playing as a side effect of being asked a
question about it. Moving off either end is not an error, it is simply a queue
that reports there is nowhere further to go.
"""

from __future__ import annotations

from dataclasses import dataclass

from stellody.domain.track import Track

NOTHING = -1


@dataclass(frozen=True, slots=True)
class Queue:
    """An ordered run of tracks, with one of them current."""

    tracks: tuple[Track, ...] = ()
    index: int = NOTHING

    def __post_init__(self) -> None:
        if self.index < NOTHING:
            raise ValueError("a queue position cannot be before the start")
        if self.index >= len(self.tracks):
            raise ValueError("a queue position cannot be past the end")

    @property
    def current(self) -> Track | None:
        """What is playing, else what would; None when the queue is empty."""
        if self.index == NOTHING:
            return None
        return self.tracks[self.index]

    @property
    def has_previous(self) -> bool:
        """Whether there is a track before this one."""
        return self.index > 0

    @property
    def has_next(self) -> bool:
        """Whether there is a track after this one."""
        return NOTHING < self.index < len(self.tracks) - 1

    def previous(self) -> Queue:
        """The queue one track earlier; unchanged at the start."""
        if not self.has_previous:
            return self
        return Queue(self.tracks, self.index - 1)

    def next(self) -> Queue:
        """The queue one track later; unchanged at the end."""
        if not self.has_next:
            return self
        return Queue(self.tracks, self.index + 1)

    def wrapped_next(self) -> Queue:
        """The queue one track later, back to the first one at the end."""
        if self.index == NOTHING:
            return self
        return Queue(self.tracks, (self.index + 1) % len(self.tracks))

    def wrapped_previous(self) -> Queue:
        """The queue one track earlier, round to the last one at the start."""
        if self.index == NOTHING:
            return self
        return Queue(self.tracks, (self.index - 1) % len(self.tracks))

    def reordered(self, tracks: tuple[Track, ...]) -> Queue:
        """The same run under a given order, still at whatever is current.

        The order arrives rather than being worked out here, so the domain
        needs no source of randomness of its own. An order that has lost the
        track being played is refused: silently moving to a different track is
        the one thing reordering must not do.
        """
        playing = self.current
        if playing is None:
            return Queue(tracks)
        moved = Queue(tracks).at(playing)
        if moved.current is not playing:
            raise ValueError("a reordering must keep the track that is current")
        return moved

    def reordered_leading(self, tracks: tuple[Track, ...]) -> Queue:
        """The same run under a given order, with what is playing at its head.

        Shuffling mid-track must leave somewhere to go. Keeping the position
        the new order happens to give the current track strands everything
        scattered before it; where it falls last there is no next track at all,
        measured as a next button that did nothing. Leading with the track in
        hand puts the whole of the rest of the run ahead of it.
        """
        playing = self.current
        if playing is None:
            return Queue(tracks)
        if not any(track is playing for track in tracks):
            raise ValueError("a reordering must keep the track that is current")
        rest = tuple(track for track in tracks if track is not playing)
        return Queue((playing,) + rest, 0)

    def at(self, track: Track) -> Queue:
        """The same tracks, positioned at this one.

        Position is by identity rather than by equality, because a library may
        legitimately hold two identical tracks and the one that was activated
        is the one that should play.
        """
        for position, candidate in enumerate(self.tracks):
            if candidate is track:
                return Queue(self.tracks, position)
        return self


def queue_from(tracks: tuple[Track, ...], first: Track) -> Queue:
    """A queue of these tracks, starting at the one that was activated."""
    return Queue(tracks).at(first)
