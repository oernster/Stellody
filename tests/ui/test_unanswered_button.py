"""The tray button listing whom a run could not answer for, held to keeb.

Always in the tray beside the discovery bars and disabled while nothing is
owed (Oliver's ruling), so it wears the house's three ring states: none at
rest, green when focused, a permanent red ring while disabled. A disabled
stop is passed over by the keyboard ring; an enabled one is reached between
the transport and the discover button, which is where it is drawn.

The rings are read off the paint under the real stylesheet. An offscreen grab
settles what the sheet paints; whether it reads at Oliver's display scaling is
for the built application.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMenu, QWidget
from tray_support import WIDE_STRIP_PX

from stellody.ui import shortfall
from stellody.ui.ring import is_a_stop
from stellody.ui.theme import Mode, palette_for, stylesheet
from stellody.ui.toolbar import LibraryTray


@pytest.fixture
def tray(application: QApplication) -> Iterator[LibraryTray]:
    """A tray on its own in the dark appearance, laid out wide and active."""
    application.setStyleSheet(stylesheet(Mode.DARK))
    made = LibraryTray(None, lambda: None, lambda: None, QMenu())
    made.resize(WIDE_STRIP_PX, made.sizeHint().height())
    made.show()
    made.activateWindow()
    application.processEvents()
    yield made
    made.deleteLater()
    application.setStyleSheet("")


def _border(button: QWidget) -> str:
    """The colour along the middle of the button's top edge."""
    shot = button.grab().toImage()
    return shot.pixelColor(shot.width() // 2, 0).name()


def test_it_is_built_disabled_wearing_its_artwork(tray: LibraryTray) -> None:
    """Present before any run, inert until one leaves somebody unanswered."""
    button = tray.unanswered_button
    assert button.isVisible()
    assert not button.isEnabled()
    assert not button.icon().isNull()
    assert button.toolTip() == shortfall.NOTHING_UNANSWERED_TIP


def test_disabled_it_wears_the_permanent_red_ring(tray: LibraryTray) -> None:
    """The red border IS the disabled state, with nothing hovered."""
    assert _border(tray.unanswered_button) == palette_for(Mode.DARK).danger


def test_enabled_it_rests_without_a_ring(
    application: QApplication, tray: LibraryTray
) -> None:
    """No ring at rest; the green belongs to focus and hover alone."""
    button = tray.unanswered_button
    button.setEnabled(True)
    application.processEvents()
    colour = palette_for(Mode.DARK)
    assert _border(button) not in (colour.danger, colour.ring)


def test_focused_by_tab_it_wears_the_green_ring(
    application: QApplication, tray: LibraryTray
) -> None:
    """Focus is confirmed before the pixel is believed."""
    button = tray.unanswered_button
    button.setEnabled(True)
    button.setFocus(Qt.FocusReason.TabFocusReason)
    application.processEvents()
    assert button.hasFocus(), "a focus that went nowhere would read as no ring"
    assert _border(button) == palette_for(Mode.DARK).ring


def test_the_ring_passes_it_over_while_disabled(tray: LibraryTray) -> None:
    """A stop the user can do nothing with is not a stop."""
    assert not is_a_stop(tray.unanswered_button, tray.window())


def test_the_ring_reaches_it_once_enabled(tray: LibraryTray) -> None:
    """Named between discover and the toggle, which is where it is drawn."""
    button = tray.unanswered_button
    button.setEnabled(True)
    assert is_a_stop(button, tray.window())
    stops = tray.ring_stops()
    assert stops.index(button) == stops.index(tray.discover_button) + 1
    assert stops.index(button) == stops.index(tray.theme_button) - 1


def test_the_ring_reads_the_tray_left_to_right(
    application: QApplication, tray: LibraryTray
) -> None:
    """The declared order cannot lie about where the stops are drawn."""
    tray.unanswered_button.setEnabled(True)
    application.processEvents()
    drawn = [stop for stop in tray.ring_stops() if stop.isVisible()]
    lefts = [stop.mapTo(tray, stop.rect().center()).x() for stop in drawn]
    assert lefts == sorted(lefts)


def test_enabling_it_moves_nothing(
    application: QApplication, tray: LibraryTray
) -> None:
    """It holds its place while disabled, so a run ending shuffles nothing."""
    held = (*tray.transport_stops(), tray.unanswered_button, tray.discover_button)
    before = [widget.geometry() for widget in held]
    tray.unanswered_button.setEnabled(True)
    application.processEvents()
    assert [widget.geometry() for widget in held] == before


def test_it_closes_discovery_s_group_inside_the_rule(tray: LibraryTray) -> None:
    """Right of discover, left of the rule ruling discovery off from the rest."""
    place = tray.unanswered_button.geometry()
    assert tray.discover_button.geometry().right() < place.left()
    assert place.right() < tray.library_separator.geometry().left()
    assert tray.library_separator.geometry().right() < tray.theme_button.x()
