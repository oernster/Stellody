"""The two controls that turn the answer's pages, with the words between them.

**The direction that cannot be taken wears its own picture struck through.**
Oliver's ruling, the same one the sweep at the top of the discovery dialog and
every switch along the foot of the window follow: the cross is one file laid
over another, so what a press would do is said by the picture as well as by
whether the control responds. A greyed control alone says a press does
nothing; it does not say which way is left to go.

**Both directions are struck through where there is only one page.** The pager
holds its place rather than appearing once an answer is long enough, for the
reason the strip above the list does: a control that arrives with the answer
is a control nobody knew was there; its arrival would move everything else
on the screen.

**The position is words.** Two arrows can say that a page can be turned; they
cannot say how much of the answer is behind them, which is the complaint
against one long list in the first place.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from stellody.shared import resources
from stellody.ui.dialogs import CONTROL_ICON_PX
from stellody.ui.icons import plain_icon, struck_through
from stellody.ui.results_words import (
    NEXT_PAGE,
    PREVIOUS_PAGE,
    where_in_the_answer,
)

# Oliver's own artwork, one file a direction. A control whose picture is
# missing keeps its words rather than becoming a blank square.
PREVIOUS_ICON = "prev-page.png"
NEXT_ICON = "next-page.png"
# The gap the dialog puts between its parts, so the pager sits in the same
# rhythm as everything above it.
APART_PX = 12


class ResultsPager(QWidget):
    """Where in the answer somebody is, with the way to the rest of it."""

    turned = Signal(int)

    def __init__(self, pages: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # A container is never a stop on the keyboard ring; the controls in it
        # are. It paints nothing, so there is no border to lose.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._pages = pages
        self._showing = 0
        self._previous_art = resources.find_asset(PREVIOUS_ICON)
        self._next_art = resources.find_asset(NEXT_ICON)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(APART_PX)
        row.addStretch()
        self.previous_button = self._control(PREVIOUS_PAGE, self._back)
        row.addWidget(self.previous_button)
        self.position = QLabel(self)
        self.position.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.position.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.position)
        self.next_button = self._control(NEXT_PAGE, self._on)
        row.addWidget(self.next_button)
        row.addStretch()
        self.showing(0)

    def _control(self, label: str, pressed) -> QPushButton:
        """One direction, wearing its words and its picture.

        The words as well as the picture, for the reason the controls beside
        the Close button carry theirs: two unlabelled squares under a list are
        two squares somebody has to press to find out about.
        """
        button = QPushButton(label, self)
        button.setIconSize(QSize(CONTROL_ICON_PX, CONTROL_ICON_PX))
        button.setAutoDefault(False)
        button.clicked.connect(pressed)
        return button

    def showing(self, at: int) -> None:
        """Say which page is in front; say what can be done from here."""
        self._showing = at
        self.position.setText(where_in_the_answer(at, self._pages))
        self._dress(self.previous_button, self._previous_art, at > 0)
        self._dress(self.next_button, self._next_art, at < self._pages - 1)

    @staticmethod
    def _dress(button: QPushButton, artwork, usable: bool) -> None:
        """Put a direction's picture on it, crossed out where it leads nowhere.

        Disabled as well as struck through, since the picture is what says
        which way is left and the state is what stops the press: a control
        that merely looked spent would still be reachable from the keyboard.
        """
        button.setEnabled(usable)
        button.setIcon(
            plain_icon(artwork)
            if usable
            else struck_through(
                artwork, resources.negative_icon_path(), CONTROL_ICON_PX
            )
        )

    def _back(self) -> None:
        """Ask for the page before this one."""
        self.turned.emit(self._showing - 1)

    def _on(self) -> None:
        """Ask for the page after this one."""
        self.turned.emit(self._showing + 1)
