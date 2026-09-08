"""The fakes and the small readings the two results suites are written from.

One home for them rather than a copy apiece: the dialog's suite and the
worker's suite ask the same catalogue the same questions, so a stand-in that
drifted between them would have the two testing different things while
appearing to test one. It is also what keeps either file clear of the line
cap.

Nothing here asserts. What each suite is ABOUT stays in that suite.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QTreeWidgetItem

from stellody.application.expanding import Expansion
from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.ui.palette import Mode
from stellody.ui.results_dialog import ResultsDialog

# How long a test waits for an answer that crosses a thread before calling it
# a failure. Generous, since a loaded machine schedules a thread when it feels
# like it; a passing run reaches it in a millisecond or two.
PATIENCE_MS = 5000
SLICE_MS = 10


class Asking(QObject):
    """An asker that records the question and answers when the test says so."""

    ready = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, refuse: tuple[str, ...] = ()) -> None:
        super().__init__()
        self.asked: list[str] = []
        self.stopped = 0
        self._refuse = refuse

    def ask(self, identifier: str) -> bool:
        """Take the question, unless this one was set up to be refused."""
        self.asked.append(identifier)
        return identifier not in self._refuse

    def stop(self) -> None:
        """Record being told to let go."""
        self.stopped += 1


class Catalogue:
    """A catalogue answering about one artist, counting what it was asked."""

    def __init__(self, albums=(), raises: Exception | None = None) -> None:
        self._albums = albums
        self._raises = raises
        self.asked: list[str] = []
        self.wanted: list[object] = []

    def albums_of(self, identifier: str, wanted=None) -> tuple[ReleaseGroup, ...]:
        """What this artist released; whatever it was told to raise instead."""
        self.asked.append(identifier)
        self.wanted.append(wanted)
        if self._raises is not None:
            raise self._raises
        return self._albums


class Slow:
    """A catalogue that does not answer until the test lets it go."""

    def __init__(self) -> None:
        self.entered = False
        self.let_go = False

    def albums_of(self, identifier: str, wanted=None) -> tuple[ReleaseGroup, ...]:
        """Sit in the request until released, checking whether anybody waits."""
        self.entered = True
        for _slice in range(PATIENCE_MS // SLICE_MS):
            if self.let_go or (wanted is not None and not wanted()):
                break
            QThread.msleep(SLICE_MS)
        return ()


def expansion(catalogue) -> Expansion:
    """The use case over this catalogue, waiting for nothing."""
    return Expansion(catalogue=catalogue, pause=lambda _seconds: None)


def heard(signal) -> list[tuple]:
    """Everything a signal says, kept in the order it said it."""
    said: list[tuple] = []
    signal.connect(lambda *arguments: said.append(arguments))
    return said


def gaps_with(albums: int = 0, artists: int = 0, artist: str = "U2") -> Gaps:
    """One source artist holding this many albums and this many candidates."""
    return Gaps(
        artist=artist,
        albums=tuple(ReleaseGroup(title=f"Album {n}") for n in range(albums)),
        artists=tuple(
            SimilarArtist(name=f"Artist {n}", identifier=f"id-{n}")
            for n in range(artists)
        ),
    )


def rows_under(item: QTreeWidgetItem) -> tuple[str, ...]:
    """What is written on the rows beneath this one."""
    return tuple(item.child(at).text(0) for at in range(item.childCount()))


def made(
    gaps: tuple[Gaps, ...],
    asking: object | None = None,
    ticked: tuple[str, ...] = (),
) -> ResultsDialog:
    """The dialog over these gaps, drawn in the dark appearance."""
    return ResultsDialog(gaps, asking=asking, mode=Mode.DARK, ticked=ticked)


def candidate_in(dialog: ResultsDialog, at: int = 0) -> QTreeWidgetItem:
    """The candidate artist sitting at this place under the first source."""
    source = dialog.sources[0]
    return source.child(source.childCount() - 1 - at)


def waited_for(application, done, patience: int = PATIENCE_MS) -> bool:
    """Turn the event loop until this is true; False where it never was.

    A loop of slices rather than one sleep: the answer arrives as a queued
    signal, so it is delivered by the loop rather than despite it.
    """
    from PySide6.QtTest import QTest

    for _slice in range(patience // SLICE_MS):
        if done():
            return True
        QTest.qWait(SLICE_MS)
    return done()
