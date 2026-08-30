"""Showing an album's cover in the library, once it has been read.

Reading a cover means going to disk and decoding an image, so it happens on a
thread of its own. What the window does here is ask for one the first time a
row wants it, then take the answer and hand it to the model.

Until an answer arrives an album draws a placeholder; an album that turns out
to carry no cover anywhere keeps it rather than leaving a
gap where every other row has a picture.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Slot
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QStyledItemDelegate

from stellody.application.artwork import AlbumArt, AlbumArtSources
from stellody.ui.art_worker import ArtRunner
from stellody.ui.theme import RADIUS_PX, Mode, palette_for

# One pixmap serves both views. It is kept at the size the grid draws it and
# Qt scales it down for a row, so switching views costs no second reading.
GRID_COVER_PX = 160
# Big enough to tell one sleeve from another down a list, small enough that a
# row stays a row.
ROW_COVER_PX = 40


class RowCover(QStyledItemDelegate):
    """Draws an album's cover at the size a row can carry.

    One pixmap serves both views and it is kept at the size the GRID draws it,
    which left every row in the list as tall as a sleeve. A view's icon size
    does not fix that: Qt reads the decoration size off the pixmap itself and
    never consults the view for one. Measured here, a 40px icon size on the
    tree still gave a 166px album row; stating the size in the option gives 44.

    Only a row carrying a picture is touched, so a track stays the height of
    the line of text it is.
    """

    def initStyleOption(self, option, index) -> None:
        """Say how big the decoration is, rather than let the pixmap say."""
        super().initStyleOption(option, index)
        if not option.icon.isNull():
            option.decorationSize = QSize(ROW_COVER_PX, ROW_COVER_PX)


def placeholder_for(mode: Mode) -> QPixmap:
    """The square drawn where a cover has not arrived yet or is not there at all."""
    palette = palette_for(mode)
    pixmap = QPixmap(GRID_COVER_PX, GRID_COVER_PX)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(palette.surface_alt))
    painter.drawRoundedRect(pixmap.rect(), RADIUS_PX, RADIUS_PX)
    painter.end()
    return pixmap


def cover_pixmap(cover: object) -> QPixmap | None:
    """A read cover as something drawable; None when there was none to read."""
    if not isinstance(cover, bytes):
        return None
    pixmap = QPixmap()
    if not pixmap.loadFromData(cover):
        return None
    return pixmap.scaled(
        GRID_COVER_PX,
        GRID_COVER_PX,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


class Covering:
    """The window's half of showing album covers."""

    def start_covering(self, art: AlbumArt | None) -> None:
        """Wire the model to a reader, when there is one to wire it to."""
        self._art_runner = ArtRunner(art, self) if art is not None else None
        if self._art_runner is not None:
            self._art_runner.ready.connect(self._on_cover)
            self._model.cover_wanted.connect(self._art_runner.want)

    def show_art(self, art: tuple[AlbumArtSources, ...]) -> None:
        """Say where each album's cover might be found, after a load or a scan.

        A rescan can change what an album's cover is read from, so what was
        asked for before is forgotten rather than trusted.
        """
        if self._art_runner is not None:
            self._art_runner.forget()
        self._model.set_art(art)

    def show_cover_appearance(self, mode: Mode) -> None:
        """Redraw the placeholder in the appearance the window is wearing."""
        self._model.set_placeholder(placeholder_for(mode))

    def stop_covering(self) -> None:
        """Let go of the reading thread on the way out."""
        if self._art_runner is not None:
            self._art_runner.stop()

    @Slot(str, object)
    def _on_cover(self, key: str, cover: object) -> None:
        """Take one album's cover, else the news that it has none."""
        self._model.set_cover(key, cover_pixmap(cover))
