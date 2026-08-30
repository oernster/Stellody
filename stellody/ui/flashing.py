"""Taking the eye to a row, without moving anything else on the way.

A search leaves the album whole, so the track it hit is one row among many.
Selecting it says where the row is; a couple of gentle pulses says look here.

**The colour is a role of its own.** The hit row is selected at the same
moment, so a pulse in the selection colour would show nothing at all. The
palette's `found` exists for this and differs from the selection by hue rather
than by brightness, which is what makes a pulse gentle instead of a strobe.

**The model is told what to paint, never when.** All the timing lives here, so
the model holds no clock and the pulse can be changed without touching it.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    QTimer,
)
from PySide6.QtGui import QBrush, QColor

# Twice, which reads as "look here" rather than as a fault. A third pulse is
# where a gentle thing starts to nag.
PULSES = 2
# Slow enough to read as a fade rather than a blink.
HALF_CYCLE_MS = 450
# On, off, on, off: two turns to a pulse.
TURNS_PER_PULSE = 2
TURNS = PULSES * TURNS_PER_PULSE


class RowFlash(QObject):
    """Pulses one row's background a couple of times, then forgets it."""

    def __init__(self, model, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._timer = QTimer(self)
        self._timer.setInterval(HALF_CYCLE_MS)
        self._timer.timeout.connect(self._turn)
        self._where: QPersistentModelIndex | None = None
        self._colour: QColor | None = None
        self._ink: QColor | None = None
        self._lit = False
        self._left = 0
        model.set_flash(self)

    @property
    def lit(self) -> bool:
        """True while the row is painted rather than merely chosen."""
        return self._lit

    @property
    def running(self) -> bool:
        """True between starting a flash and its last turn."""
        return self._timer.isActive()

    def start(self, where: QModelIndex, colour: str, ink: str) -> None:
        """Pulse this row in this colour, replacing whatever was pulsing.

        The ink comes with it because this is a highlighter rather than a
        tint: the same yellow serves both appearances and the writing on it
        changes instead, which is what keeps it readable in either.
        """
        self.stop()
        self._where = QPersistentModelIndex(where)
        self._colour = QColor(colour)
        self._ink = QColor(ink)
        self._lit = True
        self._left = TURNS
        self._redraw()
        self._timer.start()

    def stop(self) -> None:
        """Stop pulsing and leave the row exactly as it was."""
        self._timer.stop()
        self._left = 0
        self._lit = False
        was = self._where
        self._where = None
        self._colour = None
        self._ink = None
        if was is not None and was.isValid():
            self._model.redraw_row(QModelIndex(was))

    def paint(self, index: QModelIndex, role: int) -> QBrush | None:
        """The paint for one cell in one role; None for anything else."""
        if not self._on(index):
            return None
        if role == Qt.ItemDataRole.BackgroundRole:
            return QBrush(self._colour)
        return QBrush(self._ink)

    def _on(self, index: QModelIndex) -> bool:
        """True when this cell is in the row currently being painted."""
        where = self._where
        if not self._lit or self._colour is None or self._ink is None:
            return False
        if where is None or not where.isValid():
            return False
        return index.row() == where.row() and index.parent() == where.parent()

    def _turn(self) -> None:
        """One half of a pulse: lit becomes dark, dark becomes lit."""
        self._left -= 1
        if self._left <= 0:
            self.stop()
            return
        self._lit = not self._lit
        self._redraw()

    def _redraw(self) -> None:
        """Ask the model to draw the row again."""
        where = self._where
        if where is not None and where.isValid():
            self._model.redraw_row(QModelIndex(where))
