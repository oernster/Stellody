"""The form a shop is added or edited in. SHOPS.md Amendment 1.

**It will not save a shop that cannot search.** Each problem is said beside the
field it concerns, so a form wrong in two places says both at once (FR-S20,
FR-S21). That is the whole answer to a hand-edited row vanishing: the list is
changed here now, where a broken shop is stopped while somebody is looking.

**Try is a look, not a save.** It opens the address the form holds for the
first album ticked, so whether a shop works is judged on its own page before it
is kept (FR-S22). Only the address has to be right to try one.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stellody.application.shop_editing import ShopEditing, ShopListUnwritable
from stellody.domain.shop_list import Row, ShopProblem
from stellody.domain.shopping import Shop, WantedAlbum
from stellody.shared import resources
from stellody.ui.dialogs import CLOSE_ICON, FirstStopDialog, title_label, wearing
from stellody.ui.shop_rows import COULD_NOT_SAVE, PROBLEM_WORDS
from stellody.ui.theme import Mode, palette_for

ADD_TITLE = "Add a shop"
EDIT_TITLE = "Edit a shop"
NAME_LABEL = "Name"
ADDRESS_LABEL = "Search address"
NOTE_LABEL = "Note"
TRY_LABEL = "Try"
SAVE_LABEL = "Save"
CANCEL_LABEL = "Cancel"
ADDRESS_HINT = "https://example.com/search?q={artist}%20{album}"
# Said after a try, where it worked and where it did not. FR-S22, FR-S23.
TRIED = "Opened in your browser for {artist}, {title}."
WOULD_NOT_OPEN = "That address could not be opened. Is there a browser here?"
# What a try is called where the name box is still empty; the name is not part
# of the address, so it need not hold one yet.
TRY_NAME = "Try"
FORM_WIDTH_PX = 560
NAME_PROBLEMS = (ShopProblem.NO_NAME, ShopProblem.NAME_TAKEN)
ADDRESS_PROBLEMS = (
    ShopProblem.NO_ADDRESS,
    ShopProblem.NOT_SECURE,
    ShopProblem.NO_PLACEHOLDER,
)


class ShopForm(FirstStopDialog):
    """Name, address and note for one shop, with a way to try it first."""

    def __init__(
        self,
        editing: ShopEditing,
        album: WantedAlbum | None,
        index: int | None = None,
        row: Row | None = None,
        mode: Mode = Mode.DARK,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._editing = editing
        self._album = album
        self._index = index
        self._colour = palette_for(mode)
        title = ADD_TITLE if row is None else EDIT_TITLE
        self.setWindowTitle(title)
        self.setMinimumWidth(FORM_WIDTH_PX)
        outer = QVBoxLayout(self)
        outer.addWidget(title_label(title, self))
        fields = QFormLayout()
        self.name = QLineEdit(row.name if row is not None else "", self)
        self.address = QLineEdit(row.template if row is not None else "", self)
        self.address.setPlaceholderText(ADDRESS_HINT)
        self.note = QLineEdit(row.note if row is not None else "", self)
        self.name_problem = self._problem_line()
        self.address_problem = self._problem_line()
        fields.addRow(NAME_LABEL, self.name)
        fields.addRow("", self.name_problem)
        fields.addRow(ADDRESS_LABEL, self.address)
        fields.addRow("", self.address_problem)
        fields.addRow(NOTE_LABEL, self.note)
        outer.addLayout(fields)
        self.said = self._problem_line()
        outer.addWidget(self.said)
        outer.addLayout(self._buttons())

    def _problem_line(self) -> QLabel:
        """A line that says what is wrong, empty until something is."""
        line = QLabel("", self)
        line.setWordWrap(True)
        line.setStyleSheet(f"color: {self._colour.warning}")
        return line

    def _buttons(self) -> QHBoxLayout:
        """Try on the left, the two ways out on the right."""
        row = QHBoxLayout()
        self.try_button = QPushButton(TRY_LABEL, self)
        self.try_button.setAutoDefault(False)
        self.try_button.setEnabled(self._album is not None)
        self.try_button.clicked.connect(self.try_it)
        row.addWidget(self.try_button)
        row.addStretch()
        self.save_button = QPushButton(SAVE_LABEL, self)
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save)
        row.addWidget(self.save_button)
        self.cancel_button = wearing(
            QPushButton(CANCEL_LABEL, self), resources.find_asset(CLOSE_ICON)
        )
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.clicked.connect(self.reject)
        row.addWidget(self.cancel_button)
        return row

    def _problems(self) -> tuple[ShopProblem, ...]:
        """What stops this form saving, as it stands."""
        return self._editing.problems(
            self.name.text(), self.address.text(), self._index
        )

    def _show(self, problems: tuple[ShopProblem, ...]) -> None:
        """Say each problem beside its own field; clear the ones now put right."""
        for line, kinds in (
            (self.name_problem, NAME_PROBLEMS),
            (self.address_problem, ADDRESS_PROBLEMS),
        ):
            found = [problem for problem in problems if problem in kinds]
            line.setText(PROBLEM_WORDS[found[0]].capitalize() if found else "")

    def save(self) -> None:
        """Keep the shop and close, unless something is wrong. FR-S19 to FR-S21."""
        problems = self._problems()
        self._show(problems)
        if problems:
            return
        shop = Shop(
            name=self.name.text().strip(),
            template=self.address.text().strip(),
            note=self.note.text().strip(),
        )
        try:
            if self._index is None:
                self._editing.add(shop)
            else:
                self._editing.edit(self._index, shop)
        except ShopListUnwritable:
            self.said.setText(COULD_NOT_SAVE)
            return
        self.accept()

    def try_it(self) -> None:
        """Open the address for the first ticked album, keeping nothing. FR-S22."""
        trouble = tuple(p for p in self._problems() if p in ADDRESS_PROBLEMS)
        self._show(trouble)
        if trouble or self._album is None:
            return
        shop = Shop(
            name=self.name.text().strip() or TRY_NAME,
            template=self.address.text().strip(),
        )
        if self._editing.try_shop(shop, self._album):
            self.said.setText(
                TRIED.format(artist=self._album.artist, title=self._album.title)
            )
            return
        self.said.setText(WOULD_NOT_OPEN)
