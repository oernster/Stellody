"""The Discover dialog's Taste profiles button and what it lifts. FR-D87 to FR-D92.

Built on the dialog that lays it out, beside Select all, as the queue switches
are built on the bottom strip: this owns the button, its list and the two
questions it asks, while the dialog says where it goes.

The list lifts the way the visualiser's styles do (`lift_menu.py`): the saved
profiles by name, alphabetically, then "Delete a profile" opening the same
names. Choosing a name puts that profile's selection back; choosing one to delete
asks first, naming it. With nothing saved the button is disabled, which wears
the red ring every disabled control wears.

The two questions arrive as callables, so a test answers them rather than a
person: the name to save under (None for Not now) and a yes or no.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QPushButton, QWidget

from stellody.domain.taste import TasteProfile, holding, named, saved, without
from stellody.shared import resources
from stellody.ui.dialogs import said_yes, wearing
from stellody.ui.lift_menu import LiftMenu, emptied, pop_up_above
from stellody.ui.taste_prompt import asked_name
from stellody.ui.taste_store import TasteStore

TASTE_LABEL = "Taste profiles"
TASTE_ICON = "taste-profiles.png"
DELETE_MENU = "Delete a profile"
DELETE_TITLE = "Delete taste profile"
DELETE_ASK = "Delete the taste profile “{name}”? Nothing ticked changes."
REPLACE_TITLE = "Replace taste profile"
REPLACE_ASK = "A taste profile called “{name}” is already saved. Replace it?"
# A literal ampersand in a menu line would mark a shortcut and vanish.
AMPERSAND = "&"
LITERAL_AMPERSAND = "&&"

NameFor = Callable[[tuple[str, ...]], str | None]
Ask = Callable[[str, str], bool]


def _line(name: str) -> str:
    """A profile's name as a menu line shows it, ampersands kept."""
    return name.replace(AMPERSAND, LITERAL_AMPERSAND)


class TasteControls:
    """The button, its list and the saving and deleting behind them."""

    def __init__(
        self,
        parent: QWidget,
        store: TasteStore | None,
        put_back: Callable[[TasteProfile], None],
        icon_px: int,
        name_for: NameFor | None = None,
        ask: Ask | None = None,
    ) -> None:
        self._store = store
        self._put_back = put_back
        self._name_for = name_for or (lambda genres: asked_name(parent, genres))
        self._ask = ask or (lambda title, text: said_yes(parent, title, text))
        self.button = wearing(
            QPushButton(TASTE_LABEL, parent), resources.find_asset(TASTE_ICON)
        )
        self.button.setIconSize(QSize(icon_px, icon_px))
        self.menu = LiftMenu(parent)
        self.button.clicked.connect(lambda: pop_up_above(self.menu, self.button))
        self.refresh()

    def profiles(self) -> tuple[TasteProfile, ...]:
        """What is saved, read afresh; none where nothing keeps them."""
        return () if self._store is None else self._store.profiles()

    def refresh(self) -> None:
        """Rebuild the list from what is saved; disable the button over none."""
        profiles = self.profiles()
        self.button.setEnabled(bool(profiles))
        emptied(self.menu)
        for profile in profiles:
            action = self.menu.addAction(_line(profile.name))
            action.triggered.connect(
                lambda _checked=False, chosen=profile: self._put_back(chosen)
            )
        if not profiles:
            return
        self.menu.addSeparator()
        deleting = self.menu.addMenu(DELETE_MENU)
        for profile in profiles:
            action = deleting.addAction(_line(profile.name))
            action.triggered.connect(
                lambda _checked=False, name=profile.name: self.delete(name)
            )

    def offer(self, selection: TasteProfile) -> None:
        """On Find: offer to save a selection no profile holds yet. FR-D90.

        A name already taken is replaced only once that is confirmed; refused,
        the offer is made again, which is the name field coming back (FR-D91).
        """
        if self._store is None or not selection.genres:
            return
        if holding(self.profiles(), selection) is not None:
            return
        while True:
            name = self._name_for(selection.genres)
            if name is None:
                return
            taken = named(self.profiles(), name)
            if taken is None or self._ask(
                REPLACE_TITLE, REPLACE_ASK.format(name=taken.name)
            ):
                self._store.keep(saved(self.profiles(), name, selection))
                self.refresh()
                return

    def delete(self, name: str) -> None:
        """Remove the profile going by this name, once that is confirmed. FR-D92."""
        if self._store is None:
            return
        if self._ask(DELETE_TITLE, DELETE_ASK.format(name=name)):
            self._store.keep(without(self.profiles(), name))
            self.refresh()
