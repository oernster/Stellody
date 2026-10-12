"""Putting a staged restore in place as Stellody starts. BACKUP.md FR-B24.

Done before the library is opened, by the start that follows a confirmed
restore, because nothing can safely replace the database while a store holds
it: Windows refuses outright, while elsewhere the running store would carry on
writing into a file nobody reads any more. Done by ANY start rather than only
the one the restore asked for, since that relaunch can fail or the listener can
quit before it happens.

**The live set is moved aside, never deleted, until the restored one is in.**
Every move is a rename inside Stellody's own directory, which cannot half
happen. A failure part way moves the old files back, so the folder holds one
whole set or the other and never a mixture (FR-B34). The database's write ahead
log and shared memory file go aside with it: a log left beside the restored
database would be replayed onto it (FR-B26).

**A file of the set the backup does not hold is removed with the rest** (FR-B25):
a restore replaces; it does not merge.
"""

from __future__ import annotations

import json
import pathlib
import shutil
from collections.abc import Iterable
from dataclasses import dataclass

from stellody.infrastructure import paths
from stellody.infrastructure.backup_file import (
    BACKED_UP,
    BACKUP_KEY,
    NAMES_KEY,
    SAFETY_KEY,
    STAGED_NOTE,
    STAGING_DIR,
)
from stellody.infrastructure.opening import SIDECAR_SUFFIXES

# Where the live set waits while the restored one is moved in.
ASIDE_DIR = "restore-previous"


@dataclass(frozen=True, slots=True)
class Restored:
    """What a start found staged and what became of it. FR-B33, FR-B34."""

    backup: str
    safety: str
    failure: str = ""


def _live_names(backed_up: Iterable[str]) -> tuple[str, ...]:
    """Every live file a restore replaces, the database's sidecars included."""
    names = list(backed_up)
    names.extend(paths.DATABASE_NAME + suffix for suffix in SIDECAR_SUFFIXES)
    return tuple(names)


def _note(staging: pathlib.Path) -> dict | None:
    """The finished staging's note; None where staging never finished."""
    try:
        note = json.loads((staging / STAGED_NOTE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return note if isinstance(note, dict) else None


def apply(
    data_dir: pathlib.Path, backed_up: Iterable[str] = BACKED_UP
) -> Restored | None:
    """Put a staged restore in place; None where nothing was waiting.

    A staging with no note was interrupted while it was being made, so it is
    discarded: half a backup must never be put in place.
    """
    staging = data_dir / STAGING_DIR
    if not staging.is_dir():
        return None
    note = _note(staging)
    if note is None:
        shutil.rmtree(staging, ignore_errors=True)
        return None
    staged = [str(name) for name in note.get(NAMES_KEY, ())]
    restored = Restored(str(note.get(BACKUP_KEY, "")), str(note.get(SAFETY_KEY, "")))
    aside = data_dir / ASIDE_DIR
    moved: list[str] = []
    placed: list[str] = []
    try:
        shutil.rmtree(aside, ignore_errors=True)
        aside.mkdir()
        for name in _live_names(backed_up):
            if (data_dir / name).exists():
                (data_dir / name).replace(aside / name)
                moved.append(name)
        for name in staged:
            (staging / name).replace(data_dir / name)
            placed.append(name)
    except OSError as error:
        _put_back(data_dir, aside, moved, placed)
        shutil.rmtree(staging, ignore_errors=True)
        return Restored(restored.backup, restored.safety, str(error))
    shutil.rmtree(aside, ignore_errors=True)
    shutil.rmtree(staging, ignore_errors=True)
    return restored


def _put_back(
    data_dir: pathlib.Path,
    aside: pathlib.Path,
    moved: list[str],
    placed: list[str],
) -> None:
    """Undo a restore that failed part way, so the old set is whole again.

    Whatever cannot be moved back stays in the aside folder rather than being
    lost; the listener is told where the safety backup is either way.
    """
    for name in placed:
        try:
            (data_dir / name).unlink(missing_ok=True)
        except OSError:
            continue
    for name in moved:
        try:
            (aside / name).replace(data_dir / name)
        except OSError:
            continue
