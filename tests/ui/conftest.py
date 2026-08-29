"""One QApplication for the suite; no window outliving the test that made it.

Closing a window is not destroying it. A window left for the garbage collector
is destroyed at whatever moment Python next collects it, which is typically
inside the NEXT test: measured as an access violation in setStyleSheet, which
repaints every widget the application knows about and walked into a half
destroyed one. Five runs in six.

So every top level widget is destroyed here, deterministically, between tests.
Qt is never mocked; this only makes its lifetimes match the tests'.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication for the whole session."""
    existing = QApplication.instance()
    return existing or QApplication([])


@pytest.fixture(autouse=True)
def _no_window_outlives_its_test(application: QApplication):
    """Destroy anything left on screen once a test is done with it."""
    yield
    for widget in list(application.topLevelWidgets()):
        widget.close()
        widget.deleteLater()
    application.processEvents()
    application.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()
