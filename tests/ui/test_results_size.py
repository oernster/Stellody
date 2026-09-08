"""How big the results screen opens, which is a property of the screen.

Its own file rather than more of `test_results_dialog`, which was already
within five lines of the danger band the line cap draws.

A run over a whole library answers with hundreds of source artists, each
carrying albums and similar artists under it. At the size this opened at,
700 by 560, that is a column of text somebody scrolls for minutes while the
room to show it sits unused either side of the dialog.
"""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication

from stellody.ui.results_dialog import ResultsDialog
from stellody.ui.results_room import (
    DIALOG_HEIGHT_PX,
    DIALOG_WIDTH_PX,
    SCREEN_SHARE,
)


def _room():
    """The room a whole window has on the screen this opens on."""
    return QGuiApplication.primaryScreen().availableGeometry()


def test_it_opens_at_most_of_the_screen(application) -> None:
    """The share, rather than a size that means different things everywhere."""
    dialog = ResultsDialog()
    try:
        room = _room()
        assert dialog.width() == max(DIALOG_WIDTH_PX, int(room.width() * SCREEN_SHARE))
        assert dialog.height() == max(
            DIALOG_HEIGHT_PX, int(room.height() * SCREEN_SHARE)
        )
    finally:
        dialog.deleteLater()


def test_it_leaves_the_screen_something(application) -> None:
    """Nine tenths rather than all of it, so it is a dialog and not a takeover."""
    dialog = ResultsDialog()
    try:
        room = _room()
        assert dialog.width() <= room.width()
        assert dialog.height() <= room.height()
    finally:
        dialog.deleteLater()


def test_it_never_opens_smaller_than_it_used_to(application) -> None:
    """The old fixed size is the floor now: a small screen still gets a screen
    wide enough for an album title under an artist under a heading."""
    dialog = ResultsDialog()
    try:
        assert dialog.width() >= DIALOG_WIDTH_PX
        assert dialog.height() >= DIALOG_HEIGHT_PX
        assert dialog.minimumWidth() == DIALOG_WIDTH_PX
        assert dialog.minimumHeight() == DIALOG_HEIGHT_PX
    finally:
        dialog.deleteLater()
