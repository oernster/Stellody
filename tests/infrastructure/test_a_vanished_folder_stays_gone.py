"""A folder that is gone from disk stays gone after a restart.

Measured on 2026-09-10 before this was fixed. With two folders scanned and then
one removed, a rescan showed one album and three tracks while a restart showed
two albums and five: the store still held the missing folder, the scan left it
off and the load read it straight back. Every rescan after a restart then named
the same album and the same tracks gone, which is how a real library reported
twelve tracks gone on every scan without a file changing.

Driven through the real store, the real walker and the real probe on real
files, since the disagreement was between two real readings of one table.
"""

from __future__ import annotations

import pathlib

import numpy as np
import soundfile as sf

from stellody.application.loading import LoadLibrary
from stellody.application.scan import ScanLibrary
from stellody.domain.changes import compare_libraries
from stellody.infrastructure.probe import AudioProbe
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.infrastructure.textfile import SidecarTextReader
from stellody.infrastructure.walker import FolderWalker

CD_RATE = 44100
KEPT_TRACKS = 3
GONE_TRACKS = 2


def _write(folder: pathlib.Path, count: int) -> None:
    """A folder of readable audio, named so it groups as its own album."""
    folder.mkdir(parents=True)
    wave = 0.2 * np.sin(2 * np.pi * 440 * np.arange(CD_RATE) / CD_RATE)
    single = wave.astype("float32")
    tone = np.column_stack([single, single])
    for number in range(1, count + 1):
        sf.write(folder / f"{number:02d} Track.flac", tone, CD_RATE)


def _remove(folder: pathlib.Path) -> None:
    """Take a folder off the disk, as a rename or a deletion reads."""
    for path in folder.iterdir():
        path.unlink()
    folder.rmdir()


def _scanner(store: SqliteLibraryStore) -> ScanLibrary:
    return ScanLibrary(FolderWalker(), AudioProbe(), SidecarTextReader(), store)


def _library(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """A kept folder and one that is about to go, scanned once."""
    root = tmp_path / "music"
    _write(root / "A kept album", KEPT_TRACKS)
    doomed = root / "A folder that goes"
    _write(doomed, GONE_TRACKS)
    return root, doomed


def test_a_restart_does_not_bring_a_vanished_folder_back(
    tmp_path: pathlib.Path,
) -> None:
    root, doomed = _library(tmp_path)
    store = SqliteLibraryStore(str(tmp_path / "library.sqlite3"))
    try:
        _scanner(store).run(str(root))
        _remove(doomed)
        rescanned = _scanner(store).run(str(root))
        loaded = LoadLibrary(store).run()
    finally:
        store.close()

    assert len(loaded.albums) == len(rescanned.albums)
    assert loaded.track_count == rescanned.track_count == KEPT_TRACKS


def test_a_rescan_after_a_restart_reports_nothing_gone(
    tmp_path: pathlib.Path,
) -> None:
    """What a listener saw: the same album named gone on every scan."""
    root, doomed = _library(tmp_path)
    store = SqliteLibraryStore(str(tmp_path / "library.sqlite3"))
    try:
        _scanner(store).run(str(root))
        _remove(doomed)
        _scanner(store).run(str(root))
        on_screen = LoadLibrary(store).run().albums
        again = _scanner(store).run(str(root))
    finally:
        store.close()

    change = compare_libraries(on_screen, again.albums)
    assert change.gone_albums == ()
    assert change.gone_tracks == 0
    assert change.nothing_changed is True


def test_a_folder_that_comes_back_is_read_again(tmp_path: pathlib.Path) -> None:
    """Leaving a folder out of the load must not lose it for good."""
    root, doomed = _library(tmp_path)
    store = SqliteLibraryStore(str(tmp_path / "library.sqlite3"))
    try:
        _scanner(store).run(str(root))
        _remove(doomed)
        _scanner(store).run(str(root))
        _write(doomed, GONE_TRACKS)
        returned = _scanner(store).run(str(root))
        loaded = LoadLibrary(store).run()
    finally:
        store.close()

    assert returned.track_count == KEPT_TRACKS + GONE_TRACKS
    assert loaded.track_count == KEPT_TRACKS + GONE_TRACKS


def test_a_folder_of_undecodable_audio_is_still_loaded(
    tmp_path: pathlib.Path,
) -> None:
    """A record with no file rows exists to say what cannot be played.

    It holds no file to be marked absent, so it must not be mistaken for a
    folder whose every file has gone.
    """
    root = tmp_path / "music"
    folder = root / "An album nothing decodes"
    folder.mkdir(parents=True)
    (folder / "01 Track.ape").write_bytes(b"")
    store = SqliteLibraryStore(str(tmp_path / "library.sqlite3"))
    try:
        _scanner(store).run(str(root))
        loaded = LoadLibrary(store).run()
    finally:
        store.close()

    assert any(".ape" in issue.detail for issue in loaded.issues)


def test_the_walker_knows_a_missing_root(tmp_path: pathlib.Path) -> None:
    """The one question a walk cannot answer about itself."""
    walker = FolderWalker()

    assert walker.reachable(str(tmp_path)) is True
    assert walker.reachable(str(tmp_path / "not connected")) is False
