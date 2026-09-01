"""The album picked in the grid, opened underneath it with its tracks.

A grid of sleeves says what a library holds; it says nothing about what is on
any of them. Rather than make somebody switch back to the list to find out,
picking a cover opens this pane beneath the grid with that album's tracks in
it; picking a track in it plays that track exactly as the list does.

The tracks are the SAME model rooted at the album, not a copy of it. So the
order the library is in, the durations and the two ways of starting a track
are the ones already built rather than a second set that could disagree.

They run down two columns rather than one, the way a sleeve's back does: the
first column takes the top half of the album and the second carries on from
there. Both columns are that one model on that one album, each showing only
its own run of rows, so a second column costs no second reading and no widget
built by hand. Keyboard reach is untouched: an item view is still what holds
the tracks, so the arrows walk a column and the ring lands on real rows.

One selection is shared between the columns, so the highlight is somewhere in
the album rather than once in each column. Opening an album puts that highlight
on its first track, which is what the play button at the top then starts.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from stellody.domain.album import Album
from stellody.shared import resources
from stellody.ui.covering import RowCover
from stellody.ui.models import AlbumTreeModel
from stellody.ui.row_text import Column
from stellody.ui.stars import StarRating
from stellody.ui.theme import RADIUS_PX, Mode, palette_for

# Said rather than left to be inferred: this rates the ALBUM, while the stars
# down on the position row rate one track; the two are inches apart.
ALBUM_RATING_CAPTION = "Album rating"
# Named so the appearance can reach them: each carries its own fill from the
# blanket rule, so each is a rectangle whether or not it was meant to be one.
TITLE_NAME = "AlbumTitle"
ARTIST_NAME = "AlbumArtist"
CAPTION_NAME = "AlbumRatingCaption"
ALBUM_RATING_TOOLTIP = "Rate this album as a whole, not the track highlighted in it"
# This button doubles the tray's, so it says what the tray's says: the picture
# is the action a press would take rather than the state playback is in.
PLAY_TOOLTIP = "Play this album"
PAUSE_TOOLTIP = "Pause"
PANE_COVER_PX = 72
PANE_ICON_PX = 32
# The button follows the icon rather than being sized a second time, so the
# picture keeps the same breathing room around it whatever it is drawn at.
PANE_BUTTON_PADDING_PX = 12
PANE_BUTTON_PX = PANE_ICON_PX + PANE_BUTTON_PADDING_PX
PANE_GAP_PX = 10
PANE_MARGIN_PX = 10
TRACK_COLUMNS = 2
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


def _spans(rows: int) -> tuple[tuple[int, int], ...]:
    """Where each column starts and stops, filling the first one first.

    An odd count leaves the longer run on the left, which is where a reader
    starts, rather than on the right where it would read as an overflow.
    """
    down = -(-rows // TRACK_COLUMNS)
    return tuple(
        (position * down, min(position * down + down, rows))
        for position in range(TRACK_COLUMNS)
    )


def _track_column(parent: QWidget, model: AlbumTreeModel) -> QTreeView:
    """One column of an album's tracks, on the library's own model."""
    view = QTreeView(parent)
    view.setItemDelegate(RowCover(view))
    view.setModel(model)
    view.setUniformRowHeights(True)
    view.setAllColumnsShowFocus(True)
    view.setRootIsDecorated(False)
    view.setHeaderHidden(True)
    view.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
    view.setColumnHidden(Column.ARTIST, True)
    # The detail cell is shown here, unlike the artist's, because it is where
    # a track says what it has been played. It is empty until one has, so it
    # costs an album nobody has listened to nothing at all.
    header = view.header()
    header.setSectionResizeMode(Column.TITLE, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(Column.DETAIL, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(Column.LENGTH, QHeaderView.ResizeMode.ResizeToContents)
    return view


class AlbumPane(QWidget):
    """One album opened under the grid, with its tracks listed."""

    closed = Signal()
    play_wanted = Signal()
    track_activated = Signal(QModelIndex)
    rated = Signal(int)

    def __init__(self, model: AlbumTreeModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # A holder, never a stop: the ring belongs to the controls inside it.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._mode = Mode.DARK
        self.cover = QLabel(self)
        self.cover.setFixedSize(PANE_COVER_PX, PANE_COVER_PX)
        self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title = QLabel(self)
        self.title.setObjectName(TITLE_NAME)
        self.artist = QLabel(self)
        self.artist.setObjectName(ARTIST_NAME)
        # Said in words beside the stars, because a rating in an album's
        # header would otherwise be read as a rating of whatever track is
        # highlighted in it: the two sit inches apart and look alike.
        self.rating_caption = QLabel(ALBUM_RATING_CAPTION, self)
        self.rating_caption.setObjectName(CAPTION_NAME)
        self.album_stars = StarRating(self)
        self.album_stars.setToolTip(ALBUM_RATING_TOOLTIP)
        self.album_stars.chosen.connect(self.rated)
        self.play_button = _button(
            self, resources.play_icon_path(), PLAY_TOOLTIP, self.play_wanted.emit
        )
        self.close_button = _button(
            self, resources.negative_icon_path(), "Close this album", self.closed.emit
        )
        self._model = model
        self.columns = tuple(_track_column(self, model) for _ in range(TRACK_COLUMNS))
        for column in self.columns:
            column.activated.connect(self.track_activated)
        # One selection across all of them, so the highlight is in the album
        # rather than once per column. The first column's is the one kept;
        # handing a view back its own would destroy what it was given.
        for column in self.columns[1:]:
            column.setSelectionModel(self.columns[0].selectionModel())
        self._lay_out()

    def _lay_out(self) -> None:
        """The cover and its names above, the tracks below.

        The two buttons sit on the rating row rather than beside the names, so
        the album's title runs the whole width instead of stopping short to
        leave room for them. Pushed to the right by the same stretch that holds
        the stars to the left, they land at the end of the row under the title.
        """
        heading = QVBoxLayout()
        heading.setSpacing(0)
        heading.addWidget(self.title)
        heading.addWidget(self.artist)
        rating = QHBoxLayout()
        rating.setContentsMargins(0, PANE_GAP_PX, 0, 0)
        rating.setSpacing(PANE_GAP_PX)
        rating.addWidget(self.rating_caption)
        rating.addWidget(self.album_stars)
        rating.addStretch()
        rating.addWidget(self.play_button)
        rating.addWidget(self.close_button)
        heading.addLayout(rating)
        heading.addStretch()
        header = QHBoxLayout()
        header.setSpacing(PANE_GAP_PX)
        header.addWidget(self.cover)
        header.addLayout(heading, 1)
        listing = QHBoxLayout()
        listing.setSpacing(PANE_GAP_PX)
        for column in self.columns:
            listing.addWidget(column, 1)
        body = QVBoxLayout(self)
        body.setContentsMargins(
            PANE_MARGIN_PX, PANE_MARGIN_PX, PANE_MARGIN_PX, PANE_MARGIN_PX
        )
        body.setSpacing(PANE_GAP_PX)
        body.addLayout(header)
        body.addLayout(listing, 1)

    def set_playing(self, playing: bool) -> None:
        """Wear the pause face while something plays, as the tray's does.

        Two play buttons on one screen that disagree about what a press does
        would be worse than one: this doubles the tray's, so it toggles with
        it rather than sitting there offering to start what is already going.
        """
        path = resources.pause_icon_path() if playing else resources.play_icon_path()
        if path is not None:
            self.play_button.setIcon(QIcon(str(path)))
        self.play_button.setToolTip(PAUSE_TOOLTIP if playing else PLAY_TOOLTIP)

    def show_album_stars(self, stars: int) -> None:
        """Show the rating this album carries, without reporting one."""
        self.album_stars.show_stars(stars)
        self.album_stars.setToolTip(ALBUM_RATING_TOOLTIP)

    def show_appearance(self, mode: Mode) -> None:
        """Follow the appearance the rest of the window is wearing."""
        self._mode = mode
        self.album_stars.show_appearance(mode)
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
        self.show_cover(cover)
        self._fill_columns(where)

    def show_cover(self, cover: QPixmap | None) -> None:
        """Put the album's sleeve on, at the size this pane draws it.

        Apart from opening, because a cover is read on another thread and so
        is usually not there yet at the moment somebody opens an album. Taking
        it once left the placeholder under the pane until the album was opened
        again; the placeholder is the pane's own colour, so it read as no sleeve
        at all rather than as one still on its way.
        """
        if cover is None:
            self.cover.clear()
            return
        self.cover.setPixmap(
            cover.scaled(
                PANE_COVER_PX,
                PANE_COVER_PX,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _fill_columns(self, where: QModelIndex) -> None:
        """Run the album down the first column, then on down the second.

        Hiding rows rather than slicing the model keeps both columns pointed
        at the same album in the same order, so neither can drift from it.
        """
        rows = self._model.rowCount(where)
        for column, (start, stop) in zip(self.columns, _spans(rows)):
            column.setRootIndex(where)
            for row in range(rows):
                column.setRowHidden(row, where, row < start or row >= stop)
            column.expandAll()
            column.setVisible(start < stop)
        self.columns[0].setCurrentIndex(self._first_track(where))

    def _first_track(self, where: QModelIndex) -> QModelIndex:
        """The album's first track, reached through a disc where there is one.

        A multi-disc album puts discs at the top level, so the first row under
        it is a container rather than something that can be played.
        """
        index = self._model.index(0, Column.TITLE, where)
        while index.isValid() and self._model.track_at(index) is None:
            index = self._model.index(0, Column.TITLE, index)
        return index

    def show_track(self, index: QModelIndex) -> bool:
        """Put the highlight on a track of the album open here.

        Answers whether it could. A track of some other album is not in
        this pane at all, so pointing the pane at it would highlight
        nothing while reporting that something had been highlighted.

        The columns share one selection, so setting it on the first puts
        the highlight wherever in the album that track is drawn.
        """
        root = self.columns[0].rootIndex()
        if not root.isValid():
            return False
        parent = index.parent()
        while parent.isValid() and parent != root:
            parent = parent.parent()
        if parent != root:
            return False
        self.columns[0].setCurrentIndex(index)
        return True

    def current_index(self) -> QModelIndex:
        """Where the highlight is, wherever in the album it has been moved."""
        return self.columns[0].currentIndex()

    def clear(self) -> None:
        """Shut on nothing, so nothing of the last album is left showing."""
        self.columns[0].selectionModel().clearSelection()
        self.columns[0].setCurrentIndex(QModelIndex())
        for column in self.columns:
            column.setRootIndex(QModelIndex())
