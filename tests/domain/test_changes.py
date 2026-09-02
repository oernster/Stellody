"""Comparing two readings of a library, which is what a scan report says."""

from __future__ import annotations

import pytest

from stellody.domain.album import Album
from stellody.domain.changes import LibraryChange, compare_libraries
from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import TrackSource
from tests.domain.factories import make_track


def _album(title: str, *paths: str, artist: str = "Holst") -> Album:
    """One album of one track per path, so a path is a track."""
    return Album(
        identity=AlbumIdentity(album_artist=artist, title=title),
        tracks=tuple(
            make_track(source=TrackSource(path=path), track_number=number)
            for number, path in enumerate(paths, start=1)
        ),
    )


def test_a_first_reading_is_all_new() -> None:
    after = (_album("Planets", "a.flac"), _album("Blue", "b.mp3"))
    change = compare_libraries((), after)
    assert change.is_first_reading is True
    assert len(change.new_albums) == 2
    assert change.new_tracks == 2
    assert change.gone_albums == ()
    assert change.gone_tracks == 0
    assert change.total_albums == 2
    assert change.total_tracks == 2
    assert change.previous_albums == 0


def test_an_unchanged_library_reports_nothing_changed() -> None:
    library = (_album("Planets", "a.flac"),)
    change = compare_libraries(library, library)
    assert change.nothing_changed is True
    assert change.is_first_reading is False
    assert change.total_albums == 1


def test_an_added_album_is_new_with_its_tracks() -> None:
    before = (_album("Planets", "a.flac"),)
    after = before + (_album("Blue", "b.mp3", "c.mp3"),)
    change = compare_libraries(before, after)
    assert [identity.title for identity in change.new_albums] == ["Blue"]
    assert change.new_tracks == 2
    assert change.nothing_changed is False
    assert change.total_tracks == 3


def test_a_removed_album_is_reported_rather_than_ignored() -> None:
    before = (_album("Planets", "a.flac"), _album("Blue", "b.mp3"))
    after = (_album("Planets", "a.flac"),)
    change = compare_libraries(before, after)
    assert [identity.title for identity in change.gone_albums] == ["Blue"]
    assert change.gone_tracks == 1
    assert change.new_albums == ()


def test_a_track_added_to_a_known_album_counts_without_a_new_album() -> None:
    """The case a folder gaining one file produces, which is the common one."""
    before = (_album("Planets", "a.flac"),)
    after = (_album("Planets", "a.flac", "b.flac"),)
    change = compare_libraries(before, after)
    assert change.new_albums == ()
    assert change.new_tracks == 1
    assert change.nothing_changed is False


def test_a_retag_reads_as_one_album_leaving_and_another_arriving() -> None:
    """Reported as both halves, so a rename is not described as a discovery."""
    before = (_album("Planets", "a.flac"),)
    after = (_album("The Planets", "a.flac"),)
    change = compare_libraries(before, after)
    assert [identity.title for identity in change.new_albums] == ["The Planets"]
    assert [identity.title for identity in change.gone_albums] == ["Planets"]
    # The audio itself never moved, so no track is new.
    assert change.new_tracks == 0
    assert change.gone_tracks == 0


def test_new_albums_come_back_in_the_order_the_library_uses() -> None:
    after = (
        _album("Zebra", "z.flac", artist="Zoe"),
        _album("Apple", "a.flac", artist="Adam"),
    )
    change = compare_libraries((), after)
    assert [identity.title for identity in change.new_albums] == ["Apple", "Zebra"]


def test_a_cue_sheet_album_counts_its_slices_apart() -> None:
    """One file, many tracks: the slice is part of what makes a track."""
    whole = AlbumIdentity(album_artist="Holst", title="Planets")
    tracks = tuple(
        make_track(
            source=TrackSource(
                path="album.flac", start_frame=start, end_frame=start + 10
            ),
            track_number=number,
        )
        for number, start in enumerate((0, 10, 20), start=1)
    )
    change = compare_libraries((), (Album(identity=whole, tracks=tracks),))
    assert change.new_tracks == 3
    assert change.total_tracks == 3


@pytest.mark.parametrize(
    "overrides",
    [
        {"new_tracks": -1},
        {"gone_tracks": -1},
        {"total_albums": -1},
        {"total_tracks": -1},
        {"previous_albums": -1},
    ],
)
def test_a_negative_count_is_refused(overrides: dict[str, int]) -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        LibraryChange(**overrides)
