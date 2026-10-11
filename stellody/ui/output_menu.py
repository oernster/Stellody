"""The list of output devices, as a menu: one home for its words and its lines.

`OUTPUTS.md` FR-O02 to FR-O06, FR-O14 and FR-O17. The same list appears in two
places, popped up from the button on the bottom strip and as a submenu of the
Sound menu, so one function fills both from the transport's entries. Two
builders would be two lists that could come to disagree.

How the list lifts, closes and answers the keyboard (FR-O18) is shared with the
visualiser's styles, so it lives in `lift_menu.py`; what is here is what is
particular to devices.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QMenu

from stellody.domain.outputs import OutputChoice, OutputEntry
from stellody.ui.lift_menu import Line, fill_choices

OUTPUT_TOOLTIP = "Choose the output device"
SYSTEM_DEFAULT_LABEL = "System default"
# A missing choice stays in the list, saying why it cannot be heard (FR-O14).
NOT_CONNECTED_LABEL = "{name} (not connected)"

Choose = Callable[[OutputChoice], None]


def entry_text(entry: OutputEntry) -> str:
    """The words one line of the list shows."""
    if entry.choice.follows_default:
        return SYSTEM_DEFAULT_LABEL
    if not entry.connected:
        return NOT_CONNECTED_LABEL.format(name=entry.label)
    return entry.label


def fill_output_menu(
    menu: QMenu, entries: tuple[OutputEntry, ...], choose: Choose
) -> None:
    """Replace the menu's lines with these entries, the chosen one marked (FR-O06).

    Safe while the menu is open, which is how a device connected with the list
    up appears in it at once (FR-O13).
    """
    fill_choices(
        menu,
        tuple(
            Line(
                entry_text(entry),
                entry.chosen,
                lambda choice=entry.choice: choose(choice),
            )
            for entry in entries
        ),
    )
