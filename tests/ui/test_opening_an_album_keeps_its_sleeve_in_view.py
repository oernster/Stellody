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

Measured again on 2026-09-14, after the pane learned to fit its album: showing
the pane lays the page out at once, the grid's viewport going from 514 pixels
to 386 inside the call that shows it. So on a first open the grid already has
its real room by the time it scrolls again. The layout is forced through for
the other case: a pane already open that grows because the album picked is
longer than the one it held. Every album here used to be two tracks long, so
that case never arose and taking the forcing out failed nothing. The picked
album is now a long one; one test opens it over a short album already showing.

These tests are about WHERE the grid comes to rest, so the glide is set to no
duration; how it travels is held in `test_gliding_grid`.
"""

from __future__ import annotations

import pytest
from playback_support import BareStore, track
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer

from stellody.application.loading import LoadLibrary
from stellody.application.scan import ScanLibrary
from stellody.application.transport import Transport
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.ui.main_window import MainWindow

# Enough albums that one late in the library is well off screen.
ALBUMS = 60
PICKED = 45
# The offscreen screen is 800 by 800 and the window maximises to fit it. These
# tests used to cap the pane at 140 pixels by hand, because it took 300 whatever
# the album and left the grid less than a sleeve. The pane now fits its album up
# to what leaves the grid a whole row of sleeves: measured at 128 pixels for a
# two-track album and 272 for the long one picked, so there is nothing to cap.
SHORT_TRACKS = 2
LONG_TRACKS = 20
# The album left open before the picked one is chosen. Measured with the
# forcing taken out, the three albums just before the picked one still left
# its sleeve whole, while the fourth to the eighth did not; six before sits in
# the middle of that band rather than at its edge.
OPEN_FIRST = PICKED - 6


def albums() -> tuple[Album, ...]:
    """A library long enough to scroll, each album its own."""
    return tuple(
        Album(
            identity=AlbumIdentity(
                album_artist=f"Artist {number:02d}", title=f"Album {number:02d}"
            ),
            tracks=tuple(
                track(n + 1)
                for n in range(LONG_TRACKS if number == PICKED else SHORT_TRACKS)
            ),
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


def test_picking_a_longer_album_over_an_open_one_leaves_its_sleeve_whole(
    window: MainWindow, application: QApplication
) -> None:
    """The pane is already showing, so it grows rather than appears.

    Showing a pane lays the page out; growing one that already shows does not,
    measured, so this is the case the grid forces the layout through for.
    """
    window.toggle_view()
    application.processEvents()
    window._grid.setCurrentIndex(window._model.index(OPEN_FIRST, 0))
    application.processEvents()
    assert window._album_pane.isVisible()
    window._grid.setCurrentIndex(window._model.index(PICKED, 0))
    application.processEvents()
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
    """After the pane has been open once, by the list's route back to it.

    Switching to the list shuts the pane, measured, so the switch back opens
    it afresh; a pane already open is the longer-album test's case.
    """
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
