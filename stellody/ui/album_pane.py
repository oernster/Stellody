"""The album picked in the grid, opened underneath it with its tracks.

A grid of sleeves says what a library holds; it says nothing about what is on
any of them. Rather than make somebody switch back to the list to find out,
picking a cover opens this pane beneath the grid with that album's tracks in
it; picking a track in it plays that track exactly as the list does.

The tracks are the SAME model rooted at the album, not a copy of it. So the
order the library is in, the durations and the two ways of starting a track
are the ones already built rather than a second set that could disagree.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from stellody.domain.album import Album
from stellody.shared import resources
from stellody.ui.models import AlbumTreeModel, Column
from stellody.ui.theme import RADIUS_PX, Mode, palette_for

PANE_COVER_PX = 72
PANE_BUTTON_PX = 28
PANE_ICON_PX = 16
PANE_GAP_PX = 10
PANE_MARGIN_PX = 10
TRACK_COLUMN_PX = 420
YEAR_LENGTH = 4


def _button(parent: QWidget, path, tip: str, on_click) -> QPushButton:
    """One picture button, sized for this pane's header."""
    button = QPushButton(parent)
    button.setObjectName("TrayButton")
    button.setToolTip(tip)
    button.setFixedSize(PANE_BUTTON_PX, PANE_BUTTON_PX)
    button.setIconSize(QSize(PANE_ICON_PX, PANE_ICON_PX))
    if path is not None:
        button.setIcon(QIcon(str(path)))
    button.clicked.connect(on_click)
    return button


class AlbumPane(QWidget):
    """One album opened under the grid, with its tracks listed."""

    closed = Signal()
    play_wanted = Signal()

    def __init__(self, model: AlbumTreeModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # A holder, never a stop: the ring belongs to the controls inside it.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._mode = Mode.DARK
        self.cover = QLabel(self)
        self.cover.setFixedSize(PANE_COVER_PX, PANE_COVER_PX)
        self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title = QLabel(self)
        self.artist = QLabel(self)
        self.play_button = _button(
            self, resources.play_icon_path(), "Play this album", self.play_wanted.emit
        )
        self.close_button = _button(
            self, resources.negative_icon_path(), "Close this album", self.closed.emit
        )
        self.tracks = QTreeView(self)
        self.tracks.setModel(model)
        self.tracks.setUniformRowHeights(True)
        self.tracks.setAllColumnsShowFocus(True)
        self.tracks.setRootIsDecorated(False)
        self.tracks.setHeaderHidden(True)
        self.tracks.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self.tracks.setColumnHidden(Column.ARTIST, True)
        self.tracks.setColumnHidden(Column.DETAIL, True)
        self.tracks.setColumnWidth(Column.TITLE, TRACK_COLUMN_PX)
        self._lay_out()

    def _lay_out(self) -> None:
        """The cover and its names above, the tracks below."""
        heading = QVBoxLayout()
        heading.setSpacing(0)
        heading.addWidget(self.title)
        heading.addWidget(self.artist)
        heading.addStretch()
        header = QHBoxLayout()
        header.setSpacing(PANE_GAP_PX)
        header.addWidget(self.cover)
        header.addLayout(heading, 1)
        header.addWidget(self.play_button)
        header.addWidget(self.close_button)
        column = QVBoxLayout(self)
        column.setContentsMargins(
            PANE_MARGIN_PX, PANE_MARGIN_PX, PANE_MARGIN_PX, PANE_MARGIN_PX
        )
        column.setSpacing(PANE_GAP_PX)
        column.addLayout(header)
        column.addWidget(self.tracks, 1)

    def show_appearance(self, mode: Mode) -> None:
        """Follow the appearance the rest of the window is wearing."""
        self._mode = mode
        self.update()

    def paintEvent(self, event) -> None:
        """A panel of its own, so it reads as opened rather than as more list."""
        palette = palette_for(self._mode)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(palette.surface_alt))
        painter.drawRoundedRect(self.rect(), RADIUS_PX, RADIUS_PX)
        painter.end()

    def show_album(
        self, album: Album, where: QModelIndex, cover: QPixmap | None
    ) -> None:
        """Open on one album, listing what is on it."""
        year = album.identity.date[:YEAR_LENGTH]
        named = album.identity.title
        if year:
            named = f"{named}  ({year})"
        self.title.setText(named)
        self.artist.setText(album.identity.album_artist)
        if cover is None:
            self.cover.clear()
        else:
            self.cover.setPixmap(
                cover.scaled(
                    PANE_COVER_PX,
                    PANE_COVER_PX,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        self.tracks.setRootIndex(where)
        self.tracks.expandAll()
