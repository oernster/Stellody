"""What a finished discovery run puts on screen.

The dialog is built from the discovery FILE rather than from the report in
hand, so these drive it from gaps read back the way the reader hands them
over. FR-D28 to FR-D34.

What happens when somebody OPENS a candidate is next door, in
`test_opening_a_candidate`: that one reaches a catalogue, crosses a thread and
can fail, which is a different concern from what a finished run puts up.
"""

from __future__ import annotations

import pytest
from discovery_wiring_support import (
    Results,
    a_report,
    completed,
    make_window,
    opened_results,
)
from results_support import (
    Catalogue,
    expansion,
    gaps_with,
    made,
    rows_under,
)

from stellody.ui.palette import Mode, palette_for
from stellody.ui.results_dialog import TITLE, ResultsDialog
from stellody.ui.results_words import source_row


def test_a_completed_run_opens_the_results(application, monkeypatch) -> None:
    """The whole of FR-D28: written first, then shown from what was written."""
    shown = opened_results(monkeypatch)
    found = (gaps_with(albums=2),)
    window = make_window(application, results=Results(found))
    completed(window, a_report(albums=2, artists=0))
    assert len(shown) == 1
    assert rows_under(shown[0].sources[0]) == ("Album 0", "Album 1")


def test_the_results_are_modal(application, monkeypatch) -> None:
    """Ruled by Oliver on 2026-09-08, after runs stacked without limit.

    Asserted as the STRUCTURE rather than as the symptom. Closing a standing
    screen as a new one opened was tried first and did not hold in the running
    application; a modal screen cannot stack because the window underneath it
    cannot start a second run while it is up. So what is held here is that the
    screen is opened by `exec` and never by `show`.
    """
    shown = opened_results(monkeypatch)
    showed: list[object] = []
    monkeypatch.setattr(ResultsDialog, "show", lambda dialog: showed.append(dialog))
    window = make_window(application, results=Results((gaps_with(albums=1),)))
    completed(window, a_report(albums=1, artists=0))
    assert len(shown) == 1, "opened with exec, which is what makes it modal"
    assert showed == [], "never with show, which would make it modeless again"


def test_the_ending_is_said_before_the_results_open(application, monkeypatch) -> None:
    """A message set after a modal screen appears only once it is closed.

    The unwanted sibling of making it modal. The status line and the button
    are put back by the same call, so saying it afterwards would leave the
    button crossed out for as long as somebody read their results.
    """
    said_when: list[int] = []
    window = make_window(application, results=Results((gaps_with(albums=1),)))

    def instead(dialog: ResultsDialog) -> int:
        """Record how much had been said by the time the screen opened."""
        said_when.append(len(window._status.said))
        return 0

    monkeypatch.setattr(ResultsDialog, "exec", instead)
    completed(window, a_report(albums=1, artists=0))
    assert said_when == [1], "the ending was said before the screen opened"


def test_the_genres_shown_come_from_the_file_it_is_showing(
    application, monkeypatch
) -> None:
    """The screen's question and its answer are read in one go.

    The ticks handed over when the run started are not consulted: the dialog
    is built from the file, so what it says it looked in has to come from
    there too, else a run started with one set of ticks could be shown above
    another run's gaps.
    """
    shown = opened_results(monkeypatch)
    found = (gaps_with(albums=1),)
    window = make_window(application, results=Results(found, ticked=("Folk",)))
    completed(window, a_report(albums=1, artists=0))
    assert "Folk" in shown[0].top.looked_in.text()


def test_a_run_that_found_nothing_still_shows_its_screen(
    application, monkeypatch
) -> None:
    """Ruled by Oliver on 2026-09-09, having twice been shown nothing. FR-D33.

    An empty screen is a poor screen; an hour of running that reports into a
    strip nobody is watching is worse. The screen says what was looked in and
    what could not be answered about, which the sentence alone does not.
    """
    shown = opened_results(monkeypatch)
    window = make_window(application, results=Results((), ticked=("Folk",)))
    completed(window, a_report(albums=0, artists=0))
    assert len(shown) == 1
    assert "Folk" in shown[0].top.looked_in.text()


def test_the_dialog_is_given_something_to_ask_with_where_there_is_one(
    application, monkeypatch
) -> None:
    """The wiring a candidate needs: an asker, belonging to the dialog.

    Parented to the dialog rather than left loose, so what asks the questions
    lives exactly as long as the rows the answers go in: a runner outliving
    its dialog would answer into rows Qt had already destroyed.
    """
    found = (gaps_with(artists=1),)
    shown = opened_results(monkeypatch)
    window = make_window(
        application,
        results=Results(found),
        expansion=expansion(Catalogue()),
    )
    completed(window, a_report(albums=0, artists=1))
    dialog = shown[0]
    assert dialog._asking is not None
    assert dialog._asking.parent() is dialog
    dialog.reject()


def test_a_source_artist_carries_its_albums(application) -> None:
    """Once each, with what they are missing beneath the name. FR-D29."""
    dialog = made((gaps_with(albums=2, artist="Kate Bush"),))
    assert len(dialog.sources) == 1
    source = dialog.sources[0]
    assert source.text(0) == source_row(gaps_with(albums=2, artist="Kate Bush"))
    assert "Kate Bush" in source.text(0)
    assert rows_under(source) == ("Album 0", "Album 1")


@pytest.mark.parametrize("mode", tuple(Mode))
def test_the_two_kinds_of_artist_are_coloured_apart(application, mode: Mode) -> None:
    """A list reading the same for both says nothing about which is which. FR-D34."""
    colour = palette_for(mode)
    dialog = ResultsDialog((gaps_with(albums=1, artists=1),), mode=mode)
    source = dialog.sources[0]
    candidate = source.child(source.childCount() - 1)
    drawn = source.foreground(0).color().name()
    assert drawn == colour.source_artist
    assert candidate.foreground(0).color().name() == colour.candidate_artist
    assert drawn != candidate.foreground(0).color().name()


def test_it_says_which_run_it_is_the_answer_to(application) -> None:
    """Asked for by Oliver on 2026-09-09, reading "What the last run found".

    Stellody has two kinds of run, a scan of the library and a discovery over
    the catalogues; this screen opens minutes after the question was asked.
    The same words in the title bar and across the top, from one constant,
    since a heading that drifts from the window title is two names for one
    dialog.
    """
    dialog = made((gaps_with(albums=1),))
    assert "discovery run" in TITLE
    assert dialog.title.text() == TITLE == dialog.windowTitle()
