"""What a run says it could not answer for, checked without a screen.

The words and the report are built apart from the dialog that shows them, so
this suite reads them directly. What the WINDOW does with them, the sentence in
the bar and the button beside it, is asserted in `test_discovery_wiring.py`.
"""

from __future__ import annotations

from PySide6.QtWidgets import QTextBrowser

from stellody.application.values import (
    Ambiguity,
    RunOutcome,
    RunReport,
    SourceFailure,
)
from stellody.ui import shortfall

# Assembled rather than written out, so the prose sweep does not read the
# assertion that the rule holds as a breach of it.
SERIAL_COMMA = "," + " and"


def a_run(failed: int = 0, unresolved: int = 0, ambiguous: int = 0) -> RunReport:
    """A completed run that could not answer for this many, of each kind."""
    return RunReport(
        outcome=RunOutcome.COMPLETED,
        failed=tuple(
            SourceFailure(artist=f"Nobody {n}", reason="a server error")
            for n in range(failed)
        ),
        unresolved=tuple(f"Unknown {n}" for n in range(unresolved)),
        ambiguous=tuple(
            Ambiguity(artist=f"Several {n}", identifiers=("a", "b"))
            for n in range(ambiguous)
        ),
    )


class TestCounting:
    """All three kinds are the same news to somebody reading a total."""

    def test_a_clean_run_counts_nothing(self) -> None:
        """Nothing owed, so nothing is said and no button is offered."""
        assert shortfall.counted(a_run()) == 0
        assert shortfall.sentence(a_run()) == ""

    def test_the_three_kinds_add_up(self) -> None:
        """The button's count is every artist the run could not answer for."""
        assert shortfall.counted(a_run(failed=4, unresolved=3, ambiguous=2)) == 9


class TestTheSentence:
    """What goes in the status bar beside the run's own message."""

    def test_one_of_each_kind_reads_as_one(self) -> None:
        """Nothing here says 1 artists or 1 names."""
        said = shortfall.sentence(a_run(failed=1, unresolved=1, ambiguous=1))
        assert "one artist could not be asked about" in said.lower()
        assert "one name was not recognised" in said
        assert "one name matched more than one artist" in said

    def test_the_clauses_carry_no_comma_before_the_and(self) -> None:
        """The house rule holds in what the application says, not only in its
        source."""
        said = shortfall.sentence(a_run(failed=4, unresolved=3, ambiguous=2))
        assert SERIAL_COMMA not in said
        assert "about, 3 names" in said, "the list separates on commas alone"

    def test_it_opens_with_a_capital(self) -> None:
        """It follows a full stop, so it is the start of a sentence."""
        said = shortfall.sentence(a_run(failed=1))
        assert said.startswith(" One artist")

    def test_a_count_opens_without_one(self) -> None:
        """A clause that begins with a digit cannot be capitalised."""
        assert shortfall.sentence(a_run(failed=4)).startswith(" 4 artists")

    def test_it_ends_by_saying_why_the_count_matters(self) -> None:
        """A count with no consequence attached is a number nobody acts on."""
        assert shortfall.sentence(a_run(ambiguous=2)).endswith(shortfall.SO_INCOMPLETE)

    def test_only_what_happened_is_named(self) -> None:
        """A run with one kind of silence says one thing, not three with zeroes."""
        said = shortfall.sentence(a_run(unresolved=3))
        assert "3 names were not recognised" in said
        assert "could not be asked about" not in said
        assert "matched more than one" not in said


class TestTheButtonLabel:
    """It outlives its sentence, so it has to stand up alone."""

    def test_one_reads_as_one(self) -> None:
        """The singular, since the button carries a count of its own."""
        assert shortfall.button_label(a_run(failed=1)) == "1 artist unanswered"

    def test_several_are_counted(self) -> None:
        """Across all three kinds, since they are one question to a reader."""
        label = shortfall.button_label(a_run(failed=4, unresolved=3, ambiguous=2))
        assert label == "9 artists unanswered"


class TestTheList:
    """The names themselves, grouped by what went wrong."""

    def test_each_group_is_named_under_its_own_heading(self) -> None:
        """The three are not the same news; a single list would hide that."""
        page = shortfall.shortfall_html(a_run(failed=1, unresolved=1, ambiguous=1))
        assert shortfall.ASK_HEADING in page
        assert shortfall.RECOGNISED_HEADING in page
        assert shortfall.SEVERAL_HEADING in page

    def test_an_empty_group_brings_no_heading_with_it(self) -> None:
        """A heading over nothing reads as a group that came back empty."""
        page = shortfall.shortfall_html(a_run(unresolved=2))
        assert shortfall.RECOGNISED_HEADING in page
        assert shortfall.ASK_HEADING not in page
        assert shortfall.SEVERAL_HEADING not in page

    def test_every_artist_is_listed(self) -> None:
        """The whole point of pressing the button."""
        page = shortfall.shortfall_html(a_run(failed=2, unresolved=2, ambiguous=2))
        for name in ("Nobody 0", "Nobody 1", "Unknown 0", "Several 1"):
            assert f"<li>{name}</li>" in page

    def test_the_total_leads_the_page(self) -> None:
        """The answer to the question the button asked."""
        assert "<b>9 artists</b>" in shortfall.shortfall_html(
            a_run(failed=4, unresolved=3, ambiguous=2)
        )

    def test_one_artist_reads_as_one_here_too(self) -> None:
        """The same rule the button follows."""
        assert "<b>1 artist</b>" in shortfall.shortfall_html(a_run(failed=1))

    def test_a_name_carrying_markup_is_escaped_rather_than_rendered(self) -> None:
        """A library holds whatever somebody's tags hold, `<b>` included."""
        page = shortfall.shortfall_html(
            RunReport(outcome=RunOutcome.COMPLETED, unresolved=("<b>Nirvana</b>",))
        )
        assert "&lt;b&gt;Nirvana&lt;/b&gt;" in page
        assert "<li><b>Nirvana</b></li>" not in page


class TestTheDialog:
    """The screen itself, which is the words in a frame and nothing more.

    That it opens on a usable control is asserted by the sweep in
    `test_dialog_first_stop.py`, which discovers every dialog the package
    defines rather than being told about them, so it is not repeated here.
    """

    def test_it_shows_what_the_report_says(self, application) -> None:
        """Built from the same text this suite has just read."""
        dialog = shortfall.ShortfallDialog(a_run(failed=1, unresolved=1))
        try:
            shown = dialog.findChild(QTextBrowser).toPlainText()
            assert "Nobody 0" in shown
            assert "Unknown 0" in shown
        finally:
            dialog.deleteLater()
