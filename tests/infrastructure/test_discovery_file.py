"""Writing down what a run found, then keeping what it learned.

Every path here is pointed at a temporary directory: a test that wrote into
Stellody's own directory would put runs nobody made beside the ones somebody
did.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import replace

import pytest

from stellody.application.carrying_over import IncompleteAnswer
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
    """A completed run with one of everything in it, a failure included.

    A run carrying a failure about an artist nothing was ever known about is
    not written at all, so this is what the tests about refusing to write are
    driven with; `an_answer` below is the same run having answered about
    everybody.
    """
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


def an_answer() -> RunReport:
    """The same run, having answered about everybody it asked about."""
    return replace(a_report(), failed=())


def test_the_file_is_keyed_by_the_artist_it_was_found_for() -> None:
    """What makes it usable as the resource a later stage reads."""
    where = discovery_file.write(an_answer())
    written = json.loads(where.read_text(encoding="utf-8"))
    assert list(written["gaps"]) == ["Peter Gabriel"]
    album = written["gaps"]["Peter Gabriel"]["albums"][0]
    assert album["title"] == "Secret World Live"
    assert album["kinds"] == ["live"]
    assert written["gaps"]["Peter Gabriel"]["artists"][0]["name"] == "Talk Talk"


def test_what_could_not_be_answered_is_carried_beside_the_answers() -> None:
    """A name the catalogue does not know and a name it knows twice are
    answers rather than failures, so they are written down as such."""
    written = json.loads(discovery_file.write(an_answer()).read_text(encoding="utf-8"))
    assert written["unresolved"] == ["Smetana"]
    assert written["ambiguous"][0]["identifiers"] == ["us", "uk"]
    assert written["failed"] == [], "a written answer has no holes in it"


def test_an_answer_with_a_hole_in_it_is_not_written_at_all() -> None:
    """Demanded by Oliver on 2026-09-08: a file holding whichever artists a
    service felt like answering about is a different file every time."""
    discovery_file.write(an_answer())
    with pytest.raises(IncompleteAnswer, match="U2"):
        discovery_file.write(a_report())
    written = json.loads(discovery_file.discovery_path().read_text(encoding="utf-8"))
    assert list(written["gaps"]) == ["Peter Gabriel"], "the last one still stands"


def test_an_artist_already_answered_for_is_not_a_hole() -> None:
    """A run that could not reach somebody the last run reached keeps that
    answer, so the file is written exactly as it was before."""
    discovery_file.write(an_answer())
    again = replace(
        a_report(),
        gaps=(),
        failed=(SourceFailure(artist="Peter Gabriel", reason="refused"),),
    )
    written = json.loads(discovery_file.write(again).read_text(encoding="utf-8"))
    assert list(written["gaps"]) == ["Peter Gabriel"]


def test_the_artists_are_written_in_one_order_however_they_arrived() -> None:
    """The same content in two orders is two different screens."""
    scrambled = replace(
        an_answer(),
        gaps=(Gaps(artist="Wire"), Gaps(artist="Aztec Camera"), Gaps(artist="Móż")),
    )
    written = json.loads(discovery_file.write(scrambled).read_text(encoding="utf-8"))
    assert list(written["gaps"]) == sorted(["Wire", "Aztec Camera", "Móż"])


def test_a_second_run_replaces_the_first() -> None:
    """Ruled on 2026-09-06: a run states what is missing now."""
    discovery_file.write(an_answer())
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
    where = discovery_file.write(an_answer())
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
