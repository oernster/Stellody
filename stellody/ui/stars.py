"""The rating control: five stars in a rectangle of their own.

A rating is a small number with a shape everybody already reads, so it is
drawn rather than spelled out. Five stars in a panel, filled up to the rating
and outlined past it, with a press on a star setting the rating to it.

**Pressing the star that is already the rating takes the rating back.** There
is no separate clear, because nought is not a sixth rating; it is the absence
of one; the gesture that undoes a thing should be the gesture that did it.

The panel is drawn rather than assembled out of buttons. Five buttons would
each be a stop in the keyboard ring, so reaching the control past it would
take five presses; they would also each carry a focus ring, which would say
there are five controls here rather than one. This is one control holding one
value, so it is one stop that paints one ring.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from stellody.domain.listening import MAXIMUM_STARS, NO_STARS
from stellody.ui.theme import RADIUS_PX, Mode, palette_for

STAR_PX = 20
STAR_GAP_PX = 4
PANEL_MARGIN_PX = 6
OUTLINE_PX = 1.4
RING_PX = 2
# A five-pointed star is ten points: an outer one at each tip and an inner one
# in each valley between them.
STAR_POINTS = 5
POINTS_PER_STAR = STAR_POINTS * 2
# The waist of the star, as a fraction of its radius. Measured by eye against
# the tray's own artwork rather than derived: a fatter star reads as a blob at
# twenty pixels and a thinner one as a splash.
INNER_RATIO = 0.42
QUARTER_TURN = math.pi / 2
FULL_TURN = math.pi * 2


def _star_path(centre: QPointF, radius: float) -> QPainterPath:
    """A five-pointed star, point upwards, around this centre."""
    path = QPainterPath()
    for step in range(POINTS_PER_STAR):
        reach = radius if step % 2 == 0 else radius * INNER_RATIO
        angle = step * FULL_TURN / POINTS_PER_STAR - QUARTER_TURN
        point = QPointF(
            centre.x() + reach * math.cos(angle),
            centre.y() + reach * math.sin(angle),
        )
        if step == 0:
            path.moveTo(point)
        else:
            path.lineTo(point)
    path.closeSubpath()
    return path


class StarRating(QWidget):
    """Five stars in a rectangle; a press on one sets the rating to it."""

    chosen = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StarRating")
        # A control, so it takes the ring and paints one.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._mode = Mode.DARK
        self._stars = NO_STARS
        self.setFixedSize(
            MAXIMUM_STARS * STAR_PX
            + (MAXIMUM_STARS - 1) * STAR_GAP_PX
            + PANEL_MARGIN_PX * 2,
            STAR_PX + PANEL_MARGIN_PX * 2,
        )

    @property
    def stars(self) -> int:
        """The rating currently shown."""
        return self._stars

    def show_stars(self, stars: int) -> None:
        """Show a rating without reporting one, which is how a track arrives."""
        self._stars = stars
        self._say_what_it_holds()
        self.update()

    def show_appearance(self, mode: Mode) -> None:
        """Follow the appearance the rest of the window is wearing."""
        self._mode = mode
        self.update()

    def _say_what_it_holds(self) -> None:
        """Put the rating into words as well, for anyone not reading shapes."""
        if self._stars == NO_STARS:
            self.setToolTip("Not rated")
            return
        stars = "star" if self._stars == 1 else "stars"
        self.setToolTip(f"Rated {self._stars} {stars} out of {MAXIMUM_STARS}")

    def _centre_of(self, position: int) -> QPointF:
        """Where one star sits, counting from nought at the left."""
        left = PANEL_MARGIN_PX + position * (STAR_PX + STAR_GAP_PX)
        return QPointF(left + STAR_PX / 2, PANEL_MARGIN_PX + STAR_PX / 2)

    def _star_at(self, x: int) -> int:
        """Which star a press at this distance across landed on, from one."""
        reach = x - PANEL_MARGIN_PX
        position = int(reach // (STAR_PX + STAR_GAP_PX))
        return min(max(position + 1, 1), MAXIMUM_STARS)

    def _choose(self, stars: int) -> None:
        """Take a rating, unless it is the one already held: that takes it back."""
        wanted = NO_STARS if stars == self._stars else stars
        self.show_stars(wanted)
        self.chosen.emit(wanted)

    def mousePressEvent(self, event) -> None:
        """A press on a star is a rating; a press beside them is not."""
        if event.button() is not Qt.MouseButton.LeftButton or not self.isEnabled():
            super().mousePressEvent(event)
            return
        self._choose(self._star_at(int(event.position().x())))

    def keyPressEvent(self, event) -> None:
        """Up and Down move the rating; the horizontal keys belong to the ring.

        Left and Right step the keyboard ring everywhere in this application,
        so a control that answered them would be a trap: there would be no way
        out of it but the mouse.
        """
        key = event.key()
        if key == Qt.Key.Key_Up and self._stars < MAXIMUM_STARS:
            self._choose_directly(self._stars + 1)
        elif key == Qt.Key.Key_Down and self._stars > NO_STARS:
            self._choose_directly(self._stars - 1)
        else:
            super().keyPressEvent(event)

    def _choose_directly(self, stars: int) -> None:
        """Take a rating as given, without the press-again-to-clear rule.

        Stepping down through the ratings has to be able to reach nought,
        which the mouse rule would turn into a jump back to where it started.
        """
        self.show_stars(stars)
        self.chosen.emit(stars)

    def paintEvent(self, event) -> None:
        """The panel, then a star for each point of the scale."""
        palette = palette_for(self._mode)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(palette.surface_alt))
        painter.drawRoundedRect(self.rect(), RADIUS_PX, RADIUS_PX)
        for position in range(MAXIMUM_STARS):
            path = _star_path(self._centre_of(position), STAR_PX / 2)
            if position < self._stars:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(palette.star))
            else:
                painter.setPen(QPen(QColor(palette.text_dim), OUTLINE_PX))
                painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        if self.hasFocus():
            painter.setPen(QPen(QColor(palette.focus_ring), RING_PX))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                self.rect().adjusted(1, 1, -1, -1), RADIUS_PX, RADIUS_PX
            )
        painter.end()
