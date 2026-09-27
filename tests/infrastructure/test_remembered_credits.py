"""Credits remembered between runs; identities under the old rule forgotten.

FR-D08, FR-D09. The identity answers kept before 2026-09-27 were matched on
case alone, so "Hernan Cattaneo" was remembered as nobody. They are filed
under a section no longer read, which is what these prove.
"""

from __future__ import annotations

import json

import pytest

from stellody.application.remembering import CREDITED, IDENTIFIERS, stamp_for
from stellody.infrastructure import catalogue_memory, paths

RETIRED = "identifiers"
QUESTION = "album|anyma|genesys"
NOW = 1_700_000_000.0


@pytest.fixture(autouse=True)
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Keep every file this writes inside the test's own directory."""
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    return tmp_path


def test_the_retired_section_is_not_read() -> None:
    catalogue_memory.memory_path().write_text(
        json.dumps(
            {
                RETIRED: {"Hernan Cattaneo": []},
                "written_at": {f"{RETIRED}:Hernan Cattaneo": NOW},
            }
        ),
        encoding="utf-8",
    )
    kept = catalogue_memory.remembered()
    assert kept.identifiers == {}
    assert kept.written_at == {}


def test_the_retired_section_is_gone_once_the_file_is_written() -> None:
    catalogue_memory.memory_path().write_text(
        json.dumps({RETIRED: {"Anyma": ["a", "b"]}}), encoding="utf-8"
    )
    catalogue_memory.remember(catalogue_memory.remembered())
    written = json.loads(catalogue_memory.memory_path().read_text(encoding="utf-8"))
    assert RETIRED not in written
    assert IDENTIFIERS != RETIRED


def test_a_noted_credit_survives_a_run_that_dies() -> None:
    catalogue_memory.note(CREDITED, QUESTION, ("anyma-milleri",), NOW)
    kept = catalogue_memory.remembered()
    assert kept.credited == {QUESTION: ("anyma-milleri",)}
    assert kept.written_at[stamp_for(CREDITED, QUESTION)] == NOW
