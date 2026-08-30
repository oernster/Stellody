"""What every test of the setup program needs.

The real QApplication lives here rather than in one test module, so a file
split out of another does not lose it. Qt is never mocked; it draws offscreen.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication for the whole session."""
    existing = QApplication.instance()
    return existing or QApplication([])
