"""The repair screen's stand-in store holds a pin once, as the real store does.

Accepting everything over more than one album sends a batch naming the same pin
more than once. The real table keys on album, file and field, so it holds each
pin once with the later value; the stand-in kept every copy, so an album's reset
read five files where the real store holds three. The real store's answer is
taken as the expected one rather than restated here.
"""

from __future__ import annotations

import pathlib

from repair_support import MemoryStore

from stellody.domain.overrides import Override, OverrideField
from stellody.infrastructure.store import SqliteLibraryStore

ALBUM = "0123456789abcdef"
FILE = "H:/Music/Portishead/Dummy/01 Mysterons.flac"


def _keyed(held: tuple[Override, ...]) -> list[Override]:
    """Pins in key order, since the real store reads them back sorted."""
    return sorted(held, key=lambda item: (item.album, item.path, str(item.field)))


def test_a_pin_named_twice_in_one_batch_is_held_once_with_the_later_value(
    tmp_path: pathlib.Path,
) -> None:
    batch = (
        Override(ALBUM, OverrideField.TITLE, "Early", FILE),
        Override(ALBUM, OverrideField.TITLE, "Late", FILE),
    )
    real = SqliteLibraryStore(str(tmp_path / "library.db"))
    try:
        real.accept_overrides(batch)
        expected = _keyed(real.all_overrides())
    finally:
        real.close()
    stand_in = MemoryStore()
    stand_in.accept_overrides(batch)
    assert _keyed(stand_in.all_overrides()) == expected
