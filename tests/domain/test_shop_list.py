"""The shop list rules: editing it and meeting a release. SHOPS.md Amendment 1."""

from __future__ import annotations

import pytest

from stellody.domain.shop_list import (
    BrokenRow,
    NameTakenError,
    ShopBook,
    ShopProblem,
    form_problems,
    merged,
    row_problem,
)
from stellody.domain.shopping import Shop

QOBUZ = Shop("Qobuz", "https://www.qobuz.com/search?q={artist}%20{album}", "Hi-res.")
BLEEP = Shop("Bleep", "https://bleep.com/search?q={artist}", "Warp.")
BEATPORT = Shop("Beatport", "https://www.beatport.com/search?q={album}")
JUNO = Shop("Juno", "https://www.juno.co.uk/search?q={artist}")
BROKEN = BrokenRow("Odd", "https://odd.example/search", "", ShopProblem.NO_PLACEHOLDER)
SHIPPED = (QOBUZ, BLEEP, BEATPORT)


def book(*rows, deleted=(), retired=()) -> ShopBook:
    return ShopBook(rows=tuple(rows), shipped=SHIPPED, deleted=deleted, retired=retired)


class TestARowThatIsNotAShop:
    def test_a_row_with_no_name(self) -> None:
        assert row_problem("  ", "https://x/{artist}") is ShopProblem.NO_NAME

    def test_a_row_with_no_address(self) -> None:
        assert row_problem("X", " ") is ShopProblem.NO_ADDRESS

    def test_a_row_naming_no_placeholder(self) -> None:
        assert row_problem("X", "https://x/") is ShopProblem.NO_PLACEHOLDER

    def test_a_row_that_is_a_shop(self) -> None:
        assert row_problem("X", "http://x/{album}") is None


class TestTheForm:
    def test_a_shop_that_cannot_search_is_not_saved(self) -> None:
        problems = form_problems("Odd", "https://example.com/search", ())
        assert problems == (ShopProblem.NO_PLACEHOLDER,)

    def test_a_name_already_used_is_refused(self) -> None:
        problems = form_problems("qobuz", "https://x/{artist}", ("Qobuz",))
        assert problems == (ShopProblem.NAME_TAKEN,)

    def test_an_empty_form_names_both_fields(self) -> None:
        assert form_problems(" ", "", ()) == (
            ShopProblem.NO_NAME,
            ShopProblem.NO_ADDRESS,
        )

    def test_an_address_that_is_not_https_is_refused(self) -> None:
        problems = form_problems("X", "http://x/{artist}", ())
        assert problems == (ShopProblem.NOT_SECURE,)

    def test_a_good_form_has_nothing_to_say(self) -> None:
        assert form_problems("X", " HTTPS://x/{artist} ", ("Y",)) == ()


class TestEditing:
    def test_an_added_shop_goes_last(self) -> None:
        assert book(QOBUZ).added(JUNO).rows == (QOBUZ, JUNO)

    def test_adding_a_name_already_listed_raises(self) -> None:
        taken = Shop("QOBUZ", "https://x/{artist}")
        with pytest.raises(NameTakenError):
            book(QOBUZ).added(taken)

    def test_an_edited_shop_keeps_its_place(self) -> None:
        edited = Shop("Qobuz", QOBUZ.template, "Changed.")
        result = book(BLEEP, QOBUZ, JUNO).replaced(1, edited)
        assert result.rows == (BLEEP, edited, JUNO)
        assert result.deleted == ()

    def test_an_edit_may_keep_its_own_name(self) -> None:
        assert book(QOBUZ).replaced(0, QOBUZ).rows == (QOBUZ,)

    def test_an_edit_may_not_take_another_rows_name(self) -> None:
        with pytest.raises(NameTakenError):
            book(QOBUZ, BLEEP).replaced(1, Shop("qobuz", BLEEP.template))

    def test_renaming_a_shipped_shop_records_the_old_name(self) -> None:
        renamed = Shop("Qobuz UK", QOBUZ.template)
        result = book(QOBUZ).replaced(0, renamed)
        assert result.rows == (renamed,)
        assert result.deleted == ("Qobuz",)

    def test_renaming_an_own_shop_records_nothing(self) -> None:
        assert book(JUNO).replaced(0, Shop("Juno UK", JUNO.template)).deleted == ()

    def test_a_broken_row_can_be_mended_in_place(self) -> None:
        mended = Shop("Odd", "https://odd.example/search?q={artist}")
        assert book(BROKEN, QOBUZ).replaced(0, mended).rows == (mended, QOBUZ)

    def test_deleting_a_shipped_shop_records_it(self) -> None:
        result = book(QOBUZ, BEATPORT).removed(1)
        assert result.rows == (QOBUZ,)
        assert result.deleted == ("Beatport",)

    def test_deleting_it_twice_records_it_once(self) -> None:
        result = book(BEATPORT, deleted=("beatport",)).removed(0)
        assert result.deleted == ("beatport",)

    def test_deleting_an_own_shop_records_nothing(self) -> None:
        assert book(JUNO).removed(0).deleted == ()

    def test_only_shops_can_be_searched(self) -> None:
        assert book(BROKEN, QOBUZ).shops == (QOBUZ,)

    def test_every_name_is_offered_where_no_row_is_being_edited(self) -> None:
        assert book(QOBUZ, JUNO).names_other_than(None) == ("Qobuz", "Juno")


class TestMoving:
    def test_dragging_moves_the_shop(self) -> None:
        assert book(QOBUZ, BLEEP, JUNO).moved_to(2, 0).rows == (JUNO, QOBUZ, BLEEP)

    def test_a_move_up_goes_one_place(self) -> None:
        assert book(QOBUZ, BLEEP).moved(1, -1).rows == (BLEEP, QOBUZ)

    @pytest.mark.parametrize("index, offset", [(0, -1), (1, 1), (1, 0)])
    def test_a_move_past_either_end_or_nowhere_changes_nothing(
        self, index: int, offset: int
    ) -> None:
        start = book(QOBUZ, BLEEP)
        assert start.moved(index, offset) is start


class TestTheWayBack:
    def test_putting_back_keeps_own_shops(self) -> None:
        edited = Shop("Qobuz", QOBUZ.template, "Changed.")
        start = book(JUNO, edited, BROKEN, deleted=("Beatport",))
        result = start.put_back()
        assert result.rows == (QOBUZ, BLEEP, BEATPORT, JUNO, BROKEN)
        assert result.deleted == ()

    def test_announcing_empties_the_retired_record(self) -> None:
        assert book(QOBUZ, retired=("Juno",)).announced().retired == ()


def settle(rows, current, recorded=SHIPPED, deleted=(), retired=()) -> ShopBook:
    return merged(tuple(rows), recorded, deleted, retired, current)


class TestMeetingARelease:
    def test_a_new_shipped_shop_is_added_last(self) -> None:
        result = settle((QOBUZ, BLEEP, BEATPORT), (*SHIPPED, JUNO))
        assert result.rows == (QOBUZ, BLEEP, BEATPORT, JUNO)
        assert result.shipped == (*SHIPPED, JUNO)

    def test_a_deleted_shop_never_returns(self) -> None:
        result = settle((QOBUZ, BLEEP), SHIPPED, deleted=("BEATPORT",))
        assert result.rows == (QOBUZ, BLEEP)
        assert result.deleted == ("BEATPORT",)

    def test_an_untouched_shop_takes_the_new_address(self) -> None:
        moved = Shop("Qobuz", "https://www.qobuz.com/gb-en/s?q={artist}", "Hi-res.")
        result = settle((BLEEP, QOBUZ, BEATPORT), (moved, BLEEP, BEATPORT))
        assert result.rows == (BLEEP, moved, BEATPORT)

    def test_an_edited_shop_keeps_the_edit(self) -> None:
        edited = Shop("Qobuz", QOBUZ.template, "Mine.")
        moved = Shop("Qobuz", "https://www.qobuz.com/gb-en/s?q={artist}", "Hi-res.")
        result = settle((edited, BLEEP, BEATPORT), (moved, BLEEP, BEATPORT))
        assert result.rows == (edited, BLEEP, BEATPORT)

    def test_a_dropped_untouched_shop_is_removed(self) -> None:
        result = settle((QOBUZ, BLEEP, BEATPORT), (QOBUZ, BEATPORT), retired=("X",))
        assert result.rows == (QOBUZ, BEATPORT)
        assert result.retired == ("X", "Bleep")

    def test_a_dropped_edited_shop_stays(self) -> None:
        edited = Shop("Bleep", BLEEP.template, "Mine.")
        result = settle((QOBUZ, edited, BEATPORT), (QOBUZ, BEATPORT))
        assert result.rows == (QOBUZ, edited, BEATPORT)
        assert result.retired == ()

    def test_own_shops_and_broken_rows_are_left_where_they_are(self) -> None:
        result = settle((JUNO, BROKEN, QOBUZ, BLEEP, BEATPORT), SHIPPED)
        assert result.rows == (JUNO, BROKEN, QOBUZ, BLEEP, BEATPORT)

    def test_an_older_file_is_not_added_to(self) -> None:
        result = settle((QOBUZ, BLEEP), SHIPPED, deleted=None)
        assert result.rows == (QOBUZ, BLEEP)
        assert result.deleted == ()

    def test_a_file_with_no_record_is_read_as_settled_against_this_release(
        self,
    ) -> None:
        edited = Shop("Qobuz", QOBUZ.template, "Mine.")
        result = settle((edited, BLEEP), SHIPPED, recorded=None, deleted=None)
        assert result.rows == (edited, BLEEP)
        assert result.shipped == SHIPPED
