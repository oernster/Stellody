"""Drawing an album's cover in the library, standing in until it arrives.

A cover is asked for the first time a row wants one rather than up front, so
a library of a few hundred albums does not read a few hundred covers to draw
a dozen rows.
"""

from __future__ import annotations

from PySide6.QtCore import QBuffer, QIODevice, QModelIndex, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from stellody.application.artwork import AlbumArtSources
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource
from stellody.ui.covering import (
    GRID_COVER_PX,
    CoverSize,
    cover_pixmap,
    placeholder_for,
)
from stellody.ui.models import AlbumTreeModel, Column
from stellody.ui.theme import Mode

DECORATION = Qt.ItemDataRole.DecorationRole


def _album(title: str = "The Planets") -> Album:
    """One album with a single track."""
    return Album(
        identity=AlbumIdentity(album_artist="Holst", title=title),
        tracks=(
            Track(
                source=TrackSource(path="01.flac"),
                disc_number=1,
                track_number=1,
                title="Mars",
                artists=("Holst",),
                duration_ms=1000,
                sample_rate=CD_SAMPLE_RATE,
                bit_depth=16,
            ),
        ),
    )


def _png(size: int = 200) -> bytes:
    """Real image bytes to stand in for a cover that has been read."""
    image = QImage(size, size, QImage.Format.Format_RGB32)
    image.fill(0x884422)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    data = bytes(buffer.data())
    buffer.close()
    return data


def _model(album: Album, application: QApplication) -> AlbumTreeModel:
    """A model holding one album, told where its cover might be."""
    model = AlbumTreeModel()
    model.set_albums((album,))
    model.set_art((AlbumArtSources(key=album.identity.art_key, sidecars=("a.jpg",)),))
    return model


def _decoration(model: AlbumTreeModel):
    """Whatever the first album row draws in its first column."""
    return model.data(model.index(0, Column.TITLE, QModelIndex()), DECORATION)


class TestStandingIn:
    def test_a_placeholder_is_drawn_at_the_largest_size_on_offer(
        self, application: QApplication
    ) -> None:
        """Drawn once and scaled down, so a grown grid never shows it blurred."""
        assert placeholder_for(Mode.DARK).width() == int(CoverSize.EXTRA_LARGE)

    def test_each_appearance_gets_its_own_placeholder(
        self, application: QApplication
    ) -> None:
        """It sits among the rows, so it follows the window rather than fighting it."""
        light = placeholder_for(Mode.LIGHT).toImage()
        dark = placeholder_for(Mode.DARK).toImage()
        assert light != dark

    def test_a_cover_that_was_read_becomes_something_drawable(
        self, application: QApplication
    ) -> None:
        drawn = cover_pixmap(_png(), GRID_COVER_PX)
        assert drawn is not None
        assert drawn.width() == GRID_COVER_PX

    def test_an_album_with_no_cover_has_nothing_to_draw(
        self, application: QApplication
    ) -> None:
        assert cover_pixmap(None, GRID_COVER_PX) is None

    def test_bytes_that_are_not_an_image_have_nothing_to_draw(
        self, application: QApplication
    ) -> None:
        assert cover_pixmap(b"not an image at all", GRID_COVER_PX) is None


class TestAskingFromTheRow:
    def test_an_album_asks_for_its_cover_when_it_is_first_drawn(
        self, application: QApplication
    ) -> None:
        album = _album()
        model = _model(album, application)
        asked: list[str] = []
        model.cover_wanted.connect(lambda sources: asked.append(sources.key))
        _decoration(model)
        assert asked == [album.identity.art_key]

    def test_an_album_nobody_recorded_art_for_asks_for_nothing(
        self, application: QApplication
    ) -> None:
        model = AlbumTreeModel()
        model.set_albums((_album(),))
        asked: list[str] = []
        model.cover_wanted.connect(lambda sources: asked.append(sources.key))
        assert _decoration(model) is None
        assert asked == []

    def test_a_cover_that_arrived_is_what_gets_drawn(
        self, application: QApplication
    ) -> None:
        album = _album()
        model = _model(album, application)
        model.set_placeholder(placeholder_for(Mode.DARK))
        cover = cover_pixmap(_png(), GRID_COVER_PX)
        model.set_cover(album.identity.art_key, cover)
        assert _decoration(model) is cover

    def test_an_album_with_no_cover_keeps_the_placeholder(
        self, application: QApplication
    ) -> None:
        """A gap where every other row has a picture reads as a fault."""
        album = _album()
        model = _model(album, application)
        placeholder = placeholder_for(Mode.DARK)
        model.set_placeholder(placeholder)
        model.set_cover(album.identity.art_key, None)
        assert _decoration(model) is placeholder

    def test_an_album_already_answered_is_not_asked_again(
        self, application: QApplication
    ) -> None:
        album = _album()
        model = _model(album, application)
        model.set_cover(album.identity.art_key, None)
        asked: list[str] = []
        model.cover_wanted.connect(lambda sources: asked.append(sources.key))
        _decoration(model)
        assert asked == []

    def test_a_replaced_library_forgets_what_it_had_drawn(
        self, application: QApplication
    ) -> None:
        """A rescan can change what an album's cover is read from."""
        album = _album()
        model = _model(album, application)
        model.set_cover(album.identity.art_key, cover_pixmap(_png(), GRID_COVER_PX))
        model.set_albums((album,))
        asked: list[str] = []
        model.cover_wanted.connect(lambda sources: asked.append(sources.key))
        _decoration(model)
        assert asked == [album.identity.art_key]

    def test_only_an_album_row_carries_a_cover(self, application: QApplication) -> None:
        album = _album()
        model = _model(album, application)
        parent = model.index(0, Column.TITLE, QModelIndex())
        track = model.index(0, Column.TITLE, parent)
        assert model.data(track, DECORATION) is None

    def test_no_other_column_carries_one(self, application: QApplication) -> None:
        album = _album()
        model = _model(album, application)
        where = model.index(0, Column.ARTIST, QModelIndex())
        assert model.data(where, DECORATION) is None
