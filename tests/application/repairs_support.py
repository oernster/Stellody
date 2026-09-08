"""The pieces every repair test builds on: a watching store, tracks, findings.

Held apart from the tests so the file holding them stays inside the length a
module here is allowed; also so a second file about one corner of the same
service does not grow its own copy of them.
"""

from __future__ import annotations

from stellody.application.scan import LibraryView
from stellody.domain.album import Album
from stellody.domain.health import IssueKind, LibraryIssue
from stellody.domain.identity import AlbumIdentity
from stellody.domain.overrides import AlbumEdit, Override
from stellody.domain.track import Track, TrackSource

FOLDER = "H:/Music/Portishead/Dummy"
RATE = 44100


class RecordingStore:
    # Whatever anybody has stated about an album, kept as the real store
    # keeps it: a set that starts empty and grows only when something is said.
    stated_albums: tuple = ()

    """Just enough store to watch what the service asks of it."""

    def __init__(self) -> None:
        self.accepted: tuple[Override, ...] = ()
        self.discarded: tuple[Override, ...] = ()

    def all_overrides(self) -> tuple[Override, ...]:
        return self.accepted

    def accept_overrides(self, accepted: tuple[Override, ...]) -> None:
        self.accepted = self.accepted + accepted

    def discard_overrides(self, unwanted: tuple[Override, ...]) -> None:
        self.discarded = self.discarded + unwanted
        dropped = {(item.album, item.path, item.field) for item in unwanted}
        self.accepted = tuple(
            item
            for item in self.accepted
            if (item.album, item.path, item.field) not in dropped
        )

    def all_album_edits(self) -> tuple[AlbumEdit, ...]:
        return self.stated_albums

    def state_album_edits(self, stated: tuple[AlbumEdit, ...]) -> None:
        self.stated_albums = self.stated_albums + tuple(stated)

    def discard_album_edits(self, unwanted: tuple[AlbumEdit, ...]) -> None:
        dropped = {(item.folder, item.field) for item in unwanted}
        self.stated_albums = tuple(
            item
            for item in self.stated_albums
            if (item.folder, item.field) not in dropped
        )


def track(
    file_name: str, disc: int = 1, number: int = 1, folder: str = FOLDER
) -> Track:
    """One resolved track, as the rules would have left it."""
    return Track(
        source=TrackSource(path=f"{folder}/{file_name}"),
        disc_number=disc,
        track_number=number,
        title=f"Title of {file_name}",
        artists=("Portishead",),
        duration_ms=1000,
        sample_rate=RATE,
        bit_depth=16,
    )


IDENTITY = AlbumIdentity(album_artist="Portishead", title="Dummy", date="1994")
OTHER = AlbumIdentity(album_artist="Portishead", title="Third", date="2008")
ALBUM = Album(
    identity=IDENTITY,
    tracks=(
        track("01 Mysterons.flac", number=1),
        track("02 Sour Times.flac", number=2),
    ),
)
VIEW = LibraryView(albums=(ALBUM,))


def issue(
    kind: IssueKind,
    paths: tuple[str, ...] = (),
    key: str = "",
    addresses: tuple[str, ...] | None = None,
) -> LibraryIssue:
    """A finding attributed to the album under test unless told otherwise.

    The addresses default to the files those names stand for in this album's
    own folder, which is what a scan of it would have carried. A test about one
    name worn twice states them itself, that being the case where a single name
    is two different files.
    """
    return LibraryIssue(
        kind=kind,
        album="Portishead - Dummy",
        paths=paths,
        album_key=key or IDENTITY.handle,
        addresses=(
            tuple(f"{FOLDER}/{name}" for name in paths)
            if addresses is None
            else addresses
        ),
    )
