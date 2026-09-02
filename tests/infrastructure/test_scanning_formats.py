"""Scanning a real folder of each format, all the way to an assembled library.

This is the test whose absence let a broken release through. `test_probing.py`
proves the probe reads every format; the domain tests prove a `Track` obeys its
own rules. Neither joins the two, so a probe reporting nought for a lossy file
and a `Track` refusing nought both passed while the two together could not scan
a single MP3. The scan raised; because folder records are written before the
library is assembled, every later start then failed to load as well.

So these tests use the real walker, the real probe and the real store on real
files, asserting the whole way through to albums. Nothing here is faked,
because everything that was faked is what hid the defect.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest
import soundfile as sf

from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.infrastructure.probe import OPUS_SAMPLE_RATE, AudioProbe
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.infrastructure.textfile import SidecarTextReader
from stellody.infrastructure.walker import FolderWalker

CD_RATE = 44100
SECONDS = 1
# Every format the walk takes, against the rate it must be written at. The
# suffixes are stated here rather than imported so that a suffix added to the
# walker without a scan behind it fails this test instead of passing silently.
FORMATS = (
    ("flac", "album.flac", CD_RATE),
    ("mp3", "album.mp3", CD_RATE),
    ("ogg", "album.ogg", CD_RATE),
    ("opus", "album.opus", OPUS_SAMPLE_RATE),
    ("wav", "album.wav", CD_RATE),
    ("aiff", "album.aiff", CD_RATE),
)
# The formats that state a depth, so a track from one may be bit perfect.
STATES_DEPTH = frozenset({"flac", "wav", "aiff"})


def _tone(rate: int) -> np.ndarray:
    """One second of stereo, which is enough to have a length to read."""
    wave = 0.2 * np.sin(2 * np.pi * 440 * np.arange(rate * SECONDS) / rate)
    single = wave.astype("float32")
    return np.column_stack([single, single])


def _write(directory: pathlib.Path, name: str, rate: int) -> None:
    """One audio file, written by its suffix except where Opus needs saying."""
    if name.endswith(".opus"):
        sf.write(directory / name, _tone(rate), rate, format="OGG", subtype="OPUS")
        return
    sf.write(directory / name, _tone(rate), rate)


def _library(root: pathlib.Path) -> None:
    """One folder per format, each named so it groups as its own album."""
    for label, name, rate in FORMATS:
        folder = root / f"An album in {label}"
        folder.mkdir(parents=True)
        _write(folder, name, rate)


def _scanner(store: SqliteLibraryStore) -> ScanLibrary:
    return ScanLibrary(FolderWalker(), AudioProbe(), SidecarTextReader(), store)


def test_every_readable_format_scans_into_an_album(tmp_path: pathlib.Path) -> None:
    """The whole chain: walk, probe, store, assemble. No fakes anywhere."""
    root = tmp_path / "music"
    _library(root)
    store = SqliteLibraryStore(str(tmp_path / "library.db"))
    try:
        report = _scanner(store).run(str(root))
    finally:
        store.close()

    assert report.files_unreadable == 0
    assert len(report.albums) == len(FORMATS)
    assert report.track_count == len(FORMATS)


def test_a_lossy_track_states_no_depth_and_is_not_high_resolution(
    tmp_path: pathlib.Path,
) -> None:
    """The honesty rule, read off the assembled library rather than the probe.

    Opus is the case worth having: it decodes at 48 kHz whatever it was
    encoded from, so a rate test alone would call it better than CD.
    """
    root = tmp_path / "music"
    _library(root)
    store = SqliteLibraryStore(str(tmp_path / "library.db"))
    try:
        report = _scanner(store).run(str(root))
    finally:
        store.close()

    by_label = {album.identity.title: album for album in report.albums}
    for label, _, _ in FORMATS:
        album = by_label[f"An album in {label}"]
        track = album.tracks[0]
        assert track.states_depth is (label in STATES_DEPTH), label
        if label not in STATES_DEPTH:
            assert track.bit_depth == 0, label
            assert track.is_high_resolution is False, label


def test_a_scanned_library_still_loads_on_the_next_start(
    tmp_path: pathlib.Path,
) -> None:
    """The half that made the defect persistent rather than merely annoying.

    Folder records are saved inside the walk, before the library is assembled,
    so a rule that assembly refuses is already in the store by the time it is
    refused. A load reads the same records through the same assembly, which is
    how one unscannable file became an application that would not start.
    """
    root = tmp_path / "music"
    _library(root)
    database = str(tmp_path / "library.db")
    store = SqliteLibraryStore(database)
    try:
        scanned = _scanner(store).run(str(root))
    finally:
        store.close()

    reopened = SqliteLibraryStore(database)
    try:
        loaded = LoadLibrary(reopened).run()
    finally:
        reopened.close()

    assert len(loaded.albums) == len(scanned.albums)
    assert loaded.track_count == scanned.track_count


@pytest.mark.parametrize("label", sorted(STATES_DEPTH))
def test_a_lossless_format_still_states_its_depth(
    tmp_path: pathlib.Path, label: str
) -> None:
    """The fix must not buy honesty about lossy files by losing it elsewhere."""
    root = tmp_path / "music"
    _library(root)
    store = SqliteLibraryStore(str(tmp_path / "library.db"))
    try:
        report = _scanner(store).run(str(root))
    finally:
        store.close()

    album = {a.identity.title: a for a in report.albums}[f"An album in {label}"]
    assert album.tracks[0].bit_depth > 0
    assert album.tracks[0].states_depth is True
