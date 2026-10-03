"""A cue sheet or a picture added beside music already scanned is noticed.

A rescan compared the audio alone, so a cue sheet written beside a single file
album after its first scan was never read: the album stayed one long track for
ever, since nothing it compared had changed. A cover added later went the same
way, as did a cue sheet corrected in place.
"""

from __future__ import annotations

from fakes import FakeProbe, FakeStore, FakeTextReader, FakeWalker, properties, stat

from stellody.application.scan import ScanLibrary
from stellody.application.values import FolderListing

FOLDER = "H:/Music/Sasha/Involver"
SINGLE = f"{FOLDER}/Involver.flac"
CUE = f"{FOLDER}/Involver.cue"
COVER = f"{FOLDER}/cover.jpg"
PROBES = {SINGLE: properties(ALBUM=("Involver",))}


def folder(*sidecars) -> FolderListing:
    """The folder as the walker finds it, holding these cue sheets and pictures."""
    return FolderListing(
        folder=FOLDER,
        audio=(stat(SINGLE, "Involver.flac"),),
        cue_paths=tuple(item.path for item in sidecars if item.path == CUE),
        image_paths=tuple(item.path for item in sidecars if item.path == COVER),
        sidecars=tuple(sidecars),
    )


def scan(store: FakeStore, listing: FolderListing):
    """One scan of the folder into this store."""
    return ScanLibrary(
        FakeWalker((listing,)), FakeProbe(PROBES), FakeTextReader(None), store
    ).run("H:/Music")


def test_a_cue_sheet_added_later_rereads_the_folder() -> None:
    store = FakeStore()
    scan(store, folder())
    assert scan(store, folder(stat(CUE, "Involver.cue"))).folders_probed == 1


def test_a_cover_added_later_rereads_the_folder() -> None:
    store = FakeStore()
    scan(store, folder(stat(CUE, "Involver.cue")))
    report = scan(store, folder(stat(CUE, "Involver.cue"), stat(COVER, "cover.jpg")))
    assert report.folders_probed == 1


def test_a_cue_sheet_corrected_in_place_rereads_the_folder() -> None:
    store = FakeStore()
    scan(store, folder(stat(CUE, "Involver.cue")))
    report = scan(store, folder(stat(CUE, "Involver.cue", mtime=999)))
    assert report.folders_probed == 1


def test_a_cue_sheet_taken_away_rereads_the_folder() -> None:
    store = FakeStore()
    scan(store, folder(stat(CUE, "Involver.cue")))
    assert scan(store, folder()).folders_probed == 1


def test_unchanged_sidecars_still_let_the_folder_be_reused() -> None:
    store = FakeStore()
    scan(store, folder(stat(CUE, "Involver.cue"), stat(COVER, "cover.jpg")))
    report = scan(store, folder(stat(CUE, "Involver.cue"), stat(COVER, "cover.jpg")))
    assert report.folders_reused == 1
    assert report.folders_probed == 0
