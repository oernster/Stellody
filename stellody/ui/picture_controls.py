"""The one control on the picture: make it fill the window, then put it back.

Drawn here rather than loaded, in the same hand as the rest of the artwork. Two
arrows in a rounded square, one pair pointing out of the corners and one pair
pointing into them, which is the same picture read in both directions: what a
press would DO, as every switch in this application says.

A typed glyph was never an option for the same reason the chevrons in the
library heading are drawn: what font a widget lands in is not decided here, while
a glyph the font lacks shows as a box rather than as nothing.

It is a real button rather than a hot corner, so it is a keyboard stop like any
other control and a listener who never touches the mouse can still reach it.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton, QWidget

BUTTON_PX = 34
CORNER_RADIUS = 6
# The plate is dark and translucent so it reads against any frame behind it,
# which a picture gives no say over.
PLATE = QColor(0, 0, 0, 150)
PLATE_HOVER = QColor(0, 0, 0, 200)
MARK = QColor(255, 255, 255, 230)
MARK_WIDTH = 2.0

# The ring is painted here rather than named in the stylesheet, for the reason
# the star rating gives: this control draws itself entirely, so a sheet rule
# would be a rule nothing applies. It sits on a picture whose colours are not
# ours to choose, so it is drawn in the same white as the arrows rather than in
# a theme colour that could land on a white frame and vanish.
RING = QColor(255, 255, 255, 235)
RING_WIDTH = 2.0
RING_INSET = 2.0

# Where the arrows live inside the button, as a share of its side. The arms
# stop short of the plate's edge so nothing touches the rounded corner.
INSET = 0.26
REACH = 0.20
HEAD = 0.10


class SizeButton(QAbstractButton):
    """A square that says whether a press fills the window or restores it."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._filling = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(QSize(BUTTON_PX, BUTTON_PX))
        self._say_what_a_press_does()

    @property
    def filling(self) -> bool:
        """True while the picture already fills the window."""
        return self._filling

    def set_filling(self, filling: bool) -> None:
        """Say which way the arrows point, plus what the tooltip claims."""
        if filling == self._filling:
            return
        self._filling = filling
        self._say_what_a_press_does()
        self.update()

    def _say_what_a_press_does(self) -> None:
        """One wording, kept where the picture that carries it is drawn."""
        wording = "Put the picture back" if self._filling else "Fill the window"
        self.setToolTip(wording)
        self.setAccessibleName(wording)

    def sizeHint(self) -> QSize:
        """One size; it is a fixed square whatever is around it."""
        return QSize(BUTTON_PX, BUTTON_PX)

    def paintEvent(self, event) -> None:
        """The plate, then the two arrows, in the direction a press goes."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        plate = PLATE_HOVER if (self.underMouse() or self.hasFocus()) else PLATE
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(plate)
        painter.drawRoundedRect(
            QRectF(0, 0, self.width(), self.height()), CORNER_RADIUS, CORNER_RADIUS
        )
        pen = QPen(MARK, MARK_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._arrows())
        if self.hasFocus():
            painter.setPen(QPen(RING, RING_WIDTH))
            painter.drawRoundedRect(
                QRectF(
                    RING_INSET,
                    RING_INSET,
                    self.width() - RING_INSET * 2,
                    self.height() - RING_INSET * 2,
                ),
                CORNER_RADIUS - RING_INSET / 2,
                CORNER_RADIUS - RING_INSET / 2,
            )

    def _arrows(self) -> QPainterPath:
        """Two arrows on the leading diagonal, into the corners or out of them.

        The same two lines either way; only which end wears the head changes,
        which is what makes the two states read as one picture reversed rather
        than as two drawings that have to be kept looking alike.
        """
        side = float(self.width())
        near = side * INSET
        far = side - near
        reach = side * REACH
        head = side * HEAD
        outer = (QPointF(near, near), QPointF(far, far))
        inner = (
            QPointF(near + reach, near + reach),
            QPointF(far - reach, far - reach),
        )
        path = QPainterPath()
        for corner, middle in zip(outer, inner):
            tail, point = (middle, corner) if not self._filling else (corner, middle)
            self._one_arrow(path, tail, point, head)
        return path

    @staticmethod
    def _one_arrow(
        path: QPainterPath, tail: QPointF, point: QPointF, head: float
    ) -> None:
        """A line from `tail` to `point`, with a head opening back along it."""
        path.moveTo(tail)
        path.lineTo(point)
        step_x = 1.0 if point.x() > tail.x() else -1.0
        step_y = 1.0 if point.y() > tail.y() else -1.0
        path.moveTo(QPointF(point.x() - step_x * head, point.y()))
        path.lineTo(point)
        path.lineTo(QPointF(point.x(), point.y() - step_y * head))
