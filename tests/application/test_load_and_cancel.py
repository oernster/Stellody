"""Showing the remembered library, then giving up on a scan part way through.

Two things that only matter because a real library is large: starting the
application must not walk it; quitting during a scan must not wait for one.
"""

from __future__ import annotations

from fakes import FakeProbe, FakeStore, FakeTextReader, FakeWalker, properties, stat

from stellody.application.ports import FolderListing
from stellody.application.scan import LibraryView, LoadLibrary, ScanLibrary

FOLDER = "H:/Music/Sasha/Involver"
ONE = f"{FOLDER}/01. Wavy Gravy.flac"
TWO = f"{FOLDER}/02. Cutting Room.flac"
OTHER = "H:/Music/Orbital/In Sides"
THREE = f"{OTHER}/01. The Girl With The Sun In Her Head.flac"


def listing(folder: str, paths: tuple[str, ...]) -> FolderListing:
    """One folder of ordinary tracks."""
    return FolderListing(
        folder=folder,
        audio=tuple(stat(path, path.rsplit("/", 1)[1]) for path in paths),
    )


def tagged(album: str, artist: str, title: str, track: str) -> dict:
    """A well-tagged track."""
    return {
        "ALBUM": (album,),
        "ALBUMARTIST": (artist,),
        "ARTIST": (artist,),
        "TITLE": (title,),
        "TRACKNUMBER": (track,),
    }


def scanned_store() -> FakeStore:
    """A store holding what one completed scan of two folders found."""
    store = FakeStore()
    scanner = ScanLibrary(
        FakeWalker((listing(FOLDER, (ONE, TWO)), listing(OTHER, (THREE,)))),
        FakeProbe(
            {
                ONE: properties(**tagged("Involver", "Sasha", "Wavy Gravy", "1")),
                TWO: properties(**tagged("Involver", "Sasha", "Cutting Room", "2")),
                THREE: properties(**tagged("In Sides", "Orbital", "The Girl", "1")),
            }
        ),
        FakeTextReader(None),
        store,
    )
    scanner.run("H:/Music")
    return store


def test_the_remembered_library_is_assembled_without_reading_any_music() -> None:
    """Launch must not walk the music folder; the store already knows."""
    view = LoadLibrary(scanned_store()).run()
    assert len(view.albums) == 2
    assert view.track_count == 3


def test_an_empty_store_loads_as_an_empty_library() -> None:
    view = LoadLibrary(FakeStore()).run()
    assert view.albums == ()
    assert view.track_count == 0


def test_a_view_with_no_albums_counts_no_tracks() -> None:
    assert LibraryView().track_count == 0


def test_a_cancelled_scan_stops_at_the_next_folder() -> None:
    """Qt cannot interrupt a running scan, so the scan has to be asked."""
    walker = FakeWalker((listing(FOLDER, (ONE, TWO)), listing(OTHER, (THREE,))))
    scanner = ScanLibrary(
        walker,
        FakeProbe({ONE: properties(), TWO: properties(), THREE: properties()}),
        FakeTextReader(None),
        FakeStore(),
    )
    seen: list[str] = []
    report = scanner.run(
        "H:/Music",
        progress=lambda step: seen.append(step.folder),
        cancelled=lambda: len(seen) >= 1,
    )
    assert report.cancelled is True
    assert seen == [FOLDER]


def test_a_cancelled_scan_reports_nothing_rather_than_a_short_library() -> None:
    """A short library read as a real one would look like albums had gone."""
    store = scanned_store()
    scanner = ScanLibrary(
        FakeWalker((listing(FOLDER, (ONE, TWO)),)),
        FakeProbe({ONE: properties(), TWO: properties()}),
        FakeTextReader(None),
        store,
    )
    report = scanner.run("H:/Music", cancelled=lambda: True)
    assert report.albums == ()
    assert report.cancelled is True
    # The store is untouched, so what was already known is still there.
    assert len(LoadLibrary(store).run().albums) == 2


def test_a_scan_that_finishes_is_not_marked_cancelled() -> None:
    scanner = ScanLibrary(
        FakeWalker((listing(FOLDER, (ONE, TWO)),)),
        FakeProbe({ONE: properties(), TWO: properties()}),
        FakeTextReader(None),
        FakeStore(),
    )
    assert scanner.run("H:/Music", cancelled=lambda: False).cancelled is False
