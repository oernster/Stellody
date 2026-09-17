"""The open album's pane is as tall as its album, up to a row of sleeves.

Reported from the built application on 2026-09-14: an album of eight tracks
opened a pane with room for about eight rows a column and used four of them.
Measured before anything was changed, the pane was 300 pixels under albums of
two, eight and twenty tracks alike, because it took a list view's default
height whatever the album held.

So each column asks for the height of its own rows; the page the pane opens on
keeps one whole row of sleeves for the grid and lets the pane have the rest at
most. Both halves are held here, together with the album long enough to want
more room than the page has, which is where either half could come apart.
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
from stellody.ui.covering import COVER_SIZES
from stellody.ui.covers_page import GRID_SHARE_OF_PAGE
from stellody.ui.main_window import MainWindow

SHORT = 2
EIGHT = 8
# Far more rows than the offscreen screen has room for under any sleeve size.
LONG = 80
LENGTHS = (SHORT, EIGHT, LONG)
# Enough albums that the ones picked sit well down the grid rather than on its
# first row, where a sleeve is whole however little room is left.
ALBUMS = 30
DEEP = 24


def albums() -> tuple[Album, ...]:
    """A long library whose albums run short, eight tracks, long, in turn."""
    return tuple(
        Album(
            identity=AlbumIdentity(
                album_artist=f"Artist {number:02d}", title=f"Album {number:02d}"
            ),
            tracks=tuple(track(n + 1) for n in range(LENGTHS[number % len(LENGTHS)])),
        )
        for number in range(ALBUMS)
    )


@pytest.fixture
def window(application: QApplication) -> MainWindow:
    """A real window showing the sleeves, over that library."""
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
    made.toggle_view()
    application.processEvents()
    return made


def open_album(window: MainWindow, application: QApplication, length: int):
    """Pick the album of that length deep in the grid; the pane it opens."""
    row = DEEP + LENGTHS.index(length)
    window._grid.setCurrentIndex(window._model.index(row, 0))
    application.processEvents()
    return window._album_pane


def grid_keeps_a_row(window: MainWindow) -> bool:
    """True when the grid has room left for one whole row of sleeves."""
    grid = window._grid
    return grid.viewport().height() >= grid.gridSize().height()


def sleeve_is_whole(window: MainWindow) -> bool:
    """True when every pixel of the picked sleeve is inside the viewport."""
    grid = window._grid
    rect = grid.visualRect(grid.currentIndex())
    port = grid.viewport().rect()
    return rect.top() >= port.top() and rect.bottom() <= port.bottom()


def test_a_short_album_opens_a_shorter_pane_than_a_longer_one(
    window: MainWindow, application: QApplication
) -> None:
    """The reported fault: every album was given the same height."""
    short = open_album(window, application, SHORT).height()
    eight = open_album(window, application, EIGHT).height()
    assert short < eight


def test_an_album_that_fits_shows_every_track_without_scrolling(
    window: MainWindow, application: QApplication
) -> None:
    """Fitting the album must not mean cutting its last row off."""
    pane = open_album(window, application, EIGHT)
    for column in pane.columns:
        assert column.verticalScrollBar().maximum() == 0


def test_a_long_album_leaves_the_grid_a_whole_row_of_sleeves(
    window: MainWindow, application: QApplication
) -> None:
    """However long the album, the sleeve just picked stays on screen."""
    pane = open_album(window, application, LONG)
    assert grid_keeps_a_row(window)
    assert sleeve_is_whole(window)
    assert pane.columns[0].verticalScrollBar().maximum() > 0, "the rest scrolls"


def test_moving_from_a_short_album_to_a_long_one_keeps_the_sleeve_whole(
    window: MainWindow, application: QApplication
) -> None:
    """With the pane already open, so it grows rather than appears."""
    open_album(window, application, SHORT)
    open_album(window, application, LONG)
    assert sleeve_is_whole(window)


def test_larger_sleeves_leave_a_long_album_less_room(
    window: MainWindow, application: QApplication
) -> None:
    """The row kept for the grid is a row at the size the sleeves are drawn."""
    window.show_cover_size_choice(COVER_SIZES[0])
    pane = open_album(window, application, LONG)
    smallest = pane.sizeHint().height()
    window.show_cover_size_choice(COVER_SIZES[-1])
    application.processEvents()
    assert pane.sizeHint().height() < smallest


def test_a_long_album_is_kept_to_half_the_page(
    window: MainWindow, application: QApplication
) -> None:
    """Reported by Oliver on 2026-09-17: one album's pane dominated the screen.

    The grid used to keep one row of sleeves and give the pane everything
    else, so a long album left a single row showing where a short one left
    three. Half the page reads the same under every album.
    """
    pane = open_album(window, application, LONG)
    page = window._covers_page
    assert page.height() > 2 * (
        window._grid.gridSize().height() + 2 * window._grid.frameWidth()
    ), "the page has to be taller than two rows for the share to be the binding rule"
    assert pane.height() <= page.height() // GRID_SHARE_OF_PAGE


def test_the_grid_keeps_its_share_under_a_long_album(
    window: MainWindow, application: QApplication
) -> None:
    """What he asked for: sleeves to go on browsing, not one album's listing.

    Said as the share rather than as a number of rows, because the offscreen
    page is 535 pixels and one row of the smallest sleeve is 196 of them: a row
    count provable here would be a row count of one. The share is the rule and
    it is what makes a real window show several rows.
    """
    open_album(window, application, LONG)
    page = window._covers_page
    kept = page.height() - window._album_pane.height()
    assert kept >= page.height() // GRID_SHARE_OF_PAGE
