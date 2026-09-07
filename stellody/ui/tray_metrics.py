"""What the tray measures, what it says and the button built to those sizes.

Its own module because three widgets need these and only one of them is the
tray: the bottom strip derives its own smaller sizes from them and the showing
controls draw the same hairline. Reaching into `toolbar` for a number is how
that was done before, which made a strip at the foot of the window depend on
the tray at the top of it for no reason beyond where the number happened to
live.

Sizes and words together rather than split, since both answer the same
question: what does this row of buttons look like and say.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QPushButton, QWidget

from stellody.shared import resources
from stellody.ui.icons import plain_icon, struck_through
from stellody.ui.tray_parts import icon_button

# The button is a way in to several things rather than one thing, so it is
# named for the menu it opens rather than for the entry that used to be all
# of it. What each entry does is said by the entry.
HELP_TOOLTIP = "Help"
GUIDE_ENTRY = "Guide"
ABOUT_ENTRY = "About"
UPDATES_ENTRY = "Check for updates"

ICON_PX = 60
BUTTON_PX = 91
TRAY_MARGIN_PX = 6
TRAY_GAP_PX = 6
SEPARATOR_WIDTH_PX = 1
# The line stops short of the tray's own edges, so it reads as a division
# between buttons rather than as a border on the tray.
SEPARATOR_INSET_PX = 12
SEPARATOR_HEIGHT_PX = BUTTON_PX - SEPARATOR_INSET_PX - SEPARATOR_INSET_PX
# Wide enough for an album title rather than for a word, since that is what
# somebody types when they are looking for one.
SEARCH_BOX_PX = 260
# Sized against the buttons beside it rather than against a dialog field:
# a default line edit is a third of a tray button and reads as a mistake.
SEARCH_BOX_HEIGHT_PX = 48
SEARCH_PLACEHOLDER = "Album, artist or track"
# The filter button's own name, said while nothing is being asked for.
FILTER_TOOLTIP = "Filter the library"
DISCOVER_TOOLTIP = "Discover music the library does not hold"
# Said in its place while a run is under way, so one button carries both
# meanings: the thing wanted of a run in progress is to stop it.
STOP_DISCOVERY_TOOLTIP = "Stop looking"
# Said in its place while something is being shown, so what is on screen can
# be read off the control rather than guessed at from what is missing.
FILTERED_TOOLTIP = "Showing {what}"


def tray_button(parent: QWidget, path, tip: str, on_click: Callable) -> QPushButton:
    """One picture-only button at the top tray's own size."""
    return icon_button(parent, path, tip, on_click, BUTTON_PX, ICON_PX)


def show_discovery_running(button: QPushButton, running: bool) -> None:
    """Say on the button itself whether a press starts a run or stops one.

    The picture and the words are set together, in one place, because they are
    one statement: a button wearing the cross while its tooltip offers to start
    a run is worse than either alone. Three separate places used to set the
    tooltip on its own, so the two agreed only by everybody remembering.

    The cross is the same artwork the switches at the foot of the window wear,
    laid over the discovery picture rather than drawn into a second file, so a
    change to it reaches every use of it at once.
    """
    discover = resources.discover_icon_path()
    button.setIcon(
        struck_through(discover, resources.negative_icon_path(), ICON_PX)
        if running
        else plain_icon(discover)
    )
    button.setToolTip(STOP_DISCOVERY_TOOLTIP if running else DISCOVER_TOOLTIP)
