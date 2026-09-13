"""Where the list of shops lives, plus the ones shipped to start with.

**The list is data rather than code; that was decided by measurement.** On
2026-09-07 eight digital shops were checked by loading their search and reading
what came back. Juno Download had closed, announcing it on its own front page.
7digital had put a bot wall in front of its search. Volumo's search path
answered 404. Three of eight in one afternoon: a list compiled into the
application is a release every time that happens, while a file is an edit.

**The file is changed from the shops dialog now; it is still the record.**
SHOPS.md Amendment 1. What an edit means and how a release's shops meet the
list live in `domain/shop_list.py`. This reads the file into those rules and
writes their answer back, so the file never holds a list the dialog did not
show. It is written the first time it is wanted (FR-S09) and again whenever
settling it against this release changes anything (FR-S30 to FR-S36).

**A file that cannot be read falls back and is LEFT ALONE.** A file halfway
through being edited by hand must not be replaced under the person editing it.
FR-S12. A list holding rows that cannot be searched is not that: it is read row
by row, each broken row kept in its place with its reason (FR-S42).

Nothing here opens a page. Who opens what is `browsing.py` and the use cases.
"""

from __future__ import annotations

import json
import pathlib

from stellody.application.shop_editing import ShopListUnwritable
from stellody.domain.shop_list import (
    BrokenRow,
    Row,
    ShopBook,
    ShopProblem,
    merged,
    row_problem,
)
from stellody.domain.shopping import Shop
from stellody.infrastructure import paths
from stellody.infrastructure.atomic import written

SHOPS_NAME = "shops.json"
SHOPS_KEY = "shops"
# The release list the rows were last settled against, which is how an edited
# shipped shop is told from an untouched one. FR-S32, FR-S33.
SHIPPED_KEY = "shipped"
# Shipped shops the listener removed, so no release puts them back. FR-S25.
DELETED_KEY = "deleted"
# Shops a release dropped that the dialog has yet to announce. FR-S34.
RETIRED_KEY = "retired"
NAME_KEY = "name"
TEMPLATE_KEY = "template"
NOTE_KEY = "note"
KEYS = (SHOPS_KEY, SHIPPED_KEY, DELETED_KEY, RETIRED_KEY)

# Every template below was loaded and answered: seven on 2026-09-07 here; then
# 7digital on 2026-09-08 in a browser, since its search refuses an automated
# visitor.
#
# A note says what a shop STOCKS, which is as much a part of choosing it as its
# name: a Bandcamp search for a major label artist is not a broken search, it is
# an empty catalogue. A note is NOT the place for a caveat about the address.
# Ruled by Oliver on 2026-09-08, on being shown one: every shop here opens.
# Whether one particular search finds one particular record is a thing to read
# on the page rather than a warning to carry around under a button.
#
# The ORDER is the order they are offered in; it is chosen rather than
# alphabetical: 7digital leads, by Oliver's ruling on 2026-09-08. A release
# adds a new shop at the bottom of a list somebody already has (FR-S30), so
# their order is theirs.
DEFAULT_SHOPS: tuple[Shop, ...] = (
    Shop(
        name="7digital",
        template="https://uk.7digital.com/search?q={artist}%20{album}&fallback=true",
        note="The UK storefront.",
    ),
    Shop(
        name="Qobuz",
        template="https://www.qobuz.com/gb-en/search?q={artist}%20{album}",
        note="Lossless and hi-res downloads only.",
    ),
    Shop(
        name="Bandcamp",
        template="https://bandcamp.com/search?q={artist}%20{album}&item_type=a",
        note="Independent catalogue, so major label releases are absent.",
    ),
    Shop(
        name="Boomkat",
        template=(
            "https://boomkat.com/products?q[keywords]={artist}&q[format]=Download"
        ),
        note="Digital only, by its own filter. Searches the artist alone.",
    ),
    Shop(
        name="Bleep",
        template="https://bleep.com/search/query?q={artist}%20{album}",
        note="Warp's shop. FLAC, WAV and MP3.",
    ),
    Shop(
        name="Presto Music",
        template=("https://www.prestomusic.com/search?search_query={artist}%20{album}"),
        note="Classical and jazz lean. Mixes downloads with discs and books.",
    ),
    Shop(
        name="ProStudioMasters",
        template="https://www.prostudiomasters.com/search?q={artist}%20{album}",
        note="Hi-res, with FLAC, MQA and DSD.",
    ),
    Shop(
        name="Beatport",
        template="https://www.beatport.com/search?q={artist}%20{album}",
        note="Electronic. WAV, AIFF and MP3 rather than FLAC.",
    ),
)


def shops_path() -> pathlib.Path:
    """Where the list belongs, whether or not it is there yet."""
    return paths.data_dir() / SHOPS_NAME


def _row_written(row: Row) -> dict:
    """One row as the file carries it, broken or not."""
    return {NAME_KEY: row.name, TEMPLATE_KEY: row.template, NOTE_KEY: row.note}


def _as_written(book: ShopBook) -> dict:
    """The whole list in the shape the file carries it."""
    return {
        SHOPS_KEY: [_row_written(row) for row in book.rows],
        SHIPPED_KEY: [_row_written(shop) for shop in book.shipped],
        DELETED_KEY: list(book.deleted),
        RETIRED_KEY: list(book.retired),
    }


def _row(entry: object) -> Row:
    """One entry of the file: a shop, else a broken row saying why not."""
    if not isinstance(entry, dict):
        return BrokenRow("", "", "", ShopProblem.NOT_A_ROW)
    name = str(entry.get(NAME_KEY) or "")
    template = str(entry.get(TEMPLATE_KEY) or "")
    note = str(entry.get(NOTE_KEY) or "")
    problem = row_problem(name, template)
    if problem is not None:
        return BrokenRow(name, template, note, problem)
    return Shop(name=name, template=template, note=note)


def _held() -> dict | None:
    """The file as an object; None where there is nothing usable to read."""
    try:
        held = json.loads(shops_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return held if isinstance(held, dict) else None


def _record(held: dict) -> tuple[Shop, ...] | None:
    """The recorded release list; None where the file carries none."""
    rows = held.get(SHIPPED_KEY)
    if not isinstance(rows, list):
        return None
    return tuple(row for row in map(_row, rows) if isinstance(row, Shop))


def _names(held: dict, key: str) -> tuple[str, ...] | None:
    """A list of names under `key`; None where the file carries no such list."""
    names = held.get(key)
    if not isinstance(names, list):
        return None
    return tuple(name for name in names if isinstance(name, str))


def _defaults() -> ShopBook:
    """The shipped list, as a first run holds it."""
    return ShopBook(rows=DEFAULT_SHOPS, shipped=DEFAULT_SHOPS)


def _write_quietly(book: ShopBook) -> None:
    """Keep this list where possible; a directory that refuses costs the file.

    Only for writes nobody asked for. A change somebody made goes through
    `FileShopBook.save`, which says so when it fails.
    """
    try:
        written(shops_path(), _as_written(book))
    except OSError:
        pass


def read_book() -> ShopBook:
    """The list, settled against this release; written back where that changed it.

    A missing file is written with the defaults. A file that cannot be read is
    answered with the defaults and left alone; so is one whose shops are not a
    list.
    """
    if not shops_path().exists():
        book = _defaults()
        _write_quietly(book)
        return book
    held = _held()
    rows = held.get(SHOPS_KEY) if held is not None else None
    if held is None or not isinstance(rows, list):
        return _defaults()
    book = merged(
        rows=tuple(_row(entry) for entry in rows),
        recorded=_record(held),
        deleted=_names(held, DELETED_KEY),
        retired=_names(held, RETIRED_KEY) or (),
        current=DEFAULT_SHOPS,
    )
    if _as_written(book) != {key: held.get(key) for key in KEYS}:
        _write_quietly(book)
    return book


class FileShopBook:
    """The shop file as the editor's store."""

    def book(self) -> ShopBook:
        """The list as it stands, settled against this release."""
        return read_book()

    def save(self, book: ShopBook) -> None:
        """Keep this list, saying so where the file will not take it. FR-S29."""
        try:
            written(shops_path(), _as_written(book))
        except OSError as error:
            raise ShopListUnwritable(str(error)) from error


class FileShopList:
    """The shops that can be searched, for the use case that searches them."""

    def shops(self) -> tuple[Shop, ...]:
        """Every searchable shop, in the list's order."""
        return read_book().shops
