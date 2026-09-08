"""Handing an address to whatever the machine opens pages with.

**This opens no connection and is not in the offline guard's list for a
reason.** Stellody does not fetch the page: it asks the operating system to
give the address to the browser the listener already uses, which is the same
act as clicking a link in any other application. Everything after that happens
in the browser, under the listener's own cookies, on their own account, with
Stellody neither watching nor able to.

What goes out is the shop's own template with an artist and an album put into
it; nothing else. NFR-S-PRIV-001 states that; the domain builds it; this
merely posts it.

**A refusal is reported rather than raised.** A machine with no browser is an
ordinary thing for a listener to be told about; so is one that declines.
Neither is a reason to end anything. Qt answers with a boolean, so this does
too. FR-S13.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication


class SystemBrowser:
    """Opens an address in whatever the machine calls its browser."""

    def open(self, address: str) -> bool:
        """True where the machine took it; False where it would not."""
        return QDesktopServices.openUrl(QUrl(address))


class SystemClipboard:
    """Puts plain text where a paste will find it."""

    def put(self, text: str) -> None:
        """Replace whatever is on the clipboard with this.

        A machine with no clipboard at all is answered by doing nothing rather
        than by failing: the offscreen platform is one, so this is the case
        every test run is in.
        """
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(text)
