"""The catalogue memory is read once a session and written whole once, at quit.

Reported by Oliver on 2026-10-11: pressing Discover made the music judder, as
did stopping a run. The diary showed the device run dry within half a second of
each, with the feeder waiting to run; reading the 18 MB memory file and
writing it whole were measured holding Python's interpreter for a tenth of a
second at a stretch. What is held here is that neither happens while a run
starts or stops; also that nothing learned is lost by putting the write off.
"""

from __future__ import annotations

import threading

import pytest

from stellody.application.remembering import IDENTIFIERS, Recollection
from stellody.infrastructure import catalogue_memory, held_memory, journal, paths

WHEN = 1.0


@pytest.fixture(autouse=True)
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Keep the memory in a folder of the test's own."""
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def writes(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Every whole write of the file, counted rather than prevented."""
    made: list[object] = []
    real = catalogue_memory._written

    def counted(where, held) -> None:
        made.append(held)
        real(where, held)

    monkeypatch.setattr(catalogue_memory, "_written", counted)
    return made


def _learned(memory: held_memory.FileCatalogueMemory, key: str) -> Recollection:
    """A run's copy holding one new answer, noted as a run notes it."""
    kept = memory.remembered()
    answer = (f"id-{key}",)
    kept.identifiers[key] = answer
    kept.written_at[f"{IDENTIFIERS}:{key}"] = WHEN
    memory.note(IDENTIFIERS, key, answer, WHEN)
    return kept


def test_the_file_is_read_once_however_often_it_is_asked_for(monkeypatch) -> None:
    reads: list[int] = []
    real = held_memory.remembered

    def counted() -> Recollection:
        reads.append(1)
        return real()

    monkeypatch.setattr(held_memory, "remembered", counted)
    memory = held_memory.FileCatalogueMemory()
    for _ in range(3):
        memory.remembered()
    memory.remember(memory.remembered())
    assert len(reads) == 1


def test_a_run_ending_writes_nothing_while_quitting_writes_once(writes) -> None:
    """The judder was the whole file written as a run was stopped."""
    memory = held_memory.FileCatalogueMemory()
    memory.remember(_learned(memory, "wolf"))
    assert writes == []
    memory.keep()
    assert len(writes) == 1
    assert journal.replayed(catalogue_memory.journal_path()) == ()
    assert "wolf" in catalogue_memory.remembered().identifiers


def test_quitting_with_nothing_new_writes_nothing(writes) -> None:
    memory = held_memory.FileCatalogueMemory()
    memory.remembered()
    memory.keep()
    assert writes == []


def test_a_process_that_dies_before_quitting_loses_nothing(writes) -> None:
    """The next session reads the running record on top of the file."""
    _learned(held_memory.FileCatalogueMemory(), "wolf")
    assert writes == []
    assert "wolf" in held_memory.FileCatalogueMemory().remembered().identifiers


def test_each_caller_is_handed_a_copy() -> None:
    """A stopped run still adding to its copy cannot change another's."""
    memory = held_memory.FileCatalogueMemory()
    stopped = memory.remembered()
    stopped.identifiers["late"] = ("id-late",)
    assert "late" not in memory.remembered().identifiers


def test_a_note_reaches_what_later_callers_are_handed() -> None:
    memory = held_memory.FileCatalogueMemory()
    _learned(memory, "wolf")
    assert memory.remembered().identifiers["wolf"] == ("id-wolf",)


class TestReadingAhead:
    def test_the_memory_is_read_on_a_thread_of_its_own(self, monkeypatch) -> None:
        read = threading.Event()
        memory = held_memory.FileCatalogueMemory()
        monkeypatch.setattr(memory, "remembered", read.set)
        held_memory.warm_memory(memory, lambda _said: None)
        assert read.wait(timeout=5)

    def test_a_memory_that_cannot_be_read_ahead_is_noted(self, monkeypatch) -> None:
        said: list[str] = []
        noted = threading.Event()

        def refuse() -> None:
            raise RuntimeError("unreadable")

        def note(message: str) -> None:
            said.append(message)
            noted.set()

        memory = held_memory.FileCatalogueMemory()
        monkeypatch.setattr(memory, "remembered", refuse)
        held_memory.warm_memory(memory, note)
        assert noted.wait(timeout=5)
        assert "unreadable" in said[0]
