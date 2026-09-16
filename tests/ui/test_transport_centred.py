"""The transport sits at the middle of the tray, whatever sits at its two ends.

Reported by Oliver on a 13 inch 4K screen: previous, play, stop and next stood
left of centre. A stretch either side of them centres them in what the two end
groups leave OVER, which is the middle of the tray only while those groups are
the same width. They are not: discovery's bars, its button, a rule, the
appearance toggle and Help outweigh choosing, filtering and searching. Measured
offscreen at 1800 pixels before the fix: 91 pixels left of the middle, still
42 with the search box open.

Built on its own rather than inside a window, for the reason the bottom strip's
test gives: the offscreen platform will not grow a window past the screen it
reports, so a tray measured through one is only measured at that width.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtWidgets import QApplication, QMenu
from tray_support import CENTRE_SLACK_PX, WIDE_STRIP_PX

from stellody.ui.toolbar import LibraryTray

# Down from wide to the narrowest the tray will lay itself out at.
NARROWING_PX = (2400, WIDE_STRIP_PX, 1600, 1400)


@pytest.fixture
def tray(application: QApplication) -> Iterator[LibraryTray]:
    """A tray on its own, shown so its layout runs."""
    made = LibraryTray(None, lambda: None, lambda: None, QMenu())
    made.show()
    yield made
    made.deleteLater()


def _laid_out(application: QApplication, tray: LibraryTray, width: int) -> None:
    """Size the tray to a width and let its layout catch up."""
    tray.resize(width, tray.sizeHint().height())
    application.processEvents()


def _transport_middle(tray: LibraryTray) -> int:
    """Halfway between the left edge of previous and the right edge of next."""
    first, *_, last = tray.transport_stops()
    return (first.geometry().left() + last.geometry().right() + 1) // 2


def test_the_transport_sits_at_the_middle_of_a_wide_tray(
    application: QApplication, tray: LibraryTray
) -> None:
    """Not the middle of what the two end groups leave over."""
    _laid_out(application, tray, WIDE_STRIP_PX)
    assert abs(_transport_middle(tray) - WIDE_STRIP_PX // 2) <= CENTRE_SLACK_PX


def test_opening_the_search_box_does_not_move_it(
    application: QApplication, tray: LibraryTray
) -> None:
    """The box widens the left group, which must not carry the transport with it."""
    tray.set_searching(True)
    _laid_out(application, tray, WIDE_STRIP_PX)
    assert abs(_transport_middle(tray) - WIDE_STRIP_PX // 2) <= CENTRE_SLACK_PX


@pytest.mark.parametrize("searching", (False, True))
def test_nothing_is_sat_on_however_narrow_it_gets(
    application: QApplication, tray: LibraryTray, searching: bool
) -> None:
    """Where there is no room to centre, the transport gives way rather than
    being covered by either end."""
    tray.set_searching(searching)
    for width in NARROWING_PX:
        _laid_out(application, tray, max(width, tray.minimumSizeHint().width()))
        first, *_, last = tray.transport_stops()
        left = tray.search_box if searching else tray.search_button
        assert left.geometry().right() < first.geometry().left(), f"at {width}"
        assert last.geometry().right() < tray.discovery_bar.geometry().left()
