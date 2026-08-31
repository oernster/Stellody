"""Walking a music library folder. Reads directory entries, writes nothing."""

from __future__ import annotations

import os
from collections.abc import Iterator

from stellody.application.values import FileStat, FolderListing

AUDIO_SUFFIXES = frozenset({".flac"})
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
    return os.path.splitext(name)[1].casefold() in AUDIO_SUFFIXES


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

    def count(self, root: str) -> int:
        """Count the folders holding audio, without stat-ing a single file.

        Measured over a 510 folder, 4870 file library: 0.04 seconds, against a
        full scan of the same tree in the tens of seconds. Cheap enough to pay
        for a percentage that means something.
        """
        found = 0
        for _folder, directories, files in os.walk(root):
            directories[:] = [
                name for name in directories if not _is_skippable_directory(name)
            ]
            if any(_names_audio(name) for name in files):
                found += 1
        return found

    def _listing(self, folder: str, files: list[str]) -> FolderListing | None:
        """Classify one folder's files; None when it holds no audio."""
        audio: list[FileStat] = []
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
            elif suffix in CUE_SUFFIXES:
                cues.append(path)
            elif suffix in IMAGE_SUFFIXES:
                images.append(path)
        if not audio:
            return None
        images.sort(key=lambda path: _art_rank(os.path.basename(path)))
        return FolderListing(
            folder=folder,
            audio=tuple(audio),
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
