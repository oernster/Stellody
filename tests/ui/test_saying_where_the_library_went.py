"""What the window says when the library file would not open.

It used to call the file an index and offer a rescan, which read as though a
rescan would bring everything back. It does not: ratings, play counts, track
corrections and album edits live in that same file; only the index is rebuilt
by scanning. So the message names the file, says where it is and says what is
in it.
"""

from __future__ import annotations

import pathlib

from stellody.ui.display import native_path
from stellody.ui.scanning import set_aside_message


def test_the_message_names_the_file_and_where_it_is(tmp_path: pathlib.Path) -> None:
    moved = tmp_path / "library.sqlite3.damaged"
    assert native_path(str(moved)) in set_aside_message(moved)


def test_the_message_says_what_a_rescan_cannot_bring_back(
    tmp_path: pathlib.Path,
) -> None:
    said = set_aside_message(tmp_path / "library.sqlite3.damaged")
    for kept in ("ratings", "play counts", "corrections", "edits"):
        assert kept in said
    assert "rebuilds only the library index" in said
