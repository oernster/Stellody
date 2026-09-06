"""What the keyboard walks; the order it walks it in.

Held apart from the window because it is one concern with one question behind
it: given everything the window has built, where does Tab go next. The window
builds its furniture; this states how a reader moves through it.

Two halves. The ORDER is stated rather than inherited, because Qt builds its
chain in creation order and creation order is not reading order here: the tree
is created before the tray, since the tray is handed it. The ARROWS are then
given the job Tab already has, so somebody who reaches for a cursor key finds
the ring rather than nothing.
"""

from __future__ import annotations

import itertools

from PySide6.QtWidgets import QWidget

from stellody.ui.activating import SpaceChooses
from stellody.ui.ring import ArrowRing


def ring_stops(window) -> tuple[QWidget, ...]:
    """Every stop the ring visits, in the order the window is read.

    The menu bar leads, so somebody reaching for the keyboard finds File
    before anything else, exactly as it is drawn. Then the tray above, the
    library itself with the open album under it, then the strip along the
    foot.
    """
    return (
        window.menuBar(),
        *window._tray.ring_stops(),
        window._tree,
        window._grid,
        window._album_pane.album_stars,
        *window._album_pane.columns,
        window._position_bar.slider,
        window._position_bar.stars,
        *window._bottom_tray.ring_stops(),
    )


def state_ring_order(window) -> None:
    """Pin Tab and Shift+Tab to the order the window is read in."""
    for earlier, later in itertools.pairwise(ring_stops(window)):
        QWidget.setTabOrder(earlier, later)


def wire_the_arrows(window) -> tuple[ArrowRing, SpaceChooses]:
    """Give Left and Right the job Tab has; give Space the job Enter has.

    Both are parented to the window, so they live exactly as long as the ring
    they walk. They listen to the application rather than to the window, which
    is what puts a dialog under the same rule without it being told.
    """
    return ArrowRing(window), SpaceChooses(window)
