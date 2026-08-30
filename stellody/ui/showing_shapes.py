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

**Measuring starts the moment the highlight moves.** It was made to settle for
a fraction of a second first, on the reasoning that a decode per row passed
over would be wasteful. Measured, that reasoning had the wrong culprit: the
cost was not the decodes but letting go of one, which blocked the interface
thread for a full two seconds because a decode cannot be interrupted by asking
its thread to quit. Both halves are now fixed where they belong. A measurement
is told to give up and stops at the next block it reads; letting go of one
never waits, so starting one on every step is affordable and the wait before it
bought nothing.

Nothing here decodes. The measurement runs on the thread `ShapeRunner` owns;
a shape already measured comes back from the store without touching the file
at all, which is the ordinary case for anything played before and costs 0.6
milliseconds, measured.
"""

from __future__ import annotations

from PySide6.QtCore import Slot


class ShowingShapes:
    """The window's half of drawing the shape under the position line."""

    def follow_shape(self) -> None:
        """Draw the shape of what is loaded, else of what is highlighted.

        Called both from the transport poll and from the highlight moving, so
        one path decides what the bar is showing whatever moved. Driving it
        from the poll alone left up to a quarter of a second between arrowing
        on to a track and its shape appearing, for no reason a listener could
        see.
        """
        if self._shape_runner is None:
            return
        source = self._shape_source()
        if source == self._shape_shown:
            return
        self._shape_shown = source
        if source is None:
            self._position_bar.show_shape(None)
            return
        remembered = self._shapes.remembered(source) if self._shapes else None
        self._position_bar.show_shape(remembered)
        if remembered is None:
            self._shape_runner.measure(source)

    def stop_shapes(self) -> None:
        """Let go of a measurement in flight on the way out."""
        if self._shape_runner is not None:
            self._shape_runner.stop()

    def _shape_source(self):
        """The track the bar should be drawing; None when there is none."""
        playing = self._transport.current
        if playing is not None:
            return playing.source
        highlighted = self._model.track_at(self.highlighted())
        return None if highlighted is None else highlighted.source

    @Slot(object, object)
    def _on_shape(self, source, shape) -> None:
        """Draw a measurement that has just arrived, if it is still wanted."""
        if source == self._shape_shown:
            self._position_bar.show_shape(shape)
