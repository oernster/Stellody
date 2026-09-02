"""A pane is chrome, so it is never clicked into and rarely tabbed into.

Reported as a useless border that could be clicked, in About and in Library
health. Measured: every read-only text view carried Qt's default StrongFocus,
so a click anywhere in the page focused the pane and drew the ring round it.

Two properties are asserted here and the first is the one a reader notices: a
click never focuses a reading pane. The second is that the stop itself is
conditional, so a page that fits its viewport is not on the ring at all.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTextBrowser

from stellody.application.scan import ScanReport
from stellody.domain.changes import LibraryChange
from stellody.domain.health import IssueKind, LibraryIssue
from stellody.domain.identity import AlbumIdentity
from stellody.shared import resources
from stellody.ui.bottom_tray import REPAIR_TOOLTIP
from stellody.ui.dialogs import AboutDialog, LicenceDialog
from stellody.ui.health import HealthDialog
from stellody.ui.scan_summary import ScanSummaryDialog
from stellody.ui.theme import Mode, stylesheet

ISSUE_COUNT = 40
NEW_ALBUM_COUNT = 40
CLICK_AT = QPoint(20, 20)


def issues() -> tuple[LibraryIssue, ...]:
    """Enough reported damage that the health page has to scroll."""
    return tuple(
        LibraryIssue(
            kind=IssueKind.DUPLICATE_TRACK_NUMBER,
            album=f"Album {number}",
            detail="two tracks claim track 3",
            paths=(f"H:/music/{number}.flac",),
        )
        for number in range(ISSUE_COUNT)
    )


def a_busy_scan() -> tuple[LibraryChange, ScanReport]:
    """A scan that found enough to make its report overflow."""
    change = LibraryChange(
        new_albums=tuple(
            AlbumIdentity(album_artist=f"Artist {number}", title=f"Album {number}")
            for number in range(NEW_ALBUM_COUNT)
        ),
        # Both lists are capped in the report, so one long list alone no longer
        # fills the dialog now that it is sized for doubled text. Overflow is
        # what this fixture exists to produce, so it supplies both.
        gone_albums=tuple(
            AlbumIdentity(album_artist=f"Gone {number}", title=f"Departed {number}")
            for number in range(NEW_ALBUM_COUNT)
        ),
        new_tracks=NEW_ALBUM_COUNT,
        gone_tracks=NEW_ALBUM_COUNT,
        total_albums=NEW_ALBUM_COUNT,
        total_tracks=NEW_ALBUM_COUNT,
        previous_albums=1,
    )
    return change, ScanReport(issues=issues())


def shown(application: QApplication, dialog):
    """A dialog on screen, with its text view laid out and measured."""
    application.setStyleSheet(stylesheet(Mode.DARK))
    dialog.show()
    application.processEvents()
    return dialog, dialog.findChild(QTextBrowser)


@pytest.fixture
def overflowing(application: QApplication):
    """The three reading panes that hold more than fits."""
    return {
        "About": shown(application, AboutDialog()),
        "Licence": shown(
            application, LicenceDialog("Model", resources.model_licence_path())
        ),
        "Health": shown(application, HealthDialog(issues())),
        "Scan summary": shown(application, ScanSummaryDialog(*a_busy_scan())),
    }


def test_clicking_a_reading_pane_never_focuses_it(overflowing) -> None:
    """The reported fault. A ring earned by a click marks nothing to act on."""
    for name, (_dialog, view) in overflowing.items():
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=CLICK_AT)
        assert not view.hasFocus(), f"{name}: a click focused the pane"


def test_a_page_that_scrolls_is_still_reachable_by_tab(overflowing) -> None:
    """Losing the stop entirely would leave a long text unreadable by keyboard."""
    for name, (_dialog, view) in overflowing.items():
        assert view.verticalScrollBar().maximum() > 0, f"{name}: expected overflow"
        assert view.focusPolicy() == Qt.FocusPolicy.TabFocus, name


def test_a_page_that_fits_is_not_a_stop_at_all(application: QApplication) -> None:
    """It scrolls nowhere, so it is not something to act on."""
    _dialog, view = shown(application, HealthDialog(()))
    assert view.verticalScrollBar().maximum() == 0, "expected it to fit"
    assert view.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_no_viewport_is_reachable_behind_its_own_pane(overflowing) -> None:
    """The viewport is a separate focusable child, so it is set apart."""
    for name, (_dialog, view) in overflowing.items():
        assert view.viewport().focusPolicy() == Qt.FocusPolicy.NoFocus, name


def test_the_stop_is_recomputed_rather_than_decided_once(
    application: QApplication,
) -> None:
    """The same page overflows or not depending on how the window was sized."""
    dialog, view = shown(application, HealthDialog(issues()))
    assert view.focusPolicy() == Qt.FocusPolicy.TabFocus
    dialog.resize(dialog.width(), dialog.height() * 8)
    application.processEvents()
    if view.verticalScrollBar().maximum() == 0:
        assert view.focusPolicy() == Qt.FocusPolicy.NoFocus, "it fits now"


def test_the_repair_button_sits_above_the_report_it_would_repair(
    application: QApplication,
) -> None:
    """Above the scrolling area rather than inside it, so it cannot scroll off."""
    dialog, view = shown(application, HealthDialog(issues()))
    row = dialog.layout()
    positions = []
    for index in range(row.count()):
        item = row.itemAt(index)
        inner = item.layout()
        if inner is not None and inner.indexOf(dialog.repair_button) >= 0:
            positions.append(("button", index))
        if item.widget() is view:
            positions.append(("report", index))
    order = [name for name, _index in positions]
    assert order == ["button", "report"], "the button is laid out before the report"


def test_the_repair_button_does_not_move_when_the_report_is_scrolled(
    application: QApplication,
) -> None:
    """The reported requirement: always at the top, whatever the reader does."""
    dialog, view = shown(application, HealthDialog(issues()))
    bar = view.verticalScrollBar()
    assert bar.maximum() > 0, "expected a report long enough to scroll"
    before = dialog.repair_button.mapTo(dialog, QPoint(0, 0))
    bar.setValue(bar.maximum())
    application.processEvents()
    assert bar.value() > 0, "the report really did scroll"
    assert dialog.repair_button.mapTo(dialog, QPoint(0, 0)) == before


def test_the_repair_button_reads_its_wording_from_one_home(
    application: QApplication,
) -> None:
    """The dialog's control and the strip's cannot say different things.

    A dialog told there is nothing to act on keeps it disabled, exactly as the
    strip does, since the screen it opens would say nothing.
    """
    dialog, _view = shown(application, HealthDialog(issues()))
    assert not dialog.repair_button.isEnabled()
    assert dialog.repair_button.toolTip() == REPAIR_TOOLTIP, "one wording, one home"
    assert not dialog.repair_button.icon().isNull(), "drawn, not merely reserved"


def test_the_repair_button_is_offered_once_there_is_something_to_do(
    application: QApplication,
) -> None:
    dialog, _view = shown(application, HealthDialog(issues(), can_repair=True))
    assert dialog.repair_button.isEnabled()
