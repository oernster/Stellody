"""Reading a cover once, then keeping it at the size it is drawn.

Written against real image bytes, because what is checked is that an oversized
scan comes back scaled and a small one comes back untouched. The picture
inside an audio file is stood in for, since opening music files belongs to a
different module on purpose.
"""

from __future__ import annotations

import json
import pathlib

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage

from stellody.infrastructure.artwork import THUMBNAIL_PX, FileArtwork

KEY = "0123456789abcdef"
SMALL_PX = 64
LARGE_PX = THUMBNAIL_PX * 2


def _image(size: int) -> bytes:
    """A real PNG of a given square size."""
    image = QImage(size, size, QImage.Format.Format_RGB32)
    image.fill(0x3366CC)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    data = bytes(buffer.data())
    buffer.close()
    return data


def _width_of(data: bytes) -> int:
    """How wide a kept cover turned out."""
    image = QImage()
    assert image.loadFromData(data)
    return image.width()


class _Pictures:
    """The embedded-picture reader, stood in for. It counts what it opened."""

    def __init__(self, data: bytes | None = None) -> None:
        self.data = data
        self.opened: list[str] = []

    def picture(self, path: str) -> bytes | None:
        """Record the ask, then answer."""
        self.opened.append(path)
        return self.data


def _sidecar(tmp_path: pathlib.Path, size: int = SMALL_PX) -> str:
    """A cover file sitting beside the music."""
    path = tmp_path / "cover.png"
    path.write_bytes(_image(size))
    return str(path)


def test_a_cover_beside_the_music_is_read_and_kept(tmp_path) -> None:
    cache = tmp_path / "art"
    art = FileArtwork(cache, _Pictures())
    kept = art.read(KEY, (_sidecar(tmp_path),), ())
    assert kept is not None
    assert art.remembered(KEY) == kept


def test_a_kept_cover_is_not_read_again(tmp_path) -> None:
    """Decoding is the expensive thing here, so it happens once."""
    cache = tmp_path / "art"
    pictures = _Pictures(_image(SMALL_PX))
    art = FileArtwork(cache, pictures)
    audio = str(tmp_path / "track.flac")
    pathlib.Path(audio).write_bytes(b"stand-in for audio")
    first = art.read(KEY, (), (audio,))
    second = art.read(KEY, (), (audio,))
    assert first == second
    assert pictures.opened == [audio]


def test_a_cover_replaced_at_the_same_name_is_read_again(tmp_path) -> None:
    import os

    cache = tmp_path / "art"
    art = FileArtwork(cache, _Pictures())
    path = _sidecar(tmp_path, SMALL_PX)
    first = art.read(KEY, (path,), ())
    pathlib.Path(path).write_bytes(_image(LARGE_PX))
    os.utime(path, (0, 0))
    second = art.read(KEY, (path,), ())
    assert second is not None
    assert second != first


def test_a_picture_inside_the_audio_is_used_when_nothing_sits_beside_it(
    tmp_path,
) -> None:
    cache = tmp_path / "art"
    audio = str(tmp_path / "track.flac")
    pathlib.Path(audio).write_bytes(b"stand-in for audio")
    art = FileArtwork(cache, _Pictures(_image(SMALL_PX)))
    assert art.read(KEY, (), (audio,)) is not None


def test_a_file_beside_the_music_is_preferred_to_one_inside_it(tmp_path) -> None:
    """Reading a file is cheaper than opening a decoder."""
    cache = tmp_path / "art"
    pictures = _Pictures(_image(SMALL_PX))
    art = FileArtwork(cache, pictures)
    audio = str(tmp_path / "track.flac")
    pathlib.Path(audio).write_bytes(b"stand-in for audio")
    assert art.read(KEY, (_sidecar(tmp_path),), (audio,)) is not None
    assert pictures.opened == []


def test_a_candidate_that_is_not_an_image_is_passed_over(tmp_path) -> None:
    cache = tmp_path / "art"
    broken = tmp_path / "cover.jpg"
    broken.write_bytes(b"this is not an image")
    good = tmp_path / "folder.png"
    good.write_bytes(_image(SMALL_PX))
    art = FileArtwork(cache, _Pictures())
    assert art.read(KEY, (str(broken), str(good)), ()) is not None


def test_a_candidate_that_is_not_there_is_passed_over(tmp_path) -> None:
    cache = tmp_path / "art"
    art = FileArtwork(cache, _Pictures())
    missing = str(tmp_path / "gone.png")
    assert art.read(KEY, (missing, _sidecar(tmp_path)), ()) is not None


def test_an_album_with_nothing_anywhere_has_no_cover(tmp_path) -> None:
    art = FileArtwork(tmp_path / "art", _Pictures())
    assert art.read(KEY, (), ()) is None


def test_nothing_is_remembered_about_an_album_never_read(tmp_path) -> None:
    assert FileArtwork(tmp_path / "art", _Pictures()).remembered(KEY) is None


def test_an_oversized_scan_is_kept_scaled_down(tmp_path) -> None:
    cache = tmp_path / "art"
    art = FileArtwork(cache, _Pictures())
    kept = art.read(KEY, (_sidecar(tmp_path, LARGE_PX),), ())
    assert kept is not None
    assert _width_of(kept) == THUMBNAIL_PX


def test_a_small_cover_is_not_enlarged(tmp_path) -> None:
    """Enlarging invents detail the file never held."""
    cache = tmp_path / "art"
    art = FileArtwork(cache, _Pictures())
    kept = art.read(KEY, (_sidecar(tmp_path, SMALL_PX),), ())
    assert kept is not None
    assert _width_of(kept) == SMALL_PX


def test_a_damaged_record_is_ignored_rather_than_believed(tmp_path) -> None:
    cache = tmp_path / "art"
    art = FileArtwork(cache, _Pictures())
    art.read(KEY, (_sidecar(tmp_path),), ())
    (cache / f"{KEY}.json").write_text("{ not json", encoding="utf-8")
    assert art.remembered(KEY) is None


def test_a_record_of_another_format_is_ignored(tmp_path) -> None:
    cache = tmp_path / "art"
    art = FileArtwork(cache, _Pictures())
    art.read(KEY, (_sidecar(tmp_path),), ())
    record = json.loads((cache / f"{KEY}.json").read_text(encoding="utf-8"))
    record["version"] = 999
    (cache / f"{KEY}.json").write_text(json.dumps(record), encoding="utf-8")
    assert art.remembered(KEY) is None


def test_a_cover_whose_source_has_gone_is_not_offered(tmp_path) -> None:
    cache = tmp_path / "art"
    art = FileArtwork(cache, _Pictures())
    path = _sidecar(tmp_path)
    art.read(KEY, (path,), ())
    pathlib.Path(path).unlink()
    assert art.remembered(KEY) is None


def test_a_cache_that_cannot_be_written_is_not_an_error(tmp_path) -> None:
    """A cover that cannot be kept is still a cover worth drawing once."""
    blocked = tmp_path / "art"
    blocked.write_bytes(b"a file where a directory should be")
    art = FileArtwork(blocked, _Pictures())
    assert art.read(KEY, (_sidecar(tmp_path),), ()) is not None
