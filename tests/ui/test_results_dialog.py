"""What a finished discovery run puts on screen.

The dialog is built from the discovery FILE rather than from the report in
hand, so these drive it from gaps read back the way the reader hands them
over. FR-D28 to FR-D34.

The asking is stood in for in most of these, because what the dialog does with
an answer is a different question from how the answer is fetched. One test at
the end drives the REAL runner over a fake catalogue, so the thread the answer
actually crosses is exercised rather than assumed.
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
    Asking,
    Catalogue,
    candidate_in,
    expansion,
    gaps_with,
    made,
    rows_under,
    waited_for,
)

from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.ui.expansion_worker import ExpansionRunner
from stellody.ui.palette import Mode, palette_for
from stellody.ui.results_dialog import ResultsDialog
from stellody.ui.results_words import (
    COULD_NOT_ASK,
    NOBODY_TO_ASK,
    NOTHING_OFFERED,
    asking_about,
    candidate_row,
    source_row,
)


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


def test_a_run_that_found_nothing_shows_no_dialog(application, monkeypatch) -> None:
    """An empty dialog says less than the sentence shown in its place. FR-D33."""
    shown = opened_results(monkeypatch)
    window = make_window(application, results=Results(()))
    completed(window, a_report(albums=0, artists=0))
    assert shown == []


def test_a_file_that_reads_back_empty_opens_nothing(application, monkeypatch) -> None:
    """A run can find things and the file still read back as nothing.

    A separate case from the one above rather than the same one twice: there
    the run found nothing, so nothing was written; here something was written
    and the reader came back empty, which is a file that could not be read.
    Planting the removal of the guard proved the test above did not cover it.
    """
    shown = opened_results(monkeypatch)
    reader = Results(())
    window = make_window(application, results=reader)
    completed(window, a_report(albums=2, artists=1))
    assert reader.reads == 1
    assert shown == []


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


def test_a_candidate_artist_starts_collapsed(application) -> None:
    """Named, with nothing beneath and nothing asked for yet. FR-D30."""
    asking = Asking()
    dialog = made((gaps_with(artists=3),), asking=asking)
    source = dialog.sources[0]
    assert rows_under(source) == tuple(candidate_row(f"Artist {n}") for n in range(3))
    for at in range(source.childCount()):
        assert source.child(at).childCount() == 0
    assert asking.asked == []


def test_expanding_a_candidate_asks_for_their_albums(application) -> None:
    """The question is put when it is opened; never before. FR-D31."""
    asking = Asking()
    dialog = made((gaps_with(artists=2),), asking=asking)
    candidate = candidate_in(dialog, at=1)
    candidate.setExpanded(True)
    assert asking.asked == ["id-0"]
    assert rows_under(candidate) == ()
    assert dialog.asking_bar.format() == asking_about(("Artist 0",))
    dialog.show_releases("id-0", (ReleaseGroup(title="Hounds of Love"),))
    assert rows_under(candidate) == ("Hounds of Love",)


def test_a_candidate_is_asked_about_once_however_often_it_is_opened(
    application,
) -> None:
    """Closing and opening one again is not a second request to pay for."""
    asking = Asking()
    dialog = made((gaps_with(artists=1),), asking=asking)
    candidate = candidate_in(dialog)
    candidate.setExpanded(True)
    dialog.show_releases("id-0", (ReleaseGroup(title="The Dreaming"),))
    candidate.setExpanded(False)
    candidate.setExpanded(True)
    assert asking.asked == ["id-0"]
    assert rows_under(candidate) == ("The Dreaming",)


def test_a_candidate_the_catalogue_could_not_name_says_so(application) -> None:
    """A name with no identifier is nobody to ask about, so it says that."""
    asking = Asking()
    nameless = Gaps(artist="U2", artists=(SimilarArtist(name="Someone"),))
    dialog = made((nameless,), asking=asking)
    candidate = candidate_in(dialog)
    candidate.setExpanded(True)
    assert asking.asked == []
    assert rows_under(candidate) == (NOBODY_TO_ASK,)


def test_a_candidate_with_nothing_to_offer_says_that_rather_than_nothing(
    application,
) -> None:
    """An entry opening onto emptiness reads as one still loading."""
    dialog = made((gaps_with(artists=1),), asking=Asking())
    candidate = candidate_in(dialog)
    candidate.setExpanded(True)
    dialog.show_releases("id-0", ())
    assert rows_under(candidate) == (NOTHING_OFFERED,)


def test_opening_a_source_artist_asks_for_nothing(application) -> None:
    """What a source artist holds was found by the run; there is nothing to ask."""
    asking = Asking()
    dialog = made((gaps_with(albums=1, artists=1),), asking=asking)
    source = dialog.sources[0]
    source.setExpanded(False)
    source.setExpanded(True)
    assert asking.asked == []


def test_a_question_the_asker_would_not_take_leaves_the_row_alone(
    application,
) -> None:
    """A refusal is not an answer, so the row does not claim to be waiting."""
    asking = Asking(refuse=("id-0",))
    dialog = made((gaps_with(artists=1),), asking=asking)
    candidate = candidate_in(dialog)
    candidate.setExpanded(True)
    assert asking.asked == ["id-0"]
    assert rows_under(candidate) == ()


def test_a_failed_expansion_says_so_and_spares_the_rest(application) -> None:
    """One artist nobody could look up is not a reason to lose the run. FR-D32."""
    asking = Asking()
    dialog = made((gaps_with(albums=1, artists=2),), asking=asking)
    first, second = candidate_in(dialog, at=1), candidate_in(dialog, at=0)
    first.setExpanded(True)
    dialog.show_failure("id-0", "the service answered 503")
    assert rows_under(first) == (
        COULD_NOT_ASK.format(reason="the service answered 503"),
    )
    second.setExpanded(True)
    dialog.show_releases("id-1", (ReleaseGroup(title="Aerial"),))
    assert rows_under(second) == ("Aerial",)
    assert rows_under(dialog.sources[0])[0] == "Album 0"


def test_an_artist_that_failed_is_asked_again_the_next_time_it_is_opened(
    application,
) -> None:
    """A service that refused once may well answer the next time."""
    asking = Asking()
    dialog = made((gaps_with(artists=1),), asking=asking)
    candidate = candidate_in(dialog)
    candidate.setExpanded(True)
    dialog.show_failure("id-0", "nothing answered at all")
    candidate.setExpanded(False)
    candidate.setExpanded(True)
    assert asking.asked == ["id-0", "id-0"]


def test_the_same_candidate_under_two_sources_is_answered_under_both(
    application,
) -> None:
    """Two artists can lead to one candidate; both rows are owed the answer."""
    shared = SimilarArtist(name="Peter Gabriel", identifier="id-pg")
    dialog = made(
        (
            Gaps(artist="Genesis", artists=(shared,)),
            Gaps(artist="Kate Bush", artists=(shared,)),
        ),
        asking=Asking(),
    )
    dialog.sources[0].child(0).setExpanded(True)
    dialog.show_releases("id-pg", (ReleaseGroup(title="So"),))
    assert rows_under(dialog.sources[0].child(0)) == ("So",)
    assert rows_under(dialog.sources[1].child(0)) == ("So",)


def test_a_dialog_given_nobody_to_ask_simply_does_not_open_a_candidate(
    application,
) -> None:
    """The whole dialog can be driven with nothing behind it."""
    dialog = made((gaps_with(artists=1),))
    candidate = candidate_in(dialog)
    candidate.setExpanded(True)
    assert rows_under(candidate) == ()


def test_closing_lets_go_of_every_question_still_in_flight(application) -> None:
    """A thread still running when Qt tears its owner down ends the process."""
    asking = Asking()
    dialog = made((gaps_with(artists=1),), asking=asking)
    dialog.reject()
    assert asking.stopped == 1


def test_a_dialog_with_no_asker_closes_without_looking_for_one(application) -> None:
    """The sibling of the test above, for a dialog given nothing behind it."""
    dialog = made((gaps_with(artists=1),))
    dialog.reject()
    assert not dialog.isVisible()


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


def test_the_answer_reaches_the_dialog_across_the_thread_it_is_asked_on(
    application,
) -> None:
    """The real runner over a fake catalogue: the wiring, not a stand-in for it.

    Everything above puts the answer in by hand, which says what the dialog
    does with one and nothing about whether one ever arrives. This drives the
    runner that actually asks, so the moveToThread, the signals and the
    teardown are exercised.
    """
    catalogue = Catalogue(albums=(ReleaseGroup(title="Hounds of Love"),))
    runner = ExpansionRunner(expansion(catalogue))
    dialog = made((gaps_with(artists=1),), asking=runner)
    runner.setParent(dialog)
    candidate = candidate_in(dialog)
    candidate.setExpanded(True)
    assert waited_for(application, lambda: rows_under(candidate) == ("Hounds of Love",))
    assert catalogue.asked == ["id-0"]
    assert not runner.asking_about("id-0")
    dialog.reject()


def test_a_failure_on_that_thread_arrives_as_a_line_under_the_artist(
    application,
) -> None:
    """The unwanted sibling of the test above, over the same real runner."""
    catalogue = Catalogue(raises=RuntimeError("nothing answered at all"))
    runner = ExpansionRunner(expansion(catalogue))
    dialog = made((gaps_with(artists=1),), asking=runner)
    runner.setParent(dialog)
    candidate = candidate_in(dialog)
    candidate.setExpanded(True)
    assert waited_for(
        application,
        lambda: rows_under(candidate)
        == (COULD_NOT_ASK.format(reason="nothing answered at all"),),
    )
    dialog.reject()
