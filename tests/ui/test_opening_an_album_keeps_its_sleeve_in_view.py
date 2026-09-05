"""Picking an album leaves its sleeve on screen, not behind the pane it opens.

Reported from the built application: clicking a sleeve scrolls so the pane
below is visible, which is right, while the artwork itself is sometimes only
partly shown or not shown at all. Switching from the list to the sleeves was
the case that showed it most clearly.

Measured before anything was changed, by watching the scroll from inside:
picking an album deep in the library, Qt chose where to go while the viewport
was still 518 pixels tall, because the pane had not appeared yet. The pane then
took 300 of those pixels and the scrollbar kept the value it had been given, so
the sleeve came to rest 294 pixels below the bottom of what was left. Nothing
was wrong with Qt's answer: it was the right answer to a question asked one
moment too early.

These tests are about WHERE the grid comes to rest, so the glide is set to no
duration; how it travels is held in `test_gliding_grid`.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from playback_support import BareStore, track
from PySide6.QtWidgets import QApplication

from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.ui.main_window import MainWindow

# Enough albums that one late in the library is well off screen.
ALBUMS = 60
PICKED = 45
# The offscreen screen is 800 by 800 and the window maximises to fit whatever
# screen it is on, so there is no asking for a taller one here. At that height
# the pane's own 300 pixels leave 218 for the grid, which is less than the 224
# a sleeve occupies at the smallest cover size: nothing could be fully visible
# and every test below would pass by being impossible to fail. Capping the pane
# leaves it taking real room, just less of it, which is the whole of what these
# tests are about.
PANE_HEIGHT = 140


def albums() -> tuple[Album, ...]:
    """A library long enough to scroll, each album its own."""
    return tuple(
        Album(
            identity=AlbumIdentity(
                album_artist=f"Artist {number:02d}", title=f"Album {number:02d}"
            ),
            tracks=(track(1), track(2)),
        )
        for number in range(ALBUMS)
    )


@pytest.fixture
def window(application: QApplication) -> MainWindow:
    """A real window over a library of sixty albums, at a workable size."""
    store = BareStore()

    def session():
        return ScanLibrary(None, None, None, store), store

    made = MainWindow(
        scan_session=session,
        loader=LoadLibrary(store),
        transport=Transport(RecordingPlayer()),
        settings=store,
    )
    made.show()
    made._album_pane.setMaximumHeight(PANE_HEIGHT)
    application.processEvents()
    made._model.set_albums(albums())
    application.processEvents()
    made._grid.glide.setDuration(0)
    return made


def sleeve_is_whole(window: MainWindow) -> bool:
    """True when every pixel of the picked sleeve is inside the viewport."""
    grid = window._grid
    rect = grid.visualRect(grid.currentIndex())
    port = grid.viewport().rect()
    return rect.top() >= port.top() and rect.bottom() <= port.bottom()


def test_there_is_room_for_a_whole_sleeve(
    window: MainWindow, application: QApplication
) -> None:
    """Otherwise the tests below would pass by being impossible to fail."""
    window.toggle_view()
    window._grid.setCurrentIndex(window._model.index(PICKED, 0))
    application.processEvents()
    grid = window._grid
    assert grid.visualRect(grid.currentIndex()).height() < grid.viewport().height()


def test_picking_an_album_leaves_its_sleeve_fully_visible(
    window: MainWindow, application: QApplication
) -> None:
    """The pane opening under it must not push it off the bottom."""
    window.toggle_view()
    application.processEvents()
    window._grid.setCurrentIndex(window._model.index(PICKED, 0))
    application.processEvents()
    assert window._album_pane.isVisible()
    assert sleeve_is_whole(window)


def test_switching_to_the_sleeves_leaves_the_carried_album_fully_visible(
    window: MainWindow, application: QApplication
) -> None:
    """The reported route: from the list, with a track deep in the library."""
    album = window._model.index(PICKED, 0)
    window._tree.setCurrentIndex(window._model.index(0, 0, album))
    application.processEvents()
    window.toggle_view()
    application.processEvents()
    assert window.showing_covers
    assert sleeve_is_whole(window)


def test_switching_back_and_forth_still_lands_on_the_sleeve(
    window: MainWindow, application: QApplication
) -> None:
    """With the pane already open, so its appearance cannot be what saves it."""
    window.toggle_view()
    window._grid.setCurrentIndex(window._model.index(0, 0))
    application.processEvents()
    window.toggle_view()
    album = window._model.index(PICKED, 0)
    window._tree.setCurrentIndex(window._model.index(0, 0, album))
    application.processEvents()
    window.toggle_view()
    application.processEvents()
    assert sleeve_is_whole(window)
