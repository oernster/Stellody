"""The album tree: albums, their discs and their tracks.

Built as a real item model rather than a widget per row, so a library of
several hundred albums and several thousand tracks stays responsive. A disc
level appears only when an album actually spans more than one disc.
"""

from __future__ import annotations

from enum import IntEnum

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt

from stellody.domain.album import Album, Disc
from stellody.domain.track import Track

MILLISECONDS_PER_SECOND = 1000
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60

HEADINGS = ("Title", "Artist", "Detail", "Length")


class Column(IntEnum):
    """The columns the tree shows."""

    TITLE = 0
    ARTIST = 1
    DETAIL = 2
    LENGTH = 3


def format_duration(milliseconds: int) -> str:
    """A duration as h:mm:ss; m:ss when it is under an hour."""
    seconds = milliseconds // MILLISECONDS_PER_SECOND
    minutes, seconds = divmod(seconds, SECONDS_PER_MINUTE)
    hours, minutes = divmod(minutes, MINUTES_PER_HOUR)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


class _Node:
    """One row in the tree, holding whichever value it represents."""

    __slots__ = ("album", "children", "disc", "parent", "row", "track")

    def __init__(
        self,
        row: int,
        parent: _Node | None,
        album: Album | None = None,
        disc: Disc | None = None,
        track: Track | None = None,
    ) -> None:
        self.row = row
        self.parent = parent
        self.album = album
        self.disc = disc
        self.track = track
        self.children: list[_Node] = []


def _track_nodes(tracks: tuple[Track, ...], parent: _Node) -> list[_Node]:
    """Child nodes for a run of tracks."""
    return [
        _Node(row=position, parent=parent, track=track)
        for position, track in enumerate(tracks)
    ]


def _build(albums: tuple[Album, ...]) -> list[_Node]:
    """The whole node tree for a library."""
    roots: list[_Node] = []
    for position, album in enumerate(albums):
        node = _Node(row=position, parent=None, album=album)
        if album.disc_count > 1:
            for disc_position, disc in enumerate(album.discs):
                disc_node = _Node(row=disc_position, parent=node, disc=disc)
                disc_node.children = _track_nodes(disc.tracks, disc_node)
                node.children.append(disc_node)
        else:
            node.children = _track_nodes(album.ordered_tracks(), node)
        roots.append(node)
    return roots


def _find_track(nodes: list[_Node], track: Track) -> _Node | None:
    """The node holding this exact track, searched depth first.

    Depth first rather than over the albums alone, because a multi-disc album
    keeps its tracks a level further down.
    """
    for node in nodes:
        if node.track is track:
            return node
        deeper = _find_track(node.children, track)
        if deeper is not None:
            return deeper
    return None


def _album_text(album: Album, column: Column) -> str:
    """One cell of an album row."""
    if column is Column.TITLE:
        return album.identity.display_title
    if column is Column.ARTIST:
        return album.identity.display_artist
    if column is Column.LENGTH:
        return format_duration(album.duration_ms)
    parts = [part for part in (album.identity.date, album.genre) if part]
    parts.append(f"{album.track_count} tracks")
    if album.disc_count > 1:
        parts.append(f"{album.disc_count} discs")
    return "  ".join(parts)


def _disc_text(disc: Disc, column: Column) -> str:
    """One cell of a disc row."""
    if column is Column.TITLE:
        return f"Disc {disc.number}"
    if column is Column.DETAIL:
        return f"{len(disc.tracks)} tracks"
    if column is Column.LENGTH:
        return format_duration(disc.duration_ms)
    return ""


def _track_text(track: Track, column: Column) -> str:
    """One cell of a track row."""
    if column is Column.TITLE:
        return f"{track.track_number:>2}.  {track.title}"
    if column is Column.ARTIST:
        return track.artist_text
    if column is Column.LENGTH:
        return format_duration(track.duration_ms)
    if track.is_high_resolution:
        return f"{track.sample_rate // MILLISECONDS_PER_SECOND} kHz / {track.bit_depth}"
    return ""


def _text(node: _Node, column: Column) -> str:
    """The display text for any node."""
    if node.album is not None:
        return _album_text(node.album, column)
    if node.disc is not None:
        return _disc_text(node.disc, column)
    return _track_text(node.track, column)  # type: ignore[arg-type]


class AlbumTreeModel(QAbstractItemModel):
    """Presents a scanned library as albums, discs and tracks."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self._albums: tuple[Album, ...] = ()
        self._roots: list[_Node] = []
        self._descending = False

    def set_albums(self, albums: tuple[Album, ...]) -> None:
        """Replace the whole library."""
        self.beginResetModel()
        self._albums = albums
        self._rebuild()
        self.endResetModel()

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
        found = _find_track(self._roots, track)
        if found is None:
            return QModelIndex()
        return self.createIndex(found.row, 0, found)

    def _rebuild(self) -> None:
        """Rebuild the node tree in the current order."""
        ordered = sorted(self._albums, key=lambda album: album.identity.sort_key)
        if self._descending:
            ordered.reverse()
        self._roots = _build(tuple(ordered))

    def _node(self, index: QModelIndex) -> _Node | None:
        """The node behind an index; None for the invisible root."""
        if not index.isValid():
            return None
        return index.internalPointer()

    def _children(self, index: QModelIndex) -> list[_Node]:
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
            return _text(node, Column(index.column()))
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
