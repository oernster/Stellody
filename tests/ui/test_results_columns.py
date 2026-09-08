"""The run's answer runs down several columns rather than one tall list.

Reported by Oliver on 2026-09-08 with a two genre run already running off the
foot of the screen while the room to show it sat empty either side. A whole
library answers with hundreds of source artists, so one column is a shape
nobody reaches the end of.

Two things are being held here. The arithmetic answers how much room the
screen takes and which artist lands in which column, which is tested at widths
no machine running this suite has: the offscreen platform reports an 800
square screen, so every case worth reading is wider than anything it offers.
The widgets are then handed a width directly, for the same reason.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication
from results_support import gaps_with

from stellody.domain.discovery import Gaps, SimilarArtist
from stellody.ui.results_columns import ResultsColumns
from stellody.ui.results_room import (
    COLUMN_PX,
    COLUMNS_AT_THE_CEILING,
    DIALOG_HEIGHT_PX,
    DIALOG_WIDTH_PX,
    SCREEN_SHARE,
    THIRTEEN_INCH_HEIGHT_PX,
    THIRTEEN_INCH_WIDTH_PX,
    columns_for,
    dealt_into_columns,
    height_of,
    opening_size,
)
from stellody.ui.results_ticks import ARTIST_ROLE, TICKED, ticked_albums
from stellody.ui.theme import Mode, palette_for

# Three columns' worth of room, which is what the widget cases are built at.
THREE_COLUMNS_PX = COLUMN_PX * 3


class TestHowMuchRoomItTakes:
    def test_a_small_screen_gets_the_floor(self) -> None:
        """The share of a small screen is under the old fixed size; that
        size is what makes a title readable, so the floor wins."""
        assert opening_size(QSize(700, 500)) == QSize(DIALOG_WIDTH_PX, DIALOG_HEIGHT_PX)

    def test_an_ordinary_screen_gets_the_share(self) -> None:
        room = QSize(1600, 900)
        assert opening_size(room) == QSize(
            int(1600 * SCREEN_SHARE), int(900 * SCREEN_SHARE)
        )

    def test_a_wide_monitor_gets_no_more_than_a_13_inch_display(self) -> None:
        """Oliver's ruling: nine tenths of a 3440 monitor is 3096 pixels of
        dialog, which is a window nobody can read across and a shape that
        cannot be checked on the machines this has to run on."""
        assert opening_size(QSize(3440, 1440)) == QSize(
            THIRTEEN_INCH_WIDTH_PX, THIRTEEN_INCH_HEIGHT_PX
        )

    def test_it_never_asks_for_more_room_than_there_is(self) -> None:
        for width, height in ((1366, 768), (1920, 1080), (2560, 1440), (3440, 1440)):
            size = opening_size(QSize(width, height))
            assert size.width() <= width, width
            assert size.height() <= height, height


class TestHowManyColumns:
    def test_the_floor_affords_exactly_one(self) -> None:
        assert columns_for(DIALOG_WIDTH_PX) == 1

    def test_a_dialog_narrower_than_a_column_still_gets_one(self) -> None:
        assert columns_for(COLUMN_PX - 1) == 1

    def test_three_is_the_ruling_rather_than_whatever_the_constant_says(
        self,
    ) -> None:
        """Oliver ruled three on 2026-09-08, having seen a two-column screen.

        Stated as the number rather than against the constant, since a test
        that reads the constant agrees with every value it could hold.
        """
        assert COLUMNS_AT_THE_CEILING == 3

    def test_the_13_inch_ceiling_affords_the_three_that_were_asked_for(
        self,
    ) -> None:
        assert columns_for(THIRTEEN_INCH_WIDTH_PX) == 3

    def test_the_column_width_is_the_ruling_rather_than_a_number(self) -> None:
        """Three at the ceiling is the decision; the width follows from it."""
        assert COLUMN_PX * COLUMNS_AT_THE_CEILING <= THIRTEEN_INCH_WIDTH_PX
        assert (COLUMN_PX + 1) * COLUMNS_AT_THE_CEILING > THIRTEEN_INCH_WIDTH_PX

    def test_room_is_measured_in_readable_columns(self) -> None:
        assert columns_for(THREE_COLUMNS_PX) == 3


class TestWhichArtistLandsWhere:
    def test_an_artist_is_as_tall_as_what_opens_under_it(self) -> None:
        assert height_of(gaps_with(albums=3, artists=2)) == 6

    def test_nobody_found_deals_nothing(self) -> None:
        assert dealt_into_columns((), 3) == ((), (), ())

    def test_every_artist_lands_in_exactly_one_column(self) -> None:
        """The property that matters: nobody lost between the columns."""
        found = tuple(gaps_with(albums=n % 4) for n in range(20))
        for columns in range(1, 5):
            dealt = dealt_into_columns(found, columns)
            landed = sorted(at for column in dealt for at in column)
            assert landed == list(range(len(found))), f"{columns} columns"

    def test_a_column_keeps_the_order_the_run_answered_in(self) -> None:
        found = tuple(gaps_with(albums=1) for _ in range(9))
        for column in dealt_into_columns(found, 3):
            assert list(column) == sorted(column)

    def test_it_deals_by_height_rather_than_by_count(self) -> None:
        """One artist carrying fifteen albums beside three carrying one is
        not four artists to share out; it is eighteen rows."""
        found = (gaps_with(albums=15),) + tuple(gaps_with(albums=1) for _ in range(3))
        assert dealt_into_columns(found, 2) == ((0,), (1, 2, 3))


def _built(found: tuple[Gaps, ...], width: int = THREE_COLUMNS_PX) -> ResultsColumns:
    """The columns over these artists, drawn in the dark appearance."""
    return ResultsColumns(found, palette_for(Mode.DARK), width)


@pytest.fixture
def columns(application: QApplication):
    """Six artists over three columns, each carrying one album."""
    made = _built(tuple(gaps_with(albums=1, artist=f"Artist {n}") for n in range(6)))
    yield made
    made.deleteLater()


class TestTheColumnsOnScreen:
    def test_it_builds_what_the_width_affords(self, columns) -> None:
        assert len(columns.trees) == 3

    def test_every_artist_is_drawn_exactly_once(self, columns) -> None:
        drawn = [
            tree.topLevelItem(at).text(0)
            for tree in columns.trees
            for at in range(tree.topLevelItemCount())
        ]
        assert sorted(drawn) == sorted(source.text(0) for source in columns.sources)
        assert len(drawn) == 6

    def test_the_artists_are_answered_in_the_order_the_run_found_them(
        self, columns
    ) -> None:
        """Where one landed is the layout's business; what was first is not."""
        assert [source.text(0).split(" (")[0] for source in columns.sources] == [
            f"Artist {n}" for n in range(6)
        ]

    def test_fewer_artists_than_columns_builds_no_empty_column(
        self, application
    ) -> None:
        made = _built((gaps_with(albums=1),))
        try:
            assert len(made.trees) == 1
        finally:
            made.deleteLater()

    def test_a_run_that_found_nobody_still_gets_a_screen(self, application) -> None:
        made = _built(())
        try:
            assert len(made.trees) == 1
            assert made.sources == ()
        finally:
            made.deleteLater()

    def test_the_container_is_not_a_stop_on_the_ring(self, columns) -> None:
        """A focus ring belongs to a control, never to what holds it."""
        assert columns.focusPolicy() is columns.focusPolicy().NoFocus

    def test_one_candidate_under_two_columns_keeps_both_rows(self, application) -> None:
        """The same artist can be suggested by two sources dealt apart;
        an answer arriving later is owed to both rows."""
        shared = SimilarArtist(name="Nick Cave", identifier="id-shared")
        found = tuple(
            Gaps(artist=f"Artist {n}", albums=(), artists=(shared,)) for n in range(2)
        )
        made = _built(found)
        try:
            assert len(made.rows["id-shared"]) == 2
        finally:
            made.deleteLater()


class TestOneSelectionAcrossThem:
    def test_choosing_in_one_column_clears_the_others(self, columns) -> None:
        first, second = columns.trees[0], columns.trees[1]
        first.setCurrentItem(first.topLevelItem(0))
        assert first.selectedItems()
        second.setCurrentItem(second.topLevelItem(0))
        assert second.selectedItems()
        assert first.selectedItems() == []


class TestWhatIsTickedAcrossThem:
    def test_the_ticks_are_read_from_every_column(self, columns) -> None:
        for source in columns.sources:
            source.child(0).setCheckState(0, TICKED)
        assert len(ticked_albums(columns.trees)) == 6

    def test_they_come_back_a_column_at_a_time_from_the_left(self, columns) -> None:
        for source in columns.sources:
            source.child(0).setCheckState(0, TICKED)
        expected = [
            tree.topLevelItem(at).child(0).data(0, ARTIST_ROLE)
            for tree in columns.trees
            for at in range(tree.topLevelItemCount())
        ]
        assert [album.artist for album in ticked_albums(columns.trees)] == expected
