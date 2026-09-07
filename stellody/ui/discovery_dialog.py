"""Asking what the library is missing, in the genres somebody chose.

The same catalogue the filter asks with, for the same reason: two grids built
from one catalogue cannot come to disagree, while a second vocabulary invented
here would.

**Ticking is what scopes the run, so it is what the dialog is mostly made of.**
A run over the whole library names 327 artists to two public catalogues; a run
over Folk names one. The ticks are the difference between those, which is why
the action cannot be pressed until at least one box is.

**It says what it is doing, by name.** A run over a whole library takes about
eleven minutes at the rate the catalogues permit. A bar with nothing written
against it is indistinguishable from a hang, so the artist being looked up is
named as it happens.

**It holds no service and reaches no network.** Starting and stopping are
handed in, so the whole dialog can be driven with nothing behind it.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stellody.application.values import DiscoveryProgress
from stellody.ui.dialogs import FirstStopDialog, title_label
from stellody.ui.genre_grid import ASKING, GenreGrid

TITLE = "Discover new music"
FIND_LABEL = "Find"
CLOSE_LABEL = "Close"
CANCEL_LABEL = "Cancel"
# What the dialog says before anything has been asked of it.
RESTING = "Tick the genres to look around, then press Find."
# Named rather than counted alone, since a count says nothing about whether
# anything is still happening.
LOOKING_AT = "Looking up {artist} ({done} of {total})"
# Wide enough for the catalogue's three columns without the longest name
# wrapping; the same measurement the filter dialog is built to.
DIALOG_WIDTH_PX = 700
APART_PX = 12


class DiscoveryDialog(FirstStopDialog):
    """Collects the genres to look around, then reports on the looking."""

    def __init__(
        self,
        start: Callable[[tuple[str, ...]], None] = lambda _genres: None,
        stop: Callable[[], None] = lambda: None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._start = start
        self._stop = stop
        self._running = False
        self.setWindowTitle(TITLE)
        self.setMinimumWidth(DIALOG_WIDTH_PX)
        outer = QVBoxLayout(self)
        # The same words as the title bar, from the same constant: two spellings
        # of one name is the kind of drift nobody notices until it is shipped.
        self.title = title_label(TITLE, self)
        outer.addWidget(self.title)
        outer.addSpacing(APART_PX)
        self.grid = GenreGrid("", self, manner=ASKING)
        for box in self.grid.boxes.values():
            box.toggled.connect(self._ticks_changed)
        outer.addWidget(self.grid)
        outer.addSpacing(APART_PX)
        self.message = QLabel(RESTING, self)
        self.message.setWordWrap(True)
        outer.addWidget(self.message)
        self.bar = QProgressBar(self)
        self.bar.setVisible(False)
        outer.addWidget(self.bar)
        outer.addLayout(self._buttons())
        self._ticks_changed()

    def _buttons(self) -> QHBoxLayout:
        """Away to the left, then the one that does the work."""
        row = QHBoxLayout()
        row.addStretch()
        self.close_button = QPushButton(CLOSE_LABEL, self)
        self.close_button.clicked.connect(self.reject)
        row.addWidget(self.close_button)
        self.find_button = QPushButton(FIND_LABEL, self)
        self.find_button.setDefault(True)
        self.find_button.clicked.connect(self._find)
        row.addWidget(self.find_button)
        return row

    @property
    def running(self) -> bool:
        """Whether a run is under way, which most of the state follows from."""
        return self._running

    def chosen(self) -> tuple[str, ...]:
        """The genres ticked, in catalogue order."""
        return self.grid.chosen()

    def _ticks_changed(self) -> None:
        """Nothing ticked is nothing to ask about, so the action goes.

        A run over no genres has no artists to look up, so offering it invites
        a press that can only report emptiness.
        """
        if self._running:
            return
        self.find_button.setEnabled(bool(self.chosen()))

    def _find(self) -> None:
        """Hand the ticked genres over and settle into watching.

        Guarded rather than merely disabled: two runs racing would double the
        rate against both services, then race each other to replace one file.
        """
        if self._running or not self.chosen():
            return
        self._running = True
        self.find_button.setEnabled(False)
        self.close_button.setText(CANCEL_LABEL)
        self.bar.setVisible(True)
        self.bar.setRange(0, 0)
        self.message.setText(RESTING)
        self._start(self.chosen())

    def progressed(self, progress: DiscoveryProgress) -> None:
        """Say which artist is being looked up, plus how far along that is."""
        self.message.setText(
            LOOKING_AT.format(
                artist=progress.artist, done=progress.done + 1, total=progress.total
            )
        )
        self.bar.setRange(0, progress.total)
        self.bar.setValue(progress.done)

    def finished(self, message: str) -> None:
        """A run has ended, however it ended; say so and offer another."""
        self._running = False
        self.bar.setVisible(False)
        self.close_button.setText(CLOSE_LABEL)
        self.message.setText(message)
        self._ticks_changed()

    def reject(self) -> None:
        """Cancel a run in progress rather than leaving the window.

        The button carries both meanings, since while a run is under way the
        thing somebody wants of it is to stop; a dialog that closed instead
        would leave the run going with nowhere to report to. Escape arrives
        here too, which is the whole reason the guard lives here rather than
        on the button.
        """
        if self._running:
            self._stop()
            return
        super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        """A window closed mid-run is a cancel expressed differently.

        The close is refused rather than taken, so the dialog is still there
        to say how the run ended.
        """
        if self._running:
            self._stop()
            event.ignore()
            return
        super().closeEvent(event)
