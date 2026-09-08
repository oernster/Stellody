"""What the composition root actually hands the discovery service.

Written because the opposite went unnoticed: a genre cache was built, tested
and never wired to anything, so every run re-asked every candidate at one
request a second. Every test it had passed, because each tested the cache
rather than whether a run had been given one.

So this asserts the wiring itself, over a real window built the way the
application builds it.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest
from PySide6.QtCore import QEvent

from stellody.application.discovery_ports import NothingRemembered
from stellody.application.shopping import Shopping
from stellody.composition import build_window
from stellody.infrastructure.browsing import SystemBrowser, SystemClipboard
from stellody.infrastructure.discovery_file import FileGenreMemory
from stellody.infrastructure.shop_file import FileShopList
from stellody.infrastructure.store import SqliteLibraryStore


@pytest.fixture
def window(application):
    """The real window over a throwaway store, closed again afterwards."""
    folder = pathlib.Path(tempfile.mkdtemp())
    store = SqliteLibraryStore(str(folder / "t.sqlite3"))
    made = build_window(store)
    yield made
    # Deleted rather than merely closed, with the deletion actually delivered:
    # the suite's own cleanup closes any window still standing, so a window
    # closed a second time writes its settings to a store already shut.
    made.close()
    made.deleteLater()
    application.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    store.close()


def test_a_run_is_given_somewhere_to_remember_what_it_learns(window) -> None:
    """The wiring the cache spent a release without, in silence."""
    memory = window._discovery.memory
    assert isinstance(memory, FileGenreMemory)
    assert not isinstance(memory, NothingRemembered)


def test_the_results_are_given_something_to_shop_with(window) -> None:
    """The same defect a second time, reported 2026-09-08.

    The composition built the use case and named it to the window, which took
    the argument and never passed it on. Both controls under the results were
    then disabled whatever anybody ticked, since a window holding none offers
    neither. Every test of the shops passed throughout: each built the dialog
    with a use case by hand, which is the one thing the application did not do.

    The ports are named rather than merely counted, because a window wired to
    stand-ins would satisfy a test that only asked whether something was there.
    """
    shopping = window._shopping
    assert isinstance(shopping, Shopping)
    assert isinstance(shopping.shops, FileShopList)
    assert isinstance(shopping.opener, SystemBrowser)
    assert isinstance(shopping.clipboard, SystemClipboard)
