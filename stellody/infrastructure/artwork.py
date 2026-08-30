"""Keeping an album's cover at the size it is drawn.

Stellody's own state, written into Stellody's own directory. This module never
opens a music file: a picture living inside audio is handed over by
`covers.py`, so the module that writes and the module that can read tags are
not the same module. That separation is what lets this one be given permission
to write without granting it to anything holding a tag library.

A cover is kept against the album's identity rather than a path, so a folder
rename reuses it. What was read is recorded beside it, checked against that
file's size and modification time, so a cover replaced on disk is read again
while a rescan that changed nothing reuses what is here.

A cover somebody CHOSE is kept the same way but marked as chosen. A chosen
record is not checked against any file: there is no file, while the choice is
meant to outlive the folder it was made over. It therefore survives a rescan
and is preferred to whatever sits beside the music, which is the whole point
of having gone looking.

Covers are kept scaled down. The largest picture measured in the reference
library is 1.3 megabytes and the median is 94 kilobytes, sizes worth decoding
once rather than every time a library is drawn.
"""

from __future__ import annotations

import json
import pathlib

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage

from stellody.application.ports import EmbeddedPicturePort

# Wide enough for a grid tile on a display that doubles it, which is the
# largest thing a cover is drawn into. Never enlarged past what a file holds.
THUMBNAIL_PX = 512
JPEG_QUALITY = 85
IMAGE_FORMAT = "JPEG"
IMAGE_SUFFIX = ".jpg"
RECORD_SUFFIX = ".json"
# The source written down for a chosen cover, which has no file to point at.
CHOSEN_SOURCE = "chosen"
FORMAT_VERSION = 1


def _file_bytes(path: str) -> bytes | None:
    """A file beside the music, read whole; None when it cannot be read."""
    try:
        return pathlib.Path(path).read_bytes()
    except OSError:
        return None


def _stamp(path: str) -> tuple[int, int] | None:
    """A file's size and modification time; None when it is not there."""
    try:
        stat = pathlib.Path(path).stat()
    except OSError:
        return None
    return stat.st_size, int(stat.st_mtime)


def _thumbnail(data: bytes) -> bytes | None:
    """An image scaled to fit, encoded small; None when it is not an image.

    Scaled only downward. A cover smaller than the thumbnail is kept at the
    size it came in, since enlarging it invents detail the file never held.
    """
    image = QImage()
    if not image.loadFromData(data):
        return None
    if image.width() > THUMBNAIL_PX or image.height() > THUMBNAIL_PX:
        image = image.scaled(
            THUMBNAIL_PX,
            THUMBNAIL_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    written = image.save(buffer, IMAGE_FORMAT, JPEG_QUALITY)
    encoded = bytes(buffer.data())
    buffer.close()
    return encoded if written else None


class FileArtwork:
    """Reads an album's cover once, then keeps it."""

    def __init__(self, cache_dir: pathlib.Path, pictures: EmbeddedPicturePort) -> None:
        self._cache_dir = cache_dir
        self._pictures = pictures

    def remembered(self, key: str) -> bytes | None:
        """The cover kept for this album, when what it was read from still matches."""
        if self._read_record(key) is None:
            return None
        return _file_bytes(str(self._image_path(key)))

    def read(
        self, key: str, sidecars: tuple[str, ...], audio: tuple[str, ...]
    ) -> bytes | None:
        """The cover from the first candidate that yields an image."""
        kept = self.remembered(key)
        if kept is not None:
            return kept
        for path, load in self._candidates(sidecars, audio):
            data = load(path)
            if data is None:
                continue
            thumbnail = _thumbnail(data)
            if thumbnail is None:
                continue
            self._keep(key, path, thumbnail)
            return thumbnail
        return None

    def keep_chosen(self, key: str, data: bytes) -> bytes | None:
        """Keep a picture somebody chose; the kept copy, else None.

        Scaled down like any other cover, so one album's art is one size
        whatever it came from. A picture that will not decode keeps nothing
        and says so, rather than leaving a record pointing at rubbish.
        """
        thumbnail = _thumbnail(data)
        if thumbnail is None:
            return None
        if not self._write(key, {"source": CHOSEN_SOURCE, "chosen": True}, thumbnail):
            return None
        return thumbnail

    def _candidates(self, sidecars: tuple[str, ...], audio: tuple[str, ...]):
        """Every place to look, cheapest first: files beside, then inside."""
        for path in sidecars:
            yield path, _file_bytes
        for path in audio:
            yield path, self._pictures.picture

    def _image_path(self, key: str) -> pathlib.Path:
        """Where this album's kept cover sits."""
        return self._cache_dir / f"{key}{IMAGE_SUFFIX}"

    def _record_path(self, key: str) -> pathlib.Path:
        """Where the note of what that cover was read from sits."""
        return self._cache_dir / f"{key}{RECORD_SUFFIX}"

    def _read_record(self, key: str) -> dict | None:
        """The note beside a kept cover, when it still describes the file."""
        try:
            record = json.loads(self._record_path(key).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if record.get("version") != FORMAT_VERSION:
            return None
        if record.get("chosen"):
            # Nothing to check it against; nothing that should override it.
            return record
        stamp = _stamp(record.get("source", ""))
        if stamp is None:
            return None
        if (record.get("size"), record.get("modified")) != stamp:
            return None
        return record

    def _keep(self, key: str, source: str, thumbnail: bytes) -> None:
        """Keep a cover and the file it was read from, with that file's stamp."""
        stamp = _stamp(source)
        if stamp is None:
            return
        size, modified = stamp
        self._write(
            key,
            {"source": source, "size": size, "modified": modified},
            thumbnail,
        )

    def _write(self, key: str, record: dict, thumbnail: bytes) -> bool:
        """Put a cover and its note on disk; False when neither could go.

        A cache that cannot be written is not a failure worth raising over for
        a cover read from a file, which will simply be read again. It IS worth
        reporting for one that was chosen, since nothing will ever go looking
        for that picture a second time.
        """
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._image_path(key).write_bytes(thumbnail)
            self._record_path(key).write_text(
                json.dumps(
                    {"version": FORMAT_VERSION, **record}, separators=(",", ":")
                ),
                encoding="utf-8",
            )
        except OSError:
            return False
        return True
