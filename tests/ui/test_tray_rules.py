"""The hairlines that rule each tray off from the library between them.

Both rules are written in the stylesheet, so it would be easy to assume they
draw. Neither did. Qt applies a stylesheet BORDER to a plain `QWidget` subclass
only where `WA_StyledBackground` is set; without it the background is filled
from the sheet and the border is dropped without a word. Both trays carried a
border rule that had never rendered a pixel, the top one for its whole life.

That is why these tests read the paint rather than the stylesheet. Asserting
that the rule is in the sheet is what let the defect stand: the sheet said the
line was there the entire time it was not. So each test grabs the widget and
looks at the row of pixels where the line has to be.

An offscreen grab settles STRUCTURE, never real paint on a real screen: it
proves the paint path puts the border colour on that row. Whether the line is
visible at Oliver's display scaling is a question only the built application
answers.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from stellody.ui.bottom_tray import BottomTray
from stellody.ui.theme import Mode, palette_for, stylesheet
from stellody.ui.toolbar import LibraryTray

# Where in the grab to read. The middle of the strip, so the sample lands on
# the tray's own ground rather than on a button or on the display sitting in it.
SAMPLE_X = 300
HOST_WIDTH_PX = 900
HOST_HEIGHT_PX = 400


@pytest.fixture
def dressed(application: QApplication) -> Iterator[QApplication]:
    """The application wearing the dark appearance, undressed afterwards.

    The sheet is the thing under test, so it has to be on; it is taken off
    again because the fixture that hands out the application is session wide
    and no other test asked to be dressed.
    """
    application.setStyleSheet(stylesheet(Mode.DARK))
    yield application
    application.setStyleSheet("")


def _hosted(*trays: QWidget) -> QWidget:
    """A window holding the trays given, laid out with no gap of its own."""
    host = QWidget()
    host.resize(HOST_WIDTH_PX, HOST_HEIGHT_PX)
    column = QVBoxLayout(host)
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(0)
    for tray in trays:
        column.addWidget(tray)
    column.addStretch(1)
    host.show()
    return host


def _rows(widget: QWidget) -> tuple[str, str]:
    """The colour along the first and last rows of the widget's own paint."""
    shot: QImage = widget.grab().toImage()
    last = shot.height() - 1
    return (
        shot.pixelColor(SAMPLE_X, 0).name(),
        shot.pixelColor(SAMPLE_X, last).name(),
    )


def test_the_top_tray_is_ruled_off_along_its_bottom(dressed: QApplication) -> None:
    """The library below it starts at a line, not at a change of shade."""
    colour = palette_for(Mode.DARK)
    tray = LibraryTray(None, lambda: None, lambda: None, lambda: None, lambda: None)
    host = _hosted(tray)
    assert host is not None
    dressed.processEvents()
    first, last = _rows(tray)
    assert last == colour.border
    # The window's own edge is above it, so it needs no line up there.
    assert first == colour.surface


def test_the_bottom_tray_is_ruled_off_at_both_edges(dressed: QApplication) -> None:
    """It has the library over it, so it is closed at the top as well."""
    colour = palette_for(Mode.DARK)
    tray = BottomTray(None)
    host = _hosted(tray)
    assert host is not None
    dressed.processEvents()
    first, last = _rows(tray)
    assert first == colour.border
    assert last == colour.border


def test_the_visualiser_draws_no_rule_of_its_own(dressed: QApplication) -> None:
    """It sits inside the strip now, so the strip's edges are what rule it off.

    It drew its own top hairline back when it was a full width band. Left in
    place after it moved, that line floated across the middle of the row.
    """
    colour = palette_for(Mode.DARK)
    tray = BottomTray(None)
    host = _hosted(tray)
    assert host is not None
    dressed.processEvents()
    shot: QImage = tray.visualiser.grab().toImage()
    across = (0, shot.width() // 2, shot.width() - 1)
    assert [shot.pixelColor(x, 0).name() for x in across] == [colour.surface] * len(
        across
    )
