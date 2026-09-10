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
from m4a_support import decoded
from widened_support import FIXTURE_TAGS, WIDENED_WRITERS, write_wavpack

from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.domain.health import IssueKind
from stellody.domain.track import TrackSource
from stellody.infrastructure.decode import DecodeError, open_source
from stellody.infrastructure.packet_decode import PacketReader
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


# The formats proved by a fixture rather than by a file somebody owns, with
# the suffix each one is written under. Stated here rather than imported from the
# walker for the same reason the table above is: a suffix taken by the walker
# with no scan behind it must fail this file rather than pass in silence.
WIDENED = (("wma", ".wma"), ("wv", ".wv"), ("aac", ".aac"))

# What the two lossy widened formats must report as their stored depth, which
# is the requirement this whole change turns on.
NO_STORED_DEPTH = 0

# The depths a WavPack fixture is written at, each stated to the encoder
# rather than defaulted, since its default is eight bit.
WAVPACK_DEPTHS = (16, 32)

# How far the reader's own decode may sit from an independent one, as a share
# of full scale. The two are the same FFmpeg reached two different ways, so
# they agree on the sound; they need not agree on the encoder's priming
# frames, which is what this tolerance covers rather than any codec error.
DECODE_RMS_TOLERANCE = 0.05

# Enough of a signal to prove the frames are the tone rather than silence,
# which is what a reader that opens a file and reads nothing would give.
AUDIBLE_RMS = 0.05


def _widened_library(root: pathlib.Path, tags: dict[str, str] | None) -> None:
    """One folder per widened format, each holding one encoded fixture.

    Each states an album of its own. Measured with one album name across all
    three, the scan assembled two albums holding two tracks: the WMA and the
    WavPack state the same album and the same track number, so the duplicate
    rules read them as one record held twice and kept the lossless one. That
    is the rules working; it is not what these tests are about.

    The AAC file stood apart in that measurement for a different reason worth
    knowing: an ADTS stream carries no tag block at all, so it states nothing
    whatever a test asks FFmpeg to write; its album name comes from its folder
    as an untagged file's always does.
    """
    for label, suffix in WIDENED:
        folder = root / f"An album in {label}"
        folder.mkdir(parents=True)
        stated = None if tags is None else dict(tags, album=f"An album in {label}")
        WIDENED_WRITERS[label](folder / f"album{suffix}", tags=stated)


def _widened_report(tmp_path: pathlib.Path, tags: dict[str, str] | None = None):
    """A real scan of a real library holding one file of each widened format."""
    root = tmp_path / "music"
    _widened_library(root, tags)
    store = SqliteLibraryStore(str(tmp_path / "library.db"))
    try:
        return _scanner(store).run(str(root))
    finally:
        store.close()


def _read_all(reader) -> np.ndarray:
    """Everything the reader will give, as one block of frames."""
    blocks = []
    while True:
        block = reader.read(CD_RATE)
        if block.shape[0] == 0:
            return np.concatenate(blocks, axis=0) if blocks else np.zeros((0, 2))
        blocks.append(block)


def test_the_widened_suffixes_are_taken(tmp_path: pathlib.Path) -> None:
    """FR-F01. Taken as tracks rather than also reported as missing."""
    report = _widened_report(tmp_path, FIXTURE_TAGS)

    assert report.files_unreadable == 0
    assert report.track_count == len(WIDENED)
    assert len(report.albums) == len(WIDENED)
    unplayable = [i for i in report.issues if i.kind is IssueKind.UNPLAYABLE_FORMAT]
    assert unplayable == []


@pytest.mark.parametrize(("label", "suffix"), WIDENED)
def test_each_widened_format_decodes_through_the_packet_reader(
    tmp_path: pathlib.Path, label: str, suffix: str
) -> None:
    """FR-F02. The reader that counts packets back into frame positions.

    Checked against a decode written straight against PyAV rather than
    against the reader, so the two answers do not share their arithmetic.
    """
    path = tmp_path / f"album{suffix}"
    WIDENED_WRITERS[label](path, tags=FIXTURE_TAGS)

    reader = open_source(TrackSource(str(path)))
    try:
        assert isinstance(reader, PacketReader)
        assert reader.sample_rate == CD_RATE
        frames = _read_all(reader)
    finally:
        reader.close()

    independent = decoded(path)
    assert frames.shape[0] > 0
    assert float(np.sqrt(np.mean(frames**2))) > AUDIBLE_RMS
    difference = abs(
        float(np.sqrt(np.mean(frames**2))) - float(np.sqrt(np.mean(independent**2)))
    )
    assert difference < DECODE_RMS_TOLERANCE


def test_a_widened_suffix_that_will_not_decode_says_so(tmp_path: pathlib.Path) -> None:
    """FR-F03. A suffix taken on a fixture will meet files a fixture is not."""
    impostor = tmp_path / "album.wma"
    impostor.write_text("this is not a WMA at all", encoding="utf-8")

    with pytest.raises(DecodeError) as raised:
        open_source(TrackSource(str(impostor)))

    assert "album.wma" in str(raised.value)


def test_asf_tags_arrive_under_the_domain_names(tmp_path: pathlib.Path) -> None:
    """FR-F04. Microsoft's spellings translated into the one vocabulary."""
    path = tmp_path / "album.wma"
    WIDENED_WRITERS["wma"](path, tags=FIXTURE_TAGS)

    properties = AudioProbe().read(str(path))

    assert properties is not None
    assert properties.tags["ALBUM"] == (FIXTURE_TAGS["album"],)
    assert properties.tags["ARTIST"] == (FIXTURE_TAGS["artist"],)
    assert properties.tags["ALBUMARTIST"] == (FIXTURE_TAGS["album_artist"],)
    assert properties.tags["TRACKNUMBER"] == (FIXTURE_TAGS["track"],)
    assert properties.tags["TITLE"] == (FIXTURE_TAGS["title"],)


def test_an_untagged_widened_file_still_assembles(tmp_path: pathlib.Path) -> None:
    """FR-F05. A file that states nothing is scanned, never refused."""
    root = tmp_path / "music"
    folder = root / "An album in wv"
    folder.mkdir(parents=True)
    write_wavpack(folder / "album.wv", tags=None)
    store = SqliteLibraryStore(str(tmp_path / "library.db"))
    try:
        report = _scanner(store).run(str(root))
    finally:
        store.close()

    assert report.files_unreadable == 0
    assert report.track_count == 1
    track = report.albums[0].tracks[0]
    assert track.title


@pytest.mark.parametrize("label", ["wma", "aac"])
def test_a_lossy_widened_format_states_no_depth(
    tmp_path: pathlib.Path, label: str
) -> None:
    """FR-F06. The promise the README leads with, held by reporting."""
    suffix = dict(WIDENED)[label]
    path = tmp_path / f"album{suffix}"
    WIDENED_WRITERS[label](path, tags=FIXTURE_TAGS)

    properties = AudioProbe().read(str(path))

    assert properties is not None
    assert properties.bit_depth == NO_STORED_DEPTH


@pytest.mark.parametrize("depth", WAVPACK_DEPTHS)
def test_wavpack_keeps_the_depth_it_states(tmp_path: pathlib.Path, depth: int) -> None:
    """FR-F07. The half a guard written only against lossy formats would break."""
    path = tmp_path / f"album{depth}.wv"
    write_wavpack(path, depth=depth, tags=FIXTURE_TAGS)

    properties = AudioProbe().read(str(path))

    assert properties is not None
    assert properties.bit_depth == depth


def test_the_formats_left_out_are_still_reported(tmp_path: pathlib.Path) -> None:
    """FR-F08. Widening what is taken must not narrow what is said out loud."""
    root = tmp_path / "music"
    folder = root / "An album nothing decodes"
    folder.mkdir(parents=True)
    (folder / "01 Track.ape").write_bytes(b"")
    store = SqliteLibraryStore(str(tmp_path / "library.db"))
    try:
        report = _scanner(store).run(str(root))
    finally:
        store.close()

    unplayable = [i for i in report.issues if i.kind is IssueKind.UNPLAYABLE_FORMAT]
    assert len(unplayable) == 1
    assert ".ape" in unplayable[0].detail
    assert report.albums == ()
