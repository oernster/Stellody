"""The tree of rows the album model presents.

Kept apart from the model itself because the two answer different questions.
This half is the shape of a library: which rows exist, what each one holds and
where a particular track sits in it. The model half is Qt's questions about
those rows, which is a wider surface and moves for different reasons.

A disc level appears only where an album actually spans more than one, so a
single-disc album puts its tracks directly under itself and nobody has to walk
through a level that says nothing.
"""

from __future__ import annotations

from stellody.domain.album import Album, Disc
from stellody.domain.track import Track


class Node:
    """One row in the tree, holding whichever value it represents."""

    __slots__ = ("album", "children", "disc", "parent", "row", "track")

    def __init__(
        self,
        row: int,
        parent: Node | None,
        album: Album | None = None,
        disc: Disc | None = None,
        track: Track | None = None,
    ) -> None:
        self.row = row
        self.parent = parent
        self.album = album
        self.disc = disc
        self.track = track
        self.children: list[Node] = []


def track_nodes(tracks: tuple[Track, ...], parent: Node) -> list[Node]:
    """Child nodes for a run of tracks."""
    return [
        Node(row=position, parent=parent, track=track)
        for position, track in enumerate(tracks)
    ]


def build(albums: tuple[Album, ...]) -> list[Node]:
    """The whole node tree for a library."""
    roots: list[Node] = []
    for position, album in enumerate(albums):
        node = Node(row=position, parent=None, album=album)
        if album.disc_count > 1:
            for disc_position, disc in enumerate(album.discs):
                disc_node = Node(row=disc_position, parent=node, disc=disc)
                disc_node.children = track_nodes(disc.tracks, disc_node)
                node.children.append(disc_node)
        else:
            node.children = track_nodes(album.ordered_tracks(), node)
        roots.append(node)
    return roots


def find_track(nodes: list[Node], track: Track) -> Node | None:
    """The node holding this exact track, searched depth first.

    Depth first rather than over the albums alone, because a multi-disc album
    keeps its tracks a level further down.
    """
    for node in nodes:
        if node.track is track:
            return node
        deeper = find_track(node.children, track)
        if deeper is not None:
            return deeper
    return None
