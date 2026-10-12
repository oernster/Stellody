"""Backups written as zips, read back and staged. BACKUP.md."""

from __future__ import annotations

import hashlib
import json
import pathlib
import zipfile

import pytest
from backup_support import (
    MOMENT,
    WRITER,
    archive,
    data_folder,
    manifest_of,
    rewritten,
    setting_in,
)

from stellody.application.backing_up import BackupFailed, BackupRefused, Backups
from stellody.domain.backups import BACKUP_FORMAT, RefusalKind
from stellody.infrastructure import backup_file, database_schema, paths
from stellody.infrastructure.backup_file import (
    MANIFEST_NAME,
    STAGED_NOTE,
    STAGING_DIR,
)
from stellody.infrastructure.store import SqliteLibraryStore

NAME = "app-backup-2026-10-12-1405.zip"


@pytest.fixture
def folders(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """A data folder with a library, plus an empty folder to back up into."""
    out = tmp_path / "out"
    out.mkdir()
    return data_folder(tmp_path), out


def _written(data: pathlib.Path, out: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(archive(data).write(str(out), NAME, MOMENT))


def test_the_zip_lands_under_the_name_it_was_given(folders) -> None:
    """FR-B03: the name is chosen above; this writes it, nothing else."""
    data, out = folders
    written = _written(data, out)
    assert written == out / NAME
    assert sorted(entry.name for entry in out.iterdir()) == [NAME]


def test_a_write_still_in_the_wal_is_carried(folders, tmp_path) -> None:
    """FR-B08: a committed row the WAL still holds reaches the backup."""
    data, out = folders
    held = SqliteLibraryStore(str(data / paths.DATABASE_NAME))
    try:
        held.set_setting("probe", "only in the log")
        written = _written(data, out)
    finally:
        held.close()
    with zipfile.ZipFile(written) as zipped:
        zipped.extract(paths.DATABASE_NAME, tmp_path / "back")
    assert setting_in(tmp_path / "back" / paths.DATABASE_NAME) == "only in the log"


def test_the_manifest_names_every_file(folders) -> None:
    """FR-B14: format, writer, moment, plus each file's schema and checksum."""
    data, out = folders
    (data / "shops.json").write_text("{}", encoding="utf-8")
    written = _written(data, out)
    manifest = manifest_of(written)
    assert manifest["format"] == BACKUP_FORMAT
    assert manifest["written_by"] == WRITER
    assert manifest["written"] == MOMENT.isoformat()
    by_name = {entry["name"]: entry for entry in manifest["files"]}
    assert by_name[paths.DATABASE_NAME]["schema"] == database_schema.NEWEST
    with zipfile.ZipFile(written) as zipped:
        for name, entry in by_name.items():
            assert hashlib.sha256(zipped.read(name)).hexdigest() == entry["sha256"]


def test_a_missing_file_is_left_out(folders) -> None:
    """FR-B09: no shops.json in the folder, none in the backup."""
    data, out = folders
    written = _written(data, out)
    with zipfile.ZipFile(written) as zipped:
        assert "shops.json" not in zipped.namelist()
    assert "shops.json" not in {item["name"] for item in manifest_of(written)["files"]}


def test_the_journals_travel_with_their_files(folders) -> None:
    """DATA-B01: answers since the last whole write are not lost."""
    data, out = folders
    (data / "catalogue-memory.record").write_bytes(b'{"a": 1}\n{"b"')
    with zipfile.ZipFile(_written(data, out)) as zipped:
        assert zipped.read("catalogue-memory.record") == b'{"a": 1}\n{"b"'


def test_caches_and_logs_stay_behind(folders) -> None:
    """FR-B10."""
    data, out = folders
    (data / "artwork").mkdir()
    (data / "artwork" / "cover.jpg").write_bytes(b"x")
    (data / "stellody-diary.log").write_text("a line", encoding="utf-8")
    with zipfile.ZipFile(_written(data, out)) as zipped:
        carried = set(zipped.namelist())
    assert carried == {paths.DATABASE_NAME, MANIFEST_NAME}


def test_a_library_never_opened_is_simply_absent(tmp_path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    empty = tmp_path / "data"
    empty.mkdir()
    written = archive(empty).write(str(out), NAME, MOMENT)
    assert manifest_of(pathlib.Path(written))["files"] == []


def test_a_failed_write_leaves_nothing(folders, tmp_path) -> None:
    """FR-B12: the message names the folder; no zip, finished or not."""
    data, _ = folders
    gone = tmp_path / "not there"
    with pytest.raises(BackupFailed) as raised:
        archive(data).write(str(gone), NAME, MOMENT)
    assert str(gone) in str(raised.value)
    assert not gone.exists()


def test_the_names_in_a_folder_are_read(folders) -> None:
    data, out = folders
    _written(data, out)
    assert archive(data).names_in(str(out)) == frozenset({NAME})


def test_a_folder_that_cannot_be_read_holds_no_names(folders, tmp_path) -> None:
    data, _ = folders
    assert archive(data).names_in(str(tmp_path / "nowhere")) == frozenset()


class TestReading:
    def test_an_intact_backup_reads_back(self, folders) -> None:
        data, out = folders
        manifest = archive(data).read(str(_written(data, out)))
        assert manifest.written == MOMENT
        assert [item.name for item in manifest.carried] == [paths.DATABASE_NAME]

    def _refusal(self, data, backup):
        with pytest.raises(BackupRefused) as raised:
            archive(data).read(str(backup))
        assert raised.value.refusal.kind is RefusalKind.DAMAGED
        return str(raised.value)

    def test_a_file_that_is_not_a_zip_is_refused(self, folders) -> None:
        """FR-B28."""
        data, out = folders
        fake = out / "fake.zip"
        fake.write_text("not a zip", encoding="utf-8")
        assert "not a backup" in self._refusal(data, fake)

    def test_a_backup_with_no_manifest_is_refused(self, folders) -> None:
        data, out = folders
        written = _written(data, out)
        rewritten(written, lambda name, held: None if name == MANIFEST_NAME else held)
        assert "no readable manifest" in self._refusal(data, written)

    def test_a_manifest_of_the_wrong_shape_is_refused(self, folders) -> None:
        data, out = folders
        written = _written(data, out)
        rewritten(
            written,
            lambda name, held: b'{"format": 1}' if name == MANIFEST_NAME else held,
        )
        assert "not one this version reads" in self._refusal(data, written)

    def test_a_listed_file_that_is_missing_is_refused(self, folders) -> None:
        data, out = folders
        written = _written(data, out)
        rewritten(
            written,
            lambda name, held: None if name == paths.DATABASE_NAME else held,
        )
        assert f"{paths.DATABASE_NAME} is missing" in self._refusal(data, written)

    def test_a_changed_byte_is_refused(self, folders) -> None:
        """FR-B28: names the file and the checksum."""
        data, out = folders
        written = _written(data, out)

        def flipped(name, held):
            if name != paths.DATABASE_NAME:
                return held
            return bytes([held[0] ^ 1]) + held[1:]

        rewritten(written, flipped)
        said = self._refusal(data, written)
        assert paths.DATABASE_NAME in said and "checksum" in said


class TestStaging:
    def test_staging_unpacks_every_file_then_the_note(self, folders) -> None:
        data, out = folders
        (data / "shops.json").write_text('{"x": 1}', encoding="utf-8")
        written = _written(data, out)
        archive(data).stage(str(written), "safety.zip")
        staging = data / STAGING_DIR
        note = json.loads((staging / STAGED_NOTE).read_text(encoding="utf-8"))
        assert note == {
            "backup": str(written),
            "safety": "safety.zip",
            "names": [paths.DATABASE_NAME, "shops.json"],
        }
        assert (staging / "shops.json").read_text(encoding="utf-8") == '{"x": 1}'

    def test_a_backup_that_fails_its_check_stages_nothing(self, folders) -> None:
        data, out = folders
        fake = out / "fake.zip"
        fake.write_text("not a zip", encoding="utf-8")
        with pytest.raises(BackupFailed):
            archive(data).stage(str(fake), "safety.zip")
        assert not (data / STAGING_DIR).exists()


def test_the_errands_are_built_over_the_data_folder(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(paths, "data_location", lambda: tmp_path)
    assert isinstance(backup_file.backups(), Backups)
    assert backup_file._local_now().tzinfo is not None
