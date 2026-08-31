"""Reading properties and tags out of a FLAC file.

This module opens music files. It opens them for reading and it can do nothing
else: a structural test asserts that the mutagen write surface is unreachable
from any module that imports a tag library.
"""

from __future__ import annotations

import mutagen
from mutagen.flac import FLAC

from stellody.application.values import AudioProperties

APPLEDOUBLE_PREFIX = "._"


class FlacProbe:
    """Reads a FLAC file's stream information and Vorbis comments."""

    def read(self, path: str) -> AudioProperties | None:
        """Properties of the file; None when it cannot be read as FLAC."""
        try:
            audio = FLAC(path)
        except (mutagen.MutagenError, OSError, ValueError):
            return None
        info = getattr(audio, "info", None)
        if info is None:
            return None
        return AudioProperties(
            sample_rate=int(getattr(info, "sample_rate", 0) or 0),
            bit_depth=int(getattr(info, "bits_per_sample", 0) or 0),
            frame_count=int(getattr(info, "total_samples", 0) or 0),
            has_embedded_art=bool(audio.pictures),
            tags=_collect(audio),
        )


def _collect(audio: FLAC) -> dict[str, tuple[str, ...]]:
    """Every Vorbis comment, upper-cased, with repeated fields preserved."""
    collected: dict[str, list[str]] = {}
    for key, value in audio.tags or ():
        collected.setdefault(key.upper(), []).append(value)
    return {key: tuple(values) for key, values in collected.items()}
