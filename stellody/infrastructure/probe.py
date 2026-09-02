"""Reading properties and tags out of an audio file.

This module opens music files. It opens them for reading and it can do nothing
else: a structural test asserts that the mutagen write surface is unreachable
from any module that imports a tag library.

**Two tag shapes cover every format Stellody decodes**, measured rather than
assumed. FLAC and the Ogg family hand back `(name, value)` pairs already
spelled the way the resolution rules read them, so those pass through whole and
nothing a ripper wrote is discarded. MP3, WAV and AIFF hand back ID3 frames
keyed by a four letter code instead; `list()` over one of those yields the
codes rather than pairs, so they are translated by the table below. A frame
nobody reads is left alone rather than guessed at.

**What a format does not state is reported as absent, never invented.** A lossy
file has no bit depth, so it reports none rather than a plausible sixteen; only
FLAC states a frame count, so everything else takes its length in seconds
against its own sample rate. A number made up here would be indistinguishable
downstream from one the file actually carried.
"""

from __future__ import annotations

from collections.abc import Iterable

import mutagen
from mutagen.id3 import ID3
from mutagen.oggopus import OggOpus

from stellody.application.values import AudioProperties

APPLEDOUBLE_PREFIX = "._"

# ID3 frame codes, in the vocabulary `application/tags.py` already reads.
# TYER is ID3v2.3's year, which rippers of that era wrote where later ones
# write TDRC; both are kept because a library holds both eras.
ID3_NAMES = {
    "TIT2": "TITLE",
    "TPE1": "ARTIST",
    "TPE2": "ALBUMARTIST",
    "TALB": "ALBUM",
    "TDRC": "DATE",
    "TYER": "DATE",
    "TCON": "GENRE",
    "TRCK": "TRACKNUMBER",
    "TPOS": "DISCNUMBER",
}

ART_FRAME = "APIC"

# Opus decodes at 48 kHz whatever it was encoded from; mutagen states no
# sample rate for it at all. The format itself is the source, so this is a
# constant of Opus rather than a number chosen here.
OPUS_SAMPLE_RATE = 48000


class AudioProbe:
    """Reads one audio file's stream information and its tags."""

    def read(self, path: str) -> AudioProperties | None:
        """Properties of the file; None when it cannot be read as audio."""
        try:
            audio = mutagen.File(path)
        except (mutagen.MutagenError, OSError, ValueError):
            return None
        if audio is None:
            return None
        info = getattr(audio, "info", None)
        if info is None:
            return None
        rate = _sample_rate(audio, info)
        return AudioProperties(
            sample_rate=rate,
            bit_depth=int(getattr(info, "bits_per_sample", 0) or 0),
            frame_count=_frame_count(info, rate),
            has_embedded_art=_has_art(audio),
            tags=_collect(getattr(audio, "tags", None)),
        )


def _sample_rate(audio: object, info: object) -> int:
    """The rate the file plays at; Opus states none, so the format answers."""
    stated = int(getattr(info, "sample_rate", 0) or 0)
    if stated:
        return stated
    return OPUS_SAMPLE_RATE if isinstance(audio, OggOpus) else 0


def _frame_count(info: object, rate: int) -> int:
    """Frames in the file, from what it states, else from its own length.

    Only FLAC carries a frame count. A length in seconds against the rate is
    the same number for a lossless file and the closest honest answer for a
    lossy one, where the decoder itself is the only exact authority.
    """
    stated = int(getattr(info, "total_samples", 0) or 0)
    if stated:
        return stated
    seconds = float(getattr(info, "length", 0.0) or 0.0)
    return int(seconds * rate) if seconds > 0 and rate > 0 else 0


def _has_art(audio: object) -> bool:
    """Whether the file carries a picture of its own."""
    pictures = getattr(audio, "pictures", None)
    if pictures:
        return True
    tags = getattr(audio, "tags", None)
    if isinstance(tags, ID3):
        return bool(tags.getall(ART_FRAME))
    return False


def _collect(tags: object) -> dict[str, tuple[str, ...]]:
    """Every readable tag, upper-cased, with repeated fields preserved."""
    if tags is None:
        return {}
    if isinstance(tags, ID3):
        return _from_frames(tags)
    return _from_pairs(tags)


def _from_pairs(tags: Iterable[tuple[str, str]]) -> dict[str, tuple[str, ...]]:
    """Vorbis comments, which arrive already spelled as the rules read them."""
    collected: dict[str, list[str]] = {}
    for key, value in tags:
        collected.setdefault(key.upper(), []).append(value)
    return {key: tuple(values) for key, values in collected.items()}


def _from_frames(tags: ID3) -> dict[str, tuple[str, ...]]:
    """ID3 frames, translated into the same vocabulary as a Vorbis comment.

    A frame carries a list of strings, so a tag written twice survives as two
    values exactly as it would in a FLAC. Where two codes mean one field, as
    TYER and TDRC both mean the date, whichever the file holds is kept and a
    file holding both keeps both.
    """
    collected: dict[str, list[str]] = {}
    for code, name in ID3_NAMES.items():
        frame = tags.get(code)
        if frame is None:
            continue
        for value in getattr(frame, "text", ()):
            text = str(value).strip()
            if text:
                collected.setdefault(name, []).append(text)
    return {key: tuple(values) for key, values in collected.items()}
