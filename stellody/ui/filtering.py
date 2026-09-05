"""Narrowing what is on screen to the genres somebody asked for.

The window's half of the filter. The question is collected by a dialog and
answered in the domain; what is here is holding the answer and composing it
with the search.

**The two narrowings compose, in one direction.** The filter says which albums
the library is currently made of and a phrase then searches those, so typing
into the search box while a filter is on searches what is on screen rather than
the library behind it. Doing it the other way round would let a phrase produce
albums the filter had just excluded.

**A filter that is on says so.** The button stays down while anything is being
asked for and its tooltip names it, because a narrowed library looks exactly
like a small one: without a mark on the control, an album that is simply
filtered out reads as an album that is missing.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog

from stellody.domain.narrowing import Narrowing
from stellody.domain.searching import AlbumText
from stellody.ui.filter_dialog import FilterDialog

# What the box apart from the catalogue is called when it is named in a list of
# genres, which is the one place it has to read as a phrase rather than a name.
UNSTATED_WORD = "no genre"


def worded(asked: Narrowing) -> str:
    """What is being asked for, in a listener's words rather than a shape's."""
    named = list(asked.wanted)
    if asked.unstated:
        named.append(UNSTATED_WORD)
    return ", ".join(named)


class Filtering:
    """The genre-narrowing half of the window."""

    def start_filtering(self) -> None:
        """Begin with the whole library, nothing asked of it."""
        self._narrowing = Narrowing()

    def open_filter(self) -> None:
        """Ask which genres to show, then show them.

        Cancelling leaves what is on screen exactly as it was, including a
        filter that was already on: the dialog opens holding it, so leaving by
        the other door is the way to change nothing.
        """
        dialog = FilterDialog(self._narrowing, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._narrowing = dialog.narrowing()
        self.show_filtering()
        self._narrow()

    def show_filtering(self) -> None:
        """Put the state of the filter on its own button."""
        asked = self._narrowing
        self._tray.set_filtering(not asked.is_open, worded(asked))

    def filtered(self, prepared: tuple[AlbumText, ...]) -> tuple[AlbumText, ...]:
        """Those albums the filter keeps, in the order they arrived.

        Handed the prepared text rather than the albums, since that is what
        the search reads and preparing it again for a narrowing would be work
        the answer cannot depend on.
        """
        if self._narrowing.is_open:
            return prepared
        return tuple(one for one in prepared if self._narrowing.keeps(one.album))
