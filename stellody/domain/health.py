"""Library health: what Stellody had to work around, reported not repaired.

Stellody never writes to a music library, so a damaged tag is described rather
than corrected. The reference library carries 21 albums whose tags collide,
left behind by another player that did write to the files.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IssueKind(StrEnum):
    """The kinds of defect a scan can notice in a library."""

    DUPLICATE_TRACK_NUMBER = "duplicate-track-number"
    DISC_NUMBER_CONFLICT = "disc-number-conflict"
    MISSING_TRACK_NUMBER = "missing-track-number"
    MISSING_TITLE = "missing-title"
    MISSING_ALBUM_ARTIST = "missing-album-artist"
    NO_ARTWORK = "no-artwork"
    UNREADABLE_FILE = "unreadable-file"


SEVERITY_ORDER: dict[IssueKind, int] = {
    IssueKind.DUPLICATE_TRACK_NUMBER: 0,
    IssueKind.DISC_NUMBER_CONFLICT: 1,
    IssueKind.MISSING_TRACK_NUMBER: 2,
    IssueKind.MISSING_TITLE: 3,
    IssueKind.MISSING_ALBUM_ARTIST: 4,
    IssueKind.UNREADABLE_FILE: 5,
    IssueKind.NO_ARTWORK: 6,
}

_SUMMARIES: dict[IssueKind, str] = {
    IssueKind.DUPLICATE_TRACK_NUMBER: (
        "Several files claim the same disc and track number. "
        "Ordering fell back to the file names."
    ),
    IssueKind.DISC_NUMBER_CONFLICT: (
        "Disc number tags disagree with the folder name. " "The folder was believed."
    ),
    IssueKind.MISSING_TRACK_NUMBER: (
        "No track number in the tags. Ordering came from the file name."
    ),
    IssueKind.MISSING_TITLE: ("No title in the tags. The file name was used instead."),
    IssueKind.MISSING_ALBUM_ARTIST: (
        "No album artist in the tags. The track artist was used instead."
    ),
    IssueKind.NO_ARTWORK: "No cover art was found next to or inside the files.",
    # Named FLAC while FLAC was the only format Stellody read. It now scans six,
    # so a listener whose MP3 failed was told the wrong thing about it. The
    # second sentence is what the others all say: what Stellody did about it.
    IssueKind.UNREADABLE_FILE: (
        "The file could not be read, so it is not in your library."
    ),
}


@dataclass(frozen=True, slots=True)
class LibraryIssue:
    """One thing worth telling the user about their files."""

    kind: IssueKind
    album: str
    detail: str = ""
    paths: tuple[str, ...] = ()
    # The album's identity handle, beside the label shown to a reader. The
    # label is display text: two albums with one title and one artist share it,
    # a reissue beside its original being the ordinary case. So attributing a
    # finding to an album by its label cannot be relied on and the handle is
    # carried instead. Empty where the finding belongs to a folder rather than
    # to an assembled album, which is a finding nothing can accept anyway.
    album_key: str = ""

    @property
    def summary(self) -> str:
        """A plain sentence explaining what Stellody did about this."""
        return _SUMMARIES[self.kind]

    @property
    def sort_key(self) -> tuple[int, str, str]:
        """Most serious first, then alphabetically by album."""
        return (SEVERITY_ORDER[self.kind], self.album.casefold(), self.detail)


def sorted_issues(issues: tuple[LibraryIssue, ...]) -> tuple[LibraryIssue, ...]:
    """Order issues for display, most serious first."""
    return tuple(sorted(issues, key=lambda issue: issue.sort_key))


def issue_counts(issues: tuple[LibraryIssue, ...]) -> dict[IssueKind, int]:
    """How many of each kind of issue a library carries."""
    counts: dict[IssueKind, int] = {}
    for issue in issues:
        counts[issue.kind] = counts.get(issue.kind, 0) + 1
    return counts
