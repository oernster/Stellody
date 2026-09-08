"""Ticking albums in the results; reading back which ones are ticked.

Its own module rather than more of `results_dialog.py`, which was already
within thirty lines of the cap: ticking is a concern with a clean edge, being
everything between a box somebody clicks and the list the shops are opened for.

**Only albums are tickable.** An artist is not something a shop sells; a
candidate artist with nothing fetched has no albums to look up, so neither kind
of artist row gets a box. SHOPS.md FR-S01 and FR-S02.

**Each album row carries the artist it belongs to.** The row itself says only a
title; the row above it now says a name plus two counts, so reading an
artist back off the tree would mean parsing what was written for a human. It is
put on the row as data when the row is built instead.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from stellody.domain.shopping import WantedAlbum

# Where an album row keeps the artist it belongs to.
ARTIST_ROLE = Qt.ItemDataRole.UserRole + 2
UNTICKED = Qt.CheckState.Unchecked
TICKED = Qt.CheckState.Checked


def make_tickable(item: QTreeWidgetItem, artist: str) -> QTreeWidgetItem:
    """Give an album row a box and the artist it belongs to.

    Answers the row so this reads inline where the row is built.
    """
    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
    item.setCheckState(0, UNTICKED)
    item.setData(0, ARTIST_ROLE, artist)
    return item


def is_tickable(item: QTreeWidgetItem) -> bool:
    """Whether this row is an album with a box on it.

    Asked of the check STATE rather than of the checkable flag. Measured on
    2026-09-08: Qt gives every item that flag by default, so a flag test calls
    an artist row tickable while no box is drawn on it. What decides whether a
    box appears is whether the row carries a state at all.
    """
    return item.data(0, Qt.ItemDataRole.CheckStateRole) is not None


def _rows(item: QTreeWidgetItem):
    """This row and everything under it, however deep."""
    yield item
    for at in range(item.childCount()):
        yield from _rows(item.child(at))


def every_row(tree: QTreeWidget):
    """Every row in one list, in the order they are drawn."""
    for at in range(tree.topLevelItemCount()):
        yield from _rows(tree.topLevelItem(at))


def every_row_across(trees: Sequence[QTreeWidget]):
    """Every row in every column, a column at a time from the left.

    Reading order over the whole answer, which down a column is the order the
    run answered in and across them is the order somebody reads.
    """
    for tree in trees:
        yield from every_row(tree)


def ticked_albums(trees: Sequence[QTreeWidget]) -> tuple[WantedAlbum, ...]:
    """What has been ticked, in the order it is drawn.

    Reading order rather than tick order, since the list is shown back to
    somebody and a list in the order they happened to click is a list nobody
    can check against the screen.
    """
    return tuple(
        WantedAlbum(artist=row.data(0, ARTIST_ROLE), title=row.text(0))
        for row in every_row_across(trees)
        if is_tickable(row) and row.checkState(0) is TICKED
    )


def anything_ticked(trees: Sequence[QTreeWidget]) -> bool:
    """Whether there is anything to look up at all."""
    return any(
        is_tickable(row) and row.checkState(0) is TICKED
        for row in every_row_across(trees)
    )
