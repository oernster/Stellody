"""Reading properties and tags out of an audio file.

This module opens music files. It opens them for reading and it can do nothing
else: a structural test asserts that the mutagen write surface is unreachable
from any module that imports a tag library.

**Three tag shapes cover every format Stellody decodes**, measured rather than
assumed. FLAC and the Ogg family hand back `(name, value)` pairs already
spelled the way the resolution rules read them, so those pass through whole and
nothing a ripper wrote is discarded. MP3, WAV and AIFF hand back ID3 frames
keyed by a four letter code instead; `list()` over one of those yields the
codes rather than pairs, so they are translated by the table below. A frame
nobody reads is left alone rather than guessed at.

MP4 is the third; it is the reason the count is not two: iterating its tags
yields four character atom names, so the pair path does not merely mislabel
them, it raises. Its numbers arrive already parsed as a pair of integers rather
than as the "3/12" text every other format writes, so they are put back into
that form on the way out and the rules downstream stay one set of rules.

**What a format does not state is reported as absent, never invented.** A lossy
file has no bit depth, so it reports none rather than a plausible sixteen; only
FLAC states a frame count, so everything else takes its length in seconds
against its own sample rate. A number made up here would be indistinguishable
downstream from one the file actually carried.

MP4 is where that rule has to be enforced rather than merely observed. Measured
on a real AAC file, mutagen states sixteen bits per sample for it, because the
sample entry carries that number whatever the codec does with it. Believing it
would make a lossy track claim a stored depth; a claimed depth is what
`is_bit_perfect` tests, so an AAC file would have been badged bit perfect. The
depth is therefore taken only from a codec that genuinely stores its samples.
"""

from __future__ import annotations

from collections.abc import Iterable

import mutagen
from mutagen.id3 import ID3
from mutagen.mp4 import MP4, MP4Tags
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

# MP4 atom names, in the same vocabulary. The copyright sign prefixes the
# atoms Apple defined; `aART` is the album artist and carries no prefix.
MP4_NAMES = {
    "\xa9nam": "TITLE",
    "\xa9ART": "ARTIST",
    "aART": "ALBUMARTIST",
    "\xa9alb": "ALBUM",
    "\xa9day": "DATE",
    "\xa9gen": "GENRE",
}

# MP4 atoms holding a number and its total, which mutagen hands back as a pair
# of integers rather than as text.
MP4_PAIR_NAMES = {"trkn": "TRACKNUMBER", "disk": "DISCNUMBER"}

MP4_ART_ATOM = "covr"

# The one MP4 codec that stores its samples rather than approximating them, so
# the one whose stated bit depth means anything. mutagen spells a lossy codec
# as an object type ("mp4a.40.2") and this one by name.
MP4_LOSSLESS_CODEC = "alac"

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
            bit_depth=_bit_depth(audio, info),
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


def _bit_depth(audio: object, info: object) -> int:
    """The depth the file stores, which a lossy MP4 states but does not have."""
    stated = int(getattr(info, "bits_per_sample", 0) or 0)
    if not isinstance(audio, MP4):
        return stated
    codec = str(getattr(info, "codec", "") or "")
    return stated if codec == MP4_LOSSLESS_CODEC else 0


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
    if isinstance(tags, MP4Tags):
        return bool(tags.get(MP4_ART_ATOM))
    return False


def _collect(tags: object) -> dict[str, tuple[str, ...]]:
    """Every readable tag, upper-cased, with repeated fields preserved."""
    if tags is None:
        return {}
    if isinstance(tags, ID3):
        return _from_frames(tags)
    if isinstance(tags, MP4Tags):
        return _from_atoms(tags)
    return _from_pairs(tags)


def _from_pairs(tags: Iterable[tuple[str, str]]) -> dict[str, tuple[str, ...]]:
    """Vorbis comments, which arrive already spelled as the rules read them."""
    collected: dict[str, list[str]] = {}
    for key, value in tags:
        collected.setdefault(key.upper(), []).append(value)
    return {key: tuple(values) for key, values in collected.items()}


def _from_atoms(tags: MP4Tags) -> dict[str, tuple[str, ...]]:
    """MP4 atoms, translated into the same vocabulary as a Vorbis comment.

    The numbered atoms are the only ones needing more than a rename. mutagen
    parses them into a pair, the number and how many there are; writing
    that pair back as "3/12" is what lets one set of rules read every format:
    the reader downstream already tolerates that form, so nothing there learns
    MP4 exists.
    """
    collected: dict[str, list[str]] = {}
    for atom, name in MP4_NAMES.items():
        for value in tags.get(atom, ()):
            text = str(value).strip()
            if text:
                collected.setdefault(name, []).append(text)
    for atom, name in MP4_PAIR_NAMES.items():
        for pair in tags.get(atom, ()):
            text = _numbered(pair)
            if text:
                collected.setdefault(name, []).append(text)
    return {key: tuple(values) for key, values in collected.items()}


def _numbered(pair: object) -> str:
    """An MP4 number-and-total pair as the "3/12" text every other format writes."""
    if not isinstance(pair, tuple) or not pair:
        return ""
    number = int(pair[0])
    if number <= 0:
        return ""
    total = int(pair[1]) if len(pair) > 1 else 0
    return f"{number}/{total}" if total > 0 else str(number)


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
