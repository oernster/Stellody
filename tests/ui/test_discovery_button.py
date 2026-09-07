"""Where the discovery button sits; whether the keyboard reaches it.

A control the keyboard cannot reach is a control half the people using this
application do not have, so its place in the ring is asserted rather than
assumed to follow from where it was drawn.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from stellody.ui.toolbar import DISCOVER_TOOLTIP, LibraryTray


def make_tray(parent: QWidget, **wiring) -> LibraryTray:
    """A tray with nothing behind any of its buttons."""
    return LibraryTray(
        parent,
        choose_folder=lambda: None,
        toggle_theme=lambda: None,
        show_guide=lambda: None,
        show_about=lambda: None,
        **wiring,
    )


def test_discovery_sits_before_the_theme_button(application) -> None:
    """After the separator and left of theme, ruled on 2026-09-06.

    Discovery is a library action rather than a sound control; the separator is already the line between those two ideas.
    """
    holder = QWidget()
    tray = make_tray(holder)
    row = tray.layout()
    order = [row.itemAt(index).widget() for index in range(row.count())]
    placed = [widget for widget in order if widget is not None]
    assert placed.index(tray.discover_button) == placed.index(tray.separator) + 1
    assert placed.index(tray.discover_button) == placed.index(tray.theme_button) - 1


def test_discovery_is_reachable(application) -> None:
    """The ring visits it, in the place it is drawn."""
    holder = QWidget()
    tray = make_tray(holder)
    stops = tray.ring_stops()
    assert tray.discover_button in stops
    assert stops.index(tray.discover_button) == stops.index(tray.theme_button) - 1
    assert stops.index(tray.discover_button) == stops.index(tray.mute_button) + 1


def test_the_button_says_what_it_is_for(application) -> None:
    """A picture-only button says nothing without one."""
    holder = QWidget()
    tray = make_tray(holder)
    assert tray.discover_button.toolTip() == DISCOVER_TOOLTIP


def test_pressing_it_asks_for_the_dialog(application) -> None:
    """The tray holds no dialog; it says that one was asked for."""
    asked: list[bool] = []
    holder = QWidget()
    tray = make_tray(holder, open_discovery=lambda: asked.append(True))
    tray.discover_button.click()
    assert asked == [True]


def test_it_carries_artwork(application) -> None:
    """The asset is committed, so a button with no picture is a defect."""
    holder = QWidget()
    tray = make_tray(holder)
    assert not tray.discover_button.icon().isNull()
