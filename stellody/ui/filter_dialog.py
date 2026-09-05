"""Asking the library for the albums of a genre, several at once.

The same catalogue the tag editor states with, asked rather than stated: see
`Manner` in `genre_grid`. Nothing here decides what survives; it collects a
question and hands it over as a `Narrowing`, which is pure and lives in the
domain.

**"Not stated" is a box of its own, apart from the catalogue.** It is not a
genre, so it does not sit among them: more than a tenth of the library carries
no genre tag at all and an album whose tag names nothing in the catalogue is in
the same position, since no tick could ever reach either. Without this box that
part of the library would be hidden behind a field nobody had filled in.

**Clearing is a button rather than a chore.** Undoing a filter by finding every
ticked box is the kind of tidying a dialog should do for somebody; the only alternative
on offer is closing the dialog and hunting.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stellody.domain.narrowing import Narrowing
from stellody.domain.overrides import AlbumField
from stellody.ui.dialogs import FirstStopDialog
from stellody.ui.genre_grid import ASKING, GenreGrid
from stellody.ui.ringed_check import RingedCheckBox

TITLE = "Filter by genre"
UNSTATED_LABEL = "Albums that state no genre"
# Wide enough for the catalogue's three columns of boxes without the longest
# name wrapping, which is the same measurement the album panel is built to.
DIALOG_WIDTH_PX = 700
# The gap that rules the box apart from the catalogue above it. Without it the
# box sits directly under the last column of genres and reads as one more of
# them, which is exactly what it is not.
APART_PX = 12


class FilterDialog(FirstStopDialog):
    """Collects the genres to narrow the library to; nothing else."""

    def __init__(
        self,
        asked: Narrowing | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        asked = asked or Narrowing()
        self.setWindowTitle(TITLE)
        self.setMinimumWidth(DIALOG_WIDTH_PX)
        outer = QVBoxLayout(self)
        # Opened holding what is already being asked for, so a filter is
        # adjusted rather than rebuilt every time the dialog is opened.
        self.grid = GenreGrid("", self, manner=ASKING)
        for name in asked.wanted:
            self.grid.boxes[name].setChecked(True)
        outer.addWidget(self.grid)
        outer.addSpacing(APART_PX)
        self.unstated_box = RingedCheckBox(UNSTATED_LABEL, self)
        self.unstated_box.setChecked(asked.unstated)
        outer.addWidget(self.unstated_box)
        outer.addLayout(self._buttons())

    def _buttons(self) -> QHBoxLayout:
        """Clear away to the left, then out or on with it."""
        row = QHBoxLayout()
        self.clear_button = QPushButton("Clear", self)
        self.clear_button.clicked.connect(self.clear)
        row.addWidget(self.clear_button)
        row.addStretch()
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.reject)
        row.addWidget(self.cancel_button)
        self.show_button = QPushButton("Show", self)
        self.show_button.setDefault(True)
        self.show_button.clicked.connect(self.accept)
        row.addWidget(self.show_button)
        return row

    def clear(self) -> None:
        """Untick everything, leaving the dialog open to be asked again.

        It does not close: clearing and then showing the whole library is two
        presses, while somebody who cleared by accident has lost nothing.
        """
        for box in self.grid.boxes.values():
            box.setChecked(False)
        self.unstated_box.setChecked(False)

    def narrowing(self) -> Narrowing:
        """What has been asked for, as the domain takes it."""
        return Narrowing(
            field=AlbumField.GENRE,
            wanted=self.grid.chosen(),
            unstated=self.unstated_box.isChecked(),
        )
