"""The shop list on disk: what ships, what is read back, settled and kept.

Every test here puts Stellody's own directory somewhere temporary, since the
file lives beside the discovery answer.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from stellody.application.shop_editing import ShopListUnwritable
from stellody.domain.shop_list import BrokenRow, ShopBook, ShopProblem
from stellody.domain.shopping import Shop
from stellody.infrastructure import paths, shop_file
from stellody.infrastructure.shop_file import (
    DEFAULT_SHOPS,
    FileShopBook,
    FileShopList,
    read_book,
    shops_path,
)

MINE = Shop(name="Mine", template="https://m/{album}")
OLD = Shop(name="Gone", template="https://old/{artist}", note="Yesterday's row.")


@pytest.fixture
def elsewhere(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """Stellody's directory, somewhere a test may write."""
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def refusing(monkeypatch: pytest.MonkeyPatch):
    """A filesystem that will not take a write."""

    def refuse(*_arguments, **_named):
        raise OSError("read only")

    monkeypatch.setattr(shop_file, "written", refuse)


def put(content: object) -> None:
    """Write a shop file holding exactly this."""
    shops_path().write_text(json.dumps(content), encoding="utf-8")


def held() -> dict:
    """The shop file as it now stands."""
    return json.loads(shops_path().read_text(encoding="utf-8"))


def rows_of(*shops: Shop) -> list[dict]:
    """These shops as a file carries them."""
    return [{"name": s.name, "template": s.template, "note": s.note} for s in shops]


class TestWhatShips:
    def test_every_shipped_template_names_a_placeholder(self) -> None:
        """A row that named neither would open the same page every time."""
        for shop in DEFAULT_SHOPS:
            assert shop.names_a_placeholder, shop.name

    def test_every_shipped_template_is_an_https_address(self) -> None:
        """A shop reached over plain http would leak the search in transit."""
        for shop in DEFAULT_SHOPS:
            assert shop.template.startswith("https://"), shop.name

    def test_the_shipped_list_holds_no_two_shops_of_one_name(self) -> None:
        """Names are how a shop is recognised across releases. FR-S21."""
        names = [shop.name.casefold() for shop in DEFAULT_SHOPS]
        assert len(names) == len(set(names))

    def test_boomkat_searches_the_artist_alone(self) -> None:
        """Measured on 2026-09-07: two terms answered nothing, one answered 85."""
        boomkat = next(shop for shop in DEFAULT_SHOPS if shop.name == "Boomkat")
        assert "{artist}" in boomkat.template
        assert "{album}" not in boomkat.template

    def test_7digital_is_offered_first(self) -> None:
        """Chosen rather than alphabetical, by Oliver's ruling of 2026-09-08."""
        assert DEFAULT_SHOPS[0].name == "7digital"

    def test_7digital_keeps_the_host_and_the_fallback_it_was_seen_with(self) -> None:
        """Read from a browser on 2026-09-08, past the wall that refuses us."""
        seven = next(shop for shop in DEFAULT_SHOPS if shop.name == "7digital")
        assert seven.template.startswith("https://uk.7digital.com/search?q=")
        assert seven.template.endswith("&fallback=true")


class TestTheFirstTime:
    def test_a_missing_file_is_written_with_the_defaults(self, elsewhere) -> None:
        """FR-S09: the list arrives as something to edit rather than as code."""
        assert read_book().rows == DEFAULT_SHOPS
        assert held()["shops"] == rows_of(*DEFAULT_SHOPS)
        assert held()["deleted"] == []

    def test_a_directory_that_cannot_be_written_is_not_an_error(
        self, elsewhere, refusing
    ) -> None:
        """A read-only directory costs the file on disk, never the shops."""
        assert FileShopList().shops() == DEFAULT_SHOPS
        assert not shops_path().exists()


class TestReadingItBack:
    def test_the_rows_come_back_in_the_files_own_order(self, elsewhere) -> None:
        """Order in the file is order in the dialog, so it is not sorted."""
        second = Shop("Second", "https://b/{album}")
        first = Shop("First", "https://a/{album}")
        put({"shops": rows_of(second, first)})
        assert read_book().rows == (second, first)

    def test_a_row_with_no_note_is_still_a_row(self, elsewhere) -> None:
        """The note is optional, so its absence is not a refusal."""
        put({"shops": [{"name": "N", "template": "https://n/{album}"}]})
        assert read_book().rows == (Shop("N", "https://n/{album}"),)

    def test_unknown_keys_are_passed_over(self, elsewhere) -> None:
        """A file written by a later Stellody is read by an earlier one."""
        put({"shops": [{"name": "N", "template": "https://n/{a}{album}", "c": 1}]})
        assert read_book().shops[0].name == "N"

    def test_an_emptied_list_stays_empty(self, elsewhere) -> None:
        """Every shop deleted is a choice, not a file to refill. FR-S39.

        Deleting through the editor records each shipped name, so that is the
        file an emptied list really is.
        """
        everything = [shop.name for shop in DEFAULT_SHOPS]
        put({"shops": [], "shipped": rows_of(*DEFAULT_SHOPS), "deleted": everything})
        assert read_book().rows == ()


class TestWhatIsRefused:
    def test_a_template_with_no_placeholder_is_refused(self, elsewhere) -> None:
        """FR-S11: never searched, while still listed with its reason."""
        put(
            {
                "shops": [
                    {"name": "Good", "template": "https://g/{album}"},
                    {"name": "Homepage", "template": "https://example.com/"},
                ]
            }
        )
        book = read_book()
        assert [shop.name for shop in book.shops] == ["Good"]
        assert book.rows[1] == BrokenRow(
            "Homepage", "https://example.com/", "", ShopProblem.NO_PLACEHOLDER
        )

    def test_a_broken_row_is_read_with_its_reason(self, elsewhere) -> None:
        """FR-S42: a hand-edited file can hold anything, even a bare string."""
        put({"shops": [{"template": "https://g/{album}"}, "boomkat", {"name": "B"}]})
        problems = [row.problem for row in read_book().rows]
        assert problems == [
            ShopProblem.NO_NAME,
            ShopProblem.NOT_A_ROW,
            ShopProblem.NO_ADDRESS,
        ]


class TestWhatCannotBeRead:
    def test_an_unreadable_file_falls_back_and_is_left_alone(self, elsewhere) -> None:
        """FR-S12: a file mid-edit must not be replaced under the editor."""
        shops_path().write_text("{ this is not json", encoding="utf-8")
        assert read_book().rows == DEFAULT_SHOPS
        assert shops_path().read_text(encoding="utf-8") == "{ this is not json"

    def test_a_file_that_is_not_an_object_falls_back(self, elsewhere) -> None:
        put(["Qobuz"])
        assert read_book().rows == DEFAULT_SHOPS

    def test_a_shops_key_that_is_not_a_list_falls_back(self, elsewhere) -> None:
        put({"shops": "Qobuz"})
        assert read_book().rows == DEFAULT_SHOPS


class TestMeetingARelease:
    def test_an_older_file_is_not_added_to(self, elsewhere) -> None:
        """FR-S36: a shop removed by hand before deletes were recorded."""
        put({"shops": rows_of(*DEFAULT_SHOPS[:-1]), "shipped": rows_of(*DEFAULT_SHOPS)})
        assert read_book().rows == DEFAULT_SHOPS[:-1]
        assert held()["deleted"] == []

    def test_a_settled_file_is_not_written_again(self, elsewhere) -> None:
        """A write on every open would be a write nobody asked for."""
        read_book()
        before = shops_path().read_text(encoding="utf-8")
        shops_path().write_text(before, encoding="utf-8")
        stamp = shops_path().stat().st_mtime_ns
        read_book()
        assert shops_path().stat().st_mtime_ns == stamp

    def test_a_release_reaches_an_untouched_file(self, elsewhere) -> None:
        """FR-S30 and FR-S34: the old shop retires, the new ones arrive."""
        put({"shops": rows_of(OLD), "shipped": rows_of(OLD), "deleted": []})
        book = read_book()
        assert book.rows == DEFAULT_SHOPS
        assert held()["retired"] == ["Gone"]

    def test_a_deleted_shop_stays_deleted(self, elsewhere) -> None:
        """FR-S31."""
        put(
            {
                "shops": rows_of(*DEFAULT_SHOPS[:-1]),
                "shipped": rows_of(*DEFAULT_SHOPS),
                "deleted": ["Beatport", 7],
            }
        )
        assert read_book().rows == DEFAULT_SHOPS[:-1]
        assert held()["deleted"] == ["Beatport"]

    def test_records_of_the_wrong_shape_are_read_as_absent(self, elsewhere) -> None:
        """A mangled record is no record, which is the cautious reading."""
        put({"shops": rows_of(MINE), "shipped": "x", "deleted": "y", "retired": 1})
        book = read_book()
        assert book.rows == (MINE,)
        assert book.retired == ()


class TestSaving:
    def test_a_saved_list_is_read_back(self, elsewhere) -> None:
        """FR-S19 through the file."""
        book = ShopBook(
            rows=(*DEFAULT_SHOPS[1:], MINE),
            shipped=DEFAULT_SHOPS,
            deleted=(DEFAULT_SHOPS[0].name,),
        )
        FileShopBook().save(book)
        assert FileShopBook().book() == book

    def test_a_save_that_cannot_be_written_says_so(self, elsewhere, refusing) -> None:
        """FR-S29."""
        with pytest.raises(ShopListUnwritable):
            FileShopBook().save(ShopBook(rows=(MINE,), shipped=DEFAULT_SHOPS))


class TestTheListItself:
    def test_it_offers_only_the_searchable_shops(self, elsewhere) -> None:
        put({"shops": [*rows_of(MINE), {"name": "Bad"}]})
        assert FileShopList().shops() == (MINE,)
