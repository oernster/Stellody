"""Handing an address to the machine; text to the clipboard.

Qt is never stood in for here. The browser is kept out of the way by
registering a handler for the scheme, which is Qt's own supported means of
saying where an address should go: `openUrl` routes to the handler and answers
that it was taken, so the real call is made and no page opens on anybody's
desktop.

The refusal answer is measured rather than arranged. An empty address is one
Qt declines on its own, without asking the operating system anything, so the
False branch is reached by the real code path.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest
from PySide6.QtCore import QObject, QUrl, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QApplication

from stellody.infrastructure import browsing
from stellody.infrastructure.browsing import SystemBrowser, SystemClipboard

# The address used wherever a test needs one the machine will never reach.
# `.invalid` is reserved for exactly this, so a mistake in a handler cannot
# put a real request on the wire.
SOMEWHERE = "https://example.invalid/search?q=Autechre%20Amber"


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication, since these are Qt objects. Qt is never mocked."""
    existing = QApplication.instance()
    return existing or QApplication([])


class Catcher(QObject):
    """Takes the addresses Qt would otherwise give to a browser."""

    def __init__(self) -> None:
        super().__init__()
        self.seen: list[str] = []

    @Slot(QUrl)
    def caught(self, url: QUrl) -> None:
        """Record the address exactly as Qt carried it."""
        self.seen.append(url.toString(QUrl.ComponentFormattingOption.FullyEncoded))


@pytest.fixture
def catcher(application: QApplication):
    """Stand where the browser would, for the length of one test."""
    receiver = Catcher()
    QDesktopServices.setUrlHandler("https", receiver, "caught")
    yield receiver
    QDesktopServices.unsetUrlHandler("https")


class TestOpeningAnAddress:
    def test_the_machine_is_given_the_address_it_was_handed(self, catcher) -> None:
        """Nothing is added to it and nothing is taken away. NFR-S-PRIV-001."""
        SystemBrowser().open(SOMEWHERE)
        assert catcher.seen == [SOMEWHERE]

    def test_the_spaces_stay_encoded_on_the_way_out(self, catcher) -> None:
        """Measured on 2026-09-07: a literal plus is shown as a plus by one
        shop and read as a space by the rest, so the domain encodes by hand
        and this must not undo it."""
        SystemBrowser().open(SOMEWHERE)
        assert "%20" in catcher.seen[0]

    def test_a_machine_that_took_it_is_reported_as_having_taken_it(
        self, catcher
    ) -> None:
        """FR-S13: the answer is what happened, not what was hoped."""
        assert SystemBrowser().open(SOMEWHERE) is True

    def test_a_machine_that_would_not_take_it_says_so_rather_than_raising(
        self, application: QApplication
    ) -> None:
        """An address Qt declines on its own, so no browser is consulted.

        A listener on a machine with nothing registered for the scheme is an
        ordinary thing to be told about; it ends nothing.
        """
        assert SystemBrowser().open("") is False


class TestPuttingTextWhereAPasteFindsIt:
    def test_the_text_is_on_the_clipboard_afterwards(
        self, application: QApplication
    ) -> None:
        """The real QClipboard, read back through Qt rather than through us."""
        SystemClipboard().put("Autechre - Amber")
        assert QGuiApplication.clipboard().text() == "Autechre - Amber"

    def test_a_second_list_replaces_the_first(self, application: QApplication) -> None:
        """FR-S14: what is copied is what was ticked, never the two joined."""
        clipboard = SystemClipboard()
        clipboard.put("Autechre - Amber")
        clipboard.put("Boards of Canada - Geogaddi")
        assert QGuiApplication.clipboard().text() == "Boards of Canada - Geogaddi"

    def test_a_machine_with_no_clipboard_is_answered_by_doing_nothing(
        self, monkeypatch: pytest.MonkeyPatch, application: QApplication
    ) -> None:
        """Drives the guard in this process; the test below proves it is real.

        Qt itself is untouched: what is replaced is the one lookup this module
        performs, so the branch under test is ours rather than Qt's.
        """
        monkeypatch.setattr(
            browsing.QGuiApplication, "clipboard", staticmethod(lambda: None)
        )
        SystemClipboard().put("nobody will ever see this")


NO_CLIPBOARD = """
from PySide6.QtGui import QGuiApplication
from stellody.infrastructure.browsing import SystemClipboard

assert QGuiApplication.instance() is None
assert QGuiApplication.clipboard() is None
SystemClipboard().put("nobody will ever see this")
print("survived")
"""


def test_a_machine_with_no_clipboard_is_a_real_condition_and_not_a_guess(
    tmp_path: pathlib.Path,
) -> None:
    """The guard above is proved to catch something, in a fresh process.

    Measured on 2026-09-08: with no QGuiApplication built, `clipboard()`
    answers None rather than raising. A test in this process cannot reach that
    state, since the suite shares one application, so it is reached in another
    one. Without this the guard could be removed and every test would still
    pass.
    """
    script = tmp_path / "no_clipboard.py"
    script.write_text(NO_CLIPBOARD, encoding="utf-8")
    # A script is run from its own directory rather than from this one, so the
    # package is named on the path instead of being assumed to be found.
    root = pathlib.Path(__file__).resolve().parents[2]
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH=str(root))
    finished = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=str(root),
        env=environment,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr
    assert "survived" in finished.stdout
