"""The window fits the smallest screen it is meant for, at the scale it is drawn.

Measured on 2026-09-14: the tray under the menus alone insisted on 1360 points
on a panel offering 1280, so the right end of the window ran off the screen
whatever view was showing. Nothing checked the window's floor against any
screen at all, which is how the tray grew past one without anybody seeing it.

The floor is read from the window as built, in both views and with an album
open under the sleeves, which is where it is tallest. It is then carried onto
the screen through the same multiplier the application asks Qt for, so the
check and the drawing cannot come to disagree about how big a point is.
"""

from __future__ import annotations

from conftest import RecordingPlayer
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

from stellody.ui.interface_scale import (
    INTERFACE_SCALE,
    SCALE_VARIABLE,
    SMALLEST_ROOM_HEIGHT_PX,
    SMALLEST_ROOM_WIDTH_PX,
    on_screen,
    use_interface_scale,
)

# A scale somebody has already chosen for themselves.
CHOSEN_ELSEWHERE = "1.25"


def _fits(window, application: QApplication, view: str) -> None:
    """Assert the window's floor fits the smallest room, as drawn on screen."""
    application.processEvents()
    floor = window.minimumSizeHint()
    wide = on_screen(floor.width())
    tall = on_screen(floor.height())
    assert wide <= SMALLEST_ROOM_WIDTH_PX, (
        f"in the {view} the window needs {wide:.0f} points across at a scale of "
        f"{INTERFACE_SCALE}, while the smallest screen offers "
        f"{SMALLEST_ROOM_WIDTH_PX}"
    )
    assert tall <= SMALLEST_ROOM_HEIGHT_PX, (
        f"in the {view} the window needs {tall:.0f} points down at a scale of "
        f"{INTERFACE_SCALE}, while the smallest screen offers "
        f"{SMALLEST_ROOM_HEIGHT_PX}"
    )


def test_the_window_fits_the_smallest_screen_in_every_view(
    application: QApplication,
) -> None:
    """The list, the sleeves, then the sleeves with an album open under them."""
    window = build(RememberingStore(), RecordingPlayer())
    window.show()
    window.show_covers(False)
    _fits(window, application, "list view")
    window.show_covers(True)
    _fits(window, application, "sleeve view")
    window.open_album_at(window._model.index(0, 0))
    assert window._album_pane.isVisible(), "the album pane opened"
    _fits(window, application, "sleeve view with an album open")


def test_the_scale_is_asked_for_where_none_is() -> None:
    """An environment saying nothing is given the interface scale."""
    environment: dict[str, str] = {}
    use_interface_scale(environment)
    assert environment[SCALE_VARIABLE] == str(INTERFACE_SCALE)


def test_a_scale_already_asked_for_is_left_alone() -> None:
    """Somebody who set their own scale keeps it."""
    environment = {SCALE_VARIABLE: CHOSEN_ELSEWHERE}
    use_interface_scale(environment)
    assert environment[SCALE_VARIABLE] == CHOSEN_ELSEWHERE
