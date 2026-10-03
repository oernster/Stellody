"""A folder the system will not let the walk open is unreadable, not gone.

Measured with a subfolder refusing to be listed: the walk passed over it in
silence, so its album was reported as renamed, moved or removed under "Scan
finished" and its files were marked absent. Nothing about the music had
changed; only the permission had. A file whose size could not be read went
the same way, dropped without being counted.
"""

from __future__ import annotations

from fakes import FakeProbe, FakeStore, FakeTextReader, FakeWalker, properties, stat

from stellody.application.scan import ScanLibrary, ScanProgress
from stellody.application.values import FolderListing
from stellody.domain.health import IssueKind

BAND = "H:/Music/Band"
KEPT = f"{BAND}/Kept"
LOCKED = f"{BAND}/Locked"
INNER = f"{LOCKED}/CD1"
NEIGHBOUR = f"{BAND}/Locked Out"
KEPT_FILE = f"{KEPT}/01.flac"
LOCKED_FILE = f"{LOCKED}/01.flac"
INNER_FILE = f"{INNER}/01.flac"
NEIGHBOUR_FILE = f"{NEIGHBOUR}/01.flac"


def listing(folder: str, path: str) -> FolderListing:
    """One folder holding one track."""
    return FolderListing(folder=folder, audio=(stat(path, "01.flac"),))


def refused(folder: str) -> FolderListing:
    """What the walker yields for a folder it could not list."""
    return FolderListing(folder=folder, audio=(), listed=False)


def tagged(album: str) -> object:
    """A track tagged with its own album, so albums are told apart."""
    return properties(ALBUM=(album,), ALBUMARTIST=("Band",), TRACKNUMBER=("1",))


PROBES = {
    KEPT_FILE: tagged("Kept"),
    LOCKED_FILE: tagged("Locked"),
    INNER_FILE: tagged("Inner"),
    NEIGHBOUR_FILE: tagged("Locked Out"),
}


def scanned_once(*listings: FolderListing) -> FakeStore:
    """A store holding what one ordinary scan of these folders found."""
    store = FakeStore()
    ScanLibrary(
        FakeWalker(listings), FakeProbe(PROBES), FakeTextReader(None), store
    ).run(BAND)
    return store


def rescan(store: FakeStore, *listings: FolderListing, progress=None):
    """Scan again over these listings into the same store."""
    return ScanLibrary(
        FakeWalker(listings), FakeProbe(PROBES), FakeTextReader(None), store
    ).run(BAND, progress=progress)


def titles(report) -> set[str]:
    return {album.identity.display_title for album in report.albums}


def test_a_refused_folder_keeps_its_album_and_is_counted_unreadable() -> None:
    store = scanned_once(listing(KEPT, KEPT_FILE), listing(LOCKED, LOCKED_FILE))
    report = rescan(store, listing(KEPT, KEPT_FILE), refused(LOCKED))
    assert titles(report) == {"Kept", "Locked"}
    assert report.files_unreadable == 1
    assert LOCKED_FILE in store.absent_calls[-1], "not marked absent"


def test_a_refused_folder_is_named_in_the_report() -> None:
    store = scanned_once(listing(LOCKED, LOCKED_FILE))
    report = rescan(store, refused(LOCKED))
    found = [i for i in report.issues if i.kind is IssueKind.UNREADABLE_FOLDER]
    assert [(issue.album, issue.paths) for issue in found] == [(LOCKED, (LOCKED,))]


def test_a_refused_folder_is_not_counted_as_checked_or_progress() -> None:
    store = scanned_once(listing(KEPT, KEPT_FILE), listing(LOCKED, LOCKED_FILE))
    seen: list[ScanProgress] = []
    report = rescan(
        store, listing(KEPT, KEPT_FILE), refused(LOCKED), progress=seen.append
    )
    assert report.folders_checked == 1
    assert [step.folder for step in seen] == [KEPT]


def test_a_folder_inside_a_refused_one_is_kept_too() -> None:
    """The walk cannot go into a folder it cannot list, so cannot reach these."""
    store = scanned_once(listing(LOCKED, LOCKED_FILE), listing(INNER, INNER_FILE))
    report = rescan(store, refused(LOCKED))
    assert titles(report) == {"Locked", "Inner"}
    assert INNER_FILE in store.absent_calls[-1]


def test_a_neighbour_sharing_the_start_of_its_name_is_not_kept() -> None:
    """Beneath means beneath: "Locked Out" is beside "Locked", not inside it."""
    store = scanned_once(
        listing(LOCKED, LOCKED_FILE), listing(NEIGHBOUR, NEIGHBOUR_FILE)
    )
    report = rescan(store, refused(LOCKED))
    assert titles(report) == {"Locked"}
    assert NEIGHBOUR_FILE not in store.absent_calls[-1]


def test_a_refused_root_keeps_the_whole_library() -> None:
    store = scanned_once(listing(KEPT, KEPT_FILE), listing(LOCKED, LOCKED_FILE))
    report = rescan(store, refused(BAND))
    assert titles(report) == {"Kept", "Locked"}
    assert report.files_absent == 0


def test_a_file_whose_size_could_not_be_read_is_counted() -> None:
    store = FakeStore()
    awkward = FolderListing(
        folder=KEPT,
        audio=(stat(KEPT_FILE, "01.flac"),),
        unreadable=(f"{KEPT}/02.flac",),
    )
    report = rescan(store, awkward)
    assert report.files_unreadable == 1
    found = [i for i in report.issues if i.kind is IssueKind.UNREADABLE_FILE]
    assert [issue.paths for issue in found] == [(f"{KEPT}/02.flac",)]
