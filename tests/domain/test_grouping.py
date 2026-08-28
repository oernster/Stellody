"""Folders group, tags name: assembling scanned sources into albums."""

from __future__ import annotations

import pytest

from stellody.domain.grouping import (
    UNKNOWN_ALBUM,
    SourceEntry,
    assemble_albums,
    folder_base_and_disc,
)
from stellody.domain.health import IssueKind
from stellody.domain.ordering import UNKNOWN_ARTIST, TrackCandidate
from stellody.domain.track import TrackSource

RATE = 44100


def entry(
    folder_name: str,
    file_name: str,
    parent_path: str = "H:/Music/Iron Maiden",
    parent_name: str = "Iron Maiden",
    **overrides: object,
) -> SourceEntry:
    """A source entry with the fields a given test cares about."""
    candidate = TrackCandidate(
        file_name=file_name,
        source=TrackSource(path=f"{parent_path}/{folder_name}/{file_name}"),
        duration_ms=1000,
        sample_rate=RATE,
        bit_depth=16,
        tag_disc=overrides.pop("tag_disc", None),  # type: ignore[arg-type]
        tag_track=overrides.pop("tag_track", None),  # type: ignore[arg-type]
        tag_title=overrides.pop("tag_title", file_name),  # type: ignore[arg-type]
        artists=overrides.pop("artists", ("Iron Maiden",)),  # type: ignore[arg-type]
    )
    fields: dict[str, object] = {
        "folder_name": folder_name,
        "parent_path": parent_path,
        "parent_name": parent_name,
        "candidate": candidate,
    }
    fields.update(overrides)
    return SourceEntry(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("The Book of Souls CD1", ("The Book of Souls", 1)),
        ("White Album (Disc 2)", ("White Album", 2)),
        ("Box Set [Disk 3]", ("Box Set", 3)),
        ("Red cd2", ("Red", 2)),
        ("Northern Exposure 2", ("Northern Exposure 2", None)),
        ("Future Funk 2", ("Future Funk 2", None)),
        ("Involver", ("Involver", None)),
        ("CD1", ("CD1", None)),
    ],
)
def test_disc_suffixes_are_split_off_without_touching_titles(
    name: str, expected: tuple[str, int | None]
) -> None:
    assert folder_base_and_disc(name) == expected


def test_sibling_disc_folders_merge_into_one_album() -> None:
    entries = (
        entry(
            "The Book of Souls CD1",
            "01. If Eternity Should Fail.flac",
            tag_track=1,
            album_artist="Iron Maiden",
        ),
        entry(
            "The Book of Souls CD2",
            "01. Death or Glory.flac",
            tag_track=1,
            album_artist="Iron Maiden",
        ),
    )
    albums, issues = assemble_albums(entries)
    assert len(albums) == 1
    assert albums[0].disc_count == 2
    assert albums[0].identity.display_title == "The Book of Souls"
    assert issues == ()


def test_the_folder_disc_number_outranks_a_contradicting_tag() -> None:
    """A folder named Disc 2 holding tags claiming disc 3 is believed."""
    entries = (
        entry("Magic Flute (Disc 1)", "01. A.flac", tag_track=1, tag_disc=1),
        entry("Magic Flute (Disc 2)", "01. B.flac", tag_track=1, tag_disc=3),
        entry("Magic Flute (Disc 2)", "02. C.flac", tag_track=2, tag_disc=2),
    )
    albums, issues = assemble_albums(entries)
    assert albums[0].disc_count == 2
    assert [(t.disc_number, t.track_number) for t in albums[0].ordered_tracks()] == [
        (1, 1),
        (2, 1),
        (2, 2),
    ]
    conflicts = [i for i in issues if i.kind is IssueKind.DISC_NUMBER_CONFLICT]
    assert len(conflicts) == 1
    assert conflicts[0].detail == "1 file(s)"


def test_a_folder_disc_fills_in_a_missing_disc_tag() -> None:
    entries = (entry("Album CD2", "01. A.flac", tag_track=1),)
    albums, _ = assemble_albums(entries)
    assert albums[0].ordered_tracks()[0].disc_number == 2


def test_one_folder_stays_one_album_when_its_tags_disagree() -> None:
    """The classical case: composer in ALBUM, a different DATE on each track."""
    entries = (
        entry(
            "Mozart- Requiem",
            "01. Introitus.flac",
            tag_track=1,
            album="Wolfgang Amadeus Mozart",
            album_artist="Wolfgang Amadeus Mozart",
            date="1984",
        ),
        entry(
            "Mozart- Requiem",
            "02. Kyrie.flac",
            tag_track=2,
            album="Wolfgang Amadeus Mozart",
            album_artist="Wolfgang Amadeus Mozart",
            date="1989-04",
        ),
        entry(
            "Mozart- Requiem",
            "03. Dies Irae.flac",
            tag_track=3,
            album="Requiem",
            album_artist="Wolfgang Amadeus Mozart",
            date="1984",
        ),
    )
    albums, _ = assemble_albums(entries)
    assert len(albums) == 1
    assert albums[0].track_count == 3
    assert albums[0].identity.date == "1984"


def test_the_most_common_album_and_genre_win() -> None:
    entries = (
        entry("Folder", "01. A.flac", tag_track=1, album="Real", genre="House"),
        entry("Folder", "02. B.flac", tag_track=2, album="Real", genre="House"),
        entry("Folder", "03. C.flac", tag_track=3, album="Typo", genre="Techno"),
    )
    albums, _ = assemble_albums(entries)
    assert albums[0].identity.display_title == "Real"
    assert albums[0].genre == "House"


def test_a_missing_album_tag_falls_back_to_the_folder_name() -> None:
    albums, _ = assemble_albums((entry("Involver", "01. A.flac", tag_track=1),))
    assert albums[0].identity.display_title == "Involver"


def test_an_unnamed_folder_falls_back_to_a_placeholder_title() -> None:
    albums, _ = assemble_albums((entry("", "01. A.flac", tag_track=1),))
    assert albums[0].identity.display_title == UNKNOWN_ALBUM


def test_a_missing_album_artist_falls_back_to_the_parent_folder() -> None:
    entries = (entry("Album", "01. A.flac", tag_track=1),)
    albums, issues = assemble_albums(entries)
    assert albums[0].identity.display_artist == "Iron Maiden"
    assert [i.kind for i in issues] == [IssueKind.MISSING_ALBUM_ARTIST]


def test_an_orphaned_folder_is_credited_to_various_artists() -> None:
    entries = (
        entry("Album", "01. A.flac", parent_path="", parent_name="", tag_track=1),
    )
    albums, _ = assemble_albums(entries)
    assert albums[0].identity.is_compilation is True


def test_a_track_with_no_artist_at_all_is_still_placed() -> None:
    entries = (
        entry(
            "Album",
            "01. A.flac",
            parent_path="",
            parent_name="",
            tag_track=1,
            artists=(),
        ),
    )
    albums, _ = assemble_albums(entries)
    assert albums[0].ordered_tracks()[0].artists == (UNKNOWN_ARTIST,)


def test_albums_come_back_ordered_by_artist_then_year() -> None:
    entries = (
        entry(
            "Later",
            "01. A.flac",
            parent_path="H:/M/Sasha",
            parent_name="Sasha",
            tag_track=1,
            album_artist="Sasha",
            date="2016",
        ),
        entry(
            "Earlier",
            "01. B.flac",
            parent_path="H:/M/Sasha",
            parent_name="Sasha",
            tag_track=1,
            album_artist="Sasha",
            date="1994",
        ),
        entry(
            "Only",
            "01. C.flac",
            parent_path="H:/M/AC-DC",
            parent_name="AC/DC",
            tag_track=1,
            album_artist="AC/DC",
            date="1980",
        ),
    )
    albums, _ = assemble_albums(entries)
    assert [album.identity.display_title for album in albums] == [
        "Only",
        "Earlier",
        "Later",
    ]


def test_identically_named_folders_under_different_artists_stay_apart() -> None:
    entries = (
        entry(
            "Greatest Hits",
            "01. A.flac",
            parent_path="H:/M/Queen",
            parent_name="Queen",
            tag_track=1,
            album_artist="Queen",
        ),
        entry(
            "Greatest Hits",
            "01. B.flac",
            parent_path="H:/M/Sting",
            parent_name="Sting",
            tag_track=1,
            album_artist="Sting",
        ),
    )
    albums, _ = assemble_albums(entries)
    assert len(albums) == 2


def test_no_entries_yields_no_albums() -> None:
    assert assemble_albums(()) == ((), ())
