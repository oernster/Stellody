"""Reading properties and tags out of an audio file.

This module opens music files. It opens them for reading and it can do nothing
else: a structural test asserts that the mutagen write surface is unreachable
from any module that imports a tag library.

**Five tag shapes cover every format Stellody decodes**, measured rather than
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

WMA is the fourth. Its tags do iterate as pairs, so nothing raises; the names
are Microsoft's own, so an untranslated one would simply be a tag nobody reads,
which is the quieter failure of the two. Measured on 2026-09-09, one FFmpeg
written file states its title under both `Title` and `title`, so the table is
read without regard to case and a value already collected under a name is not
collected twice.

WavPack is the fifth and it is APEv2, which is a mapping rather than a list of
pairs: iterating one yields its KEYS, so the pair path raises there exactly as
it does for MP4. No table is needed beyond that, since the keys an APEv2 file
carries are already spelled the way the resolution rules read them, `track` and
`disc` and `album_artist` included.

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

Which families those are is the domain's to say, in `domain/formats.py`. This
module's only part in it is naming the family a file belongs to, since that is
the question a tag library can answer and the rule itself is not.
"""

from __future__ import annotations

from collections.abc import Iterable

import mutagen
from mutagen.aac import AAC
from mutagen.apev2 import APEv2
from mutagen.asf import ASF, ASFTags
from mutagen.id3 import ID3
from mutagen.mp4 import MP4, MP4Tags
from mutagen.oggopus import OggOpus

from stellody.application.values import AudioProperties
from stellody.domain.formats import (
    FAMILY_AAC,
    FAMILY_MP4_LOSSY,
    FAMILY_OTHER,
    FAMILY_WMA,
    stored_depth,
)

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

# ASF attribute names, in the same vocabulary. `Author` is the performer and
# `WM/PartOfSet` is the disc, which are Microsoft's spellings for the two
# fields whose names carry no clue. Matched without regard to case, because a
# file measured on 2026-09-09 stated its title under both `Title` and `title`;
# the date is the one field where the two spellings are not the same name, so
# both are listed. A name outside this table is left alone rather than guessed
# at, exactly as an ID3 frame nobody reads is.
ASF_NAMES = {
    "title": "TITLE",
    "author": "ARTIST",
    "wm/albumtitle": "ALBUM",
    "wm/albumartist": "ALBUMARTIST",
    "wm/year": "DATE",
    "date": "DATE",
    "wm/genre": "GENRE",
    "wm/tracknumber": "TRACKNUMBER",
    "wm/partofset": "DISCNUMBER",
}

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
    return stored_depth(_family(audio, info), stated)


def _family(audio: object, info: object) -> str:
    """Which family the domain's depth rule should judge this file by.

    Only the families that rule names are told apart. An MP4 needs its codec
    read to be placed at all, since one container holds both a codec that
    stores its samples and one that approximates them; every other family is
    one or the other outright.
    """
    if isinstance(audio, MP4):
        codec = str(getattr(info, "codec", "") or "")
        return FAMILY_OTHER if codec == MP4_LOSSLESS_CODEC else FAMILY_MP4_LOSSY
    if isinstance(audio, ASF):
        return FAMILY_WMA
    if isinstance(audio, AAC):
        return FAMILY_AAC
    return FAMILY_OTHER


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
    if isinstance(tags, ASFTags):
        return _from_attributes(tags)
    if isinstance(tags, APEv2):
        return _from_keys(tags)
    return _from_pairs(tags)


def _from_pairs(tags: Iterable[tuple[str, str]]) -> dict[str, tuple[str, ...]]:
    """Vorbis comments, which arrive already spelled as the rules read them."""
    collected: dict[str, list[str]] = {}
    for key, value in tags:
        collected.setdefault(key.upper(), []).append(value)
    return {key: tuple(values) for key, values in collected.items()}


def _from_attributes(tags: ASFTags) -> dict[str, tuple[str, ...]]:
    """ASF attributes, translated into the same vocabulary as a Vorbis comment.

    A value already collected under a name is dropped rather than collected
    twice, which is the one place this differs from the pair path. WMA states
    a field under two spellings where the others state it once, so keeping
    both would hand the resolution rules the same title as two artists' worth
    of values and nothing downstream could tell that apart from a file that
    genuinely says something twice.
    """
    collected: dict[str, list[str]] = {}
    for key, value in tags:
        name = ASF_NAMES.get(str(key).lower())
        if name is None:
            continue
        text = str(value).strip()
        if text and text not in collected.setdefault(name, []):
            collected[name].append(text)
    return {key: tuple(values) for key, values in collected.items() if values}


def _from_keys(tags: APEv2) -> dict[str, tuple[str, ...]]:
    """APEv2 items, which are already spelled as the rules read them.

    The mapping is what makes this its own path rather than the pair one:
    iterating an APEv2 yields keys alone, so the pair path raises on it. The
    names need no table, since `application/tags.py` already accepts the
    spellings APEv2 uses.
    """
    collected: dict[str, list[str]] = {}
    for key in tags:
        text = str(tags[key]).strip()
        if text:
            collected.setdefault(str(key).upper(), []).append(text)
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
