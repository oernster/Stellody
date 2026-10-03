"""A folder or file the system refuses, through the REAL walker into a real store.

Measured with a subfolder refusing to be listed: `os.walk` was given no error
handler, so it passed over the folder in silence and the album inside was
reported as renamed, moved or removed, its files marked absent. A file whose
size could not be read was dropped without being counted. The refusals are
simulated by standing in for the two calls the system answers, which is the
only way a test can make Windows refuse a folder its own user created.
"""

from __future__ import annotations

import os
import pathlib

import pytest

from stellody.application.scan import ScanLibrary
from stellody.application.values import AudioProperties
from stellody.domain.health import IssueKind
from stellody.infrastructure import walker as walker_module
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.infrastructure.walker import FolderWalker

RATE = 44100
REFUSED = PermissionError(13, "Access is denied")


class AlbumPerFolder:
    """A probe naming each track's album after the folder it sits in."""

    def read(self, path: str) -> AudioProperties:
        folder = pathlib.Path(path).parent.name
        return AudioProperties(
            sample_rate=RATE,
            bit_depth=16,
            frame_count=RATE,
            tags={"album": (folder,), "albumartist": ("Band",)},
        )


class NoCues:
    """No cue sheets in these folders."""

    def read(self, path: str) -> str | None:
        return None


@pytest.fixture
def library(tmp_path: pathlib.Path) -> pathlib.Path:
    """Two albums under one artist, one of two tracks."""
    for album, names in (("Kept", ["01.flac"]), ("Locked", ["01.flac", "02.flac"])):
        folder = tmp_path / "music" / "Band" / album
        folder.mkdir(parents=True)
        for name in names:
            (folder / name).write_bytes(b"")
    return tmp_path / "music"


def scan(root: pathlib.Path, database: pathlib.Path):
    """One real scan over a real walk into a real store."""
    store = SqliteLibraryStore(str(database))
    try:
        return ScanLibrary(FolderWalker(), AlbumPerFolder(), NoCues(), store).run(
            str(root)
        )
    finally:
        store.close()


def titles(report) -> set[str]:
    return {album.identity.display_title for album in report.albums}


def test_a_folder_that_will_not_list_is_unreadable_rather_than_gone(
    library: pathlib.Path, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "library.sqlite3"
    assert titles(scan(library, database)) == {"Kept", "Locked"}
    real_scandir = os.scandir

    def refusing(path="."):
        if os.path.basename(os.fspath(path)) == "Locked":
            raise PermissionError(13, "Access is denied", os.fspath(path))
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", refusing)
    report = scan(library, database)
    assert report.files_unreadable == 1
    assert report.files_absent == 0
    assert titles(report) == {"Kept", "Locked"}, "the album is NOT absent"
    folders = [i.album for i in report.issues if i.kind is IssueKind.UNREADABLE_FOLDER]
    assert folders == [str(library / "Band" / "Locked")]
    monkeypatch.undo()
    assert titles(scan(library, database)) == {"Kept", "Locked"}


def test_a_file_whose_size_cannot_be_read_is_counted(
    library: pathlib.Path, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_stat = os.stat
    awkward = os.path.join("Locked", "02.flac")

    def failing(path, *args, **kwargs):
        if os.fspath(path).endswith(awkward):
            raise REFUSED
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(walker_module.os, "stat", failing)
    report = scan(library, tmp_path / "library.sqlite3")
    assert report.files_unreadable == 1
    paths = [i.paths for i in report.issues if i.kind is IssueKind.UNREADABLE_FILE]
    assert paths == [(str(library / "Band" / awkward),)]
