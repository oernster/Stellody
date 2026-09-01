"""Asking what the window's close button should do.

The offered default is staying in the tray, because a music player that
vanishes mid-track when the cross is clicked is a surprise rather than a
feature. That is which button leads, never what happens to somebody who
answers nothing.

**A dismissed prompt is not an answer.** The cross on this dialog, Escape and
anything else Qt routes through `reject` all leave the choice at ASK, which is
the same word the settings use for "nobody has said". A prompt that reported
the offered default when it was waved away acted on a decision nobody made:
it minimised the window; where the remember box happened to be ticked it also
wrote that non-answer down as the standing behaviour, so it never asked again.
"""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from stellody.ui.dialogs import NeutralDialog
from stellody.ui.ringed_check import RingedCheckBox
from stellody.ui.widgets import choice_row

PROMPT_WIDTH_PX = 420


class CloseAction(StrEnum):
    """What the close button does."""

    # ASK is the absence of an answer rather than a third thing the button
    # does: it is what the settings hold before anybody has chosen. It is also
    # what this prompt reports when it is dismissed rather than answered.
    ASK = "ask"
    TRAY = "tray"
    QUIT = "quit"


class ClosePrompt(NeutralDialog):
    """Offers the two things the close button could mean."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Close Stellody")
        self.setMinimumWidth(PROMPT_WIDTH_PX)
        # Nothing has been chosen yet. Only the two buttons below may change
        # this, so every other way out of the dialog leaves it saying so.
        self.choice = CloseAction.ASK
        self._remember = RingedCheckBox("Remember my choice", self)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Keep Stellody running in the system tray? "
                "Quitting closes it completely.",
                self,
            )
        )
        layout.addWidget(self._remember)
        layout.addLayout(
            choice_row(
                self,
                primary=("Minimise to tray", self._choose_tray),
                secondary=("Quit", self._choose_quit),
            )
        )

    @property
    def answered(self) -> bool:
        """Whether somebody actually chose, rather than waving the dialog away."""
        return self.choice is not CloseAction.ASK

    @property
    def remember(self) -> bool:
        """Whether the answer should become the standing behaviour."""
        return self._remember.isChecked()

    def _choose_tray(self) -> None:
        """Keep running in the tray."""
        self.choice = CloseAction.TRAY
        self.accept()

    def _choose_quit(self) -> None:
        """Leave the application."""
        self.choice = CloseAction.QUIT
        self.accept()
