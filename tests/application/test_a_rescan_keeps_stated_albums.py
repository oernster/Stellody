"""A rescan must read an album the way the library on screen reads it.

Reported from a real library on 2026-09-10: every rescan named the same ten
albums as new and the same two as gone, on a run where no folder was re-read
at all. Nothing had changed on disk; the same music was simply being assembled
two different ways.

`LoadLibrary` lays the stated album values over its entries before assembling.
`ScanLibrary` did not, so an album somebody had stated a title or an artist for
came back off a scan under its raw tags: a different identity, which reads as
the stated album leaving and a raw-tagged one arriving, every single time and
for ever, since neither reading ever becomes the other.

Driven through the real store, the real walker and the real probe on real
files, because the two assemblies are the whole subject: a fake of either one
would agree with whichever it was written against.
"""

from __future__ import annotations

import pathlib

import numpy as np
import soundfile as sf

from stellody.application.editing import folders_of
from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.domain.changes import compare_libraries
from stellody.domain.overrides import AlbumEdit, AlbumField
from stellody.infrastructure.probe import AudioProbe
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.infrastructure.textfile import SidecarTextReader
from stellody.infrastructure.walker import FolderWalker

CD_RATE = 44100
TRACKS = 2
STATED_TITLE = "Sunset at Stone Henge"


def _write_album(root: pathlib.Path) -> None:
    """One folder of readable audio, named so it groups as its own album."""
    folder = root / "Sunset at Stonehenge"
    folder.mkdir(parents=True)
    wave = 0.2 * np.sin(2 * np.pi * 440 * np.arange(CD_RATE) / CD_RATE)
    single = wave.astype("float32")
    tone = np.column_stack([single, single])
    for number in range(1, TRACKS + 1):
        sf.write(folder / f"{number:02d} Track.flac", tone, CD_RATE)


def _scanner(store: SqliteLibraryStore) -> ScanLibrary:
    return ScanLibrary(FolderWalker(), AudioProbe(), SidecarTextReader(), store)


def _stated(store: SqliteLibraryStore, root: str) -> None:
    """State a title for the album, as the edit dialog does."""
    first = _scanner(store).run(root)
    album = first.albums[0]
    store.state_album_edits(
        tuple(
            AlbumEdit(folder=folder, field=AlbumField.TITLE, value=STATED_TITLE)
            for folder in folders_of(album)
        )
    )


def test_a_rescan_reads_a_stated_album_as_the_library_does(
    tmp_path: pathlib.Path,
) -> None:
    """The defect itself: two readings of one unchanged library must agree."""
    root = tmp_path / "music"
    _write_album(root)
    store = SqliteLibraryStore(str(tmp_path / "library.sqlite3"))
    try:
        _stated(store, str(root))
        loaded = LoadLibrary(store).run()
        rescanned = _scanner(store).run(str(root))
    finally:
        store.close()

    assert loaded.albums[0].identity.title == STATED_TITLE
    assert rescanned.albums[0].identity.title == STATED_TITLE


def test_a_rescan_of_an_unchanged_library_reports_nothing(
    tmp_path: pathlib.Path,
) -> None:
    """What a listener actually sees, which is the report that never settled.

    The comparison is the one the window makes: the library on screen against
    the library the scan produced. It must say nothing changed; it must go on
    saying that however many times the scan is run.
    """
    root = tmp_path / "music"
    _write_album(root)
    store = SqliteLibraryStore(str(tmp_path / "library.sqlite3"))
    try:
        _stated(store, str(root))
        on_screen = LoadLibrary(store).run().albums
        for _ in range(TRACKS):
            rescanned = _scanner(store).run(str(root))
            change = compare_libraries(on_screen, rescanned.albums)
            assert change.new_albums == (), change.new_albums
            assert change.gone_albums == (), change.gone_albums
            assert change.nothing_changed is True
            on_screen = rescanned.albums
    finally:
        store.close()
