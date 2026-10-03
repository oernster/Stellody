"""What a scan hands back: how far through it is, then what it found.

Kept apart from `scan.py`, which is how a library is read; this is what the
window is told about it, during the scan and once it ends. Both names are
still read from `scan.py` by everything that asked for them there.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from stellody.application.artwork import AlbumArtSources
from stellody.domain.album import Album
from stellody.domain.health import LibraryIssue

PERCENT = 100


@dataclass(frozen=True, slots=True)
class ScanProgress:
    """How far through a scan is, plus which folder it is reading.

    A library of a few thousand folders spends long enough scanning that a bar
    with no number on it says only that something is happening. The count is
    carried here rather than worked out on the interface thread, which has no
    way of knowing how many folders there are.
    """

    folder: str
    done: int = 0
    total: int = 0

    @property
    def percent(self) -> int:
        """How far through, as a whole number; nought when nothing is known."""
        if self.total <= 0:
            return 0
        return round(self.done * PERCENT / self.total)


ProgressCallback = Callable[[ScanProgress], None]
# Asked between folders, so a scan can be given up without waiting for it. A
# scan of a large library takes long enough that quitting during one is an
# ordinary thing to do; Qt cannot interrupt a running one from outside.


@dataclass(frozen=True, slots=True)
class ScanReport:
    """What one scan found, plus how much of it had to be re-read."""

    albums: tuple[Album, ...] = ()
    issues: tuple[LibraryIssue, ...] = ()
    art: tuple[AlbumArtSources, ...] = ()
    folders_probed: int = 0
    folders_reused: int = 0
    # Every readable audio file the library holds, NOT the files this scan
    # opened. A reused folder contributes its remembered files without one of
    # them being touched, so on a rescan that changed nothing this is the whole
    # library while nothing at all was read. It was called files_probed, which
    # said the opposite and was reported to a listener as "Files read".
    files_in_library: int = 0
    # Files that would not open or give their size, plus folders the system
    # would not let the walk list at all.
    files_unreadable: int = 0
    files_absent: int = 0
    cancelled: bool = False

    @property
    def track_count(self) -> int:
        """How many tracks the assembled library holds."""
        return sum(album.track_count for album in self.albums)

    @property
    def folders_checked(self) -> int:
        """Every folder the walk visited, whether or not it had to be re-read.

        A rescan that finds nothing changed still lists every folder and
        compares every file's size and modification time against the store.
        Reporting only the folders it re-read says nought, which reads as a
        scan that did nothing rather than as one that found nothing to do.
        """
        return self.folders_probed + self.folders_reused
