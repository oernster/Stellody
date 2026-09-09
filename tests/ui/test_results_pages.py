"""The answer is turned a page at a time rather than scrolled for minutes.

Three columns of a whole library are three lists nobody reaches the end of, so
a page fills every one of its columns with source artists and two controls
turn the pages.

Two things are held here, exactly as the columns suite holds them. The
arithmetic answers how long a page is and who is on it, which is tested at
sizes no machine running this suite has: the offscreen platform reports an 800
square screen. The widgets are then handed a room directly, for the same
reason.
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from results_support import gaps_with

from stellody.domain.discovery import Gaps
from stellody.ui.results_pager import ResultsPager
from stellody.ui.results_pages import ResultsPages
from stellody.ui.results_room import (
    COLUMNS_AT_THE_CEILING,
    FURNITURE_PX,
    ROWS_AT_THE_CEILING,
    THIRTEEN_INCH_HEIGHT_PX,
    THIRTEEN_INCH_WIDTH_PX,
    dealt_into_columns,
    paged,
    rows_for,
)
from stellody.ui.results_words import where_in_the_answer
from stellody.ui.theme import Mode, palette_for

# A room of the size the ceiling allows, which is what the widget cases are
# built at: three columns of thirty rows each.
CEILING = QSize(THIRTEEN_INCH_WIDTH_PX, THIRTEEN_INCH_HEIGHT_PX)
# A source artist with nothing under it, so its height is one row and a page
# holds exactly as many of them as a column holds rows.
PLAIN = gaps_with()


def _artists(many: int) -> tuple[Gaps, ...]:
    """That many source artists, each one row tall."""
    return tuple(gaps_with(artist=f"Artist {number}") for number in range(many))


class TestHowLongAPageIs:
    def test_the_ceiling_holds_the_rows_it_says_it_does(self) -> None:
        """The one number to argue with, read back at the size it is about."""
        assert rows_for(THIRTEEN_INCH_HEIGHT_PX) == ROWS_AT_THE_CEILING

    def test_a_shorter_dialog_gets_a_shorter_page(self) -> None:
        """A laptop panel gets fewer rows rather than the same page scrolled."""
        assert rows_for(THIRTEEN_INCH_HEIGHT_PX // 2) < ROWS_AT_THE_CEILING

    def test_a_dialog_with_no_room_at_all_still_shows_a_row(self) -> None:
        """It scrolls, which is what every column did before there were pages."""
        assert rows_for(FURNITURE_PX) == 1


class TestWhoIsOnWhichPage:
    def test_everybody_who_fits_is_on_one_page(self) -> None:
        artists = _artists(COLUMNS_AT_THE_CEILING)
        assert paged(artists, COLUMNS_AT_THE_CEILING, ROWS_AT_THE_CEILING) == (artists,)

    def test_a_full_page_is_columns_times_rows(self) -> None:
        """Each column is filled to its own depth before a page is done."""
        held = COLUMNS_AT_THE_CEILING * ROWS_AT_THE_CEILING
        pages = paged(_artists(held + 1), COLUMNS_AT_THE_CEILING, ROWS_AT_THE_CEILING)
        assert [len(page) for page in pages] == [held, 1]

    def test_a_page_is_dealt_the_way_the_columns_will_deal_it(self) -> None:
        """The page it filled is the page it counted; otherwise an artist
        lands in a column the page had not reckoned with."""
        tall = (gaps_with(albums=4), gaps_with(albums=1), gaps_with(albums=1))
        page = paged(tall, 2, 6)[0]
        assert all(dealt_into_columns(page, 2)), "both columns were filled"

    def test_every_page_but_the_last_carries_every_column(self) -> None:
        """Ruled by Oliver on 2026-09-09, having seen a paged whole-library
        run draw three columns on some pages and one on others.

        Driven at the heights a real library has rather than at convenient
        ones: measured from that run's answer, an artist's height runs from 1
        row to 109 against a column of 30, so an artist taller than a column
        is the ordinary case and a page that refuses to overflow one cannot
        be filled at all.
        """
        tall = tuple(
            gaps_with(albums=height, artist=f"Artist {height}")
            for height in (109, 40, 23, 1, 61, 30, 12, 3, 44, 25, 2, 18)
        )
        pages = paged(tall, COLUMNS_AT_THE_CEILING, ROWS_AT_THE_CEILING)
        filled = [
            len(
                [
                    column
                    for column in dealt_into_columns(page, COLUMNS_AT_THE_CEILING)
                    if column
                ]
            )
            for page in pages
        ]
        assert filled[:-1] == [COLUMNS_AT_THE_CEILING] * (len(pages) - 1)
        assert filled[-1] <= COLUMNS_AT_THE_CEILING, "the tail takes what is left"

    def test_an_artist_taller_than_a_column_shares_its_page(self) -> None:
        """It fills its column and that column scrolls, which is one artist's
        worth of scrolling rather than the library's. Dropping it or splitting
        it would answer a different question than the run asked."""
        giant = gaps_with(albums=ROWS_AT_THE_CEILING * 2, artist="Giant")
        pages = paged((giant, PLAIN), 2, ROWS_AT_THE_CEILING)
        assert [len(page) for page in pages] == [2], "both are on the one page"
        assert all(dealt_into_columns(pages[0], 2)), "in a column each"

    def test_an_answer_holding_nobody_is_still_one_page(self) -> None:
        """A screen saying nothing is still a screen."""
        assert paged((), COLUMNS_AT_THE_CEILING, ROWS_AT_THE_CEILING) == ((),)


class TestThePagesOnScreen:
    def _pages(self, gaps: tuple[Gaps, ...]) -> ResultsPages:
        return ResultsPages(gaps, palette_for(Mode.DARK), CEILING)

    def test_it_opens_on_the_first_page(self, application) -> None:
        pages = self._pages(_artists(COLUMNS_AT_THE_CEILING * ROWS_AT_THE_CEILING + 1))
        assert len(pages.pages) == 2
        assert pages.showing == 0

    def test_every_source_artist_is_held_whichever_page_it_is_on(
        self, application
    ) -> None:
        """What reads them is asking about the answer, not about the screen."""
        many = COLUMNS_AT_THE_CEILING * ROWS_AT_THE_CEILING + 1
        pages = self._pages(_artists(many))
        assert len(pages.sources) == many
        assert all(item is not None for item in pages.sources)

    def test_turning_to_a_page_puts_it_in_front(self, application) -> None:
        pages = self._pages(_artists(COLUMNS_AT_THE_CEILING * ROWS_AT_THE_CEILING + 1))
        pages.show_page(1)
        assert pages.showing == 1

    def test_a_page_that_is_not_there_is_not_turned_to(self, application) -> None:
        """What asks is a control reachable from the keyboard while it is off."""
        pages = self._pages((PLAIN,))
        pages.show_page(1)
        pages.show_page(-1)
        assert pages.showing == 0

    def test_one_candidate_on_two_pages_shares_its_rows(self, application) -> None:
        """An answer that reached one page would leave the other row empty."""
        together = gaps_with(artists=1, artist="First")
        apart = gaps_with(artists=1, artist="Second")
        pages = ResultsPages((together, apart), palette_for(Mode.DARK), QSize(700, 0))
        assert len(pages.pages) > 1, "the two landed on different pages"
        assert len(pages.rows["id-0"]) == 2


class TestThePager:
    def test_it_says_where_in_the_answer_somebody_is(self, application) -> None:
        pager = ResultsPager(3)
        pager.showing(1)
        assert pager.position.text() == where_in_the_answer(1, 3)

    def test_a_reader_counts_pages_from_one(self) -> None:
        assert where_in_the_answer(0, 4) == "Page 1 of 4"

    def test_the_first_page_offers_no_way_back(self, application) -> None:
        pager = ResultsPager(3)
        assert not pager.previous_button.isEnabled()
        assert pager.next_button.isEnabled()

    def test_the_last_page_offers_no_way_on(self, application) -> None:
        pager = ResultsPager(3)
        pager.showing(2)
        assert pager.previous_button.isEnabled()
        assert not pager.next_button.isEnabled()

    def test_one_page_offers_neither_direction(self, application) -> None:
        """Both struck through rather than absent, so the control is known."""
        pager = ResultsPager(1)
        assert not pager.previous_button.isEnabled()
        assert not pager.next_button.isEnabled()

    def test_a_direction_that_leads_nowhere_still_wears_a_picture(
        self, application
    ) -> None:
        """Struck through rather than blank: which way is left still shows."""
        pager = ResultsPager(3)
        assert not pager.previous_button.icon().isNull()
        assert not pager.next_button.icon().isNull()

    def test_pressing_on_asks_for_the_next_page(self, application) -> None:
        pager = ResultsPager(3)
        asked: list[int] = []
        pager.turned.connect(asked.append)
        pager.next_button.click()
        assert asked == [1]

    def test_pressing_back_asks_for_the_page_before(self, application) -> None:
        pager = ResultsPager(3)
        pager.showing(2)
        asked: list[int] = []
        pager.turned.connect(asked.append)
        pager.previous_button.click()
        assert asked == [1]

    def test_the_controls_are_stops_on_the_ring(self, application) -> None:
        """A control reachable only with a mouse is half a control."""
        pager = ResultsPager(3)
        for control in (pager.previous_button, pager.next_button):
            assert control.focusPolicy() is not control.focusPolicy().NoFocus
