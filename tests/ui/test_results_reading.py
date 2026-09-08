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

from results_support import Asking, candidate_in, gaps_with, made, rows_under

from stellody.application.discovery_ports import (
    SourceFailed,
    SourceRefused,
    SourceTooSlow,
    SourceUnavailable,
)
from stellody.domain.discovery import ReleaseGroup
from stellody.ui.palette import Mode, palette_for
from stellody.ui.results_words import (
    BUSY,
    NOT_ASKING,
    TOO_SLOW,
    UNREACHABLE,
    WENT_WRONG,
    plainly,
)


def test_a_source_row_says_how_many_of_each_sit_under_it(application) -> None:
    """Both kinds share one list under the name, so both are counted.

    Reported on 2026-09-07: an amber name indented under a blue one reads as an
    album; its own children then read as tracks. The count is half of what
    answers that; the key above the tree is the other half.
    """
    dialog = made((gaps_with(albums=3, artists=2, artist="Blues Pills"),))
    assert dialog.sources[0].text(0) == ("Blues Pills (3 albums, 2 similar artists)")


def test_a_single_album_is_not_called_albums(application) -> None:
    """One of something reads as one of it."""
    dialog = made((gaps_with(albums=1, artist="Kate Bush"),))
    assert dialog.sources[0].text(0) == "Kate Bush (1 album)"


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


def test_it_says_which_genres_the_run_looked_in(application) -> None:
    """Asked for on 2026-09-08: a run's answer without its question.

    The screen listed what was found while saying nothing about what had been
    asked for, so two runs over unlike genres produced two screens that read
    identically. The count goes with the names because a run over eleven
    genres is a different thing from a run over one.
    """
    dialog = made((gaps_with(albums=1),), ticked=("Blues", "Rock"))
    assert dialog.top.looked_in is not None
    said = dialog.top.looked_in.text()
    assert "2 genres" in said
    assert "Blues" in said
    assert "Rock" in said
    assert dialog.top.looked_in.wordWrap(), "eleven genres would run off the edge"


def test_one_genre_is_not_called_genres(application) -> None:
    """The unwanted sibling of the count above."""
    dialog = made((gaps_with(albums=1),), ticked=("Folk",))
    assert "1 genre:" in dialog.top.looked_in.text()


def test_a_run_that_names_no_genres_shows_no_line_at_all(application) -> None:
    """A file written before the genres were recorded is the only such run.

    Absent rather than blank: a line reading "looked in nothing" would be
    worse than the absence, while the gaps are unaffected either way.
    """
    dialog = made((gaps_with(albums=1),))
    assert dialog.top.looked_in is None
    assert len(dialog.sources) == 1


def test_the_genres_sit_above_the_key(application) -> None:
    """What was asked comes before how to read the answer.

    Read off the laid-out column rather than off the order they were built in,
    since a widget added to a layout is not necessarily where it was made.
    """
    dialog = made((gaps_with(albums=1),), ticked=("Blues",))
    column = dialog.top.layout()
    placed = [column.itemAt(at).widget() for at in range(column.count())]
    assert placed.index(dialog.top.looked_in) < placed.index(dialog.top.key[0])


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


def test_a_failure_says_what_can_be_done_about_it(application) -> None:
    """Reopening a failed row already asked afresh; nothing said so.

    Oliver asked for a way to try again on 2026-09-08, looking at a screen
    that had one. FR-D32.
    """
    dialog = made((gaps_with(artists=1),), asking=Asking())
    candidate = candidate_in(dialog)
    candidate.setExpanded(True)
    dialog.show_failure("id-0", "the catalogue refused all 5 asks")
    line = rows_under(candidate)[0]
    assert "the catalogue refused all 5 asks" in line, "it says what happened"
    assert "open this row" in line.casefold(), "and what can be done about it"


class TestSayingWhyInWords:
    """Reported by Oliver on 2026-09-08, shown a row reading "given up on part
    way through" followed by a MusicBrainz address: unreadable to anybody who
    did not write this; no help in deciding what to do next.

    Read off the KIND of failure rather than off its message, since a message
    is written for whoever fixes the program.
    """

    def test_a_service_that_kept_refusing_is_busy(self) -> None:
        assert plainly(SourceRefused("refused all 5 asks")) == BUSY

    def test_a_service_that_ran_out_of_time_says_so(self) -> None:
        assert plainly(SourceTooSlow("no answer inside 20 seconds")) == TOO_SLOW

    def test_a_service_nothing_could_reach_says_so(self) -> None:
        assert plainly(SourceUnavailable("HostNotFoundError")) == UNREACHABLE

    def test_anything_else_points_at_the_log(self) -> None:
        """The catch-all names no cause, since naming one would be a guess."""
        assert plainly(SourceFailed("the answer could not be read")) == WENT_WRONG
        assert plainly(RuntimeError("Qt said no")) == WENT_WRONG

    def test_none_of_them_names_a_url_or_a_class(self) -> None:
        for said in (BUSY, TOO_SLOW, UNREACHABLE, WENT_WRONG):
            assert "http" not in said
            assert "Error" not in said
