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
NAME_KEY = "name"
TEMPLATE_KEY = "template"
NOTE_KEY = "note"

# Every template below was loaded on 2026-09-07 and answered, except where the
# note says otherwise. The note travels with the row, since what a shop stocks
# is as much a part of choosing it as its name: a Bandcamp search for a major
# label artist is not a broken search, it is an empty catalogue.
DEFAULT_SHOPS: tuple[Shop, ...] = (
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
    Shop(
        name="7digital",
        template="https://www.7digital.com/search?q={artist}%20{album}",
        note="Its search refuses robots, so this address is unconfirmed.",
    ),
)


def shops_path() -> pathlib.Path:
    """Where the list belongs, whether or not it is there yet."""
    return paths.data_dir() / SHOPS_NAME


def _as_written(shops: tuple[Shop, ...]) -> dict:
    """The shops in the shape the file carries them."""
    return {
        SHOPS_KEY: [
            {NAME_KEY: shop.name, TEMPLATE_KEY: shop.template, NOTE_KEY: shop.note}
            for shop in shops
        ]
    }


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


def read() -> tuple[Shop, ...]:
    """What the file holds; the shipped defaults where it holds nothing usable.

    The file is not touched here. Writing a default list over something
    somebody is midway through editing would lose their work at the exact
    moment they most want it back.
    """
    try:
        held = json.loads(shops_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return DEFAULT_SHOPS
    rows = held.get(SHOPS_KEY) if isinstance(held, dict) else None
    if not isinstance(rows, list):
        return DEFAULT_SHOPS
    found = tuple(shop for shop in (_shop(row) for row in rows) if shop is not None)
    return found or DEFAULT_SHOPS


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
        """Every shop worth offering, writing the defaults on the first ask."""
        write_defaults_if_absent()
        return read()
