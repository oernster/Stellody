"""The table behind an album's stated description.

Its own table rather than columns on the corrections one, because the two are
keyed by different things: a correction by an album's handle, a statement by
the folder the music sits in.
"""

from __future__ import annotations

import pathlib

import pytest

from stellody.domain.overrides import AlbumEdit, AlbumField
from stellody.infrastructure.store import SqliteLibraryStore

FOLDER = "H:/FLACMusic/Sasha/Involver"


@pytest.fixture
def store(tmp_path: pathlib.Path) -> SqliteLibraryStore:
    return SqliteLibraryStore(str(tmp_path / "library.db"))


def an_edit(field: AlbumField, value: str, folder: str = FOLDER) -> AlbumEdit:
    return AlbumEdit(folder, field, value)


def test_a_new_store_has_nothing_stated(store: SqliteLibraryStore) -> None:
    assert store.all_album_edits() == ()


def test_what_is_stated_comes_back(store: SqliteLibraryStore) -> None:
    stated = (an_edit(AlbumField.TITLE, "Involv3r"),)
    store.state_album_edits(stated)
    assert store.all_album_edits() == stated


def test_stating_a_field_twice_replaces_rather_than_accumulates(
    store: SqliteLibraryStore,
) -> None:
    """A folder and field hold one value, which is what assembly reads."""
    store.state_album_edits((an_edit(AlbumField.TITLE, "First"),))
    store.state_album_edits((an_edit(AlbumField.TITLE, "Second"),))
    held = store.all_album_edits()
    assert len(held) == 1
    assert held[0].value == "Second"


def test_two_fields_of_one_folder_are_both_kept(store: SqliteLibraryStore) -> None:
    store.state_album_edits(
        (
            an_edit(AlbumField.TITLE, "Involv3r"),
            an_edit(AlbumField.ALBUM_ARTIST, "Sasha"),
        )
    )
    assert len(store.all_album_edits()) == 2


def test_stating_nothing_writes_nothing(store: SqliteLibraryStore) -> None:
    store.state_album_edits(())
    assert store.all_album_edits() == ()


def test_a_statement_can_be_withdrawn(store: SqliteLibraryStore) -> None:
    """Withdrawing is the way back out of a fold, so it has to work."""
    stated = (an_edit(AlbumField.TITLE, "Involv3r"),)
    store.state_album_edits(stated)
    store.discard_album_edits(stated)
    assert store.all_album_edits() == ()


def test_withdrawing_matches_on_what_it_applies_to_not_on_its_value(
    store: SqliteLibraryStore,
) -> None:
    """Taking one back is about which statement, never about what it said."""
    store.state_album_edits((an_edit(AlbumField.TITLE, "Involv3r"),))
    store.discard_album_edits((an_edit(AlbumField.TITLE, "something else"),))
    assert store.all_album_edits() == ()


def test_withdrawing_nothing_leaves_everything(store: SqliteLibraryStore) -> None:
    stated = (an_edit(AlbumField.TITLE, "Involv3r"),)
    store.state_album_edits(stated)
    store.discard_album_edits(())
    assert store.all_album_edits() == stated


def test_a_field_this_version_does_not_know_is_skipped(
    store: SqliteLibraryStore,
) -> None:
    """Reading a library must not fail because another Stellody wrote a row.

    A statement nobody can apply is simply not applied, rather than being an
    error that stops the library assembling at all with no way back in.
    """
    store.state_album_edits((an_edit(AlbumField.TITLE, "Involv3r"),))
    store._connection.execute(
        "INSERT INTO album_edits (folder, field, value) VALUES (?, ?, ?)",
        (FOLDER, "conductor", "Colin Davis"),
    )
    store._connection.commit()
    held = store.all_album_edits()
    assert len(held) == 1
    assert held[0].field is AlbumField.TITLE
