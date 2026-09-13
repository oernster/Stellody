"""Marking the row of the track in hand, in whichever view shows it.

Reported on 2026-09-13 and reproduced the same day: once another track was
clicked while one played, nothing on screen said which was playing. The list
and the album open under the sleeves draw from one model through one delegate,
so the mark lives in the model's background and reaches both at once.

**The model is told what to mark, never why.** Which track is in hand is the
transport's business; this holds only the answer and the colour, the way
`flashing.py` holds a pulse without the model keeping a clock.

**Marked by identity, not by position.** A search or a sort rebuilds the rows,
so a remembered row number would mark whatever landed there next. The track
itself is held and each cell asks whether it is that track.
"""

from __future__ import annotations

from PySide6.QtGui import QBrush, QColor

from stellody.domain.track import Track


class PlayingMark:
    """The one track marked as in hand, with the colour it is marked in."""

    def __init__(self, model) -> None:
        self._model = model
        self._track: Track | None = None
        self._colour: QColor | None = None
        model.set_mark(self)

    @property
    def track(self) -> Track | None:
        """The track marked; None while nothing is in hand."""
        return self._track

    def show(self, track: Track | None) -> None:
        """Mark this track instead, drawing both rows that changed."""
        if track is self._track:
            return
        was = self._track
        self._track = track
        self._redraw(was)
        self._redraw(track)

    def wear(self, colour: str) -> None:
        """Mark in this colour from now on, as an appearance changes."""
        self._colour = QColor(colour)
        self._redraw(self._track)

    def brush(self, track: Track | None) -> QBrush | None:
        """The paint for a row showing this track; None for any other row."""
        if track is None or track is not self._track or self._colour is None:
            return None
        return QBrush(self._colour)

    def _redraw(self, track: Track | None) -> None:
        """Ask the model to draw one track's row again, where it has one."""
        if track is not None:
            self._model.redraw_row(self._model.index_for(track))
