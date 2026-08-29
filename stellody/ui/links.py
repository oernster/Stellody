"""Handing a link to whatever the desktop uses to open one.

One function, in its own module, so it is a seam a test can stand in front of.
The alternative is calling Qt's opener directly from the window, which would
leave no way to prove the right address is asked for without either mocking Qt
or opening a browser in the middle of a test run. Neither is acceptable here.

Nothing in this module fetches anything. The address is passed outward and the
desktop decides what to do with it, so the application still opens no
connection of its own.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def open_externally(address: str) -> bool:
    """Ask the desktop to open this address; False when it declined to.

    A refusal is reported rather than raised: failing to open a browser is
    worth telling the user about and is not worth ending anything over.
    """
    return QDesktopServices.openUrl(QUrl(address))
