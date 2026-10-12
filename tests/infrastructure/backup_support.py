"""A data folder holding a real library, for the backup and restore tests."""

from __future__ import annotations

import json
import pathlib
import zipfile
from datetime import UTC, datetime

from stellody.infrastructure import paths
from stellody.infrastructure.backup_file import MANIFEST_NAME, ZipArchive
from stellody.infrastructure.store import SqliteLibraryStore

MOMENT = datetime(2026, 10, 12, 14, 5, tzinfo=UTC)
WRITER = "9.9.9"


def data_folder(root: pathlib.Path, setting: str = "kept") -> pathlib.Path:
    """A data folder whose library holds one setting, closed again."""
    data = root / "data"
    data.mkdir(parents=True)
    store = SqliteLibraryStore(str(data / paths.DATABASE_NAME))
    store.set_setting("probe", setting)
    store.close()
    return data


def archive(data: pathlib.Path) -> ZipArchive:
    """The archive over this data folder."""
    return ZipArchive(data, data / paths.DATABASE_NAME, WRITER)


def setting_in(database: pathlib.Path) -> str:
    """The probe setting a library file holds."""
    store = SqliteLibraryStore(str(database))
    try:
        return store.get_setting("probe")
    finally:
        store.close()


def manifest_of(backup: pathlib.Path) -> dict:
    """The parsed manifest inside a backup."""
    with zipfile.ZipFile(backup) as zipped:
        return json.loads(zipped.read(MANIFEST_NAME))


def rewritten(backup: pathlib.Path, change) -> None:
    """Rewrite a backup with every member passed through `change(name, data)`.

    A member `change` answers None for is left out.
    """
    with zipfile.ZipFile(backup) as zipped:
        members = {name: zipped.read(name) for name in zipped.namelist()}
    with zipfile.ZipFile(backup, "w") as zipped:
        for name, data in members.items():
            changed = change(name, data)
            if changed is not None:
                zipped.writestr(name, changed)
