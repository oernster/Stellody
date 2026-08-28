"""Asking what the window's close button should do.

Closing defaults to staying in the tray, because a music player that vanishes
mid-track when the cross is clicked is a surprise rather than a feature.
"""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtWidgets import QCheckBox, QLabel, QVBoxLayout, QWidget

from stellody.ui.dialogs import NeutralDialog
from stellody.ui.widgets import choice_row

PROMPT_WIDTH_PX = 420


class CloseAction(StrEnum):
    """What the close button does."""

    ASK = "ask"
    TRAY = "tray"
    QUIT = "quit"


class ClosePrompt(NeutralDialog):
    """Offers the two things the close button could mean."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Close Stellody")
        self.setMinimumWidth(PROMPT_WIDTH_PX)
        self.choice = CloseAction.TRAY
        self._remember = QCheckBox("Remember my choice", self)
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
