"""Stating an album's own description, plus what that does to a rating.

An album is not one folder, so a statement about one has to reach every folder
it is spread across. And giving an album a description another already carries
joins them, which settles a rating between two albums that have become one.
"""

from __future__ import annotations

from stellody.application.editing import (
    ALBUM_FIELDS,
    TagEditing,
    album_shown_for,
    folders_of,
    stated_value,
)
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.overrides import AlbumEdit, AlbumField
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource

PARENT = "H:/FLACMusic/Sasha"


def a_track(folder: str, number: int) -> Track:
    return Track(
        source=TrackSource(path=f"{PARENT}/{folder}/{number:02d}.flac"),
        disc_number=1,
        track_number=number,
        title=f"Track {number}",
        artists=("Sasha",),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


def an_album(*folders: str, title: str = "Involver", genre: str = "House") -> Album:
    return Album(
        identity=AlbumIdentity(album_artist="Sasha", title=title, date="2004"),
        tracks=tuple(a_track(folder, n) for n, folder in enumerate(folders, start=1)),
        genre=genre,
    )


class Store:
    stated_albums: tuple[AlbumEdit, ...] = ()

    def all_album_edits(self) -> tuple[AlbumEdit, ...]:
        return self.stated_albums

    def state_album_edits(self, stated: tuple[AlbumEdit, ...]) -> None:
        self.stated_albums = self.stated_albums + tuple(stated)

    def discard_album_edits(self, unwanted: tuple[AlbumEdit, ...]) -> None:
        dropped = {(item.folder, item.field) for item in unwanted}
        self.stated_albums = tuple(
            item
            for item in self.stated_albums
            if (item.folder, item.field) not in dropped
        )


class TestWhichFoldersAnEditReaches:
    def test_an_album_in_one_folder_is_stated_against_that_folder(self) -> None:
        assert folders_of(an_album("Involver")) == (f"{PARENT}/Involver",)

    def test_an_album_spread_over_two_folders_reaches_both(self) -> None:
        """A release in CD1 and CD2 is already one album and has to stay one.

        Stating something against one folder alone would move that folder and
        leave the other where it was, splitting the album the statement was
        meant to describe.
        """
        assert folders_of(an_album("Set CD1", "Set CD2")) == (
            f"{PARENT}/Set CD1",
            f"{PARENT}/Set CD2",
        )

    def test_one_statement_becomes_one_edit_a_folder(self) -> None:
        album = an_album("Set CD1", "Set CD2")
        edits = TagEditing.album_edits_for(album, {AlbumField.TITLE: "Northern"})
        assert {edit.folder for edit in edits} == set(folders_of(album))
        assert {edit.value for edit in edits} == {"Northern"}


class TestWhatThePanelShows:
    def test_it_shows_what_the_album_currently_says(self) -> None:
        album = an_album("Involver")
        shown = {field: album_shown_for(album, field) for field in ALBUM_FIELDS}
        assert shown == {
            AlbumField.ALBUM_ARTIST: "Sasha",
            AlbumField.TITLE: "Involver",
            AlbumField.DATE: "2004",
            AlbumField.GENRE: "House",
        }


class TestWhatIsRecorded:
    def test_stating_what_the_album_already_says_records_nothing(self) -> None:
        album = an_album("Involver")
        stated = {field: album_shown_for(album, field) for field in ALBUM_FIELDS}
        assert TagEditing.album_edits_for(album, stated) == ()

    def test_an_empty_box_states_nothing(self) -> None:
        album = an_album("Involver")
        stated = {field: "" for field in ALBUM_FIELDS}
        assert TagEditing.album_edits_for(album, stated) == ()

    def test_a_stated_value_reaches_the_store(self) -> None:
        store = Store()
        written = TagEditing(store).state_album(
            an_album("Involver"), {AlbumField.TITLE: "Involv3r"}
        )
        assert written == 1
        assert store.stated_albums[0].value == "Involv3r"
        assert store.stated_albums[0].field is AlbumField.TITLE

    def test_stating_nothing_never_reaches_the_store(self) -> None:
        store = Store()
        written = TagEditing(store).state_album(
            an_album("Involver"), {AlbumField.TITLE: ""}
        )
        assert written == 0
        assert store.stated_albums == ()

    def test_a_statement_can_be_withdrawn(self) -> None:
        """Which is the way back out of a fold nobody meant to make."""
        store = Store()
        editing = TagEditing(store)
        editing.state_album(an_album("Involver"), {AlbumField.TITLE: "Involv3r"})
        store.discard_album_edits(store.stated_albums)
        assert store.all_album_edits() == ()


class TestTheRatingWhenTwoBecomeOne:
    def test_the_merged_album_reads_the_rating_of_the_one_it_joined(self) -> None:
        """Ratings are held against an album's handle, so this falls out of it.

        Give one album the description another already carries and both resolve
        to the target's handle. The rating found under that handle is the
        target's, which is the album the other was stated INTO; the source's
        row is left behind under a handle no album now wears.
        """
        target = an_album("Involver", title="Involver")
        source = an_album("Involv3r_bonus", title="Bonus Disc")
        assert source.identity.handle != target.identity.handle

        joined = an_album("Involv3r_bonus", title="Involver")
        assert joined.identity.handle == target.identity.handle

        ratings = {target.identity.handle: 4, source.identity.handle: 2}
        assert ratings[joined.identity.handle] == 4


class TestADateTypedIn:
    """A date is reduced on the way in, so padding cannot be put back."""

    def test_a_pasted_tag_loses_its_time(self) -> None:
        assert stated_value(AlbumField.DATE, "2007-10-09T12:00:00Z") == "2007-10-09"

    def test_a_spaced_date_gains_its_dashes(self) -> None:
        assert stated_value(AlbumField.DATE, "2001 05 15") == "2001-05-15"

    def test_a_year_stays_a_year(self) -> None:
        assert stated_value(AlbumField.DATE, "1990") == "1990"

    def test_other_fields_are_taken_as_typed(self) -> None:
        """Genre is not among them: it answers from the catalogue instead."""
        for field in (AlbumField.ALBUM_ARTIST, AlbumField.TITLE):
            assert stated_value(field, "  2007-10-09T12:00:00Z ") == (
                "2007-10-09T12:00:00Z"
            )

    def test_every_field_is_trimmed(self) -> None:
        for field in ALBUM_FIELDS:
            assert stated_value(field, "   ") == ""

    def test_a_padded_date_matching_the_album_records_nothing(self) -> None:
        """The panel shows the reduced form, so typing the padded one back in
        is not a change and must not be written down as one."""
        album = an_album("Involver")
        edits = TagEditing.album_edits_for(
            album, {AlbumField.DATE: "2004-01-01T12:00:00Z"}
        )
        assert {edit.value for edit in edits} == {"2004-01-01"}

    def test_a_date_is_stored_reduced(self) -> None:
        album = an_album("Involver")
        edits = TagEditing.album_edits_for(
            album, {AlbumField.DATE: "2005-06-07T07:00:00Z"}
        )
        assert {edit.value for edit in edits} == {"2005-06-07"}


class TestAGenreChosen:
    """A genre is reduced to the catalogue, so both sides ask one question."""

    def test_it_is_written_in_catalogue_order(self) -> None:
        assert stated_value(AlbumField.GENRE, "Rock; Alternative") == (
            "Alternative; Rock"
        )

    def test_a_tag_written_in_another_case_reduces_to_the_catalogue_name(
        self,
    ) -> None:
        assert stated_value(AlbumField.GENRE, "pop") == "Pop"

    def test_a_tag_naming_nothing_in_the_catalogue_reduces_to_nothing(self) -> None:
        """No box could have been ticked for it, so it states nothing."""
        assert stated_value(AlbumField.GENRE, "dance-house") == ""

    def test_keeping_a_panel_nobody_touched_records_nothing(self) -> None:
        """The album is tagged in one case and the grid shows the other."""
        album = an_album("Involver")
        shown = album_shown_for(album, AlbumField.GENRE)
        assert shown == "House"
        assert TagEditing.album_edits_for(album, {AlbumField.GENRE: "house"}) == ()

    def test_adding_a_genre_the_tag_never_named_is_recorded(self) -> None:
        """The Green Day case, as the panel would state it.

        The album here is tagged House, which is deliberately not one of the
        seventeen, so the grid starts with nothing ticked. Ticking Rock and
        Punk states both, which is the whole point of the feature.
        """
        album = an_album("Involver")
        edits = TagEditing.album_edits_for(album, {AlbumField.GENRE: "Rock; Punk"})
        assert {edit.value for edit in edits} == {"Punk; Rock"}

    def test_a_tag_outside_the_catalogue_ticks_nothing_and_states_nothing(
        self,
    ) -> None:
        """Keeping a panel it could not represent must not wipe the tag."""
        album = an_album("Involver")
        assert album_shown_for(album, AlbumField.GENRE) == "House"
        assert TagEditing.album_edits_for(album, {AlbumField.GENRE: ""}) == ()
