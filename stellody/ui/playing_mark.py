"""Marking the row of the track in hand, in whichever view shows it.

Reported on 2026-09-13 and reproduced the same day: once another track was
clicked while one played, nothing on screen said which was playing. The list
and the album open under the sleeves draw from one model through one delegate,
so the mark lives in the model's background and reaches both at once.

**The model is told what to mark, never why.** Which track is in hand is the
transport's business; this holds only the answer and the colour, the way
`flashing.py` holds a pulse without the model keeping a clock.

**Marked by handle, not by position and not by object.** A search or a sort
rebuilds the rows, so a remembered row number would mark whatever landed
there next. An object fares no better: a scan, a repair or a tag edit reloads
the library and builds every track afresh, while the transport plays on with
the track it was handed. Reported by Oliver on 2026-09-17 and reproduced the
same day: the foot went on naming the playing track with no row marked
anywhere, which is the shape of a mark held by an object that no longer
exists. The handle is the album's identity with the disc and track number
under it, which is what the listening log uses and for this exact reason; see
`stellody.domain.listening`.
"""

from __future__ import annotations

from PySide6.QtGui import QBrush, QColor

from stellody.domain.album import Album
from stellody.domain.listening import track_handle
from stellody.domain.track import Track


def handle_for(album: Album | None, track: Track | None) -> str | None:
    """The handle this track is marked under; None where nothing is in hand."""
    if album is None or track is None:
        return None
    return track_handle(album.identity, track.disc_number, track.track_number)


class PlayingMark:
    """The one track marked as in hand, with the colour it is marked in."""

    def __init__(self, model) -> None:
        self._model = model
        self._handle: str | None = None
        self._colour: QColor | None = None
        model.set_mark(self)

    @property
    def handle(self) -> str | None:
        """The handle marked; None while nothing is in hand."""
        return self._handle

    def show(self, album: Album | None, track: Track | None) -> None:
        """Mark this track instead, drawing both rows that changed."""
        handle = handle_for(album, track)
        if handle == self._handle:
            return
        was = self._handle
        self._handle = handle
        self._redraw(was)
        self._redraw(handle)

    def wear(self, colour: str) -> None:
        """Mark in this colour from now on, as an appearance changes."""
        self._colour = QColor(colour)
        self._redraw(self._handle)

    def brush(self, handle: str | None) -> QBrush | None:
        """The paint for the row known by this handle; None for any other."""
        if handle is None or handle != self._handle or self._colour is None:
            return None
        return QBrush(self._colour)

    def _redraw(self, handle: str | None) -> None:
        """Ask the model to draw one track's row again, where it has one."""
        if handle is not None:
            self._model.redraw_row(self._model.index_for_handle(handle))
