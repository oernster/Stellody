"""Reading what an M4A says about itself: its tags, its cover and its depth.

MP4 is a third tag shape and it is not a gentle one. Iterating its tags yields
four character atom names, so the path that reads a Vorbis comment does not
merely mislabel them, it raises `ValueError: too many values to unpack`. It
holds its numbers as a parsed pair rather than as "3/12" text. It keeps its
cover in an atom that carries no picture type at all. And it states a bit depth
for a codec that has none, which is the one that could have done real harm.

Everything here runs against a real encoded file with real tags written into
it, because every one of those four facts was found by opening a file rather
than by reading about the format.
"""

from __future__ import annotations

import pathlib

import pytest
from m4a_support import RATE, write_m4a
from mutagen.mp4 import MP4, MP4Cover

from stellody.application import tags as reading
from stellody.infrastructure.covers import EmbeddedPictures
from stellody.infrastructure.probe import AudioProbe
from stellody.infrastructure.walker import AUDIO_SUFFIXES, UNPLAYABLE_SUFFIXES

ALBUM = "Emotional Technology"
ARTIST = "BT"
TITLE = "The Meeting of a Hundred Yang"
GENRE = "Electronic"

# The date atom as iTunes writes it: a whole timestamp, not a year.
STAMP = "2003-08-05T12:00:00Z"
YEAR = 2003

TRACK_NUMBER = 1
TRACK_TOTAL = 21

SMALL_COVER = b"\x89PNG\r\n\x1a\n" + b"small"
LARGE_COVER = b"\x89PNG\r\n\x1a\n" + b"considerably larger than the other one"


def _tagged(path: pathlib.Path, art: bool = True) -> pathlib.Path:
    """A real M4A carrying the tags an iTunes rip carries."""
    write_m4a(path, frames=RATE // 2)
    tags = MP4(str(path))
    tags["\xa9nam"] = [TITLE]
    tags["\xa9ART"] = [ARTIST]
    tags["aART"] = [ARTIST]
    tags["\xa9alb"] = [ALBUM]
    tags["\xa9gen"] = [GENRE]
    tags["\xa9day"] = [STAMP]
    tags["trkn"] = [(TRACK_NUMBER, TRACK_TOTAL)]
    tags["disk"] = [(1, 1)]
    if art:
        tags["covr"] = [MP4Cover(SMALL_COVER, imageformat=MP4Cover.FORMAT_PNG)]
    tags.save()
    return path


@pytest.fixture
def tagged(tmp_path: pathlib.Path) -> pathlib.Path:
    return _tagged(tmp_path / "track.m4a")


@pytest.fixture
def properties(tagged: pathlib.Path):
    read = AudioProbe().read(str(tagged))
    assert read is not None, "a real M4A must be readable at all"
    return read


class TestTheThirdTagShape:
    def test_the_probe_reads_it_rather_than_raising(self, properties) -> None:
        """The pair path raises on MP4 atoms, so reaching here is the test."""
        assert properties.tags

    def test_the_words_arrive_in_the_vocabulary_the_rules_read(
        self, properties
    ) -> None:
        assert reading.first(properties.tags, reading.TITLE) == TITLE
        assert reading.first(properties.tags, reading.ALBUM) == ALBUM
        assert reading.first(properties.tags, reading.GENRE) == GENRE

    def test_the_album_artist_atom_is_not_confused_with_the_artist(
        self, properties
    ) -> None:
        """`aART` and the prefixed `\xa9ART` are different atoms, one letter apart."""
        assert reading.first(properties.tags, reading.ALBUM_ARTIST) == ARTIST
        assert reading.artists(properties.tags) == (ARTIST,)

    def test_a_number_pair_is_read_as_the_number(self, properties) -> None:
        """mutagen hands back (1, 21); the rules downstream want "1/21"."""
        assert reading.number(properties.tags, reading.TRACK) == TRACK_NUMBER
        assert reading.number(properties.tags, reading.DISC) == 1

    def test_a_whole_timestamp_still_yields_its_year(self, properties) -> None:
        """iTunes writes the date as an instant, not as a year."""
        assert reading.number(properties.tags, reading.DATE) == YEAR

    def test_a_file_with_no_tags_at_all_is_read_as_having_none(
        self, tmp_path: pathlib.Path
    ) -> None:
        write_m4a(tmp_path / "bare.m4a", frames=RATE // 2)
        read = AudioProbe().read(str(tmp_path / "bare.m4a"))
        assert read is not None
        assert reading.first(read.tags, reading.TITLE) == ""


class TestTheDepthItStatesAndDoesNotHave:
    def test_a_lossy_file_reports_no_bit_depth(self, properties) -> None:
        """The whole point: mutagen says sixteen; sixteen is not true.

        A stated depth is what `is_bit_perfect` tests. Passing this number
        through would have let an AAC file claim to be delivered untouched.
        """
        assert properties.bit_depth == 0

    def test_the_file_really_does_state_one(self, tagged: pathlib.Path) -> None:
        """Pinning the trap itself, so this test fails if mutagen ever stops.

        If this ever fails, the suppression above has become unnecessary rather
        than wrong; someone should find out which before deleting it.
        """
        assert MP4(str(tagged)).info.bits_per_sample == 16

    def test_the_rate_is_still_read(self, properties) -> None:
        assert properties.sample_rate == RATE

    def test_a_length_is_still_read(self, properties) -> None:
        assert properties.frame_count > 0


class TestTheCoverAtom:
    def test_the_probe_sees_that_there_is_one(self, properties) -> None:
        assert properties.has_embedded_art is True

    def test_a_file_without_one_says_so(self, tmp_path: pathlib.Path) -> None:
        bare = _tagged(tmp_path / "bare.m4a", art=False)
        read = AudioProbe().read(str(bare))
        assert read is not None
        assert read.has_embedded_art is False

    def test_the_bytes_come_back_whole(self, tagged: pathlib.Path) -> None:
        assert EmbeddedPictures().picture(str(tagged)) == SMALL_COVER

    def test_the_largest_wins_when_there_are_several(
        self, tmp_path: pathlib.Path
    ) -> None:
        """An Apple cover states no picture type, so size is all there is."""
        path = _tagged(tmp_path / "two.m4a")
        tags = MP4(str(path))
        tags["covr"] = [
            MP4Cover(SMALL_COVER, imageformat=MP4Cover.FORMAT_PNG),
            MP4Cover(LARGE_COVER, imageformat=MP4Cover.FORMAT_PNG),
        ]
        tags.save()
        assert EmbeddedPictures().picture(str(path)) == LARGE_COVER

    def test_a_file_with_no_cover_yields_nothing(self, tmp_path: pathlib.Path) -> None:
        bare = _tagged(tmp_path / "bare.m4a", art=False)
        assert EmbeddedPictures().picture(str(bare)) is None


class TestTheWalkNowTakesIt:
    def test_m4a_counts_as_audio(self) -> None:
        assert ".m4a" in AUDIO_SUFFIXES

    def test_and_is_no_longer_reported_as_unplayable(self) -> None:
        assert ".m4a" not in UNPLAYABLE_SUFFIXES

    def test_the_formats_nothing_decodes_are_still_named(self) -> None:
        """Reporting them is what stops an album vanishing without a word."""
        for suffix in (".wma", ".ape", ".wv", ".mpc", ".dsf", ".dff", ".m4b"):
            assert suffix in UNPLAYABLE_SUFFIXES

    def test_no_suffix_is_in_both_sets(self) -> None:
        assert not (AUDIO_SUFFIXES & UNPLAYABLE_SUFFIXES)
