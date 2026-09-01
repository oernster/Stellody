"""The three controls saying what the library is shown as, plus how it sounds.

They sit together beside the search box because all four change what is on show
rather than what is playing: what the library is drawn as, how large the sleeves
are and the shape of what comes out of it.

Every picture here names what a press would DO rather than what is the case, so
the view toggle shows the view it would move to and the size button the size it
would move to. A button naming what is already on show reads as a label rather
than as something to press.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from stellody.shared import resources
from stellody.ui.covering import CoverSize
from stellody.ui.tray_parts import icon_button

COVERS_TOOLTIP = "Switch to album art"
LIST_TOOLTIP = "Switch to the list"
EQUALISER_TOOLTIP = "Shape what is heard"
# One picture per size, named against the size itself rather than by position,
# so adding a fourth size cannot silently shift the other three.
SIZE_ICONS = {
    CoverSize.MEDIUM: resources.medium_grid_icon_path,
    CoverSize.LARGE: resources.large_grid_icon_path,
    CoverSize.EXTRA_LARGE: resources.extra_large_grid_icon_path,
}
SIZE_NAMES = {
    CoverSize.MEDIUM: "medium",
    CoverSize.LARGE: "large",
    CoverSize.EXTRA_LARGE: "extra large",
}


class ShowingControls(QWidget):
    """The view toggle, the sleeve size and the equalizer, in that order."""

    def __init__(
        self,
        parent: QWidget,
        button_px: int,
        icon_px: int,
        gap_px: int,
        toggle_view: Callable[[], None] = lambda: None,
        toggle_cover_size: Callable[[], None] = lambda: None,
        open_equaliser: Callable[[], None] = lambda: None,
    ) -> None:
        super().__init__(parent)
        # A container is never a stop, so it is said rather than assumed.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.view_button = icon_button(
            self,
            resources.view_icon_path(),
            COVERS_TOOLTIP,
            toggle_view,
            button_px,
            icon_px,
        )
        self.size_button = icon_button(
            self, None, "", toggle_cover_size, button_px, icon_px
        )
        self.equaliser_button = icon_button(
            self,
            resources.equaliser_icon_path(),
            EQUALISER_TOOLTIP,
            open_equaliser,
            button_px,
            icon_px,
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(gap_px)
        for button in self.stops():
            row.addWidget(button)

    def stops(self) -> tuple[QPushButton, ...]:
        """These controls, left to right as they are drawn."""
        return (self.view_button, self.size_button, self.equaliser_button)

    def set_showing_covers(self, covers: bool) -> None:
        """Say what pressing the view toggle would do from here.

        The size button means nothing over the list, so it is disabled there
        rather than left to do nothing: a dead stop is skipped by the ring and
        shows no border, which is how this application says not now.
        """
        self.view_button.setToolTip(LIST_TOOLTIP if covers else COVERS_TOOLTIP)
        self.size_button.setEnabled(covers)

    def set_next_cover_size(self, size: CoverSize) -> None:
        """Show the size a press would move to; say it in the tooltip too."""
        self.size_button.setIcon(QIcon(str(SIZE_ICONS[size]())))
        self.size_button.setToolTip(f"Show {SIZE_NAMES[size]} album art")
