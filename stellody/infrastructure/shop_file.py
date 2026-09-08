"""Where the list of shops lives, plus the ones shipped to start with.

**The list is data rather than code; that was decided by measurement.** On
2026-09-07 eight digital shops were checked by loading their search and reading
what came back. Juno Download had closed, announcing it on its own front page.
7digital had put a bot wall in front of its search. Volumo's search path
answered 404. Three of eight in one afternoon: a list compiled into the
application is a release every time that happens, while a file is an edit.

So the defaults below are a starting point rather than the truth. The file is
written once, when it is first wanted; never overwritten afterwards: what
somebody put there is theirs. FR-S09.

**A file that cannot be read falls back and is LEFT ALONE.** The same judgement
the discovery file makes about its own contents, with one addition: a file
halfway through being edited must not be replaced under the person editing it.
FR-S12.

Nothing here opens a page. It reads a file and answers with shops; who opens
what is `browsing.py` and the use case above it.
"""

from __future__ import annotations

import json
import pathlib

from stellody.domain.shopping import Shop
from stellody.infrastructure import paths
from stellody.infrastructure.atomic import written

SHOPS_NAME = "shops.json"
SHOPS_KEY = "shops"
# What was shipped when the file was written, kept beside what is in use so the
# two can be compared. It is the whole of how an edit is told from an untouched
# file: a file that still says what we put in it is one nobody has changed.
# FR-S16.
SHIPPED_KEY = "shipped"
NAME_KEY = "name"
TEMPLATE_KEY = "template"
NOTE_KEY = "note"

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
# alphabetical: 7digital leads, by Oliver's ruling on 2026-09-08. Only a file
# that does not exist yet is written from this, so somebody who already has one
# keeps whatever order they have.
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


def _rows(shops: tuple[Shop, ...]) -> list[dict]:
    """The shops as the file carries them, one object a row."""
    return [
        {NAME_KEY: shop.name, TEMPLATE_KEY: shop.template, NOTE_KEY: shop.note}
        for shop in shops
    ]


def _as_written(shops: tuple[Shop, ...]) -> dict:
    """The shops in the shape the file carries them, twice.

    The second copy is what was shipped. It is written even though it is
    identical today, because tomorrow it is the only thing that can say whether
    the first copy was changed by hand or merely inherited. FR-S16.
    """
    return {SHOPS_KEY: _rows(shops), SHIPPED_KEY: _rows(shops)}


def _shop(entry: object) -> Shop | None:
    """One row as the file carries it; None where it carries nothing usable.

    A row missing a name, missing an address or naming no placeholder is passed
    over rather than raising: a list missing one shop is worth more than no
    list at all, which is the same judgement the discovery reader makes.
    """
    if not isinstance(entry, dict):
        return None
    try:
        return Shop(
            name=str(entry.get(NAME_KEY) or ""),
            template=str(entry.get(TEMPLATE_KEY) or ""),
            note=str(entry.get(NOTE_KEY) or ""),
        )
    except ValueError:
        return None


def _held() -> dict | None:
    """The file as an object; None where there is nothing usable to read."""
    try:
        held = json.loads(shops_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return held if isinstance(held, dict) else None


def _listed(held: dict | None, key: str) -> tuple[Shop, ...] | None:
    """The shops under this key; None where the key holds no usable list."""
    rows = held.get(key) if isinstance(held, dict) else None
    if not isinstance(rows, list):
        return None
    return tuple(shop for shop in (_shop(row) for row in rows) if shop is not None)


def read() -> tuple[Shop, ...]:
    """What the file holds; the shipped defaults where it holds nothing usable.

    The file is not touched here. Writing a default list over something
    somebody is midway through editing would lose their work at the exact
    moment they most want it back.
    """
    found = _listed(_held(), SHOPS_KEY)
    return found or DEFAULT_SHOPS


def _untouched(in_use: tuple[Shop, ...], shipped: tuple[Shop, ...] | None) -> bool:
    """Whether nobody has edited this file.

    Two ways to be sure of it and no third. Either the list still says exactly
    what the file records having been given; or the file records nothing and
    the list still says exactly what is shipped today, which is the same
    statement made by the only other evidence available.

    A file recording nothing whose list differs from the shipped one is the
    case that cannot be settled: it is either an edit or an older list, with
    nothing on disk to tell them apart. It is left alone, which is the
    same judgement FR-S12 makes about a file it cannot read. FR-S16.
    """
    return in_use == shipped or in_use == DEFAULT_SHOPS


def refresh_if_untouched() -> bool:
    """Follow the shipped list where nobody has edited the file; did it write.

    FR-S09 keeps the file so an EDIT survives a release, so what has to be
    answered is whether anybody edited it rather than merely whether it exists.
    Recording what was shipped is what makes that answerable.

    Two things are put right here and they are one write. A file still carrying
    an older shipped list takes the current one. A file that carries the current
    list but records nothing gains the record, without a word of its content
    changing, so the NEXT correction can reach it; that is the one case a file
    written before any of this existed falls into. FR-S16.
    """
    held = _held()
    in_use = _listed(held, SHOPS_KEY)
    shipped = _listed(held, SHIPPED_KEY)
    if not in_use or not _untouched(in_use, shipped):
        return False
    if in_use == DEFAULT_SHOPS and shipped == in_use:
        return False
    try:
        written(shops_path(), _as_written(DEFAULT_SHOPS))
    except OSError:
        return False
    return True


def refused(rows: object) -> tuple[str, ...]:
    """Which rows of a list were passed over, by name where they have one.

    Answered separately from `read` so the reader stays one job: this is what
    a screen says about a file somebody has edited, rather than something the
    list itself has to carry. FR-S11.
    """
    if not isinstance(rows, list):
        return ()
    return tuple(
        str(row.get(NAME_KEY) or "") if isinstance(row, dict) else ""
        for row in rows
        if _shop(row) is None
    )


def write_defaults_if_absent() -> bool:
    """Put the shipped list where it belongs; True where this wrote it.

    Once, on the first day somebody opens the shops. A file that already
    exists is left exactly as it is, including one that cannot be parsed.
    """
    where = shops_path()
    if where.exists():
        return False
    try:
        written(where, _as_written(DEFAULT_SHOPS))
    except OSError:
        return False
    return True


class FileShopList:
    """The shops as the file holds them, with the defaults behind it.

    A thin object over the two functions above, for the same reason the
    discovery reader is one: what the use case needs is somewhere to read
    from; the file is already that.
    """

    def shops(self) -> tuple[Shop, ...]:
        """Every shop worth offering, tidying the file first where it may be.

        Three jobs rather than one function doing three, so a reader stays a
        reader: write the file where there is none, follow the shipped list
        where nobody has edited it, then read whatever is there.
        """
        write_defaults_if_absent()
        refresh_if_untouched()
        return read()
