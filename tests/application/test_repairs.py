"""Accepting the corrections a report describes, at each granularity, then back.

The service reads the library as it is displayed and writes to Stellody's own
store. What it must never do is invent a value: everything it pins is read off
the track the reader was looking at.
"""

from __future__ import annotations

import pytest

from stellody.application.repairs import Repairs
from stellody.application.scan import LibraryView
from stellody.domain.album import Album
from stellody.domain.health import IssueKind, LibraryIssue
from stellody.domain.identity import AlbumIdentity
from stellody.domain.overrides import Override, OverrideField
from stellody.domain.track import Track, TrackSource

FOLDER = "H:/Music/Portishead/Dummy"
RATE = 44100


class RecordingStore:
    """Just enough store to watch what the service asks of it."""

    def __init__(self) -> None:
        self.accepted: tuple[Override, ...] = ()
        self.discarded: tuple[Override, ...] = ()

    def all_overrides(self) -> tuple[Override, ...]:
        return self.accepted

    def accept_overrides(self, accepted: tuple[Override, ...]) -> None:
        self.accepted = self.accepted + accepted

    def discard_overrides(self, unwanted: tuple[Override, ...]) -> None:
        self.discarded = self.discarded + unwanted
        dropped = {(item.album, item.path, item.field) for item in unwanted}
        self.accepted = tuple(
            item
            for item in self.accepted
            if (item.album, item.path, item.field) not in dropped
        )


def track(
    file_name: str, disc: int = 1, number: int = 1, folder: str = FOLDER
) -> Track:
    """One resolved track, as the rules would have left it."""
    return Track(
        source=TrackSource(path=f"{folder}/{file_name}"),
        disc_number=disc,
        track_number=number,
        title=f"Title of {file_name}",
        artists=("Portishead",),
        duration_ms=1000,
        sample_rate=RATE,
        bit_depth=16,
    )


IDENTITY = AlbumIdentity(album_artist="Portishead", title="Dummy", date="1994")
OTHER = AlbumIdentity(album_artist="Portishead", title="Third", date="2008")
ALBUM = Album(
    identity=IDENTITY,
    tracks=(
        track("01 Mysterons.flac", number=1),
        track("02 Sour Times.flac", number=2),
    ),
)
VIEW = LibraryView(albums=(ALBUM,))


def issue(kind: IssueKind, paths: tuple[str, ...] = (), key: str = "") -> LibraryIssue:
    """A finding attributed to the album under test unless told otherwise."""
    return LibraryIssue(
        kind=kind,
        album="Portishead - Dummy",
        paths=paths,
        album_key=key or IDENTITY.handle,
    )


class TestWhichFindingsAreOffered:
    def test_a_finding_that_proposes_a_value_is_offered(self) -> None:
        offered = Repairs.acceptable((issue(IssueKind.DUPLICATE_TRACK_NUMBER),))
        assert len(offered) == 1

    def test_a_finding_with_nothing_to_propose_is_not(self) -> None:
        """There is nothing there to accept, so it is reported and never offered."""
        offered = Repairs.acceptable(
            (issue(IssueKind.NO_ARTWORK), issue(IssueKind.UNREADABLE_FILE))
        )
        assert offered == ()

    def test_findings_are_selected_by_handle_not_by_label(self) -> None:
        """Two albums can share a label; a reissue beside its original does."""
        mine = issue(IssueKind.MISSING_ALBUM_ARTIST)
        theirs = issue(IssueKind.MISSING_ALBUM_ARTIST, key=OTHER.handle)
        assert Repairs.in_album((mine, theirs), IDENTITY.handle) == (mine,)


class TestWhatAcceptingRecords:
    def test_a_track_finding_pins_the_value_the_reader_was_shown(self) -> None:
        repairs = Repairs(RecordingStore())
        pins = repairs.pins_for(
            VIEW,
            (
                issue(
                    IssueKind.DUPLICATE_TRACK_NUMBER,
                    ("01 Mysterons.flac", "02 Sour Times.flac"),
                ),
            ),
        )
        assert {pin.value for pin in pins} == {"1", "2"}
        assert all(pin.field is OverrideField.TRACK_NUMBER for pin in pins)

    def test_a_disc_finding_pins_the_disc(self) -> None:
        repairs = Repairs(RecordingStore())
        pins = repairs.pins_for(
            VIEW, (issue(IssueKind.DISC_NUMBER_CONFLICT, ("01 Mysterons.flac",)),)
        )
        assert pins[0].field is OverrideField.DISC_NUMBER
        assert pins[0].value == "1"

    def test_a_title_finding_pins_the_title(self) -> None:
        repairs = Repairs(RecordingStore())
        pins = repairs.pins_for(
            VIEW, (issue(IssueKind.MISSING_TITLE, ("01 Mysterons.flac",)),)
        )
        assert pins[0].value == "Title of 01 Mysterons.flac"

    def test_an_album_artist_finding_pins_once_and_names_no_file(self) -> None:
        repairs = Repairs(RecordingStore())
        pins = repairs.pins_for(VIEW, (issue(IssueKind.MISSING_ALBUM_ARTIST),))
        assert len(pins) == 1
        assert pins[0].path == ""
        assert pins[0].value == "Portishead"

    def test_a_finding_that_proposes_nothing_records_nothing(self) -> None:
        repairs = Repairs(RecordingStore())
        assert repairs.pins_for(VIEW, (issue(IssueKind.NO_ARTWORK),)) == ()

    def test_a_finding_for_an_album_not_on_screen_is_skipped(self) -> None:
        """Skipped rather than guessed at, which is the honest answer."""
        repairs = Repairs(RecordingStore())
        assert (
            repairs.pins_for(
                VIEW, (issue(IssueKind.MISSING_ALBUM_ARTIST, key=OTHER.handle),)
            )
            == ()
        )

    def test_a_file_name_no_track_wears_pins_nothing(self) -> None:
        repairs = Repairs(RecordingStore())
        assert (
            repairs.pins_for(
                VIEW, (issue(IssueKind.MISSING_TITLE, ("99 Not Here.flac",)),)
            )
            == ()
        )

    def test_one_name_worn_by_two_tracks_pins_both(self) -> None:
        """A multi-disc album merged from CD1 and CD2 can hold one name twice."""
        doubled = Album(
            identity=IDENTITY,
            tracks=(
                track("01 Intro.flac", disc=1, number=1, folder=f"{FOLDER}/CD1"),
                track("01 Intro.flac", disc=2, number=1, folder=f"{FOLDER}/CD2"),
            ),
        )
        repairs = Repairs(RecordingStore())
        pins = repairs.pins_for(
            LibraryView(albums=(doubled,)),
            (issue(IssueKind.DUPLICATE_TRACK_NUMBER, ("01 Intro.flac",)),),
        )
        assert {pin.path for pin in pins} == {
            f"{FOLDER}/CD1/01 Intro.flac",
            f"{FOLDER}/CD2/01 Intro.flac",
        }

    def test_two_findings_on_one_album_share_its_track_index(self) -> None:
        """The names are worked out once an album, not once a finding."""
        repairs = Repairs(RecordingStore())
        pins = repairs.pins_for(
            VIEW,
            (
                issue(IssueKind.MISSING_TITLE, ("01 Mysterons.flac",)),
                issue(IssueKind.MISSING_TRACK_NUMBER, ("02 Sour Times.flac",)),
            ),
        )
        assert len(pins) == 2


class TestAcceptingAndResetting:
    def test_accepting_writes_the_pins_and_says_how_many(self) -> None:
        store = RecordingStore()
        written = Repairs(store).accept(
            VIEW,
            (
                issue(
                    IssueKind.DUPLICATE_TRACK_NUMBER,
                    ("01 Mysterons.flac", "02 Sour Times.flac"),
                ),
            ),
        )
        assert written == 2
        assert len(store.accepted) == 2

    def test_nothing_accepted_groups_into_nothing(self) -> None:
        assert Repairs(RecordingStore()).accepted() == ()

    def test_what_was_accepted_groups_by_album_and_field(self) -> None:
        store = RecordingStore()
        repairs = Repairs(store)
        repairs.accept(
            VIEW,
            (
                issue(
                    IssueKind.DUPLICATE_TRACK_NUMBER,
                    ("01 Mysterons.flac", "02 Sour Times.flac"),
                ),
                issue(IssueKind.MISSING_ALBUM_ARTIST),
            ),
        )
        groups = repairs.accepted()
        assert len(groups) == 2
        assert {group.field for group in groups} == {
            OverrideField.TRACK_NUMBER,
            OverrideField.ALBUM_ARTIST,
        }
        assert sum(group.count for group in groups) == 3

    def test_resetting_a_group_drops_its_pins(self) -> None:
        store = RecordingStore()
        repairs = Repairs(store)
        repairs.accept(VIEW, (issue(IssueKind.MISSING_ALBUM_ARTIST),))
        assert repairs.reset(repairs.accepted()) == 1
        assert store.accepted == ()

    def test_resetting_an_album_takes_back_only_that_album(self) -> None:
        store = RecordingStore()
        repairs = Repairs(store)
        repairs.accept(VIEW, (issue(IssueKind.MISSING_ALBUM_ARTIST),))
        store.accept_overrides(
            (Override(OTHER.handle, OverrideField.ALBUM_ARTIST, "Someone"),)
        )
        assert repairs.reset_album(IDENTITY.handle) == 1
        assert [pin.album for pin in store.accepted] == [OTHER.handle]

    def test_resetting_everything_empties_the_set(self) -> None:
        store = RecordingStore()
        repairs = Repairs(store)
        repairs.accept(
            VIEW,
            (
                issue(
                    IssueKind.DUPLICATE_TRACK_NUMBER,
                    ("01 Mysterons.flac", "02 Sour Times.flac"),
                ),
                issue(IssueKind.MISSING_ALBUM_ARTIST),
            ),
        )
        assert repairs.reset_everything() == 3
        assert store.accepted == ()

    @pytest.mark.parametrize(
        ("kind", "field"),
        [
            (IssueKind.DUPLICATE_TRACK_NUMBER, OverrideField.TRACK_NUMBER),
            (IssueKind.MISSING_TRACK_NUMBER, OverrideField.TRACK_NUMBER),
            (IssueKind.DISC_NUMBER_CONFLICT, OverrideField.DISC_NUMBER),
            (IssueKind.MISSING_TITLE, OverrideField.TITLE),
        ],
    )
    def test_every_track_kind_pins_its_own_field(
        self, kind: IssueKind, field: OverrideField
    ) -> None:
        repairs = Repairs(RecordingStore())
        pins = repairs.pins_for(VIEW, (issue(kind, ("01 Mysterons.flac",)),))
        assert pins[0].field is field


class TestTwoAlbumsWearingOneHandle:
    """Reported from a real library, where accepting a finding did nothing.

    The handle is a digest of the artist, the title and the year, so two
    separate recordings filed apart under one title share it. Classical music
    does this routinely: a Mahler symphony under two conductors is two albums
    with one identity. Holding them in a dictionary of one kept the last and
    silently dropped the other, so a finding belonging to the dropped one
    matched no file, wrote no pins and came back at every start however many
    times somebody pressed Accept.
    """

    def _two_albums(self) -> LibraryView:
        """Two albums that really do resolve to one handle."""
        mine = Album(identity=IDENTITY, tracks=(track("01 Allegro.flac"),))
        theirs = Album(
            identity=IDENTITY,
            tracks=(track("01 Andante.flac", folder=f"{FOLDER}/Other"),),
        )
        assert mine.identity.handle == theirs.identity.handle
        return LibraryView(albums=(mine, theirs))

    def test_a_finding_on_the_first_of_them_still_pins_its_files(self) -> None:
        """The one that used to be dropped, so this is the reported defect."""
        repairs = Repairs(RecordingStore())
        pins = repairs.pins_for(
            self._two_albums(),
            (issue(IssueKind.DISC_NUMBER_CONFLICT, ("01 Allegro.flac",)),),
        )
        assert pins, "accepting wrote nothing, which is the defect"
        assert pins[0].path.endswith("01 Allegro.flac")

    def test_a_finding_on_the_second_of_them_pins_its_files_too(self) -> None:
        repairs = Repairs(RecordingStore())
        pins = repairs.pins_for(
            self._two_albums(),
            (issue(IssueKind.MISSING_TITLE, ("01 Andante.flac",)),),
        )
        assert pins
        assert pins[0].path.endswith("01 Andante.flac")

    def test_an_album_wide_pin_covers_both_because_they_share_the_artist(
        self,
    ) -> None:
        """Sharing a handle means sharing the artist, so one value serves both."""
        repairs = Repairs(RecordingStore())
        pins = repairs.pins_for(
            self._two_albums(), (issue(IssueKind.MISSING_ALBUM_ARTIST),)
        )
        assert len(pins) == 1
        assert pins[0].value == IDENTITY.album_artist
