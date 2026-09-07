"""Writing down what a run found, then keeping what it learned.

Every path here is pointed at a temporary directory: a test that wrote into
Stellody's own directory would put runs nobody made beside the ones somebody
did.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from stellody.application.values import (
    Ambiguity,
    RunOutcome,
    RunReport,
    SourceFailure,
)
from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.domain.matching import ReleaseKind
from stellody.infrastructure import discovery_file, paths


@pytest.fixture(autouse=True)
def somewhere_of_its_own(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point the data directory at a temporary one for every test here."""
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)


def a_report() -> RunReport:
    """A completed run with one of everything in it."""
    return RunReport(
        outcome=RunOutcome.COMPLETED,
        gaps=(
            Gaps(
                artist="Peter Gabriel",
                albums=(
                    ReleaseGroup(
                        title="Secret World Live",
                        kinds=(ReleaseKind.LIVE,),
                        genres=("Rock",),
                    ),
                ),
                artists=(SimilarArtist(name="Talk Talk", identifier="tt"),),
            ),
        ),
        unresolved=("Smetana",),
        ambiguous=(Ambiguity(artist="Nirvana", identifiers=("us", "uk")),),
        failed=(SourceFailure(artist="U2", reason="the service fell over"),),
    )


def test_the_file_is_keyed_by_the_artist_it_was_found_for() -> None:
    """What makes it usable as the resource a later stage reads."""
    where = discovery_file.write(a_report())
    written = json.loads(where.read_text(encoding="utf-8"))
    assert list(written["gaps"]) == ["Peter Gabriel"]
    album = written["gaps"]["Peter Gabriel"]["albums"][0]
    assert album["title"] == "Secret World Live"
    assert album["kinds"] == ["live"]
    assert written["gaps"]["Peter Gabriel"]["artists"][0]["name"] == "Talk Talk"


def test_what_could_not_be_answered_is_carried_beside_the_answers() -> None:
    """An artist nobody could look up reads as complete otherwise."""
    written = json.loads(discovery_file.write(a_report()).read_text(encoding="utf-8"))
    assert written["unresolved"] == ["Smetana"]
    assert written["ambiguous"][0]["identifiers"] == ["us", "uk"]
    assert written["failed"][0]["reason"] == "the service fell over"


def test_a_second_run_replaces_the_first() -> None:
    """Ruled on 2026-09-06: a run states what is missing now."""
    discovery_file.write(a_report())
    discovery_file.write(RunReport(outcome=RunOutcome.COMPLETED))
    written = json.loads(discovery_file.discovery_path().read_text(encoding="utf-8"))
    assert written["gaps"] == {}


@pytest.mark.parametrize(
    "outcome",
    [RunOutcome.CANCELLED, RunOutcome.UNAVAILABLE, RunOutcome.NOTHING_TO_ASK],
)
def test_a_run_with_nothing_to_say_cannot_replace_one_that_had(
    outcome: RunOutcome,
) -> None:
    """A cancelled run discards what it gathered rather than writing it."""
    with pytest.raises(ValueError, match="nothing to write"):
        discovery_file.write(RunReport(outcome=outcome))


def test_nothing_is_left_half_written() -> None:
    """Written beside the target and moved over it, so a reader sees one or other."""
    where = discovery_file.write(a_report())
    assert list(where.parent.glob("*.writing")) == []


def test_a_run_remembers_what_it_learned() -> None:
    """The next run asks about less, which is what makes the filter affordable."""
    discovery_file.remember({"tt": ("Rock", "Pop")})
    assert discovery_file.remembered() == {"tt": ("Rock", "Pop")}


def test_nothing_remembered_yet_is_not_a_failure() -> None:
    """The first run has no cache and must not care."""
    assert discovery_file.remembered() == {}


@pytest.mark.parametrize("content", ["{", '"not a mapping"', '{"tt": "not a list"}'])
def test_a_cache_that_cannot_be_read_costs_a_few_requests(content: str) -> None:
    """Which is not worth failing a run over."""
    discovery_file.cache_path().write_text(content, encoding="utf-8")
    assert discovery_file.remembered() == {}


def test_a_cache_that_cannot_be_written_is_not_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The next run simply asks again."""

    def refuse(*arguments: object, **keywords: object) -> None:
        """Stand in for a filesystem that will not take it."""
        raise OSError("no room")

    monkeypatch.setattr(discovery_file, "_written", refuse)
    discovery_file.remember({"tt": ("Rock",)})
    assert not discovery_file.cache_path().exists()


def test_the_memory_a_run_is_handed_reads_and_writes_that_same_cache() -> None:
    """The object the composition root injects, over the file above it.

    Asserted through the object rather than the functions, since the object is
    what a run actually holds: a facade that read somewhere else would pass
    every test above and still forget everything.
    """
    memory = discovery_file.FileGenreMemory()
    assert memory.remembered() == {}
    memory.remember({"tt": ("Rock", "Pop")})
    assert memory.remembered() == {"tt": ("Rock", "Pop")}
    assert discovery_file.cache_path().exists()
