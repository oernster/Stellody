"""Offering an album a cover from the archive, when somebody asks for one.

The window's half of the cover chooser. It holds the service, opens it over
the album that was right clicked and takes the picture that comes back.

**A window built without the service simply does not offer it.** The chooser is
the one outward reach in Stellody, so it is injected like every other adapter
rather than reached for: a window assembled without one has no entry on its
menu at all, which is what lets a test raise that menu without a network in the
room.

The picture that comes back is drawn the way a read one is, by the same slot,
because by then it is a cover like any other: kept in Stellody's own store,
against the album's identity, at the size the grid draws it.
"""

from __future__ import annotations

from PySide6.QtCore import Slot

from stellody.application.choosing_covers import ChooseCover
from stellody.domain.album import Album
from stellody.ui.cover_chooser import CoverChooser


class Choosing:
    """The window's half of choosing a cover for an album."""

    def start_choosing(self, chooser: ChooseCover | None) -> None:
        """Hold the service, when there is one to hold."""
        self._chooser = chooser
        self._cover_dialog: CoverChooser | None = None

    @property
    def can_choose_covers(self) -> bool:
        """Whether this window was built with somewhere to look."""
        return self._chooser is not None

    def choose_cover(self, album: Album) -> None:
        """Open the chooser over one album, then keep whatever it hands back.

        Modal, because the picture it keeps is for the album it was opened
        over: leaving it open while the library is scrolled or rescanned under
        it would let a listener choose for something that has moved.
        """
        if self._chooser is None:
            return
        dialog = CoverChooser(self._chooser, album, self.theme_mode, self)
        dialog.chosen.connect(self._on_chosen)
        self._cover_dialog = dialog
        try:
            dialog.exec()
        finally:
            dialog.stop()
            self._cover_dialog = None

    def stop_choosing(self) -> None:
        """Let go of a chooser still open on the way out."""
        if self._cover_dialog is not None:
            self._cover_dialog.stop()

    @Slot(str, object)
    def _on_chosen(self, key: str, cover: object) -> None:
        """Draw a chosen cover exactly as a read one is drawn."""
        self._on_cover(key, cover)
