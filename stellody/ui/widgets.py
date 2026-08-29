"""Small shared widget helpers."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QHBoxLayout,
    QPushButton,
    QWidget,
)


def choice_row(
    parent: QWidget,
    primary: tuple[str, Callable[[], None]],
    secondary: tuple[str, Callable[[], None]],
) -> QHBoxLayout:
    """A trailing row of two buttons, the primary one focused and default."""
    row = QHBoxLayout()
    row.addStretch()
    secondary_button = QPushButton(secondary[0], parent)
    secondary_button.clicked.connect(secondary[1])
    row.addWidget(secondary_button)
    primary_button = QPushButton(primary[0], parent)
    primary_button.setDefault(True)
    primary_button.clicked.connect(primary[1])
    row.addWidget(primary_button)
    return row


class ReadingPane(QObject):
    """Keeps a read-only text view out of the ring unless it can be scrolled.

    A pane is chrome: it holds content rather than being something to act on.
    Qt gives the whole scroll area family StrongFocus by default, so clicking
    anywhere in a licence or an About page focused the pane and drew a ring
    round it. The ring said nothing that could be acted on and the stop cost a
    keypress to step past.

    Two changes; the first is what a reader actually notices:

    TabFocus rather than StrongFocus, so a CLICK never focuses it. The ring
    then only ever appears because somebody tabbed there, which is the one time
    it means anything.

    Then the stop itself is conditional. A page that fits its viewport scrolls
    nowhere, so it is not actionable and drops off the ring entirely. A page
    that overflows keeps the stop, because a long text with no controls of its
    own could not be read from the keyboard otherwise. That is recomputed
    rather than decided once, since the same page overflows or not depending on
    how the window has been sized.
    """

    def __init__(self, view: QAbstractScrollArea) -> None:
        super().__init__(view)
        self._view = view
        view.viewport().setFocusPolicy(Qt.FocusPolicy.NoFocus)
        view.installEventFilter(self)
        view.verticalScrollBar().rangeChanged.connect(self._sync)
        view.horizontalScrollBar().rangeChanged.connect(self._sync)
        self._sync()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Resizing changes whether the content still fits, so re-decide."""
        if event.type() == QEvent.Type.Resize:
            self._sync()
        return False

    @property
    def overflows(self) -> bool:
        """Whether there is anything to scroll to in either direction."""
        return (
            self._view.verticalScrollBar().maximum() > 0
            or self._view.horizontalScrollBar().maximum() > 0
        )

    def _sync(self, *_range: int) -> None:
        """A stop while it scrolls somewhere; never a stop when it does not."""
        self._view.setFocusPolicy(
            Qt.FocusPolicy.TabFocus if self.overflows else Qt.FocusPolicy.NoFocus
        )
