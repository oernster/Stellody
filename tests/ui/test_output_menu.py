"""The Sound menu's Output device submenu. `OUTPUTS.md` FR-O17.

The same lines as the strip's list, in the same order with the same mark,
because one function fills both.
"""

from __future__ import annotations

from output_support import (
    FOCUSRITE,
    choosing,
    chose,
    devices,
    expected_lines,
    lines,
    marked,
)
from playback_support import player, window
from PySide6.QtWidgets import QMenu

from stellody.domain.outputs import OutputDevice, output_list
from stellody.ui.output_menu import entry_text, fill_output_menu

__all__ = ["choosing", "devices", "player", "window"]


def test_the_menu_mirrors_the_list(choosing) -> None:
    choosing.choose_output(chose(FOCUSRITE))
    assert lines(choosing._output_menu) == expected_lines()
    assert marked(choosing._output_menu) == [FOCUSRITE.name]
    assert lines(choosing._output_menu) == lines(
        choosing._bottom_tray.sound.output_menu
    )


def test_it_follows_exclusive_output(choosing) -> None:
    """Beside Exclusive output, which keeps its place beside the equalizer."""
    sound_menu = choosing._output_menu.menuAction().associatedObjects()[0]
    names = [action.text() for action in sound_menu.actions()]
    assert names.index("E&xclusive output") + 1 == names.index("Output &device")


def test_choosing_from_the_menu_chooses(choosing) -> None:
    menu = choosing._output_menu
    menu.actions()[lines(menu).index(FOCUSRITE.name)].trigger()
    assert choosing._transport.output_choice == chose(FOCUSRITE)


def test_an_ampersand_in_a_name_is_shown_rather_than_eaten(application) -> None:
    """A single one would mark a shortcut and vanish from the line."""
    named = OutputDevice(identity="{rock}", name="Rock & Roll")
    entries = output_list((named,), chose(named))
    menu = QMenu()
    fill_output_menu(menu, entries, lambda _choice: None)
    assert menu.actions()[1].iconText() == entry_text(entries[1])
