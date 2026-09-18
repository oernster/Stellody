"""Two users of the catalogue memory at once lose nothing either learned.

A new run may start while a stopped one is still winding down (FR-D27); a
candidate can be opened on the results screen while a run goes on behind it.
Each keeps a copy of the memory taken when it started and saves it when it
ends. Measured on 2026-09-18, against the real file in a temporary folder:
saving a copy wrote it whole, then cleared the journal, so an answer another
user had noted since that copy was taken was lost. Lost after a crash when the
other user never saved; lost with no crash at all when the other user saved
last, over the answer the first had just written.
"""

from __future__ import annotations

import pytest

from stellody.application.remembering import IDENTIFIERS, Recollection
from stellody.infrastructure import catalogue_memory, paths

EARLY = 1.0
LATE = 2.0


@pytest.fixture(autouse=True)
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Keep the memory in a folder of the test's own."""
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    return tmp_path


def _noted(
    memory: catalogue_memory.FileCatalogueMemory,
    kept: Recollection,
    key: str,
    when: float = EARLY,
) -> None:
    """Learn one answer the way a run does: in its copy and in the journal."""
    answer = (f"id-{key}",)
    kept.identifiers[key] = answer
    kept.written_at[f"{IDENTIFIERS}:{key}"] = when
    memory.note(IDENTIFIERS, key, answer, when)


def test_an_older_copy_saved_leaves_a_newer_note_standing() -> None:
    """The stopped run saves after the new one noted; then the process dies."""
    memory = catalogue_memory.FileCatalogueMemory()
    stopped, started = memory.remembered(), memory.remembered()
    _noted(memory, started, "new-run-artist")
    memory.remember(stopped)
    assert "new-run-artist" in memory.remembered().identifiers


def test_the_last_to_save_keeps_what_the_other_saved() -> None:
    """No crash: one saves an answer, the other saves its older copy after."""
    memory = catalogue_memory.FileCatalogueMemory()
    first, second = memory.remembered(), memory.remembered()
    _noted(memory, first, "first-artist")
    memory.remember(first)
    memory.remember(second)
    assert "first-artist" in memory.remembered().identifiers


def test_of_two_answers_to_one_question_the_later_is_kept() -> None:
    """Saving an older copy never puts an older answer back."""
    memory = catalogue_memory.FileCatalogueMemory()
    older, newer = memory.remembered(), memory.remembered()
    _noted(memory, older, "artist", EARLY)
    _noted(memory, newer, "artist", LATE)
    older.identifiers["artist"] = ("id-older",)
    memory.remember(newer)
    memory.remember(older)
    kept = memory.remembered()
    assert kept.identifiers["artist"] == ("id-artist",)
    assert kept.written_at[f"{IDENTIFIERS}:artist"] == LATE
