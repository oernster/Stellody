"""An album Stellody cannot play is reported, never quietly left out.

Reported from a real library: a listener went looking for an album they own and
it was not there. It had not failed, been skipped or been counted; the walk
never yielded its folder at all, so nothing anywhere could mention it. A person
cannot tell that from a library that failed to scan.

Driven through the REAL walker on real files in a temporary folder, since the
walk is what changed. The files are empty, which is faithful: nothing opens
them, because being unable to open them is the whole point.
"""

from __future__ import annotations

import pathlib

from stellody.application.scan import ScanLibrary
from stellody.application.values import AudioProperties
from stellody.domain.health import IssueKind
from stellody.domain.overrides import can_be_accepted
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.infrastructure.walker import FolderWalker

RATE = 44100


class OnlyFlacReads:
    """A probe that reads FLAC and nothing else, as libsndfile does here."""

    def read(self, path: str) -> AudioProperties | None:
        if not path.casefold().endswith(".flac"):
            return None
        return AudioProperties(
            sample_rate=RATE,
            bit_depth=16,
            frame_count=RATE,
            tags={"album": ("Emotional Technology",), "artist": ("BT",)},
        )


class NoCues:
    """No cue sheets in these folders."""

    def read(self, path: str) -> str | None:
        return None


def _library(tmp_path: pathlib.Path, folder: str, names: list[str]) -> str:
    """A music folder holding exactly these file names."""
    album = tmp_path / folder
    album.mkdir(parents=True)
    for name in names:
        (album / name).write_bytes(b"")
    return str(tmp_path)


def _scan(root: str, database: str):
    """One real scan over a real walk into a real store."""
    store = SqliteLibraryStore(database)
    try:
        return ScanLibrary(FolderWalker(), OnlyFlacReads(), NoCues(), store).run(root)
    finally:
        store.close()


def _of_kind(report, kind: IssueKind):
    return [issue for issue in report.issues if issue.kind is kind]


class TestAFolderHoldingOnlyWhatCannotBePlayed:
    """BT's Emotional Technology, which is 21 M4A files and nothing else."""

    def _report(self, tmp_path: pathlib.Path):
        root = _library(
            tmp_path / "music",
            "BT/Emotional Technology",
            [f"{number:02d} Track.m4a" for number in range(1, 22)],
        )
        return _scan(root, str(tmp_path / "library.db"))

    def test_it_is_reported_rather_than_passed_over(
        self, tmp_path: pathlib.Path
    ) -> None:
        """The whole of what this change is for."""
        found = _of_kind(self._report(tmp_path), IssueKind.UNPLAYABLE_FORMAT)
        assert found, "an album that is not there must still be said out loud"

    def test_it_is_one_finding_for_the_folder_not_one_a_file(
        self, tmp_path: pathlib.Path
    ) -> None:
        """A thousand entries is not a report anybody reads."""
        assert len(_of_kind(self._report(tmp_path), IssueKind.UNPLAYABLE_FORMAT)) == 1

    def test_it_says_how_many_and_which_format(self, tmp_path: pathlib.Path) -> None:
        found = _of_kind(self._report(tmp_path), IssueKind.UNPLAYABLE_FORMAT)[0]
        assert "21" in found.detail
        assert ".m4a" in found.detail

    def test_it_names_the_folder_so_the_album_can_be_found(
        self, tmp_path: pathlib.Path
    ) -> None:
        found = _of_kind(self._report(tmp_path), IssueKind.UNPLAYABLE_FORMAT)[0]
        assert "Emotional Technology" in found.album

    def test_no_album_is_invented_from_files_nothing_could_read(
        self, tmp_path: pathlib.Path
    ) -> None:
        assert self._report(tmp_path).albums == ()

    def test_it_can_never_be_accepted(self, tmp_path: pathlib.Path) -> None:
        """There is nothing to accept: no value is being proposed."""
        assert not can_be_accepted(IssueKind.UNPLAYABLE_FORMAT)


class TestAFolderHoldingBoth:
    def _report(self, tmp_path: pathlib.Path):
        root = _library(
            tmp_path / "music",
            "BT/Movement in Still Life",
            ["01 One.flac", "02 Two.flac", "03 Bonus.m4a"],
        )
        return _scan(root, str(tmp_path / "library.db"))

    def test_the_album_is_still_assembled_from_what_can_be_read(
        self, tmp_path: pathlib.Path
    ) -> None:
        report = self._report(tmp_path)
        assert report.albums
        assert report.track_count == 2

    def test_and_the_rest_is_still_named(self, tmp_path: pathlib.Path) -> None:
        """A bonus track in another format must not disappear either."""
        found = _of_kind(self._report(tmp_path), IssueKind.UNPLAYABLE_FORMAT)
        assert len(found) == 1
        assert "1" in found[0].detail


class TestNothingElseChanged:
    def test_a_folder_of_readable_audio_raises_nothing_of_the_kind(
        self, tmp_path: pathlib.Path
    ) -> None:
        root = _library(tmp_path / "music", "BT/ESCM", ["01 One.flac"])
        report = _scan(root, str(tmp_path / "library.db"))
        assert _of_kind(report, IssueKind.UNPLAYABLE_FORMAT) == []
        assert report.albums

    def test_a_folder_of_nothing_but_pictures_is_still_no_folder(
        self, tmp_path: pathlib.Path
    ) -> None:
        """A stray file is not a missing album; only audio is reported."""
        root = _library(tmp_path / "music", "BT/Sleeves", ["cover.jpg", "notes.txt"])
        report = _scan(root, str(tmp_path / "library.db"))
        assert report.issues == ()
        assert report.folders_checked == 0
