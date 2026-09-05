"""One toggle at the left of the Title heading: open every album, else shut them.

Expanding and collapsing the whole library were already on the View menu, so
this is reach rather than capability: the gesture belongs beside the thing it
acts on, which is the column of albums under that heading.

The two chevrons are this application's own artwork, so the toggle is drawn in
the same hand as every other control here rather than in the platform's. A
typed triangle was never an option: what font a heading lands in is not decided
here, while a glyph the font lacks shows as a box rather than as nothing.
Measured offscreen, the fallback font carries none of the four triangles. Where
the artwork cannot be found the style's own arrow is drawn instead, so a
checkout missing its assets shows a toggle rather than an empty space.

It says what a press would DO, as every switch in this application does: the
arrow points right while a press would open the albums and down while a press
would shut them. Partly open counts as shut, so one press always finishes the
job it looks like it would.

The heading is not a keyboard stop and does not become one. Nothing here is
reachable only by mouse: View holds Expand all and Collapse all, which is the
keyboard route and was the only route until now.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHeaderView,
    QStyle,
    QStyleOption,
    QToolTip,
    QTreeView,
    QWidget,
)

from stellody.shared import resources
from stellody.ui.row_text import Column

# The arrow's own width, the space either side of it, then the padding the
# stylesheet keeps at the left of the first heading, which is the two added up.
# Derived rather than stated twice, so the room kept and the thing drawn in it
# cannot come to disagree: written as one number, the artwork ended up touching
# the word beside it.
INDICATOR_PX = 16
INDICATOR_INSET_PX = 4
HEADING_PAD_PX = INDICATOR_INSET_PX + INDICATOR_PX + INDICATOR_INSET_PX
# An album row's own chevron. Larger than the heading's, an album row being
# as tall as the sleeve it carries rather than as tall as a line of text.
BRANCH_PX = 20
OPEN_TOOLTIP = "Open every album"
SHUT_TOOLTIP = "Close every album"


def _picture(path) -> QPixmap | None:
    """The artwork at that path; None where there is none to be had.

    A missing file and a file Qt cannot read are the same answer here, since
    both leave nothing to draw and the style's arrow covers both.
    """
    if path is None:
        return None
    picture = QPixmap(str(path))
    return None if picture.isNull() else picture


class Chevrons:
    """The two pictures, fitted to whatever room asks for them.

    One home for them because two things draw the same idea: the heading says
    whether the whole library is open and each album row says whether that one
    is. Loaded once and fitted once per size, the sources being over a
    thousand pixels square while both callers repaint constantly.
    """

    def __init__(self) -> None:
        self._artwork = {
            False: _picture(resources.expand_icon_path()),
            True: _picture(resources.collapse_icon_path()),
        }
        self._fitted: dict[tuple[bool, int, int], QPixmap] = {}

    def at_size(self, open_now: bool, side: int) -> QPixmap | None:
        """The picture for that state, square at that size; None where absent."""
        picture = self._artwork[open_now]
        if picture is None or side <= 0:
            return None
        wanted = (open_now, side, side)
        if wanted not in self._fitted:
            self._fitted[wanted] = picture.scaled(
                QSize(side, side),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return self._fitted[wanted]


class ExpandingTree(QTreeView):
    """The album list, drawing an album's own chevron in this hand too.

    Qt draws a branch indicator from the platform style, which is the last
    place in this window still wearing it. The row says exactly what the
    heading above it says, one album rather than all of them, so it is drawn
    from the same two pictures.

    Only a row with something under it is drawn: a track has nothing to open,
    so the base class is left to whatever it does with the rest of the
    indentation.
    """

    # The one stop in the window that answers Left and Right itself. They
    # shut and open an album here, which is the only keyboard route into one;
    # everywhere else the horizontal arrows step the ring. Read by `ring.py`,
    # which is why the exception is stated on the thing it exempts rather
    # than in a list somewhere else.
    keeps_horizontal_keys = True

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._chevrons = Chevrons()

    def drawBranches(self, painter, rect: QRect, index) -> None:
        """The chevron for this album, else the base class's own answer."""
        model = self.model()
        if model is None or not model.hasChildren(index):
            super().drawBranches(painter, rect, index)
            return
        side = min(rect.width(), rect.height(), BRANCH_PX)
        picture = self._chevrons.at_size(self.isExpanded(index), side)
        if picture is None:
            super().drawBranches(painter, rect, index)
            return
        where = QRect(0, 0, picture.width(), picture.height())
        where.moveCenter(rect.center())
        painter.drawPixmap(where, picture)


class ExpandingHeader(QHeaderView):
    """The tree's heading row, carrying the open-everything toggle."""

    pressed_toggle = Signal()

    def __init__(self, tree: QTreeView) -> None:
        super().__init__(Qt.Orientation.Horizontal, tree)
        # A tree configures the heading it builds for itself, so replacing it
        # throws those settings away and a bare one comes back wearing Qt's
        # defaults. Measured, three differ: headings centred rather than left,
        # sections that cannot be dragged, a last section that stretches.
        # Stated here rather than left to whoever installs it, since a heading
        # that reads differently from every other tree is the sort of thing
        # nobody attributes to the control that was added beside it.
        tree_default = tree.header()
        self.setDefaultAlignment(tree_default.defaultAlignment())
        self.setSectionsMovable(tree_default.sectionsMovable())
        self.setStretchLastSection(tree_default.stretchLastSection())
        self._open = False
        self._chevrons = Chevrons()

    def show_open(self, open_now: bool) -> None:
        """Say whether every album is open, then redraw the arrow."""
        if open_now == self._open:
            return
        self._open = open_now
        self.updateSection(Column.TITLE)

    def indicator(self) -> QRect:
        """Where the arrow is drawn, in this heading's own coordinates."""
        left = self.sectionViewportPosition(Column.TITLE)
        return QRect(
            left + INDICATOR_INSET_PX,
            INDICATOR_INSET_PX,
            INDICATOR_PX,
            self.height() - INDICATOR_INSET_PX - INDICATOR_INSET_PX,
        )

    def paintSection(self, painter, rect: QRect, index: int) -> None:
        """The heading as the style draws it, with the arrow over the room kept.

        The stylesheet pads the first section by `HEADING_PAD_PX`, so the word
        beside this is already out of the way and the arrow lands in space
        nothing else is using.
        """
        super().paintSection(painter, rect, index)
        if index != Column.TITLE:
            return
        strip = self.indicator()
        picture = self._at_size(strip)
        if picture is not None:
            where = QRect(0, 0, picture.width(), picture.height())
            where.moveCenter(strip.center())
            painter.drawPixmap(where, picture)
            return
        option = QStyleOption()
        option.initFrom(self)
        option.rect = strip
        option.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Children
        arrow = (
            QStyle.PrimitiveElement.PE_IndicatorArrowDown
            if self._open
            else QStyle.PrimitiveElement.PE_IndicatorArrowRight
        )
        self.style().drawPrimitive(arrow, option, painter, self)

    def _at_size(self, strip: QRect) -> QPixmap | None:
        """The artwork for what a press would do, fitted to the room kept."""
        return self._chevrons.at_size(self._open, min(strip.width(), strip.height()))

    def mousePressEvent(self, event) -> None:
        """A press on the arrow is the toggle; anywhere else is the heading's."""
        if self.indicator().contains(event.position().toPoint()):
            self.pressed_toggle.emit()
            return
        super().mousePressEvent(event)

    def event(self, happening: QEvent) -> bool:
        """Name the press, though only while the pointer is over the arrow.

        A tooltip on the whole heading would answer over Length as well, where
        it would be describing something a press there does not do.
        """
        if happening.type() is QEvent.Type.ToolTip:
            where = happening.pos()
            if self.indicator().contains(where):
                QToolTip.showText(
                    happening.globalPos(),
                    SHUT_TOOLTIP if self._open else OPEN_TOOLTIP,
                    self,
                )
                return True
            QToolTip.hideText()
        return super().event(happening)


class ExpandToggle(QWidget):
    """Keeps the arrow and the tree saying the same thing about each other.

    A listener opening albums one at a time moves the tree without touching
    this, so the arrow is read off the rows rather than remembered: a flag
    would be a second account of the same fact, free to disagree with the
    first the moment anybody expanded anything by hand.
    """

    def __init__(self, tree: QTreeView, header: ExpandingHeader) -> None:
        super().__init__(tree)
        self.setVisible(False)
        self._tree = tree
        self._header = header
        self._busy = False
        header.pressed_toggle.connect(self.toggle)
        tree.expanded.connect(self.refresh)
        tree.collapsed.connect(self.refresh)
        self.refresh()

    def all_open(self) -> bool:
        """True while every album is open; False where the library is empty.

        An empty library has nothing to open, so the arrow points right and a
        press does nothing rather than reporting everything already open.
        """
        model = self._tree.model()
        if model is None:
            return False
        albums = model.rowCount()
        if albums == 0:
            return False
        return all(
            self._tree.isExpanded(model.index(row, Column.TITLE))
            for row in range(albums)
        )

    def toggle(self) -> None:
        """Shut them all where they are all open; open them all otherwise."""
        if self.all_open():
            self.shut_all()
        else:
            self.open_all()

    def open_all(self) -> None:
        """Open every album, then point the arrow at what that leaves."""
        self._whole_library(self._tree.expandAll)

    def shut_all(self) -> None:
        """Shut every album, then point the arrow at what that leaves."""
        self._whole_library(self._tree.collapseAll)

    def _whole_library(self, change) -> None:
        """Move every row, then read the arrow ONCE rather than per row.

        `expandAll` says what it did row by row: measured on a library of 628
        albums holding 8164 tracks, it emits 8792 `expanded` signals, one for
        every row it opened. Answering each of them by walking all 628 albums
        is over five million questions asked with the interface thread held
        throughout. It took 3.72 seconds against 0.03 for the same call with
        nothing listening. That is the whole of the difference.

        So the per-row answer is turned off for the duration of a change that
        moves everything and asked once at the end, where it is the same
        answer for a thousandth of the work. The signals are still listened to
        the rest of the time, which is what keeps the arrow honest about an
        album somebody opens by hand.
        """
        self._busy = True
        try:
            change()
        finally:
            self._busy = False
        self.refresh()

    def refresh(self, _where: QPoint | None = None) -> None:
        """Point the arrow at what a press would do from here.

        Silent while the whole library is moving, since the answer then costs
        a walk of every album and cannot be right until the move has finished.
        """
        if self._busy:
            return
        self._header.show_open(self.all_open())
