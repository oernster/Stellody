"""The shop list on disk: what ships, what is read back and what is refused.

Every test here puts Stellody's own directory somewhere temporary, since the
whole point of the file is that it lives beside the discovery answer and is
edited by hand.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from stellody.domain.shopping import Shop
from stellody.infrastructure import paths, shop_file
from stellody.infrastructure.shop_file import (
    DEFAULT_SHOPS,
    FileShopList,
    read,
    refresh_if_untouched,
    refused,
    shops_path,
    write_defaults_if_absent,
)


@pytest.fixture
def elsewhere(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """Stellody's directory, somewhere a test may write."""
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    return tmp_path


def put(where: pathlib.Path, content: object) -> None:
    """Write a shop file holding exactly this."""
    where.write_text(json.dumps(content), encoding="utf-8")


class TestWhatShips:
    def test_every_shipped_template_names_a_placeholder(self) -> None:
        """A row that named neither would open the same page every time.

        Enforced by the domain, asserted here because these eight rows are
        data rather than code and nothing else would ever construct them.
        """
        for shop in DEFAULT_SHOPS:
            assert shop.names_a_placeholder, shop.name

    def test_every_shipped_template_is_an_https_address(self) -> None:
        """A shop reached over plain http would leak the search in transit."""
        for shop in DEFAULT_SHOPS:
            assert shop.template.startswith("https://"), shop.name

    def test_the_shipped_list_holds_no_two_shops_of_one_name(self) -> None:
        """Two rows called Qobuz is a dialog with two identical buttons."""
        names = [shop.name for shop in DEFAULT_SHOPS]
        assert len(names) == len(set(names))

    def test_boomkat_searches_the_artist_alone(self) -> None:
        """Measured on 2026-09-07: two terms answered nothing, one answered 85.

        Pinned because it looks like an omission and is not: a later tidy-up
        that "fixed" this row by adding the album would break that shop.
        """
        boomkat = next(shop for shop in DEFAULT_SHOPS if shop.name == "Boomkat")
        assert "{artist}" in boomkat.template
        assert "{album}" not in boomkat.template

    def test_7digital_is_offered_first(self) -> None:
        """Chosen rather than alphabetical, so a tidy-up cannot resort it.

        Ruled by Oliver on 2026-09-08. The order the list is written in is the
        order the shops are offered in, which makes it a decision rather than
        an accident of how the rows were typed.
        """
        assert DEFAULT_SHOPS[0].name == "7digital"

    def test_7digital_keeps_the_host_and_the_fallback_it_was_seen_with(self) -> None:
        """Read from a browser on 2026-09-08, past the wall that refuses us.

        Two parts of that address look like clutter and are not. The regional
        host is the one the shop itself served; the fallback is what came back
        with it. Neither could be reached by us to be checked again, so a tidy
        up that trimmed either would be trimming the only evidence there is.
        """
        seven = next(shop for shop in DEFAULT_SHOPS if shop.name == "7digital")
        assert seven.template.startswith("https://uk.7digital.com/search?q=")
        assert seven.template.endswith("&fallback=true")


class TestTheFirstTime:
    def test_a_missing_file_is_written_with_the_defaults(self, elsewhere) -> None:
        """FR-S09: the list arrives as something to edit rather than as code."""
        assert write_defaults_if_absent()
        held = json.loads(shops_path().read_text(encoding="utf-8"))
        assert [row["name"] for row in held["shops"]] == [
            shop.name for shop in DEFAULT_SHOPS
        ]

    def test_a_file_that_exists_is_never_overwritten(self, elsewhere) -> None:
        """What somebody put there is theirs, including a broken file."""
        put(
            shops_path(), {"shops": [{"name": "Mine", "template": "https://m/{album}"}]}
        )
        assert not write_defaults_if_absent()
        assert read() == (Shop(name="Mine", template="https://m/{album}"),)

    def test_a_directory_that_cannot_be_written_is_not_an_error(
        self, elsewhere, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A read-only directory costs the defaults on disk, nothing more."""

        def refuse(*_arguments, **_named):
            """Stand in for a filesystem that will not have it."""
            raise OSError("read only")

        monkeypatch.setattr(shop_file, "written", refuse)
        assert not write_defaults_if_absent()
        assert read() == DEFAULT_SHOPS


class TestReadingItBack:
    def test_the_rows_come_back_in_the_files_own_order(self, elsewhere) -> None:
        """Order in the file is order in the dialog, so it is not sorted."""
        put(
            shops_path(),
            {
                "shops": [
                    {"name": "Second", "template": "https://b/{album}"},
                    {"name": "First", "template": "https://a/{album}"},
                ]
            },
        )
        assert [shop.name for shop in read()] == ["Second", "First"]

    def test_a_note_travels_with_the_row(self, elsewhere) -> None:
        """What a shop stocks is part of choosing it."""
        put(
            shops_path(),
            {"shops": [{"name": "N", "template": "https://n/{album}", "note": "FLAC"}]},
        )
        assert read()[0].note == "FLAC"

    def test_a_row_with_no_note_is_still_a_row(self, elsewhere) -> None:
        """The note is optional, so its absence is not a refusal."""
        put(shops_path(), {"shops": [{"name": "N", "template": "https://n/{album}"}]})
        assert read()[0].note == ""

    def test_unknown_keys_are_passed_over(self, elsewhere) -> None:
        """A file written by a later Stellody is read by an earlier one."""
        put(
            shops_path(),
            {
                "shops": [
                    {"name": "N", "template": "https://n/{album}", "colour": "blue"}
                ],
                "written_by": "2.0",
            },
        )
        assert read()[0].name == "N"


class TestWhatIsRefused:
    def test_a_template_with_no_placeholder_is_refused(self, elsewhere) -> None:
        """FR-S11: it would open the same page whatever was ticked."""
        rows = [
            {"name": "Good", "template": "https://g/{album}"},
            {"name": "Homepage", "template": "https://example.com/"},
        ]
        put(shops_path(), {"shops": rows})
        assert [shop.name for shop in read()] == ["Good"]
        assert refused(rows) == ("Homepage",)

    def test_a_row_missing_its_name_is_refused(self, elsewhere) -> None:
        """A button nobody can read is not a button."""
        rows = [{"template": "https://g/{album}"}]
        put(shops_path(), {"shops": rows})
        assert read() == DEFAULT_SHOPS
        assert refused(rows) == ("",)

    def test_a_row_that_is_not_a_row_at_all_is_refused(self, elsewhere) -> None:
        """A hand-edited file can hold anything, including a bare string."""
        rows = ["boomkat"]
        put(shops_path(), {"shops": rows})
        assert read() == DEFAULT_SHOPS
        assert refused(rows) == ("",)

    def test_nothing_refused_where_the_shape_is_wrong_entirely(self) -> None:
        """Asked about something that is not a list at all, it says nothing."""
        assert refused({"shops": "all of them"}) == ()


class TestWhatCannotBeRead:
    def test_an_unreadable_file_falls_back_and_is_left_alone(self, elsewhere) -> None:
        """FR-S12: a file mid-edit must not be replaced under the editor."""
        shops_path().write_text("{ this is not json", encoding="utf-8")
        assert read() == DEFAULT_SHOPS
        assert shops_path().read_text(encoding="utf-8") == "{ this is not json"

    def test_a_file_that_is_not_an_object_falls_back(self, elsewhere) -> None:
        """Valid JSON of the wrong shape is the same disappointment."""
        put(shops_path(), ["Qobuz"])
        assert read() == DEFAULT_SHOPS

    def test_a_shops_key_that_is_not_a_list_falls_back(self, elsewhere) -> None:
        """One level further in, the same judgement."""
        put(shops_path(), {"shops": "Qobuz"})
        assert read() == DEFAULT_SHOPS

    def test_a_list_of_nothing_usable_falls_back(self, elsewhere) -> None:
        """An empty dialog says less than the shipped list does."""
        put(shops_path(), {"shops": [{"name": "Bad"}]})
        assert read() == DEFAULT_SHOPS

    def test_a_file_that_is_not_there_falls_back(self, elsewhere) -> None:
        """The very first read, before anything has been written."""
        assert read() == DEFAULT_SHOPS


class TestTheListItself:
    def test_it_writes_the_defaults_then_answers_with_them(self, elsewhere) -> None:
        """What the use case is handed: one call, both jobs."""
        assert FileShopList().shops() == DEFAULT_SHOPS
        assert shops_path().exists()

    def test_the_shops_are_offered_even_where_nothing_can_be_written(
        self, elsewhere, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A fresh install shows the shops on every machine, file or no file.

        The list is code and the file is only an override of it, so nothing
        about a filesystem can empty the dialog: a read-only directory, a
        sandbox that will not have it, a platform whose data directory cannot
        be made. Each costs the file; none of them costs the shops.

        Asserted through the object the dialog actually holds rather than
        through the reader under it, since a dialog with no shops in it is the
        failure being ruled out.
        """

        def refuse(*_arguments, **_named):
            """Stand in for a filesystem that will not have it."""
            raise OSError("read only")

        monkeypatch.setattr(shop_file, "written", refuse)
        assert FileShopList().shops() == DEFAULT_SHOPS
        assert not shops_path().exists()

    def test_it_answers_with_what_somebody_edited(self, elsewhere) -> None:
        """The whole reason the list is a file."""
        put(
            shops_path(), {"shops": [{"name": "Mine", "template": "https://m/{album}"}]}
        )
        assert [shop.name for shop in FileShopList().shops()] == ["Mine"]


OLD = Shop(name="Gone", template="https://old/{artist}", note="Yesterday's row.")


def _as_rows(shops: tuple[Shop, ...]) -> list[dict]:
    """These shops as a file carries them."""
    return [
        {"name": shop.name, "template": shop.template, "note": shop.note}
        for shop in shops
    ]


def written_with(rows: tuple[Shop, ...], shipped: tuple[Shop, ...]) -> None:
    """A file holding this list, recording that shipped list behind it."""
    put(shops_path(), {"shops": _as_rows(rows), "shipped": _as_rows(shipped)})


class TestRefreshingAnUntouchedFile:
    """FR-S16. Found on 2026-09-08, when a corrected address could not arrive.

    FR-S09 writes the file once so an EDIT survives a release. What it actually
    did was keep the first list anybody was ever given, so 7digital's corrected
    address and the new order reached the application and stopped there. What
    has to be answered is whether somebody edited the file; the only way to
    answer that is to have written down what we put there.
    """

    def test_a_file_nobody_touched_takes_the_shipped_list(self, elsewhere) -> None:
        """The reported case: the correction arrives without anybody's help."""
        written_with((OLD,), (OLD,))
        assert FileShopList().shops() == DEFAULT_SHOPS

    def test_the_refreshed_file_records_what_it_now_carries(self, elsewhere) -> None:
        """Else it refreshes once and never again, which is worse than never."""
        written_with((OLD,), (OLD,))
        FileShopList().shops()
        held = json.loads(shops_path().read_text(encoding="utf-8"))
        assert held["shops"] == held["shipped"]
        assert held["shops"][0]["name"] == DEFAULT_SHOPS[0].name

    def test_a_file_somebody_edited_is_left_exactly_as_it_is(self, elsewhere) -> None:
        """The half this exists to protect. FR-S09 still holds."""
        written_with((OLD,), DEFAULT_SHOPS)
        before = shops_path().read_text(encoding="utf-8")
        assert [shop.name for shop in FileShopList().shops()] == ["Gone"]
        assert shops_path().read_text(encoding="utf-8") == before

    def test_a_file_recording_nothing_but_holding_the_shipped_list_gains_a_record(
        self, elsewhere
    ) -> None:
        """The one file that existed when this was written. Measured 2026-09-08.

        Oliver's own, rewritten by hand-deleting it, so it carries the current
        list and no record at all. Without this it could never refresh again,
        which would make the whole mechanism miss the only file there was.
        """
        put(shops_path(), {"shops": _as_rows(DEFAULT_SHOPS)})
        assert refresh_if_untouched()
        held = json.loads(shops_path().read_text(encoding="utf-8"))
        assert held["shipped"] == held["shops"]
        assert read() == DEFAULT_SHOPS

    def test_gaining_a_record_happens_once_rather_than_every_launch(
        self, elsewhere
    ) -> None:
        """A write on every open would be a write nobody asked for."""
        put(shops_path(), {"shops": _as_rows(DEFAULT_SHOPS)})
        assert refresh_if_untouched()
        assert not refresh_if_untouched()

    def test_a_file_recording_nothing_shipped_is_left_alone(self, elsewhere) -> None:
        """It predates this and cannot be proved either way, so it is not judged.

        The same judgement FR-S12 makes about a file it cannot read: never
        replace somebody's file on a guess about where it came from.
        """
        put(
            shops_path(),
            {"shops": [{"name": "Gone", "template": "https://old/{artist}"}]},
        )
        before = shops_path().read_text(encoding="utf-8")
        assert [shop.name for shop in FileShopList().shops()] == ["Gone"]
        assert shops_path().read_text(encoding="utf-8") == before

    def test_a_file_already_carrying_the_shipped_list_is_not_rewritten(
        self, elsewhere
    ) -> None:
        """Nothing to do is nothing done, rather than a write every launch."""
        assert FileShopList().shops() == DEFAULT_SHOPS
        assert not refresh_if_untouched()

    def test_a_file_that_cannot_be_read_is_not_refreshed(self, elsewhere) -> None:
        """Malformed is not the same as untouched. FR-S12."""
        shops_path().write_text("{ not json", encoding="utf-8")
        assert not refresh_if_untouched()

    def test_a_refresh_that_cannot_be_written_is_not_an_error(
        self, elsewhere, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A read-only directory is a disappointment rather than a failure."""
        written_with((OLD,), (OLD,))

        def refuse(*_arguments, **_named):
            raise OSError("read only")

        monkeypatch.setattr(shop_file, "written", refuse)
        assert not refresh_if_untouched()
        assert [shop.name for shop in read()] == ["Gone"]
