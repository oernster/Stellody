"""A scan of a music folder that is not there changes nothing.

Measured on 2026-09-10: a root on a drive that is not connected walks as no
folders with no error. A scan left to carry on would therefore find every file
in the store missing and mark it absent; since a load now leaves absent folders
out, the next start would open on an empty library. An unplugged drive is not
a library somebody deleted, so the scan is refused before it touches anything.
"""

from __future__ import annotations

import pytest
from fakes import FakeProbe, FakeStore, FakeTextReader, FakeWalker

from stellody.application.scan import LibraryUnreachableError, ScanLibrary

ROOT = "H:/Music"


def _unplugged() -> tuple[ScanLibrary, FakeWalker, FakeStore]:
    """A scanner whose music folder is not there."""
    walker = FakeWalker(())
    walker.root_is_there = False
    store = FakeStore()
    scanner = ScanLibrary(walker, FakeProbe({}), FakeTextReader(None), store)
    return scanner, walker, store


def test_a_root_that_is_not_there_is_refused() -> None:
    scanner, _, _ = _unplugged()

    with pytest.raises(LibraryUnreachableError) as raised:
        scanner.run(ROOT)

    assert ROOT in str(raised.value)
    assert "nothing in the library was changed" in str(raised.value)


def test_nothing_is_marked_absent() -> None:
    """The whole point: the remembered library survives a missing drive."""
    scanner, _, store = _unplugged()

    with pytest.raises(LibraryUnreachableError):
        scanner.run(ROOT)

    assert store.absent_calls == []
    assert store.saved == []


def test_the_walk_is_never_started() -> None:
    """Refused before the count as well, so no progress is ever reported."""
    scanner, walker, _ = _unplugged()

    with pytest.raises(LibraryUnreachableError):
        scanner.run(ROOT)

    assert walker.counted == []
    assert walker.roots == []
