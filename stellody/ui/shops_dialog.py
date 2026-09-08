"""Where the ticked albums are taken to a shop.

**It stays open.** Ruled by Oliver on 2026-09-08: prices are compared across
shops, so a dialog that closed on the first choice would have to be reopened
for the second. Choosing a shop opens that shop's searches and leaves
everything exactly where it was, ready for the next one. FR-S07.

**It asks before opening a great many tabs.** One album is one browser tab, so
a list of thirty ticked albums arrives as thirty tabs over whatever somebody
was doing. Above five, it says how many and waits. FR-S08.

**It opens nothing itself.** The use case handed in does that, over a port; a
shop that will not open is reported here rather than swallowed there. FR-S13.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stellody.application.shopping import Shopping
from stellody.domain.shopping import Shop, WantedAlbum
from stellody.shared import resources
from stellody.shared.version import APP_NAME
from stellody.ui.dialogs import CLOSE_ICON, FirstStopDialog, title_label, wearing
from stellody.ui.theme import Mode, palette_for

TITLE = "Find these in a shop"
CLOSE_LABEL = "Close"
# What the dialog says it is about to do. The count rather than the names,
# since a list of thirty albums would be the whole dialog.
ASKING_ABOUT = "{count} album ticked. Choose a shop; this stays open."
ASKING_ABOUT_MANY = "{count} albums ticked. Choose a shop; this stays open."
# Said after a shop has been opened, so a press that quietly worked is still
# a press somebody can see the result of.
OPENED = "Opened {count} search at {shop}."
OPENED_MANY = "Opened {count} searches at {shop}."
# Said where the machine would not take an address. FR-S13.
WOULD_NOT_OPEN = "{shop} could not be opened. Is there a browser on this machine?"
# Asked before a great many tabs arrive at once. FR-S08.
TOO_MANY_TITLE = "Open that many tabs?"
TOO_MANY = "This will open {count} browser tabs at {shop}. Continue?"
# Said where the shop list has nothing in it, which takes a deliberately
# emptied file: the reader falls back to the shipped list otherwise.
NO_SHOPS = f"No shops are configured. Edit shops.json in {APP_NAME}'s own folder."
DIALOG_WIDTH_PX = 520
APART_PX = 12
ONE = 1


class ShopsDialog(FirstStopDialog):
    """The shops, offered for whatever has been ticked."""

    def __init__(
        self,
        shopping: Shopping,
        wanted: tuple[WantedAlbum, ...] = (),
        mode: Mode = Mode.DARK,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._shopping = shopping
        self._wanted = wanted
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
        outer.addSpacing(APART_PX)
        self.shop_buttons: dict[str, QPushButton] = {}
        for shop in self._shopping.offered():
            outer.addWidget(self._shop_button(shop))
        if not self.shop_buttons:
            outer.addWidget(QLabel(NO_SHOPS, self))
        outer.addSpacing(APART_PX)
        self.said = QLabel("", self)
        self.said.setWordWrap(True)
        outer.addWidget(self.said)
        outer.addLayout(self._buttons())

    def _counted(self) -> str:
        """How many albums this press is about."""
        words = ASKING_ABOUT if len(self._wanted) == ONE else ASKING_ABOUT_MANY
        return words.format(count=len(self._wanted))

    def _shop_button(self, shop: Shop) -> QPushButton:
        """One shop, with what it stocks written under its name where known."""
        label = shop.name if not shop.note else f"{shop.name}   ({shop.note})"
        button = QPushButton(label, self)
        # Not the default button, so Return reaches Close rather than opening
        # tabs at whichever shop the ring happens to be resting on. Space
        # still chooses one, which is how a keyboard picks a button.
        button.setAutoDefault(False)
        button.clicked.connect(lambda _checked=False, at=shop: self.chose(at))
        self.shop_buttons[shop.name] = button
        return button

    def _buttons(self) -> QHBoxLayout:
        """One way out, away to the right where the house puts it."""
        row = QHBoxLayout()
        row.addStretch()
        self.close_button = wearing(
            QPushButton(CLOSE_LABEL, self), resources.find_asset(CLOSE_ICON)
        )
        self.close_button.setDefault(True)
        self.close_button.setAutoDefault(True)
        self.close_button.clicked.connect(self.reject)
        row.addWidget(self.close_button)
        return row

    def chose(self, shop: Shop) -> None:
        """Open this shop's search for every ticked album, then stay open.

        The question about a great many tabs is asked here rather than in the
        use case, since it is a thing to put to somebody rather than a rule
        about the work.
        """
        if self._shopping.needs_asking(self._wanted) and not self._agreed(shop):
            return
        refused = self._shopping.look_up(shop, self._wanted)
        self._say(shop, refused)

    def _agreed(self, shop: Shop) -> bool:
        """Whether somebody said yes to that many tabs. FR-S08."""
        answer = QMessageBox.question(
            self,
            TOO_MANY_TITLE,
            TOO_MANY.format(count=len(self._wanted), shop=shop.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

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
