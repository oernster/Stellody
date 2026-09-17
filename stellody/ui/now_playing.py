"""Saying what is playing: a mark on its row and its name along the foot.

Both follow the transport rather than a gesture. The status bar used to say
"Playing" only when a track was double clicked, for six seconds, so after Next
or a track playing out it went on naming the one before. Reproduced on
2026-09-13. The name is now a permanent widget, written from the transport on
every change however the change came about, then emptied by a stop.

**A paused track is still in hand.** Only a stop gives the device back, so the
mark and the name stay through a pause, the same line `PlaybackState.is_active`
draws.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from stellody.domain.track import Track
from stellody.ui.playing_mark import PlayingMark
from stellody.ui.theme import Mode, palette_for

NOW_PLAYING = "Playing: {title}, {artists}"
# A track whose tags credit nobody is named by its title alone, rather than
# with a comma left hanging where the artists would have gone.
NOW_PLAYING_UNCREDITED = "Playing: {title}"


def now_playing_line(track: Track | None) -> str:
    """What the foot says about this track; nothing where none is in hand."""
    if track is None:
        return ""
    if not track.artist_text:
        return NOW_PLAYING_UNCREDITED.format(title=track.title)
    return NOW_PLAYING.format(title=track.title, artists=track.artist_text)


class NowPlaying:
    """The window's half of saying what is playing."""

    def start_now_playing(self) -> None:
        """Build the mark over the model plus the name along the foot."""
        self._mark = PlayingMark(self._model)
        self._now_playing = QLabel(self)
        # Words to read rather than a control, so never a stop on the ring.
        self._now_playing.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.statusBar().addPermanentWidget(self._now_playing)

    def show_now_playing(self) -> None:
        """Mark and name the track in hand; clear both once nothing is."""
        in_hand = self._transport.current if self._transport.state.is_active else None
        # The album goes with it, because the mark is held by handle rather
        # than by the track object: see `playing_mark.py`.
        self._mark.show(self._transport.album, in_hand)
        self._now_playing.setText(now_playing_line(in_hand))

    def show_mark_appearance(self, mode: Mode) -> None:
        """Mark in the pink belonging to this appearance."""
        self._mark.wear(palette_for(mode).playing)
