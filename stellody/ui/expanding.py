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

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, Signal
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
        # Read once and kept, since a heading repaints on every hover.
        self._artwork = {
            False: _picture(resources.expand_icon_path()),
            True: _picture(resources.collapse_icon_path()),
        }
        self._fitted: dict[tuple[bool, int, int], QPixmap] = {}

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
        """The artwork for what a press would do, fitted to the room kept.

        Fitted once per size rather than per paint: the source is over a
        thousand pixels square and a heading repaints on every hover, so
        scaling it there would be the most expensive thing on the row.
        """
        picture = self._artwork[self._open]
        if picture is None:
            return None
        wanted = (self._open, strip.width(), strip.height())
        if wanted not in self._fitted:
            self._fitted[wanted] = picture.scaled(
                strip.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return self._fitted[wanted]

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
        """Open every album, then point the arrow at what that leaves.

        `expandAll` opens the rows without saying so: measured, it emits no
        `expanded` for what it opened, so nothing watching those signals hears
        about it. That is why the View menu comes through here rather than
        reaching the tree directly, which left the menu opening every album
        while the arrow beside them still offered to.
        """
        self._tree.expandAll()
        self.refresh()

    def shut_all(self) -> None:
        """Shut every album, then point the arrow at what that leaves."""
        self._tree.collapseAll()
        self.refresh()

    def refresh(self, _where: QPoint | None = None) -> None:
        """Point the arrow at what a press would do from here."""
        self._header.show_open(self.all_open())
