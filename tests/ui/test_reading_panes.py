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

from stellody.domain.health import IssueKind, LibraryIssue
from stellody.shared import resources
from stellody.ui.dialogs import AboutDialog, LicenceDialog
from stellody.ui.health import HealthDialog
from stellody.ui.theme import Mode, stylesheet

ISSUE_COUNT = 40
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
