"""The row of actions under the body, rebuilt for each screen.

Every screen carries its own actions rather than the window carrying one fixed
row it relabels as it goes. A relabelled row has to remember what it used to
mean: it is how the go-ahead button on the uninstall screen kept the styling of
a safe action while doing a destructive one; it is also how the progress screen
was left offering a Close during work it could not stop.

The window says what the actions are; this owns what a footer is.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from installer import theme

PRIMARY = "Primary"
DANGER = "Danger"


@dataclass(frozen=True, slots=True)
class Action:
    """One button: what it says, what it does and how it should read."""

    label: str
    on_click: Callable[[], None]
    kind: str = ""


class Footer(QWidget):
    """The right-aligned actions belonging to whichever screen is showing."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Footer")
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(theme.FOOTER_GAP_PX)
        self._row.addStretch()
        self._buttons: tuple[QPushButton, ...] = ()

    def show_actions(self, actions: Iterable[Action]) -> None:
        """Replace whatever is there with this screen's actions.

        The old buttons are unparented as well as scheduled for deletion: a
        button awaiting deletion is still a child, still laid out and still
        drawn, so the row would keep showing the screen that has just gone.
        """
        for button in self._buttons:
            self._row.removeWidget(button)
            button.setParent(None)
            button.deleteLater()
        made: list[QPushButton] = []
        for action in actions:
            button = QPushButton(action.label, self)
            if action.kind:
                button.setObjectName(action.kind)
            button.clicked.connect(action.on_click)
            self._row.addWidget(button)
            made.append(button)
        self._buttons = tuple(made)

    def buttons(self) -> tuple[QPushButton, ...]:
        """The buttons currently showing, left to right as they are drawn."""
        return self._buttons
