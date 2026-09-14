"""What a finished run says, against what its written file then shows.

The file keeps an earlier answer for an artist this run could not reach and
records no failure for them, FR-D46. The sentence and the button were built
from the run's report as it stood before that carrying, so a run could say an
artist went unanswered beside a results screen showing that artist's answer.
FR-D42 and FR-D43 count artists left WITHOUT a usable answer; an earlier
answer carried over is a usable one.

Every path is pointed at a temporary directory, for the reason the file's own
suite gives: a run nobody made must not land beside the ones somebody did.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from discovery_wiring_support import completed, make_window, opened_results

from stellody.application.values import RunOutcome, RunReport, SourceFailure
from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.infrastructure import discovery_file, paths
from stellody.ui import shortfall
from stellody.ui.discovery_endings import FOUND

EARLIER = "Aztec Camera"
LATER = "Wire"


@pytest.fixture(autouse=True)
def somewhere_of_its_own(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point the data directory at a temporary one for every test here."""
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)


def _gaps(artist: str) -> Gaps:
    """One artist missing one album."""
    return Gaps(artist=artist, albums=(ReleaseGroup(title=f"{artist} album"),))


def test_an_artist_carried_over_is_not_called_unanswered(
    application, monkeypatch
) -> None:
    """The message and the button agree with the file the screen is read from."""
    discovery_file.write(
        RunReport(outcome=RunOutcome.COMPLETED, gaps=(_gaps(EARLIER),))
    )
    opened_results(monkeypatch)
    window = make_window(
        application,
        write=discovery_file.write,
        results=discovery_file.FileDiscoveryResults(),
    )
    completed(
        window,
        RunReport(
            outcome=RunOutcome.COMPLETED,
            gaps=(_gaps(LATER),),
            failed=(SourceFailure(artist=EARLIER, reason="refused"),),
        ),
    )
    written = json.loads(discovery_file.discovery_path().read_text(encoding="utf-8"))
    assert written["failed"] == [], "the file holds no failure for that artist"
    albums = sum(len(entry["albums"]) for entry in written["gaps"].values())
    artists = sum(len(entry["artists"]) for entry in written["gaps"].values())
    said = window.statusBar().said[-1]
    assert shortfall.SO_INCOMPLETE not in said, "nothing went unanswered"
    assert said == FOUND.format(
        albums=albums, artists=artists, where=discovery_file.discovery_path()
    ), "the counts are the counts the screen shows"
    assert window._shortfall_button.isHidden(), "no button owes anybody anything"
