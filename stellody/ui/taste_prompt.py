"""The offer, made on Find, to save a new selection as a taste profile. FR-D90.

A small box of its own rather than a field in the Discover dialog: the offer
comes once, at the moment the selection is used; either answer lets the run
start. Save stays disabled while the name is blank once trimmed (FR-D91);
Escape answers Not now, since closing a question is declining it.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stellody.domain.taste import usable_name
from stellody.ui.dialogs import FirstStopDialog, title_label

TITLE = "Save as a taste profile?"
ASK = (
    "Save this selection as a taste profile: the genres below, the Include "
    "boxes and the years. One choice then puts it all back."
)
NAME_HINT = "A name for this profile"
SAVE_LABEL = "Save"
NOT_NOW_LABEL = "Not now"
# How the genres are listed under the question.
GENRE_JOIN = ", "


class SaveTasteDialog(FirstStopDialog):
    """Asks for a name to keep a selection of genres under."""

    def __init__(self, genres: tuple[str, ...], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(TITLE)
        outer = QVBoxLayout(self)
        outer.addWidget(title_label(TITLE, self))
        question = QLabel(ASK, self)
        question.setWordWrap(True)
        outer.addWidget(question)
        listed = QLabel(GENRE_JOIN.join(genres), self)
        listed.setWordWrap(True)
        outer.addWidget(listed)
        self.name = QLineEdit(self)
        self.name.setPlaceholderText(NAME_HINT)
        self.name.textChanged.connect(self._name_changed)
        outer.addWidget(self.name)
        row = QHBoxLayout()
        row.addStretch()
        self.not_now_button = QPushButton(NOT_NOW_LABEL, self)
        self.not_now_button.clicked.connect(self.reject)
        row.addWidget(self.not_now_button)
        self.save_button = QPushButton(SAVE_LABEL, self)
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.accept)
        row.addWidget(self.save_button)
        outer.addLayout(row)
        self._name_changed()

    def _name_changed(self) -> None:
        """Offer Save only once there is a name to save under. FR-D91."""
        self.save_button.setEnabled(usable_name(self.name.text()) is not None)

    def accept(self) -> None:
        """Close as saved, unless there is no name, which Enter can still reach."""
        if usable_name(self.name.text()) is not None:
            super().accept()

    def chosen_name(self) -> str | None:
        """The name given; None where the offer was declined."""
        if self.result() != self.DialogCode.Accepted:
            return None
        return usable_name(self.name.text())


def asked_name(parent: QWidget, genres: tuple[str, ...]) -> str | None:
    """Show the offer and wait; the name given, else None for Not now."""
    dialog = SaveTasteDialog(genres, parent)
    dialog.exec()
    return dialog.chosen_name()
