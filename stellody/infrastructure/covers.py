"""Reading a cover picture out of an audio file.

This module opens music files. It opens them for reading and it can do nothing
else: a structural test asserts that the mutagen write surface is unreachable
from any module that imports a tag library.

It deliberately decodes nothing and keeps nothing, so the module that writes
Stellody's own artwork store never opens a music file at all. Keeping the two
apart is what lets the store be given permission to write without giving that
permission to anything holding a tag library.
"""

from __future__ import annotations

import mutagen
from mutagen.flac import Picture
from mutagen.id3 import ID3, PictureType

ART_FRAME = "APIC"


def _preference(picture: Picture) -> tuple[int, int]:
    """Ordering key: a front cover first, then whichever picture is largest.

    A file may carry a back cover, a liner page or an artist photograph
    alongside the front. Taking the largest alone would sometimes choose a
    scan of the back, so what the file says the picture IS comes first and
    size settles the rest.
    """
    return (0 if picture.type == PictureType.COVER_FRONT else 1, -len(picture.data))


class EmbeddedPictures:
    """The cover embedded in a music file, as the bytes the file holds.

    Two shapes again, as with the tags: FLAC keeps pictures as a list of its
    own, while MP3, WAV and AIFF keep them as ID3 picture frames. Both carry
    the same fields, so both sort by the same preference and neither is
    treated as the special case.
    """

    def picture(self, path: str) -> bytes | None:
        """The best embedded picture in this file; None when it holds none."""
        try:
            audio = mutagen.File(path)
        except (mutagen.MutagenError, OSError, ValueError):
            return None
        if audio is None:
            return None
        pictures = _pictures(audio)
        if not pictures:
            return None
        pictures.sort(key=_preference)
        return bytes(pictures[0].data)


def _pictures(audio: object) -> list:
    """Every embedded picture, however this format chooses to hold them."""
    held = getattr(audio, "pictures", None)
    if held:
        return list(held)
    tags = getattr(audio, "tags", None)
    if isinstance(tags, ID3):
        return list(tags.getall(ART_FRAME))
    return []
