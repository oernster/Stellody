"""Drawing a track's shape, whether or not anybody has pressed play.

Split out of the transport half, along a real seam: over there is what the
buttons DO, here is which track the bar is drawing and when its shape gets
measured.

**What is loaded wins; what is highlighted fills the silence.** The playhead
belongs to the track that is loaded, so while there is one, that is the shape
under it: browsing the library during playback must not swap the picture out
from under the line crossing it. With nothing loaded there is no playhead to
contradict, so the bar draws whatever is highlighted and a track shows what it
looks like before it is played rather than a flat line that says nothing.

**A highlighted track waits; a loaded one does not.** Measuring decodes the
whole file, so measuring on every step through a list would set a decode going
for each row somebody passed over on the way to the one they wanted. A
highlight therefore has to settle first. A loaded track is measured at once:
somebody pressed play and is watching the bar.

Nothing here decodes. The measurement runs on the thread `ShapeRunner` owns;
a shape already measured comes back from the store without touching the file
at all, which is the ordinary case for anything played before.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Slot

# Long enough that arrowing down a list measures the row somebody stopped on
# rather than every row they passed, short enough that stopping on one and
# waiting does not feel like a pause before anything happens.
HIGHLIGHT_SETTLE_MS = 400


class ShowingShapes:
    """The window's half of drawing the shape under the position line."""

    def start_shapes(self) -> None:
        """Hold the settling timer the highlighted track is measured after."""
        self._shape_settle = QTimer(self)
        self._shape_settle.setSingleShot(True)
        self._shape_settle.setInterval(HIGHLIGHT_SETTLE_MS)
        self._shape_settle.timeout.connect(self._measure_settled)
        self._shape_wanted = None

    def follow_shape(self) -> None:
        """Draw the shape of what is loaded, else of what is highlighted.

        Called from the transport poll rather than wired to a selection signal,
        so one path decides what the bar is showing whatever moved: the
        transport, the highlight or the view they are read from.
        """
        if self._shape_runner is None:
            return
        source, loaded = self._shape_source()
        if source == self._shape_shown:
            return
        self._shape_shown = source
        if source is None:
            self._shape_settle.stop()
            self._position_bar.show_shape(None)
            return
        remembered = self._shapes.remembered(source) if self._shapes else None
        self._position_bar.show_shape(remembered)
        if remembered is not None:
            self._shape_settle.stop()
            return
        if loaded:
            self._shape_settle.stop()
            self._shape_runner.measure(source)
            return
        self._shape_wanted = source
        self._shape_settle.start()

    def stop_shapes(self) -> None:
        """Let go of a measurement in flight on the way out."""
        self._shape_settle.stop()
        if self._shape_runner is not None:
            self._shape_runner.stop()

    def _shape_source(self):
        """The track the bar should be drawing, plus whether it is loaded."""
        playing = self._transport.current
        if playing is not None:
            return playing.source, True
        highlighted = self._model.track_at(self.highlighted())
        return (None, False) if highlighted is None else (highlighted.source, False)

    @Slot()
    def _measure_settled(self) -> None:
        """Measure the highlighted track, now that the highlight has settled.

        The wanted track is read again rather than trusted. Between the timer
        starting and it going off, the highlight can move to something already
        measured; it can also move to nothing at all.
        """
        if self._shape_runner is None or self._shape_wanted is None:
            return
        if self._shape_wanted == self._shape_shown:
            self._shape_runner.measure(self._shape_wanted)

    @Slot(object, object)
    def _on_shape(self, source, shape) -> None:
        """Draw a measurement that has just arrived, if it is still wanted."""
        if source == self._shape_shown:
            self._position_bar.show_shape(shape)
