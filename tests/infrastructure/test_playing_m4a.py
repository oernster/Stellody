"""Playing an M4A, which libsndfile cannot open at all.

Measured off the reference library before any of this was written: 126 folders
held nothing but M4A files, 1375 of them; every one of those folders was
absent from the library rather than wrong in it. This is the decoder that
closes that gap, driven through real encoded files rather than stand-ins.

The three tests that matter are the three things that were measured and could
have been assumed instead: that a seek lands on the frame it was given rather
than near it, that the stated length is never more than the file will actually
decode and that a lossy file never claims a bit depth.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest
from m4a_support import CHANNELS, RATE, decoded, write_m4a

from stellody.domain.track import TrackSource
from stellody.infrastructure.decode import DecodeError, SourceReader, open_source
from stellody.infrastructure.packet_decode import PacketReader

SECONDS = 2
FRAMES = RATE * SECONDS
BLOCK = 4096

# How far a seek may land from the same frame reached by playing forward.
#
# Bit identity is the right bar and it is met on the reference library: every
# seek into a real iTunes file matched exactly, to the last bit. It is not met
# on a file FFmpeg encoded here, which retains about 3.1e-4 of full scale, some
# 70 dB down and inaudible. That residual is a property of the file rather than
# of this reader: plain PyAV, seeking the same fixture with no reader involved,
# differs by the same amount; adding pre-roll does not shift it.
#
# The tolerance is set three times above that and five hundred times below the
# fault it exists to catch: a seek with no pre-roll at all lands 0.5 out, so
# this still fails decisively if the pre-roll is ever removed.
SEEK_TOLERANCE = 1e-3


@pytest.fixture(scope="module")
def lossy(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """One AAC file, encoded once for the whole module."""
    folder = tmp_path_factory.mktemp("m4a")
    return write_m4a(folder / "track.m4a", frames=FRAMES)


@pytest.fixture(scope="module")
def reference(lossy: pathlib.Path) -> np.ndarray:
    """What that file decodes to, answered without the reader under test."""
    return decoded(lossy)


def _read_all(reader: PacketReader) -> np.ndarray:
    """Every frame the reader will hand over, read in blocks as the engine does."""
    blocks = []
    while True:
        block = reader.read(BLOCK)
        if block.shape[0] == 0:
            return np.concatenate(blocks, axis=0) if blocks else np.zeros((0, CHANNELS))
        blocks.append(block)


class TestChoosingTheReader:
    """`open_source` is the only place that knows there are two readers."""

    def test_an_m4a_gets_the_packet_reader(self, lossy: pathlib.Path) -> None:
        with open_source(TrackSource(path=str(lossy))) as reader:
            assert isinstance(reader, PacketReader)

    def test_the_choice_ignores_the_case_of_the_suffix(
        self, tmp_path: pathlib.Path, lossy: pathlib.Path
    ) -> None:
        """A ripper that wrote .M4A must not fall through to libsndfile."""
        shouted = tmp_path / "TRACK.M4A"
        shouted.write_bytes(lossy.read_bytes())
        with open_source(TrackSource(path=str(shouted))) as reader:
            assert isinstance(reader, PacketReader)

    def test_everything_else_still_gets_soundfile(self, tmp_path: pathlib.Path) -> None:
        soundfile = pytest.importorskip("soundfile")
        path = tmp_path / "track.wav"
        soundfile.write(str(path), np.zeros((RATE, CHANNELS), dtype="float32"), RATE)
        with open_source(TrackSource(path=str(path))) as reader:
            assert isinstance(reader, SourceReader)

    def test_a_path_with_no_suffix_at_all_still_chooses_something(
        self, tmp_path: pathlib.Path
    ) -> None:
        """A dot inside a folder name is not a suffix on the file."""
        folder = tmp_path / "album.2003"
        folder.mkdir()
        with pytest.raises(DecodeError):
            open_source(TrackSource(path=str(folder / "untitled")))


class TestReadingItThrough:
    def test_it_decodes_the_same_audio_the_codec_does(
        self, lossy: pathlib.Path, reference: np.ndarray
    ) -> None:
        """Not merely similar audio: the same samples."""
        with open_source(TrackSource(path=str(lossy))) as reader:
            read = _read_all(reader)
        assert np.array_equal(read, reference[: read.shape[0]])

    def test_it_never_claims_more_than_the_file_decodes(
        self, lossy: pathlib.Path, reference: np.ndarray
    ) -> None:
        """Overstating is the harmful direction, so it is the one pinned here.

        The stated length is not the decoded length and the gap runs both ways
        depending on who wrote the file: an iTunes one overstates by exactly
        its priming; this one, written by FFmpeg, understates because its
        trailing padding decodes as real packets. Taking the priming off is
        exact for the first and short for the second; short is safe: the
        position never runs past audio that exists.
        """
        with open_source(TrackSource(path=str(lossy))) as reader:
            assert 0 < reader.frame_count <= reference.shape[0]

    def test_it_reads_everything_it_said_it_held(self, lossy: pathlib.Path) -> None:
        with open_source(TrackSource(path=str(lossy))) as reader:
            assert _read_all(reader).shape[0] == reader.frame_count

    def test_it_states_the_rate_and_the_channels(self, lossy: pathlib.Path) -> None:
        with open_source(TrackSource(path=str(lossy))) as reader:
            assert reader.sample_rate == RATE
            assert reader.channels == CHANNELS

    def test_reading_past_the_end_gives_nothing_rather_than_raising(
        self, lossy: pathlib.Path
    ) -> None:
        """An empty block is how the feeder thread learns the track is over."""
        with open_source(TrackSource(path=str(lossy))) as reader:
            _read_all(reader)
            spare = reader.read(BLOCK)
        assert spare.shape == (0, CHANNELS)

    def test_every_block_is_two_dimensional(self, lossy: pathlib.Path) -> None:
        with open_source(TrackSource(path=str(lossy))) as reader:
            assert reader.read(BLOCK).shape[1] == CHANNELS


class TestSeeking:
    """The measurement that forced the pre-roll: a seek must land, not land near.

    See SEEK_TOLERANCE above for why these compare within a bound rather than
    for bit identity, plus the measurement that sets the bound.
    """

    @pytest.mark.parametrize("target", [0, 1000, RATE, RATE + 137, FRAMES // 2])
    def test_it_lands_on_the_frame_it_was_given(
        self, lossy: pathlib.Path, reference: np.ndarray, target: int
    ) -> None:
        """Matches a decode that played forward to the same place.

        Without pre-roll this differed by as much as half of full scale, which
        is not a rounding difference; it is the codec asked to start cold.
        """
        with open_source(TrackSource(path=str(lossy))) as reader:
            reader.seek(target)
            got = reader.read(1000)
        assert np.allclose(got, reference[target : target + 1000], atol=SEEK_TOLERANCE)

    def test_the_reported_position_follows_the_seek(self, lossy: pathlib.Path) -> None:
        with open_source(TrackSource(path=str(lossy))) as reader:
            reader.seek(RATE)
            assert reader.frame == RATE
            reader.read(100)
            assert reader.frame == RATE + 100

    def test_seeking_backwards_lands_correctly_too(
        self, lossy: pathlib.Path, reference: np.ndarray
    ) -> None:
        """The buffer left over from the first read must not leak into the second."""
        with open_source(TrackSource(path=str(lossy))) as reader:
            reader.seek(FRAMES // 2)
            reader.read(BLOCK)
            reader.seek(1000)
            got = reader.read(500)
        assert np.allclose(got, reference[1000:1500], atol=SEEK_TOLERANCE)

    def test_a_seek_past_the_end_is_clamped_to_it(self, lossy: pathlib.Path) -> None:
        with open_source(TrackSource(path=str(lossy))) as reader:
            reader.seek(reader.frame_count * 2)
            assert reader.frame == reader.frame_count
            assert reader.read(BLOCK).shape[0] == 0

    def test_a_negative_seek_is_clamped_to_the_start(
        self, lossy: pathlib.Path, reference: np.ndarray
    ) -> None:
        with open_source(TrackSource(path=str(lossy))) as reader:
            reader.seek(-5000)
            assert reader.frame == 0
            assert np.allclose(reader.read(500), reference[:500], atol=SEEK_TOLERANCE)


class TestOneCueSheetTrackOfIt:
    """The slice abstraction has to hold; otherwise a cue sheet stops working."""

    def _slice(self, path: pathlib.Path, start: int, end: int) -> TrackSource:
        return TrackSource(path=str(path), start_frame=start, end_frame=end)

    def test_a_slice_holds_only_its_own_frames(self, lossy: pathlib.Path) -> None:
        with open_source(self._slice(lossy, RATE, RATE * 2)) as reader:
            assert reader.frame_count == RATE

    def test_a_slice_starts_at_its_own_start(
        self, lossy: pathlib.Path, reference: np.ndarray
    ) -> None:
        with open_source(self._slice(lossy, RATE, RATE * 2)) as reader:
            got = reader.read(1000)
        assert np.allclose(got, reference[RATE : RATE + 1000], atol=SEEK_TOLERANCE)

    def test_frame_nought_of_a_slice_is_the_start_of_the_slice(
        self, lossy: pathlib.Path, reference: np.ndarray
    ) -> None:
        """A caller holding a slice never learns where in the file it sits."""
        with open_source(self._slice(lossy, RATE, RATE * 2)) as reader:
            reader.seek(500)
            assert reader.frame == 500
            got = reader.read(200)
        assert np.allclose(got, reference[RATE + 500 : RATE + 700], atol=SEEK_TOLERANCE)

    def test_a_slice_refuses_to_run_past_its_own_end(self, lossy: pathlib.Path) -> None:
        with open_source(self._slice(lossy, RATE, RATE * 2)) as reader:
            assert _read_all(reader).shape[0] == RATE

    def test_an_end_beyond_the_file_is_cut_back_to_the_file(
        self, lossy: pathlib.Path
    ) -> None:
        with open_source(self._slice(lossy, 0, FRAMES * 4)) as reader:
            assert reader.frame_count <= FRAMES + RATE


class TestWhatItRefusesToClaim:
    def test_a_lossy_file_states_no_bit_depth(self, lossy: pathlib.Path) -> None:
        """A stated depth is what `is_bit_perfect` tests, so this must be nought."""
        with open_source(TrackSource(path=str(lossy))) as reader:
            assert reader.bit_depth == 0

    def test_the_dtype_asked_for_is_the_dtype_handed_back(
        self, lossy: pathlib.Path
    ) -> None:
        for dtype in ("float32", "int32", "int16"):
            with open_source(TrackSource(path=str(lossy)), dtype=dtype) as reader:
                assert reader.dtype == dtype
                assert reader.read(256).dtype == np.dtype(dtype)

    def test_a_dtype_no_decoder_can_produce_is_refused(
        self, lossy: pathlib.Path
    ) -> None:
        with pytest.raises(DecodeError):
            PacketReader(TrackSource(path=str(lossy)), dtype="float64")


class TestWhenItCannotRead:
    def test_a_file_that_is_not_there(self, tmp_path: pathlib.Path) -> None:
        with pytest.raises(DecodeError):
            PacketReader(TrackSource(path=str(tmp_path / "absent.m4a")))

    def test_a_file_that_is_not_audio_at_all(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "notes.m4a"
        path.write_bytes(b"this is not a container")
        with pytest.raises(DecodeError):
            PacketReader(TrackSource(path=str(path)))

    def test_closing_twice_is_safe(self, lossy: pathlib.Path) -> None:
        """The engine tears a session down without asking what state it is in."""
        reader = PacketReader(TrackSource(path=str(lossy)))
        reader.close()
        reader.close()
