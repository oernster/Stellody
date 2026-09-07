"""Reading a run's answer back out of the file it was written to.

Its own module because the writing tests beside it are about a report going in,
while these are about a file coming back, including files no run would have
written. Every path is pointed at a temporary directory, so nothing here can
read or replace the answer a real run left.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from stellody.application.values import Gaps, RunOutcome, RunReport
from stellody.domain.discovery import ReleaseGroup, SimilarArtist
from stellody.domain.matching import ReleaseKind
from stellody.infrastructure import discovery_file, paths


@pytest.fixture(autouse=True)
def somewhere_of_its_own(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point the data directory at a temporary one for every test here."""
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)


def put(content: object) -> None:
    """Put this where the reader looks, whatever shape it is."""
    discovery_file.discovery_path().write_text(json.dumps(content), encoding="utf-8")


def a_report() -> RunReport:
    """A completed run holding one source artist with both kinds of gap."""
    return RunReport(
        outcome=RunOutcome.COMPLETED,
        gaps=(
            Gaps(
                artist="Muddy Waters",
                albums=(
                    ReleaseGroup(
                        title="Electric Mud",
                        kinds=(ReleaseKind.LIVE,),
                        genres=("Blues",),
                    ),
                ),
                artists=(SimilarArtist(name="Howlin' Wolf", identifier="wolf"),),
            ),
        ),
    )


class TestWhatARunLeftBehind:
    """The ordinary case: what was written comes back as it went in."""

    def test_a_run_is_read_back_as_it_was_written(self) -> None:
        """FR-D28: the dialog is shown from the file rather than the report."""
        discovery_file.write(a_report())
        found = discovery_file.read()
        assert [gaps.artist for gaps in found] == ["Muddy Waters"]
        assert found[0].albums[0].title == "Electric Mud"
        assert found[0].albums[0].kinds == (ReleaseKind.LIVE,)
        assert found[0].albums[0].genres == ("Blues",)
        assert found[0].artists[0].name == "Howlin' Wolf"
        assert found[0].artists[0].identifier == "wolf"

    def test_the_port_answers_with_the_same_thing(self) -> None:
        """The window holds the port; the port holds the file."""
        discovery_file.write(a_report())
        assert discovery_file.FileDiscoveryResults().last_run() == discovery_file.read()

    def test_the_order_is_the_order_the_run_met_them_in(self) -> None:
        """The catalogue had an opinion about it and this has none."""
        put(
            {
                "gaps": {
                    "Second": {"albums": [], "artists": []},
                    "First": {"albums": [], "artists": []},
                }
            }
        )
        assert [gaps.artist for gaps in discovery_file.read()] == ["Second", "First"]


class TestAFileNobodyCouldRead:
    """No results rather than no application, which is the ruling above."""

    def test_no_file_at_all_is_no_results(self) -> None:
        """The ordinary case before anybody has ever run a discovery."""
        assert discovery_file.read() == ()

    def test_a_file_that_is_not_json_is_no_results(self) -> None:
        """Something else got written there, which is not worth raising over."""
        discovery_file.discovery_path().write_text("{", encoding="utf-8")
        assert discovery_file.read() == ()

    @pytest.mark.parametrize(
        "content", [[], "not a mapping", {}, {"gaps": []}, {"gaps": "nope"}]
    )
    def test_a_file_of_the_wrong_shape_is_no_results(self, content: object) -> None:
        """A file from a later Stellody, else from nothing at all."""
        put(content)
        assert discovery_file.read() == ()


class TestEntriesThatCannotBeRead:
    """One unreadable entry loses that entry, never the whole answer."""

    def test_an_artist_whose_entry_is_not_a_mapping_is_passed_over(self) -> None:
        """The rest of a run that took eleven minutes is still worth showing."""
        put({"gaps": {"Broken": "nope", "Muddy Waters": {"albums": [], "artists": []}}})
        assert [gaps.artist for gaps in discovery_file.read()] == ["Muddy Waters"]

    def test_an_artist_with_no_name_is_passed_over(self) -> None:
        """Nothing can be shown under a name that is not there."""
        put({"gaps": {"  ": {"albums": [], "artists": []}}})
        assert discovery_file.read() == ()

    def test_an_album_with_no_title_is_passed_over(self) -> None:
        """The domain refuses one; a record nobody can name is not one."""
        put(
            {
                "gaps": {
                    "Muddy Waters": {
                        "albums": [{"title": ""}, "nope", {"title": "Electric Mud"}],
                        "artists": [],
                    }
                }
            }
        )
        found = discovery_file.read()
        assert [album.title for album in found[0].albums] == ["Electric Mud"]

    def test_a_candidate_with_no_name_is_passed_over(self) -> None:
        """A candidate nobody can be told about is not a candidate."""
        put(
            {
                "gaps": {
                    "Muddy Waters": {
                        "albums": [],
                        "artists": [{"name": ""}, "nope", {"name": "Howlin' Wolf"}],
                    }
                }
            }
        )
        found = discovery_file.read()
        assert [artist.name for artist in found[0].artists] == ["Howlin' Wolf"]

    def test_lists_that_are_not_lists_state_nothing(self) -> None:
        """A file of the wrong shape inside a right one, entry by entry."""
        put({"gaps": {"Muddy Waters": {"albums": "nope", "artists": 3}}})
        found = discovery_file.read()
        assert found[0].albums == ()
        assert found[0].artists == ()

    def test_a_kind_this_version_never_heard_of_is_carried_as_other(self) -> None:
        """A file from a later Stellody, read without inventing a plain album."""
        put(
            {
                "gaps": {
                    "Muddy Waters": {
                        "albums": [{"title": "A Record", "kinds": ["hologram"]}],
                        "artists": [],
                    }
                }
            }
        )
        found = discovery_file.read()
        assert found[0].albums[0].kinds == (ReleaseKind.OTHER,)
        assert not found[0].albums[0].is_offered
