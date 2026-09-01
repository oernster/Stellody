"""A checkbox whose ring goes round the box rather than round the words.

Measured before it was written, because the obvious route does not work. Qt
draws a checkbox's square itself; the moment a stylesheet names `::indicator`
it takes the whole subcontrol over: a rule setting only a border
there left an empty square with no tick in it at all, while a rule scoped to
`:focus` alone changed nothing whatsoever. Owning the square in the sheet would
therefore mean inventing a checked picture and an unchecked one, which is a
redrawn checkbox rather than a ring on the one Qt already draws.

So the ring is painted over the square Qt has drawn, at the rectangle Qt itself
reports for it, which is the same answer `stars.py` reached for its own reason.
The room to draw it comes from the padding the stylesheet already gives the
control: the square sits eight pixels in and five down, measured, so a ring
just outside it is not clipped.

The colours arrive through the stylesheet as properties rather than through a
mode handed down from the window. The sheet is set on the whole application, so
a dialog is reached by it wherever it was opened from; the palette stays the
one home for both values. They are properties rather than states because a
`qproperty` is read when the widget is polished; which of the two to paint is
then the widget's own question, asked of its own state.
"""

from __future__ import annotations

from PySide6.QtCore import Property, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QCheckBox, QStyle, QStyleOptionButton, QWidget

RING_PX = 2
RING_RADIUS_PX = 4
# Drawn outside the square rather than on its edge, so it reads as a ring round
# the box instead of as a recolouring of the box's own border.
RING_INSET_PX = -2


class RingedCheckBox(QCheckBox):
    """A checkbox that paints its own ring, on the square and nowhere else."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        # Without this Qt sends no hover events to a widget that is not
        # stylesheet-painted, so the ring would answer focus but not the mouse.
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._ring = ""
        self._danger = ""

    def _read_ring(self) -> str:
        """The colour a focused or hovered box is ringed in."""
        return self._ring

    def _write_ring(self, colour: str) -> None:
        """Take the colour the stylesheet is handing down."""
        self._ring = colour
        self.update()

    def _read_danger(self) -> str:
        """The colour a box that cannot be pressed is ringed in."""
        return self._danger

    def _write_danger(self, colour: str) -> None:
        """Take the colour the stylesheet is handing down."""
        self._danger = colour
        self.update()

    ringColour = Property(str, _read_ring, _write_ring)
    dangerColour = Property(str, _read_danger, _write_danger)

    def paintEvent(self, event) -> None:
        """Qt's own checkbox, then the ring over the square it drew."""
        super().paintEvent(event)
        colour = self._ring_now()
        if not colour:
            return
        option = QStyleOptionButton()
        self.initStyleOption(option)
        square = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, option, self
        )
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(colour), RING_PX))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            square.adjusted(
                RING_INSET_PX, RING_INSET_PX, -RING_INSET_PX, -RING_INSET_PX
            ),
            RING_RADIUS_PX,
            RING_RADIUS_PX,
        )
        painter.end()

    def _ring_now(self) -> str:
        """Which of the three states this box is in; empty for no ring at all.

        The same three the rest of the application wears: nothing at rest, the
        ring while it is focused or under the mouse, the danger colour while it
        cannot be pressed at all.
        """
        if not self.isEnabled():
            return self._danger
        if self.hasFocus() or self.underMouse():
            return self._ring
        return ""
