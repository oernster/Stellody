"""The panel that states tags, plus the promise it makes before anything is typed.

What is settled here is what the panel offers, what it refuses and what it
records. That nothing reaches a music file is settled in the structural suite,
by a guard that fails the build if any module reading tags so much as reaches
the API that writes them.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from stellody.application.editing import TagEditing
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.overrides import AlbumEdit, AlbumField, Override, OverrideField
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource
from stellody.ui.tag_editor import MANY_TRACKS_NOTE, TagEditor

ALBUM = "a1b2c3"


class Store:
    # Whatever anybody has stated about an album, kept as the real store
    # keeps it: a set that starts empty and grows only when something is said.
    stated_albums: tuple = ()

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


def a_track(number: int, title: str) -> Track:
    return Track(
        source=TrackSource(path=f"H:/Music/Involver/{number:02d}.flac"),
        disc_number=1,
        track_number=number,
        title=title,
        artists=("Sasha",),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


@pytest.fixture
def store() -> Store:
    return Store()


@pytest.fixture
def panel(application: QApplication, store: Store):
    def opened(*tracks: Track) -> TagEditor:
        return TagEditor(
            TagEditing(store), ALBUM, tracks or (a_track(1, "Wavy Gravy"),)
        )

    return opened


@pytest.fixture
def album_panel(application: QApplication, store: Store):
    def opened() -> TagEditor:
        album = Album(
            identity=AlbumIdentity(album_artist="Sasha", title="Involver"),
            tracks=(a_track(1, "One"), a_track(2, "Two")),
        )
        return TagEditor(
            TagEditing(store), "a1b2c3", album.ordered_tracks(), holding=album
        )

    return opened


class TestWhatItOffers:
    def test_it_shows_what_one_track_holds(self, panel) -> None:
        dialog = panel(a_track(3, "Cutting Room"))
        assert dialog._boxes[OverrideField.TITLE].text() == "Cutting Room"
        assert dialog._boxes[OverrideField.TRACK_NUMBER].text() == "3"

    def test_a_title_is_offered_over_one_track_only(self, panel) -> None:
        """Stating one title about a dozen tracks is never what anybody meant.

        It is also the exact shape of the damage this application exists to
        undo, so the panel refuses to make it available rather than making it
        available and hoping.
        """
        dialog = panel(a_track(1, "One"), a_track(2, "Two"))
        box = dialog._boxes[OverrideField.TITLE]
        assert not box.isEnabled()
        assert box.placeholderText() == MANY_TRACKS_NOTE

    def test_a_disabled_box_states_nothing_whatever_is_in_it(self, panel) -> None:
        dialog = panel(a_track(1, "One"), a_track(2, "Two"))
        dialog._boxes[OverrideField.TITLE].setText("Both Of Them")
        assert OverrideField.TITLE not in dialog.stated()

    def test_it_starts_empty_where_the_tracks_disagree(self, panel) -> None:
        dialog = panel(a_track(1, "One"), a_track(2, "Two"))
        assert dialog._boxes[OverrideField.TRACK_NUMBER].text() == ""
        assert dialog._boxes[OverrideField.ARTIST].text() == "Sasha"

    def test_the_promise_is_made_before_anything_is_typed(self, panel) -> None:
        """Said where somebody meets the gesture, not only in the About box."""
        dialog = panel()
        said = " ".join(label.text() for label in dialog.findChildren(QLabel))
        assert "not touched" in said
        assert "left alone" in said


class TestWhatItRecords:
    def test_keeping_a_stated_value_records_it(self, panel, store) -> None:
        dialog = panel(a_track(1, "One"))
        dialog._boxes[OverrideField.ARTIST].setText("Kicks Like a Mule")
        dialog.keep()
        assert dialog.written == 1
        assert store.held[0].value == "Kicks Like a Mule"

    def test_keeping_nothing_records_nothing(self, panel, store) -> None:
        dialog = panel(a_track(1, "One"))
        dialog.keep()
        assert dialog.written == 0
        assert store.held == ()

    def test_cancelling_records_nothing(self, panel, store) -> None:
        dialog = panel(a_track(1, "One"))
        dialog._boxes[OverrideField.ARTIST].setText("Somebody Else")
        dialog.reject()
        assert store.held == ()


class TestWhatItRefuses:
    def test_a_number_that_is_not_one_is_reported_rather_than_written(
        self, panel, store
    ) -> None:
        dialog = panel(a_track(1, "One"))
        dialog._boxes[OverrideField.TRACK_NUMBER].setText("nought")
        dialog.keep()
        assert store.held == ()
        assert not dialog._trouble.isHidden()
        assert "Track #" in dialog._trouble.text()

    def test_a_refusal_keeps_everything_else_that_was_typed(self, panel) -> None:
        """Closing on one bad box would throw away the rest to punish it."""
        dialog = panel(a_track(1, "One"))
        dialog._boxes[OverrideField.ARTIST].setText("Kicks Like a Mule")
        dialog._boxes[OverrideField.TRACK_NUMBER].setText("nought")
        dialog.keep()
        assert not dialog._trouble.isHidden()
        assert dialog._boxes[OverrideField.ARTIST].text() == "Kicks Like a Mule"


class TestTheAlbumHalf:
    def test_no_album_fields_where_no_album_was_given(self, panel) -> None:
        """A panel over tracks alone states nothing about the album around them."""
        dialog = panel(a_track(1, "One"))
        assert dialog._album_boxes == {}

    def test_it_shows_what_the_album_currently_says(self, album_panel) -> None:
        dialog = album_panel()
        assert dialog._album_boxes[AlbumField.TITLE].text() == "Involver"
        assert dialog._album_boxes[AlbumField.ALBUM_ARTIST].text() == "Sasha"

    def test_it_says_what_folding_will_do_before_anybody_does_it(
        self, album_panel
    ) -> None:
        """Joining two albums is easy to ask for and hard to notice afterwards."""
        dialog = album_panel()
        said = " ".join(label.text() for label in dialog.findChildren(QLabel))
        assert "joins" in said
        assert "artwork" in said

    def test_a_stated_album_value_is_recorded(self, album_panel, store) -> None:
        dialog = album_panel()
        dialog._album_boxes[AlbumField.TITLE].setText("Involv3r")
        dialog.keep()
        assert store.stated_albums[0].value == "Involv3r"
        assert store.stated_albums[0].field is AlbumField.TITLE

    def test_stating_what_it_already_says_records_nothing(
        self, album_panel, store
    ) -> None:
        dialog = album_panel()
        dialog.keep()
        assert store.stated_albums == ()
        assert dialog.written == 0
