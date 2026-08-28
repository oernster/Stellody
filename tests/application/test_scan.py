"""Scanning: probing, cue expansion, incremental reuse and absence."""

from __future__ import annotations

from fakes import (
    CD_RATE,
    FakeProbe,
    FakeStore,
    FakeTextReader,
    FakeWalker,
    properties,
    stat,
)

from stellody.application.ports import FolderListing
from stellody.application.scan import ScanLibrary

FOLDER = "H:/Music/Sasha/Involver"
ONE = f"{FOLDER}/01. Wavy Gravy.flac"
TWO = f"{FOLDER}/02. Cutting Room.flac"
SINGLE = f"{FOLDER}/Involver.flac"
CUE = f"{FOLDER}/Involver.cue"

CUE_TEXT = (
    'PERFORMER "Sasha"\n'
    'TITLE "Involver"\n'
    "REM DATE 2004\n"
    "REM GENRE House\n"
    'FILE "Involver.flac" WAVE\n'
    "  TRACK 01 AUDIO\n"
    '    TITLE "Wavy Gravy"\n'
    "    INDEX 01 00:00:00\n"
    "  TRACK 02 AUDIO\n"
    '    TITLE "Cutting Room"\n'
    "    INDEX 01 00:01:00\n"
)


def album_tags(track: str, title: str) -> dict[str, tuple[str, ...]]:
    """A well-tagged track in a well-tagged album."""
    return {
        "ALBUM": ("Involver",),
        "ALBUMARTIST": ("Sasha",),
        "ARTIST": ("Sasha",),
        "TITLE": (title,),
        "DATE": ("2004",),
        "GENRE": ("House",),
        "TRACKNUMBER": (track,),
    }


def two_file_listing() -> FolderListing:
    """A folder holding two ordinary tracks."""
    return FolderListing(
        folder=FOLDER,
        audio=(stat(ONE, "01. Wavy Gravy.flac"), stat(TWO, "02. Cutting Room.flac")),
        image_paths=(f"{FOLDER}/cover.jpg",),
    )


def single_file_listing() -> FolderListing:
    """A folder holding one file described by a cue sheet."""
    return FolderListing(
        folder=FOLDER,
        audio=(stat(SINGLE, "Involver.flac"),),
        cue_paths=(CUE,),
    )


def build(listings, results, texts=None, store=None) -> tuple[ScanLibrary, FakeStore]:
    """Wire a scanner over hand-written fakes."""
    used = store if store is not None else FakeStore()
    scanner = ScanLibrary(
        FakeWalker(tuple(listings)),
        FakeProbe(results),
        FakeTextReader(texts),
        used,
    )
    return scanner, used


def test_a_folder_of_tracks_becomes_one_album() -> None:
    scanner, store = build(
        [two_file_listing()],
        {
            ONE: properties(**album_tags("1", "Wavy Gravy")),
            TWO: properties(**album_tags("2", "Cutting Room")),
        },
    )
    report = scanner.run("H:/Music")
    assert len(report.albums) == 1
    album = report.albums[0]
    assert album.identity.display_title == "Involver"
    assert album.identity.display_artist == "Sasha"
    assert album.genre == "House"
    assert [track.title for track in album.ordered_tracks()] == [
        "Wavy Gravy",
        "Cutting Room",
    ]
    assert report.folders_probed == 1
    assert report.files_probed == 2
    assert store.saved == [FOLDER]


def test_progress_is_reported_for_every_folder() -> None:
    scanner, _ = build([two_file_listing()], {ONE: properties(), TWO: properties()})
    seen: list[str] = []
    scanner.run("H:/Music", progress=seen.append)
    assert seen == [FOLDER]


def test_a_cue_sheet_expands_one_file_into_slices() -> None:
    scanner, _ = build(
        [single_file_listing()],
        {SINGLE: properties(frames=CD_RATE * 120)},
        {CUE: CUE_TEXT},
    )
    report = scanner.run("H:/Music")
    album = report.albums[0]
    assert album.is_single_file is True
    assert album.track_count == 2
    first, second = album.ordered_tracks()
    assert first.source.start_frame == 0
    assert first.source.end_frame == CD_RATE
    assert second.source.start_frame == CD_RATE
    assert second.source.end_frame == CD_RATE * 120
    assert album.identity.display_title == "Involver"
    assert album.genre == "House"


def test_a_cue_track_beyond_the_end_of_the_file_has_no_length() -> None:
    scanner, _ = build(
        [single_file_listing()],
        {SINGLE: properties(frames=10)},
        {CUE: CUE_TEXT},
    )
    album = scanner.run("H:/Music").albums[0]
    assert album.ordered_tracks()[1].duration_ms == 0


def test_an_unreadable_cue_falls_back_to_the_whole_file() -> None:
    scanner, _ = build([single_file_listing()], {SINGLE: properties()}, {})
    album = scanner.run("H:/Music").albums[0]
    assert album.track_count == 1
    assert album.is_single_file is False


def test_a_malformed_cue_falls_back_to_the_whole_file() -> None:
    scanner, _ = build(
        [single_file_listing()],
        {SINGLE: properties()},
        {CUE: 'FILE "a.flac" WAVE\n  TRACK ZZ AUDIO\n'},
    )
    assert scanner.run("H:/Music").albums[0].track_count == 1


def test_an_empty_cue_falls_back_to_the_whole_file() -> None:
    scanner, _ = build([single_file_listing()], {SINGLE: properties()}, {CUE: "REM\n"})
    assert scanner.run("H:/Music").albums[0].track_count == 1


def test_an_unreadable_file_is_reported_and_skipped() -> None:
    scanner, _ = build(
        [two_file_listing()],
        {ONE: properties(**album_tags("1", "Wavy Gravy")), TWO: None},
    )
    report = scanner.run("H:/Music")
    assert report.files_unreadable == 1
    assert report.files_probed == 1
    assert report.albums[0].track_count == 1


def test_a_folder_of_only_unreadable_files_produces_no_album() -> None:
    scanner, _ = build([two_file_listing()], {})
    report = scanner.run("H:/Music")
    assert report.albums == ()
    assert report.files_unreadable == 2


def test_an_unchanged_folder_is_reused_rather_than_reprobed() -> None:
    probe_results = {
        ONE: properties(**album_tags("1", "Wavy Gravy")),
        TWO: properties(**album_tags("2", "Cutting Room")),
    }
    scanner, store = build([two_file_listing()], probe_results)
    scanner.run("H:/Music")

    again, _ = build([two_file_listing()], probe_results, store=store)
    report = again.run("H:/Music")
    assert report.folders_reused == 1
    assert report.folders_probed == 0
    assert report.albums[0].track_count == 2


def test_a_changed_file_forces_its_folder_to_be_reprobed() -> None:
    probe_results = {ONE: properties(**album_tags("1", "Wavy Gravy"))}
    listing = FolderListing(folder=FOLDER, audio=(stat(ONE, "01. Wavy Gravy.flac"),))
    scanner, store = build([listing], probe_results)
    scanner.run("H:/Music")

    touched = FolderListing(
        folder=FOLDER, audio=(stat(ONE, "01. Wavy Gravy.flac", mtime=999),)
    )
    again, _ = build([touched], probe_results, store=store)
    assert again.run("H:/Music").folders_probed == 1


def test_an_added_file_forces_its_folder_to_be_reprobed() -> None:
    probe_results = {
        ONE: properties(**album_tags("1", "Wavy Gravy")),
        TWO: properties(**album_tags("2", "Cutting Room")),
    }
    first = FolderListing(folder=FOLDER, audio=(stat(ONE, "01. Wavy Gravy.flac"),))
    scanner, store = build([first], probe_results)
    scanner.run("H:/Music")

    again, _ = build([two_file_listing()], probe_results, store=store)
    assert again.run("H:/Music").folders_probed == 1


def test_missing_files_are_counted_from_what_the_store_reports() -> None:
    scanner, store = build([two_file_listing()], {ONE: properties(), TWO: properties()})
    store.absent_result = 3
    report = scanner.run("H:/Music")
    assert report.files_absent == 3
    assert store.absent_calls == [frozenset({ONE, TWO})]


def test_a_root_level_folder_still_yields_an_album() -> None:
    """A library whose audio sits at the very top has no parent folder name."""
    listing = FolderListing(folder="Music", audio=(stat("Music/a.flac", "a.flac"),))
    scanner, _ = build([listing], {"Music/a.flac": properties(ALBUM=("Loose",))})
    album = scanner.run("Music").albums[0]
    assert album.identity.display_title == "Loose"


def test_an_empty_folder_path_is_survivable() -> None:
    listing = FolderListing(folder="", audio=(stat("a.flac", "a.flac"),))
    scanner, _ = build([listing], {"a.flac": properties(ALBUM=("Nowhere",))})
    assert scanner.run("").albums[0].identity.display_title == "Nowhere"


def test_the_report_counts_every_track_it_assembled() -> None:
    scanner, _ = build(
        [two_file_listing()],
        {
            ONE: properties(**album_tags("1", "Wavy Gravy")),
            TWO: properties(**album_tags("2", "Cutting Room")),
        },
    )
    assert scanner.run("H:/Music").track_count == 2


def test_a_file_reporting_no_sample_rate_is_reported_as_unreadable() -> None:
    """A truncated header must be reported, never crash the scan."""
    scanner, _ = build(
        [two_file_listing()],
        {
            ONE: properties(rate=0, **album_tags("1", "Wavy Gravy")),
            TWO: properties(rate=0, **album_tags("2", "Cutting Room")),
        },
    )
    report = scanner.run("H:/Music")
    assert report.albums == ()
    assert report.files_unreadable == 2
