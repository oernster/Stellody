"""Stating what an album is, which decides what it folds with.

Track values are laid over an assembled library. An album's own description
cannot be: it is what the album is IDENTIFIED by, so it has to be settled
before anything is folded. That ordering is the whole feature. Give one album
the artist and title another already carries and the two become one album,
which is how a release split across two disc folders has always worked.
"""

from __future__ import annotations

import pytest

from stellody.domain.entries import SourceEntry, folder_of, stated_over
from stellody.domain.grouping import assemble_albums
from stellody.domain.ordering import TrackCandidate
from stellody.domain.overrides import AlbumEdit, AlbumField
from stellody.domain.track import CD_SAMPLE_RATE, TrackSource

PARENT = "H:/FLACMusic/Sasha"


def entry(folder: str, name: str, album: str, artist: str) -> SourceEntry:
    """One scanned source in a named folder, carrying a named album."""
    return SourceEntry(
        folder_name=folder,
        parent_path=PARENT,
        parent_name="Sasha",
        candidate=TrackCandidate(
            file_name=name,
            source=TrackSource(path=f"{PARENT}/{folder}/{name}"),
            duration_ms=1000,
            sample_rate=CD_SAMPLE_RATE,
            bit_depth=16,
            tag_track=1,
            tag_title=name,
            artists=(artist,),
        ),
        album=album,
        album_artist=artist,
    )


def an_edit(folder: str, field: AlbumField, value: str) -> AlbumEdit:
    return AlbumEdit(f"{PARENT}/{folder}", field, value)


class TestWhereAnEditIsKeyed:
    def test_a_folder_is_what_an_edit_is_stated_against(self) -> None:
        """The one thing about an album that editing its name cannot change.

        A handle is a digest of the album artist, the title and the year, so an
        edit to any of those changes it. Keyed by the handle, an edit would
        answer to the album it had already stopped describing and would undo
        itself the instant it took effect.
        """
        assert folder_of(entry("Involver", "01.flac", "Involver", "Sasha")) == (
            f"{PARENT}/Involver"
        )

    def test_an_edit_needs_a_folder_and_a_value(self) -> None:
        with pytest.raises(ValueError):
            AlbumEdit("", AlbumField.TITLE, "Involver")
        with pytest.raises(ValueError):
            AlbumEdit("somewhere", AlbumField.TITLE, "")


class TestLayingThemOver:
    def test_stating_nothing_leaves_the_entries_as_they_were(self) -> None:
        entries = (entry("Involver", "01.flac", "Involver", "Sasha"),)
        assert stated_over(entries, ()) is entries

    def test_a_stated_title_replaces_what_the_tags_said(self) -> None:
        entries = (entry("Involver", "01.flac", "Involv3r", "Sasha"),)
        laid = stated_over(
            entries, (an_edit("Involver", AlbumField.TITLE, "Involver"),)
        )
        assert laid[0].album == "Involver"
        assert laid[0].album_artist == "Sasha"

    def test_a_folder_nothing_was_stated_about_is_untouched(self) -> None:
        entries = (
            entry("Involver", "01.flac", "Involver", "Sasha"),
            entry("Invol2ver", "01.flac", "Invol2ver", "Sasha"),
        )
        laid = stated_over(
            entries, (an_edit("Involver", AlbumField.ALBUM_ARTIST, "Somebody"),)
        )
        assert laid[0].album_artist == "Somebody"
        assert laid[1].album_artist == "Sasha"

    def test_the_last_statement_about_a_field_is_the_one_that_counts(self) -> None:
        entries = (entry("Involver", "01.flac", "Involver", "Sasha"),)
        laid = stated_over(
            entries,
            (
                an_edit("Involver", AlbumField.TITLE, "First"),
                an_edit("Involver", AlbumField.TITLE, "Second"),
            ),
        )
        assert laid[0].album == "Second"


class TestFolding:
    def test_two_albums_given_one_description_become_one_album(self) -> None:
        """The whole point of stating it BEFORE anything is folded.

        Two folders resolving to one artist and one title share a handle, which
        is what has always made a release split across CD1 and CD2 into a
        single album. Nothing here is a special case for editing.
        """
        entries = (
            entry("Invol_3r", "01.flac", "Invol<3r", "Sasha"),
            entry("Invol_3r_bonus", "01.flac", "Bonus Disc", "Sasha"),
        )
        before, _ = assemble_albums(entries)
        assert len(before) == 2

        laid = stated_over(
            entries, (an_edit("Invol_3r_bonus", AlbumField.TITLE, "Invol<3r"),)
        )
        after, _ = assemble_albums(laid)
        assert len(after) == 1
        assert after[0].identity.title == "Invol<3r"

    def test_the_merged_album_wears_one_handle(self) -> None:
        """Which is what artwork, ratings and pins are all found by."""
        entries = (
            entry("Invol_3r", "01.flac", "Invol<3r", "Sasha"),
            entry("Invol_3r_bonus", "02.flac", "Bonus Disc", "Sasha"),
        )
        joined = stated_over(
            entries, (an_edit("Invol_3r_bonus", AlbumField.TITLE, "Invol<3r"),)
        )
        alone, _ = assemble_albums(entries)
        merged, _ = assemble_albums(joined)
        target = next(a for a in alone if a.identity.title == "Invol<3r")
        assert merged[0].identity.handle == target.identity.handle

    def test_withdrawing_the_statement_splits_them_again(self) -> None:
        """Stating nothing is what a Reset leaves behind, so this is the way back."""
        entries = (
            entry("Invol_3r", "01.flac", "Invol<3r", "Sasha"),
            entry("Invol_3r_bonus", "01.flac", "Bonus Disc", "Sasha"),
        )
        assert len(assemble_albums(stated_over(entries, ()))[0]) == 2
