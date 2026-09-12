"""Loading the library the store already holds, reading no music at all.

Split out of `scan.py` when that file reached the length a module is allowed
here. The seam is a real one: a scan walks a folder and reads files, while a
load reads only what the last scan wrote down. They share one rule, that both
assemble albums the same way, because the window compares the two; that rule
is held by `tests/application/test_a_rescan_keeps_stated_albums.py` rather
than by keeping both in one file.
"""

from __future__ import annotations

from dataclasses import dataclass

from stellody.application.artwork import AlbumArtSources, sources_for
from stellody.application.ports import LibraryStore
from stellody.application.records import _grouping_entries
from stellody.domain.album import Album
from stellody.domain.entries import stated_over
from stellody.domain.grouping import assemble_albums
from stellody.domain.health import LibraryIssue


@dataclass(frozen=True, slots=True)
class LibraryView:
    """A library as it stands, with nothing said about how it got here.

    A scan reports counts of what it read; a load has read nothing, so it
    reports none, rather than zeroes that would read as a scan finding
    nothing.
    """

    albums: tuple[Album, ...] = ()
    issues: tuple[LibraryIssue, ...] = ()
    art: tuple[AlbumArtSources, ...] = ()

    @property
    def track_count(self) -> int:
        """How many tracks the assembled library holds."""
        return sum(album.track_count for album in self.albums)


class LoadLibrary:
    """Assembles the library the store already holds, reading no music at all.

    Starting the application is not a request to scan. On a library of any
    size a walk is felt; it reaches for a drive that may be asleep, absent or
    somebody else's machine over a network. What the store holds is
    what the last scan found, which is what the user last saw; anything newer
    arrives when they ask for it by rescanning.
    """

    def __init__(self, store: LibraryStore) -> None:
        self._store = store

    def run(self) -> LibraryView:
        """The remembered library, assembled from stored records."""
        records = tuple(self._store.load_folders())
        # Stated album values first, since they decide what an album IS and so
        # what folds with what; the accepted corrections are laid over the
        # tracks afterwards, which is where they have always gone.
        entries = stated_over(_grouping_entries(records), self._store.all_album_edits())
        albums, issues = assemble_albums(entries, self._store.all_overrides())
        return LibraryView(
            albums=albums,
            issues=tuple(issue for record in records for issue in record.issues)
            + issues,
            art=sources_for(albums, records),
        )
