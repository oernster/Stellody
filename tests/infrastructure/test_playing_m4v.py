"""Playing an M4V, which is an MP4 carrying a picture beside the sound.

Measured off the reference library before any of this was written: 26 video
files across 10 album folders, every one .m4v, every one H.264 with AAC at
48 kHz, every one a bonus track inside an album the library already holds
rather than a film beside it. The packet reader was pointed at three of them
unmodified and decoded their sound correctly, so this milestone needed no
second decoder; what it needed was for the walk to stop ignoring the files and
for the decoder to route them to the reader that can already open them.

These tests hold that routing to the same bar the M4A suite holds: not similar
audio, the same samples. The picture itself is shown elsewhere and proved
elsewhere; nothing on the sound path knows it is there, which is the property
worth pinning here.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest
from m4a_support import CHANNELS, RATE, decoded
from video_support import write_m4v

from stellody.domain.track import TrackSource
from stellody.infrastructure.decode import SourceReader, open_source
from stellody.infrastructure.packet_decode import PacketReader
from stellody.infrastructure.walker import FolderWalker

SECONDS = 2
FRAMES = RATE * SECONDS
BLOCK = 4096


@pytest.fixture(scope="module")
def bonus(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """One video file, encoded once for the whole module."""
    folder = tmp_path_factory.mktemp("m4v")
    return write_m4v(folder / "12 Bonus.m4v", frames=FRAMES)


@pytest.fixture(scope="module")
def reference(bonus: pathlib.Path) -> np.ndarray:
    """What its audio stream decodes to, answered without the reader under test."""
    return decoded(bonus)


def _read_all(reader: PacketReader | SourceReader) -> np.ndarray:
    """Every frame the reader will hand over, read in blocks as the engine does."""
    blocks = []
    while True:
        block = reader.read(BLOCK)
        if block.shape[0] == 0:
            return np.concatenate(blocks, axis=0) if blocks else np.zeros((0, CHANNELS))
        blocks.append(block)


class TestChoosingTheReader:
    def test_an_m4v_gets_the_packet_reader(self, bonus: pathlib.Path) -> None:
        """libsndfile cannot open the container, so the choice must not reach it."""
        with open_source(TrackSource(path=str(bonus))) as reader:
            assert isinstance(reader, PacketReader)

    def test_the_choice_ignores_the_case_of_the_suffix(
        self, tmp_path: pathlib.Path, bonus: pathlib.Path
    ) -> None:
        shouted = tmp_path / "12 BONUS.M4V"
        shouted.write_bytes(bonus.read_bytes())
        with open_source(TrackSource(path=str(shouted))) as reader:
            assert isinstance(reader, PacketReader)


class TestReadingItThrough:
    def test_it_decodes_the_same_audio_the_codec_does(
        self, bonus: pathlib.Path, reference: np.ndarray
    ) -> None:
        """Not merely similar audio: the same samples, as for an M4A."""
        with open_source(TrackSource(path=str(bonus))) as reader:
            read = _read_all(reader)
        assert read.shape[0] > 0
        assert np.array_equal(read, reference[: read.shape[0]])

    def test_it_states_the_rate_and_the_channels(self, bonus: pathlib.Path) -> None:
        with open_source(TrackSource(path=str(bonus))) as reader:
            assert reader.sample_rate == RATE
            assert reader.channels == CHANNELS

    def test_the_source_says_it_carries_a_picture(self, bonus: pathlib.Path) -> None:
        """The sound path is unaffected; the source still says what it holds."""
        assert TrackSource(path=str(bonus)).carries_picture is True


class TestTheWalkTakesIt:
    def test_a_video_file_is_a_track_in_its_album(
        self, tmp_path: pathlib.Path, bonus: pathlib.Path
    ) -> None:
        """The finding that opened this work: 26 such files were invisible."""
        album = tmp_path / "Album"
        album.mkdir()
        (album / "12 Bonus.m4v").write_bytes(bonus.read_bytes())
        listings = list(FolderWalker().walk(str(tmp_path)))
        assert [pathlib.Path(stat.path).name for stat in listings[0].audio] == [
            "12 Bonus.m4v"
        ]

    def test_a_folder_holding_only_video_is_still_an_album(
        self, tmp_path: pathlib.Path, bonus: pathlib.Path
    ) -> None:
        """It used to yield no listing at all, so the folder was simply absent."""
        album = tmp_path / "Video Only"
        album.mkdir()
        (album / "01 Bonus.m4v").write_bytes(bonus.read_bytes())
        assert FolderWalker().count(str(tmp_path)) == 1
