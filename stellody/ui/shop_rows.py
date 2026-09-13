"""One row of the shops dialog, plus the words the shop editor says.

SHOPS.md Amendment 1. A row is a handle to drag it by, the shop's own button,
then an edit control and a delete control, each wearing Oliver's artwork. A row
that cannot be searched (FR-S42) keeps its place, greyed out with its reason,
still offering edit and delete so it can be mended or removed.

**The handle is not a keyboard stop.** It is a mouse affordance whose keyboard
equivalent is Ctrl+Up and Ctrl+Down, so a stop on it would be a press that does
nothing (FR-S40).

**Dragging is a press and a release rather than Qt's drag loop.** The row is
placed where the release lands, which is all a reorder needs; it also keeps the
move drivable by an offscreen test, which a blocking drag loop is not.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from stellody.domain.shop_list import Row, ShopProblem
from stellody.domain.shopping import Shop
from stellody.shared import resources
from stellody.ui.dialogs import CONTROL_ICON_PX, wearing
from stellody.ui.icons import plain_icon

# Oliver's artwork, supplied on 2026-09-13.
ADD_ICON = "add.png"
EDIT_ICON = "edit.png"
DELETE_ICON = "delete.png"
DRAG_ICON = "drag-up-down.png"

ADD_LABEL = "Add a shop"
PUT_BACK_LABEL = "Put the original shops back"
EDIT_TOOLTIP = "Edit {shop}"
DELETE_TOOLTIP = "Delete {shop}"
DRAG_TOOLTIP = "Drag to move this shop. Ctrl+Up and Ctrl+Down move it too."
UNNAMED = "Unnamed line"
BROKEN = "{name}: cannot search, because {reason}."
COULD_NOT_SAVE = "That change could not be saved, so nothing has changed."

# What each problem is called wherever the editor has to say one.
PROBLEM_WORDS = {
    ShopProblem.NO_NAME: "it has no name",
    ShopProblem.NO_ADDRESS: "it has no search address",
    ShopProblem.NOT_SECURE: "the address must begin with https://",
    ShopProblem.NO_PLACEHOLDER: "the address names neither {artist} nor {album}",
    ShopProblem.NAME_TAKEN: "another shop already has that name",
    ShopProblem.NOT_A_ROW: "the line in shops.json is not a shop at all",
}


class Handle(QLabel):
    """The grip a row is dragged by; the drop is reported where it lands."""

    def __init__(self, dropped: Callable[[QPoint], None], parent: QWidget) -> None:
        super().__init__(parent)
        size = QSize(CONTROL_ICON_PX, CONTROL_ICON_PX)
        self.setPixmap(plain_icon(resources.find_asset(DRAG_ICON)).pixmap(size))
        self.setToolTip(DRAG_TOOLTIP)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._dropped = dropped

    def mousePressEvent(self, event) -> None:
        """Take hold, so the release comes back here wherever it lands."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        """Let go, reporting where on the screen that happened."""
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if event.button() == Qt.MouseButton.LeftButton:
            self._dropped(event.globalPosition().toPoint())


@dataclass(frozen=True, slots=True)
class RowControls:
    """What one row put on screen."""

    holder: QWidget
    button: QPushButton
    edit: QPushButton | None
    delete: QPushButton | None

    def stops(self) -> list[QPushButton]:
        """The row's keyboard stops, in reading order."""
        found = [self.button, self.edit, self.delete]
        return [stop for stop in found if stop is not None and stop.isEnabled()]


def _picture_button(artwork: str, tooltip: str, parent: QWidget) -> QPushButton:
    """A control named by its picture and its tooltip alone."""
    button = wearing(QPushButton("", parent), resources.find_asset(artwork))
    button.setToolTip(tooltip)
    button.setAccessibleName(tooltip)
    button.setAutoDefault(False)
    return button


def row_controls(
    row: Row,
    parent: QWidget,
    chose: Callable[[Shop], None],
    changes: (
        tuple[Callable[[], None], Callable[[], None], Callable[[QPoint], None]] | None
    ),
) -> RowControls:
    """One row; `changes` is edit, delete and drop, None where nothing may change."""
    holder = QWidget(parent)
    line = QHBoxLayout(holder)
    line.setContentsMargins(0, 0, 0, 0)
    name = row.name or UNNAMED
    if isinstance(row, Shop):
        text = row.name if not row.note else f"{row.name}   ({row.note})"
        button = QPushButton(text, holder)
        # Not the default button, so Return reaches Close rather than opening
        # tabs at whichever shop the ring happens to be resting on.
        button.setAutoDefault(False)
        button.clicked.connect(lambda _checked=False, at=row: chose(at))
    else:
        reason = PROBLEM_WORDS[row.problem]
        button = QPushButton(BROKEN.format(name=name, reason=reason), holder)
        button.setEnabled(False)
    if changes is None:
        line.addWidget(button)
        return RowControls(holder, button, None, None)
    edit, delete, dropped = changes
    line.addWidget(Handle(dropped, holder))
    line.addWidget(button, 1)
    edit_button = _picture_button(EDIT_ICON, EDIT_TOOLTIP.format(shop=name), holder)
    edit_button.clicked.connect(edit)
    line.addWidget(edit_button)
    delete_button = _picture_button(
        DELETE_ICON, DELETE_TOOLTIP.format(shop=name), holder
    )
    delete_button.clicked.connect(delete)
    line.addWidget(delete_button)
    return RowControls(holder, button, edit_button, delete_button)
