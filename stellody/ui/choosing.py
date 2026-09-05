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
from stellody.ui.cover_worker import ThreadKeeper


class Choosing:
    """The window's half of choosing a cover for an album."""

    def start_choosing(self, chooser: ChooseCover | None) -> None:
        """Hold the service, when there is one to hold.

        The keeper belongs to the window rather than to the chooser dialog,
        because that is the whole point of it: a search cancelled with a
        request in flight leaves a thread running for as long as that request
        takes; whatever holds it has to still be there when it ends. Held
        by the dialog, it was destroyed with the dialog and Qt ended the
        process over it.
        """
        self._chooser = chooser
        self._cover_dialog: CoverChooser | None = None
        self._lookups = ThreadKeeper(self)

    @property
    def lookups_in_flight(self) -> int:
        """How many cover lookups are still inside a request nobody wants.

        Read on the way out. A thread in a network read cannot be stopped and
        must not be destroyed, so what is done about it is decided where the
        application is left rather than here.
        """
        return self._lookups.waiting

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
        dialog = CoverChooser(
            self._chooser, album, self.theme_mode, self, self._lookups
        )
        dialog.chosen.connect(self._on_chosen)
        self._cover_dialog = dialog
        try:
            dialog.exec()
        finally:
            # Let go of rather than waited for: the keeper above holds any
            # thread still in a request, so closing the chooser costs nothing.
            dialog.let_go()
            self._cover_dialog = None

    def stop_choosing(self) -> None:
        """Let go of a chooser still open on the way out, plus any thread
        still in a request after it."""
        if self._cover_dialog is not None:
            self._cover_dialog.stop()
        self._lookups.stop()

    @Slot(str, object)
    def _on_chosen(self, key: str, cover: object) -> None:
        """Draw a chosen cover exactly as a read one is drawn."""
        self._on_cover(key, cover)
