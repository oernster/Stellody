"""What the infrastructure suites share: one real QApplication.

Seven suites here each built their own, word for word. A fixture written seven
times is seven fixtures the day one of them is changed, so it lives here and
every suite in this directory is handed it by name.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication, since these are Qt objects. Qt is never mocked."""
    existing = QApplication.instance()
    return existing or QApplication([])
