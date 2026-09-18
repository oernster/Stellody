"""A track's rating as a column of the library, beside its plays.

Moved off the row under the library on 2026-09-16, as Oliver asked. The stars
there followed whichever track was highlighted, else what was playing, so a
rating was only ever readable one track at a time. In a column every track
says its rating while the library is being read down, which is where a play
count is already looked for; the two sit side by side for that reason.

A cell is drawn by the row delegate rather than holding a widget: a widget per
row is what an item model exists to avoid. Two ways to set a rating, then.

- **A press on a star** sets the track to it, with the rule the album's own
  stars follow: pressing the star already held takes the rating back.
- **The number keys** set the highlighted track's rating from 1 to 5; 0 clears
  it. Up and Down already walk the rows, so they cannot also move a rating the
  way they do on the album's stars; the keypad counts as well.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QModelIndex, QObject, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent, QPainter

from stellody.domain.listening import MAXIMUM_STARS, NO_STARS
from stellody.ui.stars import chosen_rating, paint_stars, star_at, stars_width
from stellody.ui.theme import HALF, Mode

CELL_STAR_PX = 14
CELL_STAR_GAP_PX = 3
CELL_MARGIN_PX = 6
# Each number key stands for the rating it names, nought included.
RATING_KEYS = {
    Qt.Key.Key_0.value + stars: stars for stars in range(NO_STARS, MAXIMUM_STARS + 1)
}
# A number typed on the keypad is the same number, so both are taken.
PLAIN_MODIFIERS = (Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.KeypadModifier)
MOUSE_EVENTS = (
    QEvent.Type.MouseButtonPress,
    QEvent.Type.MouseButtonRelease,
    QEvent.Type.MouseButtonDblClick,
)


def cell_width() -> int:
    """How wide the column has to be to carry every star."""
    return stars_width(CELL_STAR_PX, CELL_STAR_GAP_PX) + CELL_MARGIN_PX * HALF


def _origin(rect: QRect) -> QPointF:
    """Where the first star's top left corner sits in a cell."""
    return QPointF(
        rect.left() + CELL_MARGIN_PX,
        rect.top() + (rect.height() - CELL_STAR_PX) / HALF,
    )


def paint_cell(painter: QPainter, rect: QRect, stars: int, mode: Mode) -> None:
    """One track's stars, centred down its cell."""
    painter.save()
    paint_stars(painter, _origin(rect), CELL_STAR_PX, CELL_STAR_GAP_PX, stars, mode)
    painter.restore()


def star_in_cell(rect: QRect, point: QPointF) -> int | None:
    """Which star a point in a cell is over; None when it is beside them."""
    origin = _origin(rect)
    across = point.x() - origin.x()
    down = point.y() - origin.y()
    if not 0 <= across < stars_width(CELL_STAR_PX, CELL_STAR_GAP_PX):
        return None
    if not 0 <= down < CELL_STAR_PX:
        return None
    return star_at(point.x(), origin.x(), CELL_STAR_PX, CELL_STAR_GAP_PX)


def pressed_star(event: QEvent, rect: QRect) -> int | None:
    """The star a mouse event in a cell landed on; None when it missed them."""
    if event.type() not in MOUSE_EVENTS or not isinstance(event, QMouseEvent):
        return None
    return star_in_cell(rect, event.position())


def released_rating(event: QMouseEvent, pressed: int, held: int) -> int | None:
    """The rating a left release on a star leaves; None for any other event."""
    if event.type() is not QEvent.Type.MouseButtonRelease:
        return None
    if event.button() is not Qt.MouseButton.LeftButton:
        return None
    return chosen_rating(held, pressed)


class RatingKeys(QObject):
    """Turns a number key on a list of tracks into a rating of the highlighted one.

    Answers the key only where the rating was taken. A highlight on an album
    or a disc rates nothing, so the key goes on to the view as it always did.
    """

    def __init__(
        self, rate: Callable[[QModelIndex, int], bool], parent: QObject
    ) -> None:
        super().__init__(parent)
        self._rate = rate

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Rate on a bare number key; let everything else through."""
        if event.type() is not QEvent.Type.KeyPress:
            return False
        stars = RATING_KEYS.get(event.key())
        if stars is None or event.modifiers() not in PLAIN_MODIFIERS:
            return False
        current = getattr(watched, "currentIndex", None)
        if current is None:
            return False
        return self._rate(current(), stars)
