"""Stating a genre does not send the library back to the top.

Correcting one album two thirds of the way down is not a request to be
returned to the start. The reload behind an edit replaces every album, which
is right about what the rows say and wrong about where somebody is looking, so
the place is taken before and put back after.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build, track

from stellody.application.artwork import AlbumArtSources
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.ui.row_text import Column
from stellody.ui.tag_editor import TagEditor

# Enough sleeves that there is somewhere to be other than the top.
ALBUMS = 60
# A place well down the library, in pixels rather than rows: what the grid
# scrolls in since it started counting its scrollbar that way.
DEEP_PX = 1500
LOOKED_AT = 40


def _library(genre: str = "") -> tuple[Album, ...]:
    """A library of sleeves, built afresh as a reload builds them."""
    return tuple(
        Album(
            identity=AlbumIdentity(album_artist="Turin Brakes", title=f"Album {n:02d}"),
            tracks=(track(1), track(2)),
            genre=genre if n == LOOKED_AT else "",
        )
        for n in range(ALBUMS)
    )


ART = tuple(
    AlbumArtSources(key=album.identity.art_key, sidecars=()) for album in _library()
)


@pytest.fixture
def window(application: QApplication):
    """A window showing sleeves, scrolled well down the library."""
    made = build(RememberingStore(), RecordingPlayer())
    made.resize(1400, 900)
    made.show()
    made.toggle_view()
    made.show_library(_library(), ART)
    application.processEvents()
    made._grid.verticalScrollBar().setValue(DEEP_PX)
    made._grid.glide.stop()
    application.processEvents()
    yield made
    made.close()


def _reload(window, application, albums=None) -> None:
    """What an edit does to the library: read it again, all of it new.

    The grid is then sent to the top by hand, which is the one part of this
    the offscreen platform will not do for itself. Measured on 2026-09-05: a
    model reset over 600 sleeves leaves this grid's scrollbar exactly where it
    was, while the built application jumps to the top of the library. So the
    jump is staged rather than reproduced; what these tests hold is the putting
    back, which is the half that is ours.
    """
    window.show_library(_library("Folk") if albums is None else albums, ART)
    window._grid.glide.stop()
    window._grid.verticalScrollBar().setValue(0)
    application.processEvents()


class TestWhatAPlaceIs:
    def test_it_holds_how_far_down_the_sleeves_are(self, window) -> None:
        assert window.library_place().offset == DEEP_PX

    def test_it_holds_the_album_the_keyboard_is_on(self, window) -> None:
        where = window._model.index(LOOKED_AT, Column.TITLE, QModelIndex())
        window._grid.setCurrentIndex(where)
        album = window._model.album_at(where)
        assert window.library_place().current_key == album.identity.key

    def test_it_holds_nothing_where_no_sleeve_is_current(self, window) -> None:
        assert window.library_place().current_key == ""


class TestPuttingItBack:
    def test_the_sleeves_stay_where_they_were(self, window, application) -> None:
        was = window.library_place()
        _reload(window, application)
        window.restore_place(was)
        assert window._grid.verticalScrollBar().value() == DEEP_PX

    def test_the_highlight_comes_back(self, window, application) -> None:
        where = window._model.index(LOOKED_AT, Column.TITLE, QModelIndex())
        window._grid.setCurrentIndex(where)
        was = window.library_place()
        _reload(window, application)
        window.restore_place(was)
        assert window._grid.currentIndex().row() == LOOKED_AT

    def test_the_highlight_coming_back_opens_nothing(self, window, application) -> None:
        """A sleeve can be current with the pane shut, which is what the
        close button leaves behind. Putting the highlight back is not asking
        to see the album again."""
        where = window._model.index(LOOKED_AT, Column.TITLE, QModelIndex())
        window._grid.setCurrentIndex(where)
        window.close_album()
        was = window.library_place()
        _reload(window, application)
        window.restore_place(was)
        assert not window._album_pane.isVisible()

    def test_an_open_pane_comes_back_open_on_the_same_album(
        self, window, application
    ) -> None:
        window.open_album_at(
            window._model.index(LOOKED_AT, Column.TITLE, QModelIndex())
        )
        was = window.library_place()
        _reload(window, application)
        window.restore_place(was)
        assert window._album_pane.isVisible()
        assert window._album_pane.title.text() == f"Album {LOOKED_AT:02d}"

    def test_an_album_that_is_gone_takes_only_itself(self, window, application) -> None:
        """An edit to an artist moves an album somewhere else; it can fold one
        into another. What cannot be put back is put back no further, while
        where the library was looking still is."""
        window.open_album_at(
            window._model.index(LOOKED_AT, Column.TITLE, QModelIndex())
        )
        was = window.library_place()
        shorter = tuple(
            album for n, album in enumerate(_library("Folk")) if n != LOOKED_AT
        )
        _reload(window, application, shorter)
        window.restore_place(was)
        assert not window._album_pane.isVisible()
        assert window._grid.verticalScrollBar().value() == DEEP_PX


class TestTheEditItself:
    """The wiring, driven through the entry a listener uses."""

    def test_stating_a_genre_leaves_the_library_where_it_was(
        self, window, application, monkeypatch
    ) -> None:
        album = window._model.album_at(
            window._model.index(LOOKED_AT, Column.TITLE, QModelIndex())
        )

        def kept(dialog) -> int:
            dialog.written = 1
            return 1

        monkeypatch.setattr(TagEditor, "exec", kept)
        monkeypatch.setattr(
            type(window), "load_remembered", lambda self: _reload(self, application)
        )
        window.edit_album_tags(album)
        assert window._grid.verticalScrollBar().value() == DEEP_PX

    def test_a_panel_that_stated_nothing_reloads_nothing(
        self, window, application, monkeypatch
    ) -> None:
        """Nothing to put back, since nothing was taken away."""
        album = window._model.album_at(
            window._model.index(LOOKED_AT, Column.TITLE, QModelIndex())
        )
        monkeypatch.setattr(TagEditor, "exec", lambda dialog: 0)

        def never(self) -> None:
            raise AssertionError("a panel that stated nothing reloaded the library")

        monkeypatch.setattr(type(window), "load_remembered", never)
        window.edit_album_tags(album)
        assert window._grid.verticalScrollBar().value() == DEEP_PX
