"""The button that opens the list of output devices. `OUTPUTS.md`.

FR-O01 where it sits, FR-O02 what a press opens, FR-O03 and FR-O05 what the
list says, FR-O06 its mark, FR-O18 the keyboard, FR-O19 the tooltip.
"""

from __future__ import annotations

from output_support import (
    FOCUSRITE,
    SPEAKERS,
    choosing,
    chose,
    devices,
    expected_lines,
    lines,
    marked,
)
from playback_support import player, window
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from stellody.domain.outputs import SYSTEM_DEFAULT
from stellody.ui.output_menu import OUTPUT_TOOLTIP, SYSTEM_DEFAULT_LABEL, pop_up_above

__all__ = ["choosing", "devices", "player", "window"]


def test_the_button_sits_after_the_rule_before_exclusive(choosing) -> None:
    """FR-O01: volume, mute, the rule, choose device, exclusive, equalizer."""
    sound = choosing._bottom_tray.sound
    assert sound.parts() == (
        sound.volume_button,
        sound.mute_button,
        sound.stream_separator,
        sound.output_button,
        sound.exclusive_button,
        sound.equaliser_button,
    )


def test_a_press_opens_the_list(choosing) -> None:
    """FR-O02: a vertical list against the button."""
    sound = choosing._bottom_tray.sound
    sound.output_button.click()
    assert sound.output_menu.isVisible()
    assert lines(sound.output_menu) == expected_lines()


def press_over(popup, where: QPoint) -> None:
    """A press inside the popup's window at a point given on the screen."""
    QTest.mousePress(popup, Qt.MouseButton.LeftButton, pos=popup.mapFromGlobal(where))


def test_a_second_press_closes_it(choosing) -> None:
    """FR-O20. The real shape of it: the press takes the list down, the click follows.

    Reported by Oliver on 2026-09-20 as a list the button would not close.
    Reproduced the same day: Qt closes a menu on a press outside it, so the
    press on the button put the list down and the click behind it opened a
    fresh one. Pressing the button is therefore how this is asked, since
    calling the opener twice never involves Qt closing anything and so passed
    while the application did not.
    """
    choosing.show()
    sound = choosing._bottom_tray.sound
    pop_up_above(sound.output_menu, sound.output_button)
    assert sound.output_menu.isVisible()
    press_over(sound.output_menu, sound.output_button.mapToGlobal(QPoint(0, 0)))
    assert not sound.output_menu.isVisible(), "the press closed it"
    pop_up_above(sound.output_menu, sound.output_button)
    assert not sound.output_menu.isVisible(), "and the click behind it left it down"
    pop_up_above(sound.output_menu, sound.output_button)
    assert sound.output_menu.isVisible(), "while a fresh press puts it back up"
    sound.output_menu.hide()


def test_a_press_anywhere_else_closes_it_without_swallowing_the_next(
    choosing,
) -> None:
    """FR-O20: only a press on the button itself is replayed onto it."""
    choosing.show()
    sound = choosing._bottom_tray.sound
    pop_up_above(sound.output_menu, sound.output_button)
    press_over(sound.output_menu, choosing.mapToGlobal(choosing.rect().topLeft()))
    assert not sound.output_menu.isVisible()
    pop_up_above(sound.output_menu, sound.output_button)
    assert sound.output_menu.isVisible(), "the next press is a fresh one"
    sound.output_menu.hide()


def test_choosing_a_line_leaves_the_list_able_to_open_again(choosing) -> None:
    """FR-O20: a press inside closes nothing, so it is no dismissal."""
    choosing.show()
    sound = choosing._bottom_tray.sound
    pop_up_above(sound.output_menu, sound.output_button)
    press_over(sound.output_menu, sound.output_menu.mapToGlobal(QPoint(1, 1)))
    sound.output_menu.hide()
    pop_up_above(sound.output_menu, sound.output_button)
    assert sound.output_menu.isVisible()
    sound.output_menu.hide()


def test_system_default_leads_and_is_marked_to_begin_with(choosing) -> None:
    """FR-O03, FR-O06: today's behaviour for anybody who never chooses."""
    menu = choosing._bottom_tray.sound.output_menu
    assert lines(menu)[0] == SYSTEM_DEFAULT_LABEL
    assert marked(menu) == [SYSTEM_DEFAULT_LABEL]


def test_the_choice_is_marked(choosing) -> None:
    """FR-O06."""
    choosing.choose_output(chose(FOCUSRITE))
    assert marked(choosing._bottom_tray.sound.output_menu) == [FOCUSRITE.name]


def test_pressing_a_line_chooses_it(choosing) -> None:
    """FR-O07 reached from the list itself."""
    menu = choosing._bottom_tray.sound.output_menu
    menu.actions()[lines(menu).index(FOCUSRITE.name)].trigger()
    assert choosing._transport.output_choice == chose(FOCUSRITE)


def test_the_list_is_keyboard_driven(choosing) -> None:
    """FR-O18: the arrows move along it; Enter chooses."""
    sound = choosing._bottom_tray.sound
    pop_up_above(sound.output_menu, sound.output_button)
    QTest.keyClick(sound.output_menu, Qt.Key.Key_Down)
    QTest.keyClick(sound.output_menu, Qt.Key.Key_Down)
    QTest.keyClick(sound.output_menu, Qt.Key.Key_Return)
    assert choosing._transport.output_choice == chose(SPEAKERS)


def test_escape_leaves_the_choice_alone(choosing) -> None:
    """FR-O18."""
    sound = choosing._bottom_tray.sound
    pop_up_above(sound.output_menu, sound.output_button)
    QTest.keyClick(sound.output_menu, Qt.Key.Key_Down)
    QTest.keyClick(sound.output_menu, Qt.Key.Key_Escape)
    assert not sound.output_menu.isVisible()
    assert choosing._transport.output_choice == SYSTEM_DEFAULT


def test_the_ring_stops_on_it_straight_after_mute(choosing) -> None:
    """FR-O18: in its drawn place, the rule being no stop."""
    sound = choosing._bottom_tray.sound
    stops = choosing._bottom_tray.ring_stops()
    assert stops[stops.index(sound.mute_button) + 1] is sound.output_button


def test_the_tooltip_names_the_press(choosing) -> None:
    """FR-O19."""
    assert choosing._bottom_tray.sound.output_button.toolTip() == OUTPUT_TOOLTIP
