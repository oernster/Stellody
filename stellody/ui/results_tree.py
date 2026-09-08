"""Turning what a run found into the rows somebody reads.

The building half of the results screen, kept apart from the dialog that owns
it. Nothing here knows what a press does or what an answer arriving later
looks like: it is handed the gaps and the palette; it answers with a tree
plus a note of where each candidate artist landed.

That note is the reason a builder returns two things rather than one. A
candidate is asked about long after the tree was drawn; the same candidate
can sit under two different source artists, so the answer has to reach every
row it belongs under. Reading the tree back to find them would mean matching
on text that by then says more than a name.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget

from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.ui.results_ticks import make_tickable
from stellody.ui.results_words import candidate_row, source_row
from stellody.ui.theme import Palette

# Where a candidate artist's identifier is kept, so an answer arriving later
# can find the rows it belongs under.
IDENTIFIER_ROLE = Qt.ItemDataRole.UserRole
# Where a candidate artist's name is kept, so the strip at the top can say who
# is being asked about without reading it back out of a row that now says more
# than the name.
NAME_ROLE = Qt.ItemDataRole.UserRole + 1

# Every candidate artist's rows, by the identifier to ask about. A list rather
# than one row, since two source artists can lead to the same candidate and
# both rows are owed the same answer.
CandidateRows = dict[str, list[QTreeWidgetItem]]


def coloured(item: QTreeWidgetItem, colour: str) -> QTreeWidgetItem:
    """Paint one row's writing, answering the row so this reads inline."""
    item.setForeground(0, QBrush(QColor(colour)))
    return item


def album_item(album: ReleaseGroup, artist: str, colour: Palette) -> QTreeWidgetItem:
    """One album the library does not hold, with a box to tick it by.

    The artist rides on the row as data: the row itself says only a title;
    the row above it says a name plus two counts, so reading an artist
    back off the tree would mean parsing what was written for a human.
    """
    item = coloured(QTreeWidgetItem([album.title]), colour.text)
    return make_tickable(item, artist)


def candidate_item(
    candidate: SimilarArtist, colour: Palette, rows: CandidateRows
) -> QTreeWidgetItem:
    """One artist the library holds nothing by, closed until it is opened.

    The arrow is stated rather than inherited from having children, because it
    has none: the whole point is that nothing is asked until somebody opens
    it. FR-D30.
    """
    item = coloured(
        QTreeWidgetItem([candidate_row(candidate.name)]),
        colour.candidate_artist,
    )
    item.setData(0, IDENTIFIER_ROLE, candidate.identifier)
    item.setData(0, NAME_ROLE, candidate.name)
    item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
    rows.setdefault(candidate.identifier, []).append(item)
    return item


def source_item(found: Gaps, colour: Palette, rows: CandidateRows) -> QTreeWidgetItem:
    """One source artist, with everything that artist turned up beneath.

    The albums first and the candidates after, which is the order they were
    found in: a record by somebody already held is a closer answer than an
    artist nobody has heard yet.

    The row says how many of each sit under it, because both kinds sit in one
    list and a name alone leaves a reader to work out which is which.
    """
    item = coloured(QTreeWidgetItem([source_row(found)]), colour.source_artist)
    for album in found.albums:
        item.addChild(album_item(album, found.artist, colour))
    for candidate in found.artists:
        item.addChild(candidate_item(candidate, colour, rows))
    return item


def filled_tree(
    gaps: tuple[Gaps, ...],
    colour: Palette,
    rows: CandidateRows,
    parent: QWidget | None = None,
) -> QTreeWidget:
    """One list of source artists, noting its candidates in the index handed in.

    The index is handed in rather than answered alongside, because the answer
    is now dealt over several lists side by side and a candidate can sit under
    artists that landed in different ones. One index across the lot is what
    lets an answer arriving later reach every row it belongs under.
    """
    tree = QTreeWidget(parent)
    tree.setHeaderHidden(True)
    tree.setColumnCount(1)
    for found in gaps:
        tree.addTopLevelItem(source_item(found, colour, rows))
    tree.expandToDepth(0)
    return tree
