"""Release dates, from the catalogue to the files that keep them. FR-D61 to FR-D67.

What the catalogue states is read as stated; what a run was asked for is
written beside what it found; an answer remembered from before dates were kept
is asked for again rather than read as undated.
"""

from __future__ import annotations

import json

import pytest

from stellody.application.remembering import ALBUMS, IDENTIFIERS
from stellody.application.values import RunOutcome, RunReport
from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.domain.release_years import ANY_YEAR, ReleaseYears
from stellody.infrastructure import catalogue_memory, discovery_file, paths
from stellody.infrastructure.catalogue import FIRST_RELEASE, MusicBrainz
from tests.infrastructure.test_discovery_sources import fetching

WOLF = "wolf-id"
NOW = 1_000_000.0
EIGHTIES = ReleaseYears(1980, 1989)


@pytest.fixture
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Keep every file this writes inside the test's own directory."""
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    return tmp_path


class TestReadingTheCatalogue:
    def test_every_shape_of_first_release_is_kept_as_stated(self) -> None:
        """Measured on 2026-09-26: a year, a year and month, a date or empty."""
        stated = ("1985", "1984-01", "1985-07-30", "")
        body = {
            "release-groups": [
                {"title": f"Album {n}", "primary-type": "Album", FIRST_RELEASE: when}
                for n, when in enumerate(stated)
            ]
        }
        found = MusicBrainz(fetching(body)).albums_of("id")
        assert [group.released for group in found] == list(stated)

    def test_no_first_release_at_all_is_no_date(self) -> None:
        body = {"release-groups": [{"title": "Demos", "primary-type": "Album"}]}
        assert MusicBrainz(fetching(body)).albums_of("id")[0].released == ""


class TestTheDiscoveryFile:
    def completed(self, years: ReleaseYears) -> RunReport:
        """A finished run over Rock that found one dated album."""
        gaps = Gaps(
            artist="Kate Bush",
            albums=(ReleaseGroup(title="Hounds of Love", released="1985-07-30"),),
        )
        return RunReport(
            outcome=RunOutcome.COMPLETED, gaps=(gaps,), ticked=("Rock",), years=years
        )

    def test_the_years_and_dates_come_back_as_written(self, data_dir) -> None:
        discovery_file.write(self.completed(EIGHTIES))
        answer = discovery_file.read()
        assert answer.years == EIGHTIES
        assert answer.gaps[0].albums[0].released == "1985-07-30"

    def test_one_bound_alone_comes_back_alone(self, data_dir) -> None:
        discovery_file.write(self.completed(ReleaseYears(earliest=2020)))
        assert discovery_file.read().years == ReleaseYears(earliest=2020)

    def test_no_years_come_back_as_every_year(self, data_dir) -> None:
        discovery_file.write(self.completed(ANY_YEAR))
        assert discovery_file.read().years == ANY_YEAR

    @pytest.mark.parametrize(
        "stated",
        [
            None,
            "1980",
            {"earliest": "1980", "latest": 1989},
            {"earliest": True},
            {"earliest": 1990, "latest": 1980},
        ],
    )
    def test_years_that_cannot_be_read_are_every_year(
        self, data_dir, stated: object
    ) -> None:
        """An older file names none; a damaged one costs its years, not its gaps."""
        held = {"gaps": {"Kate Bush": {"albums": [], "artists": []}}}
        if stated is not None:
            held["years"] = stated
        discovery_file.discovery_path().write_text(json.dumps(held), "utf-8")
        answer = discovery_file.read()
        assert answer.years == ANY_YEAR
        assert [gaps.artist for gaps in answer.gaps] == ["Kate Bush"]


class TestTheCatalogueMemory:
    def test_an_answer_kept_before_dates_is_asked_for_again(self, data_dir) -> None:
        """FR-D67: absent, so asked, rather than read as stating no year."""
        catalogue_memory.memory_path().write_text(
            json.dumps(
                {
                    IDENTIFIERS: {"Howlin' Wolf": [WOLF]},
                    ALBUMS: {
                        WOLF: [{"title": "Moanin'", "kinds": [], "genres": []}],
                        "dated": [{"title": "Later", "released": "1962"}],
                        "empty": [],
                    },
                }
            ),
            encoding="utf-8",
        )
        kept = catalogue_memory.remembered()
        assert WOLF not in kept.albums
        assert kept.albums["dated"][0].year == 1962
        assert kept.albums["empty"] == ()
        assert kept.identifiers == {"Howlin' Wolf": (WOLF,)}

    def test_a_noted_answer_before_dates_is_asked_for_again(self, data_dir) -> None:
        catalogue_memory.journal_path().write_text(
            json.dumps(
                {
                    "kind": ALBUMS,
                    "key": WOLF,
                    "when": NOW,
                    "answer": [{"title": "Moanin'"}],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        assert WOLF not in catalogue_memory.remembered().albums

    def test_an_answer_kept_now_keeps_its_dates(self, data_dir) -> None:
        dated = (ReleaseGroup(title="Moanin'", released="1959"),)
        catalogue_memory.note(ALBUMS, WOLF, dated, NOW)
        assert catalogue_memory.remembered().albums[WOLF] == dated
