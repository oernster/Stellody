"""Stating a selection's tags, which is the half no rule can work out for you.

The repair screen offers what the rules decided. This is the other half: what
somebody knows and the rules never could. Both land in the same table, so one
Reset takes back either.
"""

from __future__ import annotations

import pytest

from stellody.application.editing import TRACK_FIELDS, TagEditing, shown_for
from stellody.domain.overrides import AlbumEdit, Override, OverrideField
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource

ALBUM = "a1b2c3"


def a_track(number: int, title: str, artists: tuple[str, ...] = ("Sasha",)) -> Track:
    return Track(
        source=TrackSource(path=f"H:/Music/Involver/{number:02d}.flac"),
        disc_number=1,
        track_number=number,
        title=title,
        artists=artists,
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


class Store:
    # Whatever anybody has stated about an album, kept as the real store
    # keeps it: a set that starts empty and grows only when something is said.
    stated_albums: tuple = ()

    """Keeps what it is told, which is all this needs of a store."""

    def __init__(self) -> None:
        self.held: tuple[Override, ...] = ()

    def all_overrides(self) -> tuple[Override, ...]:
        return self.held

    def accept_overrides(self, accepted: tuple[Override, ...]) -> None:
        self.held = self.held + tuple(accepted)

    def discard_overrides(self, unwanted: tuple[Override, ...]) -> None:
        self.held = ()

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


class TestWhatThePanelShows:
    def test_one_track_shows_everything_it_holds(self) -> None:
        track = a_track(3, "Wavy Gravy")
        shown = {field: shown_for((track,), field) for field in TRACK_FIELDS}
        assert shown == {
            OverrideField.TITLE: "Wavy Gravy",
            OverrideField.ARTIST: "Sasha",
            OverrideField.DISC_NUMBER: "1",
            OverrideField.TRACK_NUMBER: "3",
        }

    def test_what_a_selection_agrees_on_is_shown(self) -> None:
        tracks = (a_track(1, "One"), a_track(2, "Two"))
        assert shown_for(tracks, OverrideField.ARTIST) == "Sasha"
        assert shown_for(tracks, OverrideField.DISC_NUMBER) == "1"

    def test_what_it_disagrees_on_is_shown_as_nothing(self) -> None:
        """Empty is not "they hold nothing"; it is "no one thing to show".

        Both mean the same as far as an edit goes, since leaving the box alone
        is what answers either.
        """
        tracks = (a_track(1, "One"), a_track(2, "Two"))
        assert shown_for(tracks, OverrideField.TITLE) == ""
        assert shown_for(tracks, OverrideField.TRACK_NUMBER) == ""

    def test_several_artists_are_shown_as_one_field(self) -> None:
        track = a_track(1, "One", ("Sasha", "Kicks Like a Mule"))
        assert shown_for((track,), OverrideField.ARTIST) == "Sasha, Kicks Like a Mule"


class TestWhatIsRecorded:
    def test_a_stated_value_becomes_a_pin_for_every_track_chosen(self) -> None:
        tracks = (a_track(1, "One"), a_track(2, "Two"))
        edits = TagEditing.edits_for(
            ALBUM, tracks, {OverrideField.ARTIST: "Kicks Like a Mule"}
        )
        assert len(edits) == 2
        assert {edit.path for edit in edits} == {t.source.path for t in tracks}
        assert {edit.value for edit in edits} == {"Kicks Like a Mule"}

    def test_an_empty_box_states_nothing(self) -> None:
        tracks = (a_track(1, "One"),)
        stated = {field: "" for field in TRACK_FIELDS}
        assert TagEditing.edits_for(ALBUM, tracks, stated) == ()

    def test_a_box_holding_only_spaces_states_nothing(self) -> None:
        tracks = (a_track(1, "One"),)
        assert TagEditing.edits_for(ALBUM, tracks, {OverrideField.TITLE: "   "}) == ()

    def test_stating_what_a_track_already_holds_records_nothing(self) -> None:
        """Pressing Keep having changed nothing writes nothing."""
        tracks = (a_track(3, "Wavy Gravy"),)
        stated = {
            OverrideField.TITLE: "Wavy Gravy",
            OverrideField.ARTIST: "Sasha",
            OverrideField.TRACK_NUMBER: "3",
        }
        assert TagEditing.edits_for(ALBUM, tracks, stated) == ()

    def test_only_the_track_that_differs_is_pinned(self) -> None:
        tracks = (a_track(1, "One"), a_track(2, "Two"))
        edits = TagEditing.edits_for(ALBUM, tracks, {OverrideField.TRACK_NUMBER: "2"})
        assert [edit.path for edit in edits] == [tracks[0].source.path]


class TestWhatCannotBeHeld:
    @pytest.mark.parametrize("written", ["nought", "0", "-1", "2.5", "one"])
    def test_a_number_that_is_not_a_counting_number_is_refused(
        self, written: str
    ) -> None:
        """Refused where it was typed, so somebody can be told which box.

        The domain drops an unusable pin on the way into the library, which is
        the right last defence. It is a silent one: a value written and then
        ignored looks exactly like a value that was kept.
        """
        stated = {OverrideField.TRACK_NUMBER: written}
        assert TagEditing.refused(stated) == (OverrideField.TRACK_NUMBER,)

    def test_a_refused_value_is_never_recorded(self) -> None:
        tracks = (a_track(1, "One"),)
        stated = {OverrideField.DISC_NUMBER: "0"}
        assert TagEditing.edits_for(ALBUM, tracks, stated) == ()

    def test_an_empty_box_is_not_a_refusal(self) -> None:
        """Nothing typed is nothing to complain about."""
        stated = {field: "" for field in TRACK_FIELDS}
        assert TagEditing.refused(stated) == ()

    def test_text_fields_take_any_words(self) -> None:
        stated = {OverrideField.TITLE: "0", OverrideField.ARTIST: "-1"}
        assert TagEditing.refused(stated) == ()


class TestWritingToTheStore:
    def test_stating_a_value_puts_it_in_the_store(self) -> None:
        store = Store()
        tracks = (a_track(1, "One"),)
        written = TagEditing(store).state(
            ALBUM, tracks, {OverrideField.TITLE: "Something Else"}
        )
        assert written == 1
        assert store.held[0].value == "Something Else"
        assert store.held[0].field is OverrideField.TITLE

    def test_stating_nothing_never_reaches_the_store(self) -> None:
        store = Store()
        written = TagEditing(store).state(
            ALBUM, (a_track(1, "One"),), {OverrideField.TITLE: ""}
        )
        assert written == 0
        assert store.held == ()
