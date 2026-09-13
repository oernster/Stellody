"""Where the ticked albums are taken to a shop; also where the shops are changed.

**It stays open.** Ruled by Oliver on 2026-09-08: prices are compared across
shops, so a dialog that closed on the first choice would have to be reopened
for the second. FR-S07.

**It asks before opening a great many tabs.** One album is one browser tab, so
a list of thirty ticked albums arrives as thirty tabs over whatever somebody
was doing. Above five, it says how many and waits. FR-S08.

**The list is changed here.** SHOPS.md Amendment 1: add, edit, delete, drag,
Ctrl+Up and Ctrl+Down, then putting the original shops back. Every change is
written before it is drawn, so a change the file refuses leaves the dialog
showing the list the file holds (FR-S29). A dialog given no editor offers the
shops and nothing else.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from itertools import pairwise

from PySide6.QtCore import QKeyCombination, QPoint, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stellody.application.shop_editing import ShopListUnwritable
from stellody.application.shopping import Shopping
from stellody.domain.shopping import Shop, WantedAlbum
from stellody.shared import resources
from stellody.shared.version import APP_NAME
from stellody.ui.dialogs import CLOSE_ICON, FirstStopDialog, title_label, wearing
from stellody.ui.shop_form import ShopForm
from stellody.ui.shop_rows import (
    ADD_ICON,
    ADD_LABEL,
    COULD_NOT_SAVE,
    PUT_BACK_LABEL,
    UNNAMED,
    RowControls,
    row_controls,
)
from stellody.ui.theme import Mode, palette_for

TITLE = "Find these in a shop"
CLOSE_LABEL = "Close"
ASKING_ABOUT = "{count} album ticked. Choose a shop; this stays open."
ASKING_ABOUT_MANY = "{count} albums ticked. Choose a shop; this stays open."
OPENED = "Opened {count} search at {shop}."
OPENED_MANY = "Opened {count} searches at {shop}."
WOULD_NOT_OPEN = "{shop} could not be opened. Is there a browser on this machine?"
TOO_MANY_TITLE = "Open that many tabs?"
TOO_MANY = "This will open {count} browser tabs at {shop}. Continue?"
NO_SHOPS = "No shops are configured."
NO_SHOPS_YET = "No shops yet. Press Add a shop to put one in."
DELETE_TITLE = "Delete this shop?"
DELETE_ASK = "Delete {shop} from the list?"
PUT_BACK_TITLE = "Put the original shops back?"
PUT_BACK_ASK = (
    f"The shops {APP_NAME} came with go back as they shipped. Shops you added stay."
)
RETIRED = f"Removed because {APP_NAME} no longer ships them: {{names}}."
DIALOG_WIDTH_PX = 520
APART_PX = 12
ONE = 1
UP = -1
DOWN = 1


class ShopsDialog(FirstStopDialog):
    """The shops, offered for whatever has been ticked, changed in place."""

    def __init__(
        self,
        shopping: Shopping,
        wanted: tuple[WantedAlbum, ...] = (),
        mode: Mode = Mode.DARK,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._shopping = shopping
        self._editing = shopping.editing
        self._wanted = wanted
        self._mode = mode
        self._colour = palette_for(mode)
        self.setWindowTitle(TITLE)
        self.setMinimumWidth(DIALOG_WIDTH_PX)
        outer = QVBoxLayout(self)
        self.title = title_label(TITLE, self)
        outer.addWidget(self.title)
        outer.addSpacing(APART_PX)
        self.counted = QLabel(self._counted(), self)
        self.counted.setWordWrap(True)
        outer.addWidget(self.counted)
        self.announced = QLabel(self._announcement(), self)
        self.announced.setWordWrap(True)
        self.announced.setVisible(bool(self.announced.text()))
        outer.addWidget(self.announced)
        outer.addSpacing(APART_PX)
        self.rows_holder = QWidget(self)
        self._rows = QVBoxLayout(self.rows_holder)
        self._rows.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.rows_holder)
        outer.addSpacing(APART_PX)
        self.said = QLabel("", self)
        self.said.setWordWrap(True)
        outer.addWidget(self.said)
        outer.addLayout(self._buttons())
        self.controls: list[RowControls] = []
        self.shop_buttons: dict[str, QPushButton] = {}
        self._shortcuts = [self._shortcut(key, offset) for key, offset in _MOVES]
        self._fill()

    def _counted(self) -> str:
        """How many albums this press is about."""
        words = ASKING_ABOUT if len(self._wanted) == ONE else ASKING_ABOUT_MANY
        return words.format(count=len(self._wanted))

    def _announcement(self) -> str:
        """The shops a release removed, said once. FR-S35."""
        retired = self._editing.announce() if self._editing is not None else ()
        return RETIRED.format(names=", ".join(retired)) if retired else ""

    def _shortcut(self, key: Qt.Key, offset: int) -> QShortcut:
        """Ctrl plus an arrow, moving whichever shop holds focus. FR-S28."""
        sequence = QKeySequence(
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, key)
        )
        shortcut = QShortcut(sequence, self)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(partial(self.move_focused, offset))
        return shortcut

    def _buttons(self) -> QHBoxLayout:
        """Add and put back where the list can change; Close to the right."""
        row = QHBoxLayout()
        self.add_button: QPushButton | None = None
        self.put_back_button: QPushButton | None = None
        if self._editing is not None:
            self.add_button = wearing(
                QPushButton(ADD_LABEL, self), resources.find_asset(ADD_ICON)
            )
            self.add_button.setAutoDefault(False)
            self.add_button.clicked.connect(self.add)
            row.addWidget(self.add_button)
            self.put_back_button = QPushButton(PUT_BACK_LABEL, self)
            self.put_back_button.setAutoDefault(False)
            self.put_back_button.clicked.connect(self.put_back)
            row.addWidget(self.put_back_button)
        row.addStretch()
        self.close_button = wearing(
            QPushButton(CLOSE_LABEL, self), resources.find_asset(CLOSE_ICON)
        )
        self.close_button.setDefault(True)
        self.close_button.setAutoDefault(True)
        self.close_button.clicked.connect(self.reject)
        row.addWidget(self.close_button)
        return row

    def _fill(self) -> None:
        """Draw the rows as the list now stands, then state the ring."""
        while self._rows.count():
            gone = self._rows.takeAt(0).widget()
            if gone is not None:
                gone.setParent(None)
                gone.deleteLater()
        self.controls, self.shop_buttons = [], {}
        rows = (
            self._editing.book().rows
            if self._editing is not None
            else self._shopping.offered()
        )
        for index, row in enumerate(rows):
            changes = None
            if self._editing is not None:
                changes = (
                    partial(self.edit, index),
                    partial(self.delete, index),
                    partial(self.drop, index),
                )
            made = row_controls(row, self.rows_holder, self.chose, changes)
            self._rows.addWidget(made.holder)
            self.controls.append(made)
            if isinstance(row, Shop):
                self.shop_buttons[row.name] = made.button
        if not rows:
            empty = NO_SHOPS_YET if self._editing is not None else NO_SHOPS
            self._rows.addWidget(QLabel(empty, self.rows_holder))
        self._chain()

    def _chain(self) -> None:
        """Tab walks the rows in reading order, then the controls below. FR-S40."""
        stops = [stop for made in self.controls for stop in made.stops()]
        stops += [b for b in (self.add_button, self.put_back_button) if b is not None]
        stops.append(self.close_button)
        for before, after in pairwise(stops):
            QWidget.setTabOrder(before, after)

    def _saving(self, change: Callable[[], object]) -> bool:
        """Make a change, then redraw; say so where it could not be kept."""
        try:
            change()
        except ShopListUnwritable:
            self.said.setText(COULD_NOT_SAVE)
            self.said.setStyleSheet(f"color: {self._colour.warning}")
            return False
        self._fill()
        return True

    def _asked(self, title: str, text: str) -> bool:
        """Whether somebody said yes."""
        answer = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _form(self, index: int | None) -> None:
        """Open the shop form, redrawing if it saved. FR-S17, FR-S18."""
        row = self._editing.book().rows[index] if index is not None else None
        album = self._wanted[0] if self._wanted else None
        form = ShopForm(self._editing, album, index, row, self._mode, self)
        if form.exec():
            self._fill()

    def add(self) -> None:
        """A new shop, from an empty form. FR-S17."""
        self._form(None)

    def edit(self, index: int) -> None:
        """The shop at `index`, in the form. FR-S18."""
        self._form(index)

    def delete(self, index: int) -> None:
        """Remove the row at `index` after asking, naming it. FR-S24."""
        name = self._editing.book().rows[index].name or UNNAMED
        if self._asked(DELETE_TITLE, DELETE_ASK.format(shop=name)):
            self._saving(partial(self._editing.delete, index))

    def put_back(self) -> None:
        """The shops Stellody came with, after asking. FR-S37, FR-S38."""
        if self._asked(PUT_BACK_TITLE, PUT_BACK_ASK):
            self._saving(self._editing.put_back)

    def drop(self, index: int, where: QPoint) -> None:
        """Place the row at `index` where a drag let go of it. FR-S27.

        Its new place is the number of other rows whose middle lies above the
        point it was dropped at.
        """
        above = sum(
            1
            for at, made in enumerate(self.controls)
            if at != index
            and made.holder.mapToGlobal(made.holder.rect().center()).y() < where.y()
        )
        self._saving(partial(self._editing.move_to, index, above))

    def move_focused(self, offset: int) -> None:
        """Move the shop whose control holds focus, keeping focus on it. FR-S28."""
        focus = self.focusWidget()
        for index, made in enumerate(self.controls):
            stops = made.stops()
            if focus not in stops or self._editing is None:
                continue
            kind = stops.index(focus)
            if not self._saving(partial(self._editing.move, index, offset)):
                return
            landed = min(max(index + offset, 0), len(self.controls) - 1)
            self.controls[landed].stops()[kind].setFocus(Qt.FocusReason.TabFocusReason)
            return

    def chose(self, shop: Shop) -> None:
        """Open this shop's search for every ticked album, then stay open."""
        if self._shopping.needs_asking(self._wanted) and not self._agreed(shop):
            return
        refused = self._shopping.look_up(shop, self._wanted)
        self._say(shop, refused)

    def _agreed(self, shop: Shop) -> bool:
        """Whether somebody said yes to that many tabs. FR-S08."""
        text = TOO_MANY.format(count=len(self._wanted), shop=shop.name)
        return self._asked(TOO_MANY_TITLE, text)

    def _say(self, shop: Shop, refused: tuple[str, ...]) -> None:
        """Report what happened, in the dialog that is still standing."""
        if refused:
            self.said.setText(WOULD_NOT_OPEN.format(shop=shop.name))
            self.said.setStyleSheet(f"color: {self._colour.warning}")
            return
        opened = len(self._wanted)
        words = OPENED if opened == ONE else OPENED_MANY
        self.said.setText(words.format(count=opened, shop=shop.name))
        self.said.setStyleSheet(f"color: {self._colour.text_muted}")


_MOVES = ((Qt.Key.Key_Up, UP), (Qt.Key.Key_Down, DOWN))
