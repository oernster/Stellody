"""A run whose process dies keeps every answer it had already paid for.

Reported by Oliver on 2026-09-09. He left a discovery going overnight and came
back to a run that had ended at fifty minutes; had the process died rather than
returned, all of it would have gone, because both memories were written once,
at the end. Measured from that night's own file: 581 answers standing on a
single write that a crash would simply have skipped.

So both memories note each answer as it arrives. These tests kill a run in the
only way that matters here, by never letting it reach the line that writes the
file, then ask a fresh memory what is known.
"""

from __future__ import annotations

import pytest

from stellody.application.remembering import ALBUMS, IDENTIFIERS, SIMILAR, similar_key
from stellody.domain.discovery import ReleaseGroup, SimilarArtist
from stellody.domain.matching import ReleaseKind
from stellody.infrastructure import catalogue_memory, discovery_file, paths

WOLF = "wolf-id"
NOW = 1_700_000_000.0
MOANIN = ReleaseGroup(
    title="Moanin' in the Moonlight", kinds=(ReleaseKind.LIVE,), genres=("Blues",)
)
MUDDY = SimilarArtist(name="Muddy Waters", identifier="mw-id")


@pytest.fixture(autouse=True)
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Keep every file this writes inside the test's own directory."""
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    return tmp_path


def test_answers_noted_by_a_run_that_never_finished_are_still_known() -> None:
    """Nothing consolidates them; they are known all the same."""
    catalogue_memory.note(IDENTIFIERS, "Howlin' Wolf", (WOLF,), NOW)
    catalogue_memory.note(ALBUMS, WOLF, (MOANIN,), NOW)
    catalogue_memory.note(SIMILAR, similar_key(WOLF, 10), (MUDDY,), NOW)
    kept = catalogue_memory.remembered()
    assert kept.identifiers == {"Howlin' Wolf": (WOLF,)}
    assert kept.albums == {WOLF: (MOANIN,)}
    assert kept.similar == {similar_key(WOLF, 10): (MUDDY,)}


def test_a_noted_answer_stands_from_when_it_was_noted() -> None:
    """The stamp travels with the answer, so its month is counted from then."""
    catalogue_memory.note(ALBUMS, WOLF, (MOANIN,), NOW)
    assert catalogue_memory.remembered().standing(f"{ALBUMS}:{WOLF}", NOW)


def test_a_later_answer_to_the_same_question_wins() -> None:
    catalogue_memory.note(IDENTIFIERS, "Howlin' Wolf", ("first",), NOW)
    catalogue_memory.note(IDENTIFIERS, "Howlin' Wolf", ("second",), NOW)
    assert catalogue_memory.remembered().identifiers == {"Howlin' Wolf": ("second",)}


def test_notes_are_read_on_top_of_the_file_rather_than_instead_of_it() -> None:
    """What an ended run wrote and what a dead one noted are both known."""
    catalogue_memory.note(IDENTIFIERS, "Howlin' Wolf", (WOLF,), NOW)
    catalogue_memory.remember(catalogue_memory.remembered())
    catalogue_memory.note(IDENTIFIERS, "Muddy Waters", ("mw-id",), NOW)
    assert catalogue_memory.remembered().identifiers == {
        "Howlin' Wolf": (WOLF,),
        "Muddy Waters": ("mw-id",),
    }


def test_consolidating_drops_the_record_it_has_taken_over(data_dir) -> None:
    """Both hold the same answers while both exist, so one of them goes."""
    catalogue_memory.note(IDENTIFIERS, "Howlin' Wolf", (WOLF,), NOW)
    assert catalogue_memory.journal_path().exists()
    catalogue_memory.remember(catalogue_memory.remembered())
    assert not catalogue_memory.journal_path().exists()


def test_a_record_is_kept_where_the_file_could_not_be_written(monkeypatch) -> None:
    """The safety net is not cut away when the thing it protects fails."""

    def refused(*_args, **_kwargs) -> None:
        raise OSError("no room")

    catalogue_memory.note(IDENTIFIERS, "Howlin' Wolf", (WOLF,), NOW)
    monkeypatch.setattr(catalogue_memory, "_written", refused)
    catalogue_memory.remember(catalogue_memory.remembered())
    assert catalogue_memory.journal_path().exists()
    assert catalogue_memory.remembered().identifiers == {"Howlin' Wolf": (WOLF,)}


def test_a_note_of_a_kind_this_stellody_does_not_know_is_skipped() -> None:
    """A record written by a later version costs requests, never the run."""
    catalogue_memory.note("video", WOLF, (), NOW)
    assert catalogue_memory.remembered().written_at == {}


def test_a_note_missing_its_key_or_its_stamp_is_skipped(data_dir) -> None:
    catalogue_memory.journal_path().write_text(
        '{"kind": "identifiers", "when": 1.0}\n'
        '{"kind": "identifiers", "key": "U2"}\n',
        encoding="utf-8",
    )
    assert catalogue_memory.remembered().identifiers == {}


def test_genres_noted_by_a_run_that_never_finished_are_still_known() -> None:
    """The long half of a run, which is the half with the most to lose."""
    discovery_file.note(WOLF, ("Blues",))
    assert discovery_file.remembered() == {WOLF: ("Blues",)}


def test_a_noted_genre_answer_is_read_on_top_of_the_cache() -> None:
    discovery_file.remember({WOLF: ("Blues",)})
    discovery_file.note("mw-id", ("Delta Blues",))
    assert discovery_file.remembered() == {
        WOLF: ("Blues",),
        "mw-id": ("Delta Blues",),
    }


def test_keeping_the_genre_cache_drops_its_record() -> None:
    discovery_file.note(WOLF, ("Blues",))
    assert discovery_file.cache_journal_path().exists()
    discovery_file.remember(discovery_file.remembered())
    assert not discovery_file.cache_journal_path().exists()


def test_a_genre_note_that_is_not_an_answer_is_skipped(data_dir) -> None:
    discovery_file.cache_journal_path().write_text(
        '{"identifier": "wolf-id"}\n{"genres": ["Blues"]}\n', encoding="utf-8"
    )
    assert discovery_file.remembered() == {}
