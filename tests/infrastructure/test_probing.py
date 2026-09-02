"""Reading properties and tags out of every format Stellody can decode.

These tests write real files and read them back, rather than standing in for
mutagen with a fake. The whole difficulty of this module is that each format
answers the same questions differently, so a fake shaped like one of them
would prove nothing about the others. Two measurements decided what the suffix
table may hold: mutagen returning None for a CAF, then OggOpus stating no
sample rate at all.

What is asserted is the honesty as much as the reading. A lossy file must come
back with no bit depth rather than a plausible one, since a number invented
here is indistinguishable downstream from one the file carried.
"""

from __future__ import annotations

import pathlib

import mutagen
import numpy as np
import pytest
import soundfile as sf
from mutagen.flac import Picture
from mutagen.id3 import (
    APIC,
    TALB,
    TCON,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TPOS,
    TRCK,
    PictureType,
)

from stellody.infrastructure.probe import OPUS_SAMPLE_RATE, AudioProbe

CD_RATE = 44100
CD_DEPTH = 16
SECONDS = 1
TITLE = "Capricorn"
ARTIST = "30 Seconds to Mars"
ALBUM = "30 Seconds to Mars"
COVER = b"front-cover-bytes"


def tone(rate: int) -> np.ndarray:
    """One second of stereo, which is enough to have a length to read."""
    wave = 0.2 * np.sin(2 * np.pi * 440 * np.arange(rate * SECONDS) / rate)
    single = wave.astype("float32")
    return np.column_stack([single, single])


def written(directory: pathlib.Path, name: str, rate: int, **kwargs) -> pathlib.Path:
    """One audio file of the given format, with no tags yet."""
    path = directory / name
    sf.write(path, tone(rate), rate, **kwargs)
    return path


def tag_vorbis(path: pathlib.Path, extra: dict[str, str] | None = None) -> None:
    """Tag a FLAC or an Ogg the way a ripper writes Vorbis comments."""
    audio = mutagen.File(str(path))
    if audio.tags is None:
        audio.add_tags()
    audio["title"] = TITLE
    audio["artist"] = ARTIST
    audio["album"] = ALBUM
    for key, value in (extra or {}).items():
        audio[key] = value
    audio.save()


def tag_id3(path: pathlib.Path, art: bool = False) -> None:
    """Tag an MP3, a WAV or an AIFF the way a tagger writes ID3 frames."""
    audio = mutagen.File(str(path))
    if audio.tags is None:
        audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text=[TITLE]))
    audio.tags.add(TPE1(encoding=3, text=[ARTIST]))
    audio.tags.add(TALB(encoding=3, text=[ALBUM]))
    audio.tags.add(TPE2(encoding=3, text=[ARTIST]))
    audio.tags.add(TDRC(encoding=3, text=["2002"]))
    audio.tags.add(TCON(encoding=3, text=["Rock"]))
    audio.tags.add(TRCK(encoding=3, text=["1"]))
    audio.tags.add(TPOS(encoding=3, text=["1"]))
    if art:
        audio.tags.add(
            APIC(
                encoding=3,
                mime="image/jpeg",
                type=PictureType.COVER_FRONT,
                desc="",
                data=COVER,
            )
        )
    audio.save()


class TestWhatEachFormatStates:
    """The properties, which differ per format and must not be invented."""

    def test_a_flac_states_its_depth_and_its_frame_count(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = written(tmp_path, "a.flac", CD_RATE, format="FLAC", subtype="PCM_16")
        read = AudioProbe().read(str(path))
        assert read is not None
        assert read.sample_rate == CD_RATE
        assert read.bit_depth == CD_DEPTH
        assert read.frame_count == CD_RATE * SECONDS

    def test_a_wav_states_a_depth_but_no_frame_count(
        self, tmp_path: pathlib.Path
    ) -> None:
        """So the count comes from its length, which is the same number."""
        path = written(tmp_path, "a.wav", CD_RATE, format="WAV", subtype="PCM_16")
        read = AudioProbe().read(str(path))
        assert read is not None
        assert read.bit_depth == CD_DEPTH
        assert read.frame_count == CD_RATE * SECONDS

    def test_a_lossy_file_states_no_depth_at_all(self, tmp_path: pathlib.Path) -> None:
        """Nought, honestly, rather than a plausible sixteen."""
        path = written(tmp_path, "a.mp3", CD_RATE, format="MP3")
        read = AudioProbe().read(str(path))
        assert read is not None
        assert read.bit_depth == 0
        assert read.sample_rate == CD_RATE
        assert read.frame_count > 0

    def test_an_ogg_states_no_depth_either(self, tmp_path: pathlib.Path) -> None:
        path = written(tmp_path, "a.ogg", CD_RATE, format="OGG", subtype="VORBIS")
        read = AudioProbe().read(str(path))
        assert read is not None
        assert read.bit_depth == 0
        assert read.sample_rate == CD_RATE

    def test_opus_states_no_rate_so_the_format_answers(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Opus decodes at 48 kHz whatever it was made from; mutagen says
        nothing, so the constant of the format is what stands in."""
        path = written(
            tmp_path, "a.opus", OPUS_SAMPLE_RATE, format="OGG", subtype="OPUS"
        )
        read = AudioProbe().read(str(path))
        assert read is not None
        assert read.sample_rate == OPUS_SAMPLE_RATE
        assert read.frame_count > 0


class TestTags:
    """Two shapes, one vocabulary, whichever the file happens to use."""

    @pytest.mark.parametrize(
        ("name", "kwargs"),
        [
            ("a.flac", {"format": "FLAC", "subtype": "PCM_16"}),
            ("a.ogg", {"format": "OGG", "subtype": "VORBIS"}),
        ],
    )
    def test_vorbis_comments_arrive_upper_cased(
        self, tmp_path: pathlib.Path, name: str, kwargs: dict
    ) -> None:
        path = written(tmp_path, name, CD_RATE, **kwargs)
        tag_vorbis(path)
        read = AudioProbe().read(str(path))
        assert read is not None
        assert read.tags["TITLE"] == (TITLE,)
        assert read.tags["ARTIST"] == (ARTIST,)
        assert read.tags["ALBUM"] == (ALBUM,)

    def test_a_comment_nobody_reads_survives_anyway(
        self, tmp_path: pathlib.Path
    ) -> None:
        """The store keeps raw tags, so a rule invented later still has them."""
        path = written(tmp_path, "a.flac", CD_RATE, format="FLAC", subtype="PCM_16")
        tag_vorbis(path, {"musicbrainz_albumid": "abc-123"})
        read = AudioProbe().read(str(path))
        assert read is not None
        assert read.tags["MUSICBRAINZ_ALBUMID"] == ("abc-123",)

    @pytest.mark.parametrize(
        ("name", "kwargs"),
        [
            ("a.mp3", {"format": "MP3"}),
            ("a.wav", {"format": "WAV", "subtype": "PCM_16"}),
            ("a.aiff", {"format": "AIFF", "subtype": "PCM_16"}),
        ],
    )
    def test_id3_frames_arrive_in_the_same_vocabulary(
        self, tmp_path: pathlib.Path, name: str, kwargs: dict
    ) -> None:
        """A four letter frame code is no use to rules that read TITLE."""
        path = written(tmp_path, name, CD_RATE, **kwargs)
        tag_id3(path)
        read = AudioProbe().read(str(path))
        assert read is not None
        assert read.tags["TITLE"] == (TITLE,)
        assert read.tags["ARTIST"] == (ARTIST,)
        assert read.tags["ALBUMARTIST"] == (ARTIST,)
        assert read.tags["DATE"] == ("2002",)
        assert read.tags["GENRE"] == ("Rock",)
        assert read.tags["TRACKNUMBER"] == ("1",)
        assert read.tags["DISCNUMBER"] == ("1",)

    def test_an_untagged_file_reads_as_no_tags_rather_than_a_failure(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = written(tmp_path, "a.wav", CD_RATE, format="WAV", subtype="PCM_16")
        read = AudioProbe().read(str(path))
        assert read is not None
        assert read.tags == {}


class TestEmbeddedArt:
    """Whether the file carries a picture, however it chooses to hold one."""

    def test_a_flac_picture_is_noticed(self, tmp_path: pathlib.Path) -> None:
        path = written(tmp_path, "a.flac", CD_RATE, format="FLAC", subtype="PCM_16")
        audio = mutagen.File(str(path))
        picture = Picture()
        picture.type = PictureType.COVER_FRONT
        picture.mime = "image/jpeg"
        picture.data = COVER
        audio.add_picture(picture)
        audio.save()
        read = AudioProbe().read(str(path))
        assert read is not None
        assert read.has_embedded_art is True

    def test_an_id3_picture_is_noticed_too(self, tmp_path: pathlib.Path) -> None:
        path = written(tmp_path, "a.mp3", CD_RATE, format="MP3")
        tag_id3(path, art=True)
        read = AudioProbe().read(str(path))
        assert read is not None
        assert read.has_embedded_art is True

    def test_a_file_with_no_picture_says_so(self, tmp_path: pathlib.Path) -> None:
        path = written(tmp_path, "a.mp3", CD_RATE, format="MP3")
        tag_id3(path)
        read = AudioProbe().read(str(path))
        assert read is not None
        assert read.has_embedded_art is False


class TestWhatItRefuses:
    """A file it cannot read is reported as unreadable, never guessed at."""

    def test_a_file_that_is_not_audio_reads_as_nothing(
        self, tmp_path: pathlib.Path
    ) -> None:
        plain = tmp_path / "notes.flac"
        plain.write_text("this is not a FLAC", encoding="utf-8")
        assert AudioProbe().read(str(plain)) is None

    def test_a_missing_file_reads_as_nothing(self, tmp_path: pathlib.Path) -> None:
        assert AudioProbe().read(str(tmp_path / "gone.flac")) is None
