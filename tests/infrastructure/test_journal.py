"""One answer written down the moment it arrives, then read back after a death.

The record behind the promise that a run which never ends still keeps what it
paid for. What matters here is that an append cannot be undone by whatever
happens next: a line already written is readable even where the line after it
is half a line; a file nobody can write is a missing safety net rather than a
failed run.
"""

from __future__ import annotations

import pytest

from stellody.infrastructure import journal


@pytest.fixture
def record(tmp_path):
    """A record inside the test's own directory."""
    return tmp_path / "answers.record"


def test_nothing_is_replayed_before_anything_is_noted(record) -> None:
    assert journal.replayed(record) == ()


def test_what_was_noted_comes_back_in_the_order_it_was_noted(record) -> None:
    journal.note(record, {"key": "first"})
    journal.note(record, {"key": "second"})
    assert journal.replayed(record) == ({"key": "first"}, {"key": "second"})


def test_a_half_written_last_line_costs_only_that_line(record) -> None:
    """The case the whole module exists for: a process that died mid-write."""
    journal.note(record, {"key": "first"})
    with record.open("a", encoding="utf-8") as dying:
        dying.write('{"key": "sec')
    assert journal.replayed(record) == ({"key": "first"},)


def test_a_line_holding_something_other_than_an_entry_is_skipped(record) -> None:
    record.write_text('"a bare string"\n{"key": "kept"}\n', encoding="utf-8")
    assert journal.replayed(record) == ({"key": "kept"},)


def test_a_record_nobody_can_read_is_no_answers(record) -> None:
    """A directory where a file should be: unreadable, never fatal."""
    record.mkdir()
    assert journal.replayed(record) == ()


def test_a_record_nobody_can_write_is_not_an_error(tmp_path) -> None:
    journal.note(tmp_path / "no such directory" / "answers.record", {"key": "lost"})


def test_clearing_drops_the_record(record) -> None:
    journal.note(record, {"key": "first"})
    journal.cleared(record)
    assert not record.exists()
    assert journal.replayed(record) == ()


def test_clearing_what_is_not_there_says_nothing(record) -> None:
    journal.cleared(record)


def test_a_record_that_cannot_be_dropped_is_not_an_error(record) -> None:
    """A directory cannot be unlinked, which is the shape of any refusal."""
    record.mkdir()
    journal.cleared(record)
    assert record.exists()
