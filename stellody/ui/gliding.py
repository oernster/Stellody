"""The sleeve grid, scrolled rather than snapped.

A list view counts its scrollbar in ITEMS unless it is told otherwise, so the
smallest move it can make is one whole row of sleeves. Selecting a cover a
couple of rows down therefore jumped the grid a row at a time. Counting in
pixels makes the move continuous; travelling it over a short run makes it
readable, because artwork that arrives instantly somewhere else has to be
found again by eye, which is the thing scrolling to it was meant to save.

Qt is left to decide WHERE to scroll to. The jump it would have made is taken,
put back and then travelled, so the destination is Qt's own answer and only the
journey belongs here: the rules about how far a view moves to reveal an item
stay where they already were, in Qt.

Nothing glides while the grid is off screen. A view being laid out scrolls
unwatched, as does one sitting on the page the library is not showing;
animating those would only mean the grid is still moving when it is shown.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QModelIndex, Qt, QVariantAnimation
from PySide6.QtGui import QFocusEvent, QWheelEvent
from PySide6.QtWidgets import QAbstractItemView, QListView, QWidget

# Long enough to be followed by eye, short enough that nobody is kept waiting
# for a selection they have already made. The curve starts and ends slowly, so
# the run reads as one movement rather than as a start and a stop. Judged in
# the built application rather than here: a fifth of a second was smooth but
# still read as quick, so the run was lengthened until it could be watched.
GLIDE_MS = 300

# What one detent of a mouse wheel reports, which is Qt's own unit rather than
# a number chosen here: a wheel notch is an eighth of a degree times 120.
NOTCH = 120


class GlidingGrid(QListView):
    """A grid whose scrolling is measured in pixels and travelled, not jumped."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Built before anything below it, because setting a scroll mode makes
        # Qt scroll to the current item on the way through, which arrives in
        # the override underneath. Measured as an attribute error during
        # construction, not reasoned about afterwards.
        self.glide = QVariantAnimation(self)
        self.glide.setDuration(GLIDE_MS)
        self.glide.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.glide.valueChanged.connect(self._travel)
        # Per pixel on both axes: the vertical one is what is travelled, while
        # the horizontal one is left continuous so the two cannot disagree
        # about what a unit of scrolling means.
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        # How much of a notch has been turned without a row having been moved
        # yet, so a wheel that reports in fractions still moves a row per
        # notch rather than losing the remainder on every event.
        self._turned = 0.0
        # True only while focus is coming back from a menu: see focusInEvent.
        self._menu_closing = False

    def focusInEvent(self, event: QFocusEvent) -> None:
        """Coming back from a menu is not a choice of sleeve.

        A view with no current item gives the place to its first one the
        moment focus arrives by any route other than the mouse. A right press
        is taken and dropped, so the sleeve pointed at never becomes current;
        the menu that press asks for then takes focus. Handing it back landed
        the place on the top of the library, with the pane opening an album
        nobody chose. Measured, not reasoned about: the grid went from
        no current sleeve to row 0 on the way out of the menu.
        """
        self._menu_closing = event.reason() is Qt.FocusReason.PopupFocusReason
        try:
            super().focusInEvent(event)
        finally:
            self._menu_closing = False

    def moveCursor(
        self,
        how: QAbstractItemView.CursorAction,
        modifiers: Qt.KeyboardModifier,
    ) -> QModelIndex:
        """Where the place goes next; nowhere while a menu is closing.

        This is the one road Qt takes to invent a place on focus, so refusing
        it there leaves the grid as it was without touching the keyboard, which
        asks the same question by pressing a key rather than by being handed
        focus back.
        """
        if self._menu_closing:
            return QModelIndex()
        return super().moveCursor(how, modifiers)

    def scrollTo(
        self,
        index: QModelIndex,
        hint: QAbstractItemView.ScrollHint = (
            QAbstractItemView.ScrollHint.EnsureVisible
        ),
    ) -> None:
        """Travel to wherever Qt would have jumped to.

        The base class is asked first and its answer read off the scrollbar,
        rather than the distance being worked out here: how far a view scrolls
        to reveal an item depends on the hint, the viewport and the layout; a
        second implementation of that would be a second set of rules to keep in
        step with Qt's.
        """
        bar = self.verticalScrollBar()
        start = bar.value()
        self.glide.stop()
        super().scrollTo(index, hint)
        target = bar.value()
        if target == start or not self.isVisible():
            return
        bar.setValue(start)
        self.glide.setStartValue(start)
        self.glide.setEndValue(target)
        self.glide.start()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """One notch of the wheel moves one row of sleeves, not two and a bit.

        Measured before it was written: counting the scrollbar in pixels, which
        is what makes the glide continuous, leaves Qt scrolling by the item
        height times the system's lines-per-notch. On this machine that was
        518 pixels a notch over a 236 pixel row, so a single detent carried
        two rows of artwork past the eye and part of a third. A grid of covers
        is read by the row, so a notch moves a row.

        A trackpad is left alone. It reports a pixel delta rather than notches
        and is already continuous, so rounding it to whole rows would take
        away the one thing it does better than a wheel.
        """
        if not event.pixelDelta().isNull() or event.angleDelta().y() == 0:
            super().wheelEvent(event)
            return
        self._turned += event.angleDelta().y() / NOTCH
        rows = int(self._turned)
        self._turned -= rows
        if rows:
            bar = self.verticalScrollBar()
            self.glide.stop()
            bar.setValue(bar.value() - rows * self._row_height())
        event.accept()

    def _row_height(self) -> int:
        """How tall one row of sleeves is, asked of the view rather than kept.

        The grid size is what the view lays out by, so it is the answer while
        there is one; a view with no grid size falls back to the row it draws.
        """
        stated = self.gridSize().height()
        return stated if stated > 0 else max(1, self.sizeHintForRow(0))

    def scroll_settled(self, index: QModelIndex) -> None:
        """Scroll to an item against the room the grid will actually have.

        Qt chooses where to go from the viewport as it stands, which during the
        gesture that opens the album pane is the viewport from BEFORE the pane
        takes its room. Measured rather than reasoned about: picking an album
        deep in the library, the grid chose its destination against a 518 pixel
        viewport, the pane then took 300 of them and the sleeve came to rest
        294 pixels below the bottom of what was left, so the album the listener
        had just picked was not on screen at all.

        Forcing the layout through first is what makes the destination right.
        Asking within the same turn is what keeps it to one movement: the glide
        has put the scrollbar back to where it started and not yet travelled,
        so re-aiming it is invisible.
        """
        page = self.parentWidget()
        layout = page.layout() if page is not None else None
        if layout is not None:
            layout.activate()
        self.scrollTo(index)

    def _travel(self, value: int) -> None:
        """One step of the run, put on the scrollbar the base class reads."""
        self.verticalScrollBar().setValue(value)
