"""A cue sheet or a cover added after a scan, through the REAL walker and store.

Measured before the fix: a cue sheet written beside a single file album that
had already been scanned was never read, since a rescan compared the audio
alone and the audio had not changed; a cover added later went the same way.
What the store keeps of them has to survive being written and read back;
otherwise every rescan would read every folder holding one.
"""

from __future__ import annotations

import pathlib

from stellody.application.scan import ScanLibrary
from stellody.application.values import AudioProperties
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.infrastructure.textfile import SidecarTextReader
from stellody.infrastructure.walker import FolderWalker

RATE = 44100
LENGTH_S = 120

SHEET = (
    'PERFORMER "Sasha"\n'
    'TITLE "Involver"\n'
    'FILE "Involver.flac" WAVE\n'
    "  TRACK 01 AUDIO\n"
    '    TITLE "Wavy Gravy"\n'
    "    INDEX 01 00:00:00\n"
    "  TRACK 02 AUDIO\n"
    '    TITLE "Cutting Room"\n'
    "    INDEX 01 00:01:00\n"
)


class LongFlac:
    """A probe answering two minutes of audio for any file."""

    def read(self, path: str) -> AudioProperties:
        return AudioProperties(
            sample_rate=RATE,
            bit_depth=16,
            frame_count=RATE * LENGTH_S,
            tags={"album": ("Involver",), "albumartist": ("Sasha",)},
        )


def scan(root: pathlib.Path, database: pathlib.Path):
    """One real scan over a real walk into a real store."""
    store = SqliteLibraryStore(str(database))
    try:
        return ScanLibrary(FolderWalker(), LongFlac(), SidecarTextReader(), store).run(
            str(root)
        )
    finally:
        store.close()


def test_a_cue_sheet_then_a_cover_added_later_are_both_noticed(
    tmp_path: pathlib.Path,
) -> None:
    root = tmp_path / "music"
    album = root / "Sasha" / "Involver"
    album.mkdir(parents=True)
    (album / "Involver.flac").write_bytes(b"")
    database = tmp_path / "library.sqlite3"
    assert scan(root, database).track_count == 1

    (album / "Involver.cue").write_text(SHEET, encoding="utf-8")
    added = scan(root, database)
    assert added.folders_probed == 1
    assert added.track_count == 2, "the sheet was read"

    unchanged = scan(root, database)
    assert (unchanged.folders_reused, unchanged.folders_probed) == (1, 0)

    (album / "cover.jpg").write_bytes(b"\xff\xd8\xff")
    covered = scan(root, database)
    assert covered.folders_probed == 1
    assert scan(root, database).folders_reused == 1
