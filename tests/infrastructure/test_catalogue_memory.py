"""What the catalogues said, kept in a file between runs.

The file behind the promise that two runs over one library agree. What matters
here is that it comes back exactly as it went in; a file somebody has damaged
costs a run its speed rather than its life.
"""

from __future__ import annotations

import json

import pytest

from stellody.application.remembering import Recollection, similar_key
from stellody.domain.discovery import ReleaseGroup, SimilarArtist
from stellody.domain.matching import ReleaseKind
from stellody.infrastructure import catalogue_memory, paths

WOLF = "wolf-id"


@pytest.fixture(autouse=True)
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Keep every file this writes inside the test's own directory."""
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    return tmp_path


def _full() -> Recollection:
    """A recollection with something of every kind in it."""
    return Recollection(
        identifiers={"Howlin' Wolf": (WOLF,)},
        albums={
            WOLF: (
                ReleaseGroup(
                    title="Moanin' in the Moonlight",
                    kinds=(ReleaseKind.LIVE,),
                    genres=("Blues",),
                ),
            )
        },
        similar={
            similar_key(WOLF, 100): (
                SimilarArtist(name="Muddy Waters", identifier="mw-id"),
            )
        },
        written_at={f"albums:{WOLF}": 1_700_000_000.0},
    )


def test_nothing_is_remembered_before_anything_is_kept() -> None:
    assert catalogue_memory.remembered() == Recollection()


def test_what_is_kept_comes_back_exactly() -> None:
    """The whole promise: identical in, identical out, kinds and genres too."""
    catalogue_memory.remember(_full())
    assert catalogue_memory.remembered() == _full()


def test_a_file_that_cannot_be_read_is_an_empty_memory(data_dir) -> None:
    """A run pays for it in requests rather than in an exception."""
    catalogue_memory.memory_path().write_text("not json at all", encoding="utf-8")
    assert catalogue_memory.remembered() == Recollection()


def test_a_file_holding_the_wrong_shape_is_an_empty_memory(data_dir) -> None:
    """Written by something else; written by a Stellody that shaped it
    differently."""
    catalogue_memory.memory_path().write_text('["a list"]', encoding="utf-8")
    assert catalogue_memory.remembered() == Recollection()


def test_entries_of_the_wrong_shape_are_dropped_rather_than_carried(
    data_dir,
) -> None:
    """One damaged album does not cost the artist beside it."""
    catalogue_memory.memory_path().write_text(
        json.dumps(
            {
                "identifiers": "not a mapping",
                "albums": {WOLF: [{"title": "Kept"}, {"nothing": "usable"}, "junk"]},
                "similar": {WOLF: [{"name": "Muddy Waters", "identifier": "mw"}, 7]},
            }
        ),
        encoding="utf-8",
    )
    kept = catalogue_memory.remembered()
    assert kept.identifiers == {}
    assert [album.title for album in kept.albums[WOLF]] == ["Kept"]
    assert [artist.name for artist in kept.similar[WOLF]] == ["Muddy Waters"]


def test_a_memory_that_cannot_be_written_is_not_an_error(monkeypatch) -> None:
    """Failing to remember costs the next run its requests, nothing more."""

    def refuse(where, held) -> None:
        """Stand in for a disk that will not take it."""
        raise OSError("no room")

    monkeypatch.setattr(catalogue_memory, "_written", refuse)
    catalogue_memory.remember(_full())


class TestTheMemoryARunIsHanded:
    def test_it_recalls_what_was_kept(self) -> None:
        memory = catalogue_memory.FileCatalogueMemory()
        memory.remember(_full())
        assert memory.remembered() == _full()
