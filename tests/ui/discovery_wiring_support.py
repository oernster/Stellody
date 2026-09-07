"""The window mixin over nothing else, ready to be driven.

Shared by the two suites that drive it: what is said about each ending,
against what the tray does while a run is under way. One module rather than two copies,
since a stand-in window that drifted between them would have the two suites
testing different things while appearing to test one.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox, QPushButton, QWidget

from stellody.application.values import RunOutcome, RunReport
from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.ui.discovering import Discovering
from stellody.ui.discovery_progress import DiscoveryBar
from stellody.ui.tray_metrics import BUTTON_PX

WHERE = "C:/somewhere/discovered.json"


class Tray:
    """Just enough tray to hold the two things the mixin touches.

    The bar is the real one rather than a stand-in, since what the mixin does
    with it is the whole point of the change that put it there.
    """

    def __init__(self, parent: QWidget) -> None:
        self.discover_button = QPushButton(parent)
        self.discovery_bar = DiscoveryBar(parent, BUTTON_PX)


class StatusBar:
    """A status bar that only remembers what it was told to say."""

    def __init__(self) -> None:
        self.said: list[str] = []

    def showMessage(self, message: str) -> None:
        """Qt's own spelling, since the mixin calls Qt's own method."""
        self.said.append(message)


class Window(Discovering, QObject):
    """The mixin over nothing else, which is all it needs to be driven.

    The holder is kept on the window rather than left as a local: a parent
    that goes out of scope is collected, taking the button with it.
    """

    def __init__(self) -> None:
        super().__init__()
        self._all_albums = ()
        self._holder = QWidget()
        self._tray = Tray(self._holder)
        self._status = StatusBar()

    def statusBar(self) -> StatusBar:
        """Where an ended run is announced now that no dialog is open."""
        return self._status


def answer(
    monkeypatch: pytest.MonkeyPatch,
    button: QMessageBox.StandardButton,
    asked: list[str] | None = None,
) -> None:
    """Stand in front of the question with this answer, keeping what was asked."""

    def question(_parent, _title, text, *_arguments, **_keywords):
        """Qt's own signature, since it is Qt's own method being replaced."""
        if asked is not None:
            asked.append(text)
        return button

    monkeypatch.setattr(QMessageBox, "question", question)


class RunnerInProgress:
    """A runner that is always mid-run and only records being stopped.

    Hand written rather than a real runner held open: a test that had to keep
    a thread alive to assert what a button does would be a test of the thread.
    """

    running = True

    def __init__(self) -> None:
        self.stopped = 0

    def cancel(self) -> None:
        """Record that stopping was asked for."""
        self.stopped += 1


class Service:
    """A discovery service that is never actually asked anything."""

    def run(self, albums, ticked, report, cancelled):
        """Stand in for a run; the wiring tests never reach this."""
        return RunReport(outcome=RunOutcome.COMPLETED)


def wrote(report: RunReport) -> str:
    """A writer that always succeeds, answering where it put it."""
    return WHERE


def refused(report: RunReport) -> str:
    """A writer that will not, the way a full disk will not."""
    raise OSError("no room")


def a_report(albums: int = 1, artists: int = 1) -> RunReport:
    """A completed run holding this much."""
    return RunReport(
        outcome=RunOutcome.COMPLETED,
        gaps=(
            Gaps(
                artist="U2",
                albums=tuple(ReleaseGroup(title=f"Album {n}") for n in range(albums)),
                artists=tuple(
                    SimilarArtist(name=f"Artist {n}") for n in range(artists)
                ),
            ),
        ),
    )


def make_window(application, write=wrote, service=None) -> Window:
    """A window mixin wired to a service and a writer."""
    window = Window()
    window.start_discovering(service if service is not None else Service(), write=write)
    return window
