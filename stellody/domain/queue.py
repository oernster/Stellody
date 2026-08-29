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
