"""What the results dialog SAYS, as against how it behaves.

Split from `test_results_dialog.py` on 2026-09-07, when that file went over the
line cap; the seam is the one the source already has. Over there is what the
dialog does with an answer: which rows appear, what opening one asks for, what
a failure leaves behind. Here is what a reader is told: the key, what each row
calls itself and the strip that says the catalogue is being asked.

All of it was written after the same report. Shown a real run, Oliver asked
which lines were albums and which were tracks, whether two of the amber names
were artists at all, then why opening one left the dialog looking stuck. Every
test below is one of those three questions.
"""

from __future__ import annotations

from results_support import Asking, candidate_in, gaps_with, made

from stellody.domain.discovery import ReleaseGroup
from stellody.ui.palette import Mode, palette_for
from stellody.ui.results_words import NOT_ASKING


def test_a_source_row_says_how_many_of_each_sit_under_it(application) -> None:
    """Both kinds share one list under the name, so both are counted.

    Reported on 2026-09-07: an amber name indented under a blue one reads as an
    album; its own children then read as tracks. The count is half of what
    answers that; the key above the tree is the other half.
    """
    dialog = made((gaps_with(albums=3, artists=2, artist="Blues Pills"),))
    assert dialog.tree.topLevelItem(0).text(0) == (
        "Blues Pills (3 albums, 2 similar artists)"
    )


def test_a_single_album_is_not_called_albums(application) -> None:
    """One of something reads as one of it."""
    dialog = made((gaps_with(albums=1, artist="Kate Bush"),))
    assert dialog.tree.topLevelItem(0).text(0) == "Kate Bush (1 album)"


def test_a_candidate_row_says_that_it_is_an_artist(application) -> None:
    """The row that was mistaken for an album now says what it is."""
    dialog = made((gaps_with(artists=1),), asking=Asking())
    assert candidate_in(dialog).text(0) == "Artist 0 (similar artist)"


def test_a_candidate_row_gains_its_album_count_once_it_is_answered(
    application,
) -> None:
    """Absent until asked, because until then nobody knows it."""
    dialog = made((gaps_with(artists=1),), asking=Asking())
    candidate = candidate_in(dialog)
    candidate.setExpanded(True)
    dialog.show_releases(
        "id-0",
        (ReleaseGroup(title="Firewood"), ReleaseGroup(title="Legend")),
    )
    assert candidate.text(0) == "Artist 0 (similar artist, 2 albums)"


def test_the_key_names_all_three_kinds_in_their_own_colours(application) -> None:
    """A key with a filled circle each, ruled on 2026-09-07.

    Colour alone cannot carry the meaning: it fails a reader who cannot
    separate the two hues, it fails a screenshot pasted into a message and it
    failed the person looking at it. Each line is checked for the colour it
    describes, since a key in the wrong colours is worse than none.
    """
    colour = palette_for(Mode.DARK)
    dialog = made((gaps_with(albums=1, artists=1),))
    lines = tuple(line.text() for line in dialog.key)
    assert len(lines) == 3
    for said, role in zip(
        lines, (colour.source_artist, colour.candidate_artist, colour.text)
    ):
        assert role in said
        assert "\u25cf" in said
    assert "track" in lines[2]
    for line in dialog.key:
        assert line.wordWrap(), "a key that runs off the edge is unreadable"


def test_the_strip_says_the_instruction_while_nothing_is_being_asked(
    application,
) -> None:
    """Reserved rather than shown: a strip that appeared would push the list
    down at the moment somebody clicked an arrow in it."""
    dialog = made((gaps_with(artists=1),), asking=Asking())
    assert dialog.asking_bar.format() == NOT_ASKING
    assert dialog.asking_bar.maximum() > 0


def test_the_strip_names_who_is_being_asked_about(application) -> None:
    """The reported fault: several seconds of nothing, looking stuck."""
    dialog = made((gaps_with(artists=1),), asking=Asking())
    candidate_in(dialog).setExpanded(True)
    assert dialog.asking_bar.format() == "Asking the catalogue about Artist 0"
    assert dialog.asking_bar.maximum() == 0, "busy rather than counted"


def test_the_strip_counts_them_when_several_are_in_flight(application) -> None:
    """Two names would not fit and would not help; the number does both."""
    dialog = made((gaps_with(artists=2),), asking=Asking())
    candidate_in(dialog, at=1).setExpanded(True)
    candidate_in(dialog, at=0).setExpanded(True)
    assert dialog.asking_bar.format() == "Asking the catalogue about 2 artists"


def test_the_strip_goes_quiet_when_the_last_answer_lands(application) -> None:
    """An answered question leaves nothing being asked, so it says so."""
    dialog = made((gaps_with(artists=2),), asking=Asking())
    candidate_in(dialog, at=1).setExpanded(True)
    candidate_in(dialog, at=0).setExpanded(True)
    dialog.show_releases("id-0", ())
    assert dialog.asking_bar.format() == "Asking the catalogue about Artist 1"
    dialog.show_failure("id-1", "nothing answered at all")
    assert dialog.asking_bar.format() == NOT_ASKING
    assert dialog.asking_bar.maximum() > 0
