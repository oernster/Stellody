"""The picture of the track in hand: opened as it starts, given up as it ends.

The sound is the clock. Nothing here keeps time or decides when a frame should
change; it is asked what is showing at a moment the transport has already
reached, which is what keeps one track's picture and its sound from having two
opinions about where playback is.

A track without a picture is the ordinary case rather than an error, so it
opens nothing and answers nothing; every layer above can ask the same
question of every track without first asking what kind of track it is.

The port is declared here rather than in `ports.py` because this is its only
consumer and `ports.py` is close enough to the module cap that adding to it
would leave it poised on the edge.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from stellody.domain.picture import Picture
from stellody.domain.playback import PlaybackError
from stellody.domain.track import TrackSource


class PicturePort(Protocol):
    """Reads the picture stream of one file. Never touches its sound."""

    def picture_at(self, elapsed_ms: int) -> Picture | None:
        """The frame showing that far into the track; None before the first."""
        ...

    def close(self) -> None:
        """Give the file back. The port is unusable afterwards."""
        ...


class Pictures:
    """Holds open the picture of whatever is playing. Nothing else."""

    def __init__(self, open_picture: Callable[[TrackSource], PicturePort]) -> None:
        self._open = open_picture
        self._source: TrackSource | None = None
        self._reader: PicturePort | None = None

    @property
    def showing(self) -> bool:
        """True while there is a picture to draw."""
        return self._reader is not None

    def follow(self, source: TrackSource | None) -> None:
        """Point at this source, opening or closing whatever that means.

        Safe to call on every tick with the same source, which is how the
        caller is meant to use it: asking what is playing is cheap, working
        out whether it has changed is this object's business rather than
        every caller's.

        A file that will not open shows nothing rather than raising. The sound
        is what a listener came for and it is already playing by the time this
        is asked; stopping the track because its picture could not be read
        would take away the part that was working.
        """
        if source is not None and source == self._source:
            return
        self.close()
        if source is None or not source.carries_picture:
            return
        try:
            self._reader = self._open(source)
        except PlaybackError:
            return
        self._source = source

    def at(self, elapsed_ms: int) -> Picture | None:
        """The picture showing that far into the track in hand."""
        if self._reader is None:
            return None
        return self._reader.picture_at(elapsed_ms)

    def close(self) -> None:
        """Give up whatever is open, so a file is never held after its track."""
        if self._reader is not None:
            self._reader.close()
        self._reader = None
        self._source = None
