"""FR-D69, FR-D70, FR-D74: series answers kept, read and written.

Every file here is pointed at the test's own directory. The MusicBrainz answers
are shaped as the live service answered on 2026-09-29.
"""

from __future__ import annotations

import json

import pytest
from test_discovery_sources import fetching

from stellody.application.remembering import (
    SERIES,
    SERIES_OF,
    TITLED,
    Recollection,
    stamp_for,
)
from stellody.application.values import RunOutcome, RunReport
from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.domain.matching import ReleaseKind
from stellody.domain.series import Series
from stellody.infrastructure import catalogue_memory, discovery_file, paths
from stellody.infrastructure.catalogue import RELEASE_GROUP_URL
from stellody.infrastructure.catalogue_series import SERIES_URL, MusicBrainzSeries

NOW = 1_700_000_000.0
ADAPT = "Global Underground: Adapt"
DATED = ReleaseGroup(title=f"{ADAPT} #3", released="2019-08-30")


@pytest.fixture(autouse=True)
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Keep every file this writes inside the test's own directory."""
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    return tmp_path


class TestTheMemory:
    """The three series answers survive the file and the running record."""

    def test_the_file_keeps_all_three(self) -> None:
        kept = Recollection(
            series_of={f"{ADAPT} #2": ("adapt",)},
            series={"adapt": Series(ADAPT, (DATED,))},
            titled={"Global Underground: Unique": (DATED,)},
            written_at={stamp_for(SERIES, "adapt"): NOW},
        )
        catalogue_memory.remember(kept)
        back = catalogue_memory.remembered()
        assert back.series_of == kept.series_of
        assert back.series == kept.series
        assert back.titled == kept.titled
        assert back.written_at[stamp_for(SERIES, "adapt")] == NOW

    def test_the_record_keeps_all_three(self) -> None:
        catalogue_memory.note(SERIES_OF, "t", ("adapt",), NOW)
        catalogue_memory.note(SERIES, "adapt", Series(ADAPT, (DATED,)), NOW)
        catalogue_memory.note(TITLED, "stem", (DATED,), NOW)
        back = catalogue_memory.remembered()
        assert back.series_of == {"t": ("adapt",)}
        assert back.series == {"adapt": Series(ADAPT, (DATED,))}
        assert back.titled == {"stem": (DATED,)}

    @pytest.mark.parametrize(
        "found",
        [
            "not a series",
            {"name": "", "albums": []},
            {"name": ADAPT, "albums": [{"title": "Undated"}]},
        ],
    )
    def test_an_unusable_series_is_left_out(self, found: object) -> None:
        catalogue_memory.memory_path().write_text(
            json.dumps({SERIES: {"adapt": found}}), encoding="utf-8"
        )
        assert catalogue_memory.remembered().series == {}

    def test_an_undated_search_is_left_out(self) -> None:
        catalogue_memory.memory_path().write_text(
            json.dumps({TITLED: {"stem": [{"title": "Undated"}]}}), encoding="utf-8"
        )
        assert catalogue_memory.remembered().titled == {}


def test_a_series_survives_the_file() -> None:
    """FR-D74: the flag is written and read back; an artist stays an artist."""
    discovery_file.write(
        RunReport(
            outcome=RunOutcome.COMPLETED,
            gaps=(
                Gaps(artist=ADAPT, albums=(DATED,), series=True),
                Gaps(artist="Giza Djs", albums=(DATED,)),
            ),
        )
    )
    read = {gaps.artist: gaps.series for gaps in discovery_file.read().gaps}
    assert read == {ADAPT: True, "Giza Djs": False}


class TestTheCatalogue:
    """The three questions, read from answers shaped as the service's."""

    def test_series_of_follows_the_group_in_the_same_place(self) -> None:
        search = {
            "release-groups": [
                {"id": "other", "title": "Global Underground: Adapt #3"},
                {"id": "rg2", "title": "Global Underground: Adapt #2"},
            ]
        }
        group = {
            "relations": [
                {"target-type": "series", "series": {"id": "adapt"}},
                {"target-type": "series", "series": {"id": "adapt"}},
                {"target-type": "url", "url": {"id": "x"}},
            ]
        }
        fetcher = fetching(search, group)
        found = MusicBrainzSeries(fetcher).series_of(
            "Global Underground: Adapt #2 / Unmixed"
        )
        assert found == ("adapt",)
        assert fetcher.parameters[0]["query"] == (
            'releasegroup:"Global Underground: Adapt #2"'
        )
        assert fetcher.addresses[1] == f"{RELEASE_GROUP_URL}/rg2"

    def test_a_series_lists_its_entries_in_order(self) -> None:
        answer = {
            "name": ADAPT,
            "relations": [
                {
                    "target-type": "release_group",
                    "release_group": {
                        "title": f"{ADAPT} #2",
                        "secondary-types": ["Compilation", "DJ-mix"],
                        "first-release-date": "2018-08-31",
                    },
                },
                {"target-type": "release_group", "release_group": {"title": " "}},
                {"target-type": "series", "series": {"id": "parent"}},
            ],
        }
        fetcher = fetching(answer)
        found = MusicBrainzSeries(fetcher).series("adapt")
        assert found == Series(
            ADAPT,
            (
                ReleaseGroup(
                    title=f"{ADAPT} #2",
                    kinds=(ReleaseKind.COMPILATION, ReleaseKind.DJ_MIX),
                    released="2018-08-31",
                ),
            ),
        )
        assert fetcher.addresses == [f"{SERIES_URL}/adapt"]

    def test_a_series_with_no_name_is_named_by_its_identifier(self) -> None:
        assert MusicBrainzSeries(fetching(None)).series("adapt") == Series("adapt")

    def test_titled_keeps_the_albums_a_search_answers(self) -> None:
        search = {
            "release-groups": [
                {"title": "Global Underground: Unique #2", "primary-type": "Album"},
                {
                    "title": "Global Underground: Unique (single)",
                    "primary-type": "Single",
                },
            ]
        }
        found = MusicBrainzSeries(fetching(search)).titled("Global Underground: Unique")
        assert [group.title for group in found] == ["Global Underground: Unique #2"]

    def test_it_makes_its_own_fetcher_when_given_none(self) -> None:
        assert MusicBrainzSeries() is not None
