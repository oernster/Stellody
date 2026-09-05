"""Choosing an album's genres from the catalogue, several at once.

A grid of boxes rather than a line to type in, because a genre is chosen from
a settled list rather than invented: typing invites a third spelling of a name
the library already holds two of, which is the disagreement the tag editor
exists to end.

Two columns, so seventeen names cost eight rows of height rather than
seventeen. Alphabetical, since that is the order they are read in.

It stands in for a line edit wherever the panel keeps one, answering `text()`
with the same kind of stored value a typed field gives. That is what lets the
album form hold one dictionary rather than two.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from stellody.domain.genres import GENRES, chosen_in, stated_as
from stellody.ui.ringed_check import RingedCheckBox

COLUMNS = 2

HINT = "An album can carry several. What you tick replaces what it carries now."

# Said only where the album's own tag names nothing in the catalogue, so the
# panel never silently drops what the file says while showing no box ticked.
UNMATCHED = "Currently tagged {value}, which is not one of these."


def _mnemonic_safe(name: str) -> str:
    """A genre as Qt should draw it.

    Qt reads a single ampersand in a control's text as the marker before a
    shortcut key, so `Drum & Bass` would render as `Drum  Bass` with a stray
    underline. Doubling it is how one is asked for literally.
    """
    return name.replace("&", "&&")


class GenreGrid(QWidget):
    """The catalogue as tick boxes, standing in for a line edit."""

    def __init__(self, value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # A container is never a stop on the keyboard ring; the boxes are.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.boxes: dict[str, RingedCheckBox] = {}
        ticked = set(chosen_in(value))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        hint = QLabel(HINT, self)
        hint.setWordWrap(True)
        font = hint.font()
        font.setItalic(True)
        hint.setFont(font)
        outer.addWidget(hint)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        for index, name in enumerate(GENRES):
            box = RingedCheckBox(_mnemonic_safe(name), self)
            box.setChecked(name in ticked)
            self.boxes[name] = box
            grid.addWidget(box, index // COLUMNS, index % COLUMNS)
        outer.addLayout(grid)

        stated = value.strip()
        unnamed = bool(stated) and not ticked
        self.unmatched = QLabel(UNMATCHED.format(value=stated) if unnamed else "", self)
        self.unmatched.setWordWrap(True)
        self.unmatched.setVisible(unnamed)
        outer.addWidget(self.unmatched)

    def chosen(self) -> tuple[str, ...]:
        """Every genre ticked, in catalogue order."""
        return tuple(name for name, box in self.boxes.items() if box.isChecked())

    def text(self) -> str:
        """What is ticked, as the album form's other fields answer.

        Named to match a line edit rather than to describe itself, since the
        panel holds this beside them and asks all of them the same question.
        """
        return stated_as(self.chosen())
