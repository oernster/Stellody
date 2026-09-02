"""Reading the picture a FLAC carries inside it.

Written against real files rather than a stand-in, because what is checked is
that the bytes coming out are the bytes a tagger put in; also which of several
pictures is chosen when a file carries more than one.
"""

from __future__ import annotations

import pathlib

import numpy as np
import soundfile
from mutagen.flac import FLAC, Picture
from mutagen.id3 import PictureType

from stellody.infrastructure.covers import EmbeddedPictures

SAMPLE_RATE = 44100
FRAMES = SAMPLE_RATE // 10


def _flac(path: pathlib.Path) -> pathlib.Path:
    """A short real FLAC, carrying no pictures yet."""
    samples = np.zeros((FRAMES, 2), dtype="float32")
    soundfile.write(str(path), samples, SAMPLE_RATE, format="FLAC")
    return path


def _add(path: pathlib.Path, kind: PictureType, data: bytes) -> None:
    """Put one picture into a FLAC, as a tagger would."""
    audio = FLAC(str(path))
    picture = Picture()
    picture.type = kind
    picture.mime = "image/png"
    picture.data = data
    audio.add_picture(picture)
    audio.save()


def test_the_picture_a_file_carries_is_the_picture_returned(tmp_path) -> None:
    audio = _flac(tmp_path / "one.flac")
    _add(audio, PictureType.COVER_FRONT, b"front-cover-bytes")
    assert EmbeddedPictures().picture(str(audio)) == b"front-cover-bytes"


def test_the_front_cover_wins_over_a_larger_back(tmp_path) -> None:
    """Taking the largest alone would sometimes choose a scan of the back."""
    audio = _flac(tmp_path / "two.flac")
    _add(audio, PictureType.COVER_BACK, b"x" * 5000)
    _add(audio, PictureType.COVER_FRONT, b"front")
    assert EmbeddedPictures().picture(str(audio)) == b"front"


def test_the_largest_wins_when_no_picture_claims_to_be_the_front(tmp_path) -> None:
    audio = _flac(tmp_path / "three.flac")
    _add(audio, PictureType.COVER_BACK, b"small")
    _add(audio, PictureType.LEAFLET_PAGE, b"y" * 400)
    assert EmbeddedPictures().picture(str(audio)) == b"y" * 400


def test_a_file_carrying_no_picture_has_none(tmp_path) -> None:
    audio = _flac(tmp_path / "bare.flac")
    assert EmbeddedPictures().picture(str(audio)) is None


def test_a_file_that_is_not_there_has_none(tmp_path) -> None:
    assert EmbeddedPictures().picture(str(tmp_path / "missing.flac")) is None


def test_a_file_that_is_not_audio_has_none(tmp_path) -> None:
    """A cover file handed here by mistake must not raise."""
    plain = tmp_path / "cover.jpg"
    plain.write_bytes(b"not audio at all")
    assert EmbeddedPictures().picture(str(plain)) is None
