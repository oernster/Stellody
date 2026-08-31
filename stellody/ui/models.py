"""The album tree: albums, their discs and their tracks.

Built as a real item model rather than a widget per row, so a library of
several hundred albums and several thousand tracks stays responsive. The rows
themselves are shaped in `nodes.py`; this is Qt's view of them.
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QPixmap

from stellody.application.artwork import AlbumArtSources
from stellody.application.listening import ListeningLog
from stellody.domain.album import Album
from stellody.domain.listening import track_handle
from stellody.domain.track import Track
from stellody.ui.covering import GRID_COVER_PX
from stellody.ui.nodes import Node, build, find_track
from stellody.ui.row_text import (
    HEADINGS,
    Column,
    detail_text,
    text_for,
)


class _NothingKept:
    """Stands in where no log was given: a model that remembers nothing."""

    def all_listening(self) -> dict:
        """Nothing has ever been kept here."""
        return {}

    def set_listening(self, handle: str, path: str, record) -> None:
        """Take it and forget it."""


def _track_rows(album: Node):
    """Every track under an album, whether or not discs sit between."""
    for child in album.children:
        if child.track is not None:
            yield child
        for deeper in child.children:
            if deeper.track is not None:
                yield deeper


class AlbumTreeModel(QAbstractItemModel):
    """Presents a scanned library as albums, discs and tracks."""

    cover_wanted = Signal(object)

    def __init__(
        self,
        parent: object | None = None,
        listening: ListeningLog | None = None,
    ) -> None:
        super().__init__(parent)
        # What each track has been played. Held here so a row can say it while
        # the library is being read down, which is where somebody looks for
        # it: the one beside the stars is about a single track and is gone the
        # moment that track ends and the next one starts.
        self._listening = listening or ListeningLog(_NothingKept())
        self._albums: tuple[Album, ...] = ()
        self._roots: list[Node] = []
        self._descending = False
        self._art: dict[str, AlbumArtSources] = {}
        self._covers: dict[str, QPixmap | None] = {}
        self._placeholder: QPixmap | None = None
        self._flash = None
        self._cover_px = GRID_COVER_PX

    @property
    def cover_px(self) -> int:
        """The size the covers held here were read at."""
        return self._cover_px

    def set_cover_px(self, size_px: int) -> None:
        """Read covers at a new size, dropping what was read at the old one."""
        if size_px == self._cover_px:
            return
        self._cover_px = size_px
        self._covers.clear()
        self._redraw_covers()

    def set_albums(self, albums: tuple[Album, ...]) -> None:
        """Replace the whole library.

        What has been read is kept: a cover belongs to an album rather than to
        a run of rows, so narrowing the library to a phrase does not send a
        single sleeve back to the disk. Dropping them here sent every visible
        one back on every keystroke, which put the placeholder under the pane
        the search had just opened.
        """
        self.beginResetModel()
        self._albums = albums
        self._rebuild()
        self.endResetModel()

    def plays_of(self, node: Node) -> int:
        """How many times a track row's own track has played out."""
        album = node.parent
        while album is not None and album.album is None:
            album = album.parent
        if album is None or album.album is None or node.track is None:
            return 0
        return self._listening.of(
            track_handle(
                album.album.identity,
                node.track.disc_number,
                node.track.track_number,
            )
        ).plays

    def redraw_plays(self, handle: str) -> None:
        """Draw again the one row whose count has just changed.

        Found by walking rather than by asking where a track is: that search
        is retried when it misses, so spending it here would take the attempt
        the highlight needs.
        """
        for album in self._roots:
            for row, node in enumerate(_track_rows(album)):
                if self._handle_of(album, node) == handle:
                    self._redraw_detail(node, row)
                    return

    def _handle_of(self, album: Node, node: Node) -> str:
        """The handle a track row's record is kept against."""
        return track_handle(
            album.album.identity,
            node.track.disc_number,
            node.track.track_number,
        )

    def _redraw_detail(self, node: Node, row: int) -> None:
        """Ask the view to draw one track's detail cell again."""
        where = self.createIndex(node.row, Column.DETAIL, node)
        self.dataChanged.emit(where, where, [Qt.ItemDataRole.DisplayRole])

    def set_flash(self, flash) -> None:
        """Take whatever is pulsing a row, so a cell can ask it for paint.

        The pulsing itself lives in `flashing.py`; this model is told what to
        paint and never when, so it holds no clock of its own.
        """
        self._flash = flash

    def redraw_row(self, where: QModelIndex) -> None:
        """Ask the view to draw one whole row again."""
        if not where.isValid():
            return
        last = self.index(where.row(), len(HEADINGS) - 1, where.parent())
        self.dataChanged.emit(where, last, [Qt.ItemDataRole.BackgroundRole])

    def set_art(self, art: tuple[AlbumArtSources, ...]) -> None:
        """Say where each album's cover might be found.

        Whatever was read came from the sources being replaced, so it goes
        with them. This is the one thing that can make a cover stale, which is
        why it is the one place they are dropped.
        """
        self._art = {sources.key: sources for sources in art}
        self._covers.clear()

    def set_placeholder(self, placeholder: QPixmap | None) -> None:
        """The square drawn for an album whose cover is not there yet."""
        self._placeholder = placeholder
        self._redraw_covers()

    def set_cover(self, key: str, cover: QPixmap | None) -> None:
        """Take one album's cover, else the news that it has none."""
        self._covers[key] = cover
        for node in self._roots:
            if node.album is not None and node.album.identity.art_key == key:
                self._redraw(node)

    def cover_for(self, key: str) -> QPixmap | None:
        """The sleeve an album is drawing now, without asking for it.

        The placeholder while a read is still out, exactly as a row shows.
        Asking does not queue a read, so somewhere that is not a row can show
        what a row shows without changing what gets read.
        """
        return self._covers.get(key) or self._placeholder

    def _redraw_covers(self) -> None:
        """Ask the view to draw every album's first column again."""
        for node in self._roots:
            self._redraw(node)

    def _redraw(self, node: Node) -> None:
        """Ask the view to draw one album's first column again."""
        where = self.index(node.row, Column.TITLE, QModelIndex())
        self.dataChanged.emit(where, where, [Qt.ItemDataRole.DecorationRole])

    def _cover(self, node: Node) -> QPixmap | None:
        """An album's cover, asking for it the first time it is wanted.

        Asked for from here rather than up front, so a library of a few
        hundred albums does not read a few hundred covers to draw a dozen
        rows. Reading happens on another thread; the placeholder stands in
        until an answer arrives.
        """
        if node.album is None:
            return None
        key = node.album.identity.art_key
        if key in self._covers:
            return self._covers[key] or self._placeholder
        sources = self._art.get(key)
        if sources is not None:
            self.cover_wanted.emit(sources)
        return self._placeholder

    def set_descending(self, descending: bool) -> None:
        """Order albums Z to A rather than A to Z."""
        if descending == self._descending:
            return
        self.beginResetModel()
        self._descending = descending
        self._rebuild()
        self.endResetModel()

    @property
    def descending(self) -> bool:
        """Whether the album order is currently inverted."""
        return self._descending

    def album_count(self) -> int:
        """How many albums the model holds."""
        return len(self._albums)

    def album_at(self, index: QModelIndex) -> Album | None:
        """The album an index sits under, whatever level it is at."""
        node = self._node(index)
        while node is not None and node.album is None:
            node = node.parent
        return node.album if node is not None else None

    def track_at(self, index: QModelIndex) -> Track | None:
        """The track an index refers to, when it refers to one."""
        node = self._node(index)
        return node.track if node is not None else None

    def index_for(self, track: Track) -> QModelIndex:
        """Where a track sits in the tree; an invalid index when it is absent.

        Found by identity rather than by equality, matching the queue: a
        library may legitimately hold two identical tracks; the one being
        played is a particular one of them.
        """
        found = find_track(self._roots, track)
        if found is None:
            return QModelIndex()
        return self.createIndex(found.row, 0, found)

    def _rebuild(self) -> None:
        """Rebuild the node tree in the current order."""
        ordered = sorted(self._albums, key=lambda album: album.identity.sort_key)
        if self._descending:
            ordered.reverse()
        self._roots = build(tuple(ordered))

    def _node(self, index: QModelIndex) -> Node | None:
        """The node behind an index; None for the invisible root."""
        if not index.isValid():
            return None
        return index.internalPointer()

    def _children(self, index: QModelIndex) -> list[Node]:
        """The child nodes of an index; the roots for the invisible root."""
        node = self._node(index)
        return self._roots if node is None else node.children

    # Qt's model API fixes these signatures; QModelIndex() is an immutable
    # value rather than shared state, so B008 does not apply to them.
    def index(
        self,
        row: int,
        column: int,
        parent: QModelIndex = QModelIndex(),  # noqa: B008
    ) -> QModelIndex:
        """The index of one child."""
        children = self._children(parent)
        if row < 0 or row >= len(children) or column < 0 or column >= len(HEADINGS):
            return QModelIndex()
        return self.createIndex(row, column, children[row])

    def parent(self, index: QModelIndex = QModelIndex()) -> QModelIndex:  # noqa: B008
        """The index of a node's parent."""
        node = self._node(index)
        if node is None or node.parent is None:
            return QModelIndex()
        return self.createIndex(node.parent.row, 0, node.parent)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        """How many children a node has."""
        if parent.isValid() and parent.column() > 0:
            return 0
        return len(self._children(parent))

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        """How many columns the tree shows."""
        return len(HEADINGS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """The value for one cell in one role."""
        node = self._node(index)
        if node is None:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            column = Column(index.column())
            if column is Column.DETAIL and node.track is not None:
                return detail_text(text_for(node, column), self.plays_of(node))
            return text_for(node, column)
        if (
            role == Qt.ItemDataRole.DecorationRole
            and index.column() == Column.TITLE
            and node.album is not None
        ):
            return self._cover(node)
        if role == Qt.ItemDataRole.BackgroundRole and self._flash is not None:
            return self._flash.brush(index)
        if role == Qt.ItemDataRole.TextAlignmentRole and index.column() in (
            Column.LENGTH,
        ):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        """The column headings."""
        if (
            orientation is Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(HEADINGS)
        ):
            return HEADINGS[section]
        return None
