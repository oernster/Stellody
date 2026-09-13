"""A shop row that travels with the pointer while it is dragged. FR-S27.

Reported by Oliver on 2026-09-13: the grip could be dragged, yet nothing on
screen moved until the button was let go, when the row jumped to its new place.
The row was placed by the release alone; nothing answered the movement between
the press and the release.

**The held row follows the pointer; the others make room.** While a row is held
the layout that normally places the rows is switched off, so each row can be put
where the drag says. The held row stays under the pointer exactly where it was
taken hold of. Every other row glides to the place it would take were the held
row dropped there, so the gap it would fill is always in sight.

**Where it would land is the place whose top is nearest the held row's top**,
read off where the rows started. Reading it off where the others have glided to
instead would move the answer as they move, so a row held still over a boundary
would never settle.

It used to count the other rows whose middle lay above the held row's middle.
Reported by Oliver on 2026-09-13, then measured over the eight shipped shops:
no row could reach the last place. The held row stops at the last row's top,
which puts its middle exactly level with the last row's; level is not above,
so every drag landed one place short. The top of the list was reachable
only because nothing has to be passed to get there. The nearest top has no such
edge: at the lowest point it IS the last place.

**Letting go writes first, then lands.** The move is written the moment the
button is released, as every change here is written before it is drawn (FR-S29).
The held row then glides into its place; only once it has arrived is the list
drawn again, in the same positions, so nothing jumps. A move the file refuses
glides the row back to where it started.

**Still not Qt's drag loop.** A drag loop carries a picture of a row rather than
the row itself, blocks while it runs and cannot be driven by an offscreen test.
Following the pointer inside the dialog is all a reorder needs.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

from PySide6.QtCore import QEasingCurve, QObject, QPoint, QVariantAnimation
from PySide6.QtWidgets import QLayout, QWidget

# How long the other rows take to make room, then how long the held row takes to
# settle once let go. Short enough to keep up with a hand, long enough to read
# as movement rather than as a jump. A first setting, to be judged in the built
# application as the sleeve grid's glide was.
ROOM_MS = 160
LAND_MS = 220
# Decelerating, so a row arrives gently rather than stopping dead.
EASING = QEasingCurve.Type.OutCubic


def _place(row: QWidget, top: int) -> None:
    """One step of a glide: the row at this height, where it already stood."""
    row.move(row.x(), int(top))


class RowDrag(QObject):
    """Carries one row of a column of rows from where it was taken to its place.

    `landed(index, target)` writes the move and answers whether it was kept;
    `settled(kept)` is told once the held row has arrived.
    """

    def __init__(
        self,
        layout: QLayout,
        landed: Callable[[int, int], bool],
        settled: Callable[[bool], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._layout = layout
        self._landed = landed
        self._settled = settled
        self._rows: list[QWidget] = []
        self._tops: list[int] = []
        self._grab = 0
        self._held: int | None = None
        self._target = 0
        self._landing = False
        self._glides: dict[QWidget, QVariantAnimation] = {}

    @property
    def busy(self) -> bool:
        """Whether a row is held or still landing."""
        return self._held is not None or self._landing

    @property
    def target(self) -> int:
        """Where the held row would land if it were let go now."""
        return self._target

    def take(self, rows: list[QWidget], index: int, at: QPoint) -> None:
        """Take hold of the row at `index`, pressed at the global point `at`."""
        if self.busy or not rows:
            return
        self._rows = list(rows)
        self._tops = [row.y() for row in rows]
        self._layout.setEnabled(False)
        self._held = index
        self._target = index
        held = rows[index]
        self._grab = held.parentWidget().mapFromGlobal(at).y() - held.y()
        held.raise_()

    def follow(self, at: QPoint) -> None:
        """Keep the held row under the pointer, opening the gap it would fill."""
        if self._held is None:
            return
        held = self._rows[self._held]
        wanted = held.parentWidget().mapFromGlobal(at).y() - self._grab
        top = min(max(wanted, self._tops[0]), self._tops[-1])
        held.move(held.x(), top)
        target = min(
            range(len(self._tops)), key=lambda slot: abs(self._tops[slot] - top)
        )
        if target != self._target:
            self._target = target
            self._make_room()

    def let_go(self, at: QPoint) -> None:
        """Write the move, then glide the held row into the place it takes."""
        if self._held is None:
            return
        self.follow(at)
        index = self._held
        kept = self._target != index and self._landed(index, self._target)
        if not kept:
            self._target = index
            self._make_room()
        self._held = None
        self._landing = True
        place = self._slots(self._order(index, self._target))[index]
        landing = self._glide(self._rows[index], place, LAND_MS)
        landing.finished.connect(partial(self._arrived, kept))

    def _arrived(self, kept: bool) -> None:
        """The held row is home: hand the rows back to the layout."""
        for glide in self._glides.values():
            glide.stop()
        self._glides.clear()
        self._landing = False
        self._settled(kept)
        self._layout.setEnabled(True)
        self._layout.invalidate()
        self._layout.activate()

    def _make_room(self) -> None:
        """Glide every other row to its place around the gap."""
        slots = self._slots(self._order(self._held, self._target))
        for place, row in enumerate(self._rows):
            if place != self._held:
                self._glide(row, slots[place], ROOM_MS)

    def _glide(self, row: QWidget, top: int, duration_ms: int) -> QVariantAnimation:
        """Move a row to `top` over a short run, replacing any run it was on."""
        old = self._glides.pop(row, None)
        if old is not None:
            old.stop()
            old.deleteLater()
        glide = QVariantAnimation(self)
        glide.setDuration(duration_ms)
        glide.setEasingCurve(EASING)
        glide.setStartValue(row.y())
        glide.setEndValue(top)
        glide.valueChanged.connect(partial(_place, row))
        self._glides[row] = glide
        glide.start()
        return glide

    def _order(self, index: int, target: int) -> list[int]:
        """The rows top to bottom, with the one at `index` put at `target`."""
        order = [place for place in range(len(self._rows)) if place != index]
        order.insert(target, index)
        return order

    def _slots(self, order: list[int]) -> dict[int, int]:
        """The top each row takes when the rows stand in `order`.

        The places are the ones the layout gave, handed out top to bottom, since
        every row is one line of controls of one height. Working them out from
        a height and a gap instead was measured a pixel out: the layout shares
        spare room between the rows unevenly, placing three at 0, 53 and 105,
        so a row landing on arithmetic jumped when the layout took it back.
        """
        return {place: self._tops[slot] for slot, place in enumerate(order)}
