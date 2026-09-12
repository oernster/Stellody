"""Walking a music library folder. Reads directory entries, writes nothing."""

from __future__ import annotations

import os
from collections.abc import Iterator

from stellody.application.values import FileStat, FolderListing
from stellody.domain.track import PICTURE_SUFFIXES

# What the decoder can actually open, measured against the libsndfile behind
# soundfile rather than taken from its documentation: 26 formats, of which
# these are the ones a music library holds. Every one was checked to be
# readable by mutagen as well, since a file whose tags cannot be read is not
# a file Stellody can group into an album. CAF is deliberately absent for
# exactly that reason: libsndfile decodes it, mutagen returns nothing at all
# for it, so it would scan into an album with no title.
#
# M4A is here on a different footing from the rest: libsndfile cannot open it
# at all, so it is decoded by the packet reader in `packet_decode.py` instead.
# Its tags still have to be readable by mutagen for the same reason as every
# other entry. They are, as a third tag shape the probe now understands.
#
# WMA, WavPack and AAC arrive on that same footing and on a weaker standard of
# evidence, which `FORMATS.md` states in full. Every entry above was seen to
# work against a file somebody owns; those three were proved against a file the
# suite encodes for the purpose, because the reference library holds none of
# them. That proves what FFmpeg writes rather than what a real ripper writes,
# which is the whole of the difference and is why it is written down.
AUDIO_SUFFIXES = frozenset(
    {
        ".flac",
        ".mp3",
        ".ogg",
        ".oga",
        ".opus",
        ".wav",
        ".aiff",
        ".aif",
        ".m4a",
        ".wma",
        ".wv",
        ".aac",
    }
)
# Audio this build knows by sight and cannot decode. Named rather than
# inferred from "not in AUDIO_SUFFIXES", because a stray .txt is not a missing
# album and reporting one as though it were would be noise. CAF is here for a
# different reason: libsndfile decodes it while mutagen reads nothing out of
# it, so it would scan into an album with no title.
#
# M4B is an audiobook in the same container M4A uses, measured working and
# left here anyway: an audiobook is not music and a chaptered one arrives as
# one enormous track that would read as an album nobody made.
#
# The rest are here because no fixture can be made for them: the bundled
# FFmpeg decodes Monkey's Audio, Musepack, DSD and TAK while encoding none of
# them, so there is nothing to prove the path with. TrueAudio is the one that
# decodes and encodes, cut because mutagen states no channel count for it, so
# the probe would have to invent one. `FORMATS.md` section 1.4 holds each
# reason; each reopens the day a real file is measured.
UNPLAYABLE_SUFFIXES = frozenset(
    {
        ".m4b",
        ".ape",
        ".mpc",
        ".dsf",
        ".dff",
        ".tta",
        ".tak",
        ".caf",
    }
)

# What the walk will take as a track. A video file is one: its bonus tracks sit
# inside albums the library already holds, numbered in sequence, so leaving them
# out is a track missing from an album rather than a format not supported. Which
# suffixes carry a picture is the domain's to say, so it is read from there.
PLAYABLE_SUFFIXES = AUDIO_SUFFIXES | PICTURE_SUFFIXES

CUE_SUFFIXES = frozenset({".cue"})
IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp"})

# macOS writes AppleDouble stubs beside real files on non-native volumes.
# They carry a real FLAC name and are not audio, so they are skipped.
APPLEDOUBLE_PREFIX = "._"

# Named rather than guessed. Treating a leading dot as hidden was tried and it
# silently swallowed two real albums, "...And Justice for All" and
# "...Nothing Like The Sun". A music library is allowed to start with a dot.
SKIPPED_DIRECTORIES = frozenset(
    {
        "$recycle.bin",
        "system volume information",
        "@eadir",
        ".git",
        ".svn",
        ".trash",
        ".trashes",
        ".spotlight-v100",
        ".fseventsd",
        ".temporaryitems",
        "lost+found",
    }
)

# Cover files a ripper is most likely to have written, best first.
PREFERRED_ART_STEMS = ("cover", "folder", "front", "album", "albumart")


def _is_skippable_file(name: str) -> bool:
    """True for an AppleDouble stub, which is metadata rather than audio."""
    return name.startswith(APPLEDOUBLE_PREFIX)


def _names_audio(name: str) -> bool:
    """True when a filename is one the walk would take as audio."""
    if _is_skippable_file(name):
        return False
    return os.path.splitext(name)[1].casefold() in PLAYABLE_SUFFIXES


def _holds_audio(name: str) -> bool:
    """True for any audio file, whether or not this build can decode it."""
    suffix = os.path.splitext(name)[1].casefold()
    return suffix in PLAYABLE_SUFFIXES or suffix in UNPLAYABLE_SUFFIXES


def _is_skippable_directory(name: str) -> bool:
    """True for a named system directory. Never for an ordinary album."""
    return name.casefold() in SKIPPED_DIRECTORIES


def _art_rank(name: str) -> tuple[int, str]:
    """Ordering key putting the most likely cover file first."""
    stem = os.path.splitext(name)[0].casefold()
    for position, candidate in enumerate(PREFERRED_ART_STEMS):
        if stem == candidate:
            return (position, stem)
    return (len(PREFERRED_ART_STEMS), stem)


class FolderWalker:
    """Yields one listing per folder that contains audio."""

    def walk(self, root: str) -> Iterator[FolderListing]:
        """Walk a library root, deepest detail first within each folder."""
        for folder, directories, files in os.walk(root):
            directories[:] = sorted(
                name for name in directories if not _is_skippable_directory(name)
            )
            listing = self._listing(folder, files)
            if listing is not None:
                yield listing

    def reachable(self, root: str) -> bool:
        """Whether the root is a directory that is there right now.

        `os.walk` swallows the error for a root that does not exist, so a
        library on an unplugged drive walks as no folders at all. This is the
        question the walk cannot answer about itself.
        """
        return os.path.isdir(root)

    def count(self, root: str) -> int:
        """Count the folders holding audio, without stat-ing a single file.

        Measured over the reference library: a small fraction of a second,
        against a full scan of the same tree in the tens of seconds. Cheap
        enough to pay for a percentage that means something.
        """
        found = 0
        for _folder, directories, files in os.walk(root):
            directories[:] = [
                name for name in directories if not _is_skippable_directory(name)
            ]
            if any(_holds_audio(name) for name in files):
                found += 1
        return found

    def _listing(self, folder: str, files: list[str]) -> FolderListing | None:
        """Classify one folder's files; None when it holds no audio at all.

        A folder holding only audio this build cannot decode still yields a
        listing, carrying those files so the scan can say so. It used to yield
        nothing, so such an album was not skipped, reported or counted: it was
        simply not there, so a listener looking for one they own had no way to
        tell that from a library that had failed to scan.
        """
        audio: list[FileStat] = []
        unplayable: list[str] = []
        cues: list[str] = []
        images: list[str] = []
        for name in sorted(files):
            if _is_skippable_file(name):
                continue
            suffix = os.path.splitext(name)[1].casefold()
            path = os.path.join(folder, name)
            if _names_audio(name):
                stat = self._stat(path, name)
                if stat is not None:
                    audio.append(stat)
            elif suffix in UNPLAYABLE_SUFFIXES:
                unplayable.append(path)
            elif suffix in CUE_SUFFIXES:
                cues.append(path)
            elif suffix in IMAGE_SUFFIXES:
                images.append(path)
        if not audio and not unplayable:
            return None
        images.sort(key=lambda path: _art_rank(os.path.basename(path)))
        return FolderListing(
            folder=folder,
            audio=tuple(audio),
            unplayable=tuple(unplayable),
            cue_paths=tuple(cues),
            image_paths=tuple(images),
        )

    @staticmethod
    def _stat(path: str, name: str) -> FileStat | None:
        """Size and modification time; None when the file cannot be read."""
        try:
            info = os.stat(path)
        except OSError:
            return None
        return FileStat(
            path=path,
            file_name=name,
            size=info.st_size,
            mtime=int(info.st_mtime),
        )
