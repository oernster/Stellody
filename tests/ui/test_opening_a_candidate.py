"""Opening a candidate artist on the results screen; what comes back.

Split out of `test_results_dialog` on 2026-09-09, when that file grew into the
danger band under the line cap. The seam is a real one rather than a
convenience: what the screen SHOWS of a finished run is one concern, while what
happens when somebody opens an amber row is another, since that one reaches a
catalogue, crosses a thread and can fail.

The asking is stood in for in most of these, because what the dialog does with
an answer is a different question from how the answer is fetched. The two at
the end drive the REAL runner over a fake catalogue, so the thread the answer
actually crosses is exercised rather than assumed.
"""

from __future__ import annotations

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
from stellody.ui.results_words import (
    COULD_NOT_ASK,
    NOBODY_TO_ASK,
    NOTHING_OFFERED,
    WENT_WRONG,
    asking_about,
    candidate_row,
)


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
        lambda: rows_under(candidate) == (COULD_NOT_ASK.format(reason=WENT_WRONG),),
    )
    dialog.reject()
