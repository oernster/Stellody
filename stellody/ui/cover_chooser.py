"""The pictures on offer for one album, shown after the wait they cost.

**Nothing happens without being asked.** Opening this dialog is the only thing
in Stellody that reaches outward. A listener who never opens it runs an
application that still touches nothing.

**It opens on a wait rather than on a result.** Measured on 2026-08-30, one
album took 13.5 seconds to come back with 19 pictures across 8 releases,
because the terms allow one request a second and there is a release to ask
about before there is a picture. So the dialog says what it is doing, fills in
as answers arrive and can be closed at any point in that.

**A tile says what the archive said, no more.** The listing names the thumbnail
sizes it will serve; it never names the pixel size of the original. So a
candidate carries the release it belongs to and the largest size on offer,
which is enough to tell a scan from a proper cover without fetching tens of
megabytes to find out.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stellody.application.choosing_covers import ChooseCover
from stellody.domain.album import Album
from stellody.domain.cover_choice import CoverCandidate
from stellody.ui.cover_worker import CoverRunner
from stellody.ui.covering import cover_pixmap, placeholder_for
from stellody.ui.dialogs import NeutralDialog
from stellody.ui.theme import Mode

# Big enough to tell one sleeve from another, small enough that a dozen fit
# without a scroll. The archive serves its smallest thumbnail at 250, so
# nothing here is ever drawn larger than it came.
TILE_PX = 180
TILE_TEXT_PX = 56
TILE_MARGIN_PX = 16
DIALOG_WIDTH_PX = 860
DIALOG_HEIGHT_PX = 620

LOOKING = (
    "Looking for pictures. This takes a few seconds: the archive allows one "
    "request a second and each release has to be asked about separately."
)
NOTHING = "Nothing came back for this album."
KEEPING = "Keeping the picture."
UNREACHABLE = "That picture could not be fetched, so the album is as it was."


def _counted(pictures: int) -> str:
    """What the status line says once a search has finished."""
    if not pictures:
        return NOTHING
    if pictures == 1:
        return "One picture on offer. Pick it to keep it."
    return f"{pictures} pictures on offer. Pick one to keep it."


class CoverChooser(NeutralDialog):
    """Offers an album the pictures a search found, then keeps the one picked."""

    chosen = Signal(str, object)

    def __init__(
        self,
        chooser: ChooseCover,
        album: Album,
        mode: Mode,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._album = album
        self._candidates: tuple[CoverCandidate, ...] = ()
        self._placeholder = placeholder_for(mode)
        self.setWindowTitle(f"Cover art for {album.identity.title}")
        self.resize(DIALOG_WIDTH_PX, DIALOG_HEIGHT_PX)
        layout = QVBoxLayout(self)
        self.status = QLabel(LOOKING, self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.grid = _picture_grid(self)
        self.grid.currentItemChanged.connect(self._on_pick)
        layout.addWidget(self.grid, 1)
        self.keep_button, self.close_button = _buttons(self, layout)
        self._runner = CoverRunner(chooser, self)
        self._runner.offered.connect(self._on_offered)
        self._runner.previewed.connect(self._on_previewed)
        self._runner.searched.connect(self._on_searched)
        self._runner.kept.connect(self._on_kept)
        self._runner.search(album.identity)

    @property
    def searching(self) -> bool:
        """True while the search or a fetch is still in flight."""
        return self._runner.running

    def reject(self) -> None:
        """Close, letting go of whatever was still being asked for.

        A request already in flight runs to its own timeout; its answer is
        dropped rather than drawn. Waiting for it instead would mean a dialog
        that ignores the close it was just given.
        """
        self._runner.cancel()
        super().reject()

    def stop(self) -> None:
        """Let go of the thread on the way out of the application."""
        self._runner.stop()

    @Slot()
    def keep_picked(self) -> None:
        """Fetch the picture that is picked and keep it for this album."""
        candidate = self.picked()
        if candidate is None:
            return
        self.status.setText(KEEPING)
        self.keep_button.setEnabled(False)
        self._runner.keep(self._album.identity.art_key, candidate)

    def picked(self) -> CoverCandidate | None:
        """The candidate under the current tile; None when none is picked."""
        row = self.grid.currentRow()
        if 0 <= row < len(self._candidates):
            return self._candidates[row]
        return None

    @Slot(object)
    def _on_offered(self, candidates: object) -> None:
        """Draw a tile for each picture on offer, before any has arrived."""
        self._candidates = tuple(candidates)
        for candidate in self._candidates:
            item = QListWidgetItem(candidate.described, self.grid)
            item.setIcon(QIcon(self._placeholder))
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)

    @Slot(int, object)
    def _on_previewed(self, position: int, thumbnail: object) -> None:
        """Put one picture on its tile, when it could be had at all."""
        item = self.grid.item(position)
        picture = cover_pixmap(thumbnail, TILE_PX)
        if item is not None and picture is not None:
            item.setIcon(QIcon(picture))

    @Slot()
    def _on_searched(self) -> None:
        """Say what the search came back with, now that it has finished."""
        self.status.setText(_counted(len(self._candidates)))

    @Slot(str, object)
    def _on_kept(self, key: str, kept: object) -> None:
        """Hand on the picture that was kept, else say none was.

        The dialog closes on a picture rather than staying open over an album
        that now has one. A fetch that failed leaves it open, since the next
        candidate is the obvious thing to try.
        """
        if not isinstance(kept, bytes):
            self.status.setText(UNREACHABLE)
            self.keep_button.setEnabled(self.picked() is not None)
            return
        self.chosen.emit(key, kept)
        self.accept()

    @Slot()
    def _on_pick(self) -> None:
        """Offer to keep a picture only while one is picked."""
        self.keep_button.setEnabled(self.picked() is not None)


def _picture_grid(dialog: CoverChooser) -> QListWidget:
    """The wall of tiles, arranged to the width the dialog happens to have."""
    grid = QListWidget(dialog)
    grid.setViewMode(QListWidget.ViewMode.IconMode)
    grid.setResizeMode(QListWidget.ResizeMode.Adjust)
    grid.setMovement(QListWidget.Movement.Static)
    grid.setUniformItemSizes(True)
    grid.setWordWrap(True)
    grid.setIconSize(QSize(TILE_PX, TILE_PX))
    grid.setGridSize(
        QSize(TILE_PX + TILE_MARGIN_PX, TILE_PX + TILE_TEXT_PX),
    )
    grid.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
    return grid


def _buttons(
    dialog: CoverChooser, layout: QVBoxLayout
) -> tuple[QPushButton, QPushButton]:
    """Keep and Close, with Keep offered only once something is picked."""
    row = QHBoxLayout()
    row.addStretch()
    keep = QPushButton("Use this picture", dialog)
    keep.setEnabled(False)
    keep.clicked.connect(dialog.keep_picked)
    row.addWidget(keep)
    close = QPushButton("Close", dialog)
    close.clicked.connect(dialog.reject)
    row.addWidget(close)
    layout.addLayout(row)
    return keep, close
