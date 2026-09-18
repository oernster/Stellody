"""What MusicBrainz knows: which artist a name means and what they released.

**A release group rather than a release, which is why the matching rule can be
as short as it is.** A release group is the album as an idea; its remasters,
deluxe editions and country pressings are releases inside it. So the edition
noise a library carries in its tags does not arrive from here at all; what does
arrive states its own kinds as data rather than in a title.

**A name is only taken as identified where it matches exactly.** A search
answers with everything it thinks plausible, ranked, so accepting the top hit
would file a discography under whichever artist the ranking preferred that day.
Only artists whose name reads the same as the one asked about are returned; two
of those is an ambiguity for somebody to be told about rather than one for this
to resolve on their behalf.

Nothing here opens a connection. It says what to ask and reads what came back;
`fetching.py` is the module that holds the socket.
"""

from __future__ import annotations

from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.domain.discovery import ReleaseGroup
from stellody.domain.matching import ReleaseKind
from stellody.domain.text import comparison_key
from stellody.infrastructure.fetching import Fetcher

ARTIST_URL = "https://musicbrainz.org/ws/2/artist"
RELEASE_GROUP_URL = "https://musicbrainz.org/ws/2/release-group"
# How many artists a name search may answer with. Only exact matches are kept,
# so this is the width of the net rather than the number offered to anybody.
NAME_LIMIT = 25
# A discography in one ask where it fits. The service caps a page at 100.
GROUP_LIMIT = 100
# The most pages one artist may take. A page comes back full only where there
# is more, so this only stops a service that answers full pages forever: a
# page count is foreign input. Twenty pages is 2000 albums and EPs, beyond the
# 1474 release groups of every type measured for The Rolling Stones on
# 2026-09-08, the largest discography seen.
MOST_PAGES = 20
# The primary types worth offering. A single is not a record somebody goes
# looking for; everything else is not an album at all.
PRIMARY_WANTED = frozenset({"album", "ep"})
# What the service calls a secondary type, in the vocabulary the domain uses.
# A type absent from here is carried as OTHER rather than dropped, so a kind
# nobody anticipated is excluded by the offering rule instead of passing as a
# plain album.
SECONDARY_KINDS: dict[str, ReleaseKind] = {
    "live": ReleaseKind.LIVE,
    "remix": ReleaseKind.REMIX,
    "demo": ReleaseKind.DEMO,
    "compilation": ReleaseKind.COMPILATION,
    "soundtrack": ReleaseKind.SOUNDTRACK,
    "dj-mix": ReleaseKind.DJ_MIX,
}


def _escaped(text: str) -> str:
    """A term safe to sit inside a quoted phrase in a search."""
    return text.replace("\\", " ").replace('"', " ")


def _entries(answer: object, key: str) -> list[dict]:
    """The list under this key; empty where the answer is not what was meant.

    A service that changes shape is a service that answers nothing useful,
    which is a better outcome than an exception halfway through a run of 327.
    """
    if not isinstance(answer, dict):
        return []
    found = answer.get(key)
    if not isinstance(found, list):
        return []
    return [entry for entry in found if isinstance(entry, dict)]


def _named(entry: dict, key: str) -> tuple[str, ...]:
    """The names inside a list of named things under this key."""
    found = entry.get(key)
    if not isinstance(found, list):
        return ()
    return tuple(
        str(item.get("name") or "")
        for item in found
        if isinstance(item, dict) and item.get("name")
    )


def _kinds_of(entry: dict) -> tuple[ReleaseKind, ...]:
    """The kinds this release group states, in catalogue order."""
    stated = entry.get("secondary-types")
    names = stated if isinstance(stated, list) else []
    found = {
        SECONDARY_KINDS.get(str(name).casefold(), ReleaseKind.OTHER) for name in names
    }
    return tuple(kind for kind in ReleaseKind if kind in found)


class MusicBrainz:
    """The catalogue, asked the three questions a discovery run has for it."""

    def __init__(self, fetcher: Fetcher | None = None) -> None:
        self._fetch = fetcher if fetcher is not None else Fetcher()

    def identify(self, name: str, wanted: Wanted = always_wanted) -> tuple[str, ...]:
        """Every artist whose name reads exactly as this one; usually one."""
        answer = self._fetch.json(
            ARTIST_URL,
            {
                "query": f'artist:"{_escaped(name)}"',
                "fmt": "json",
                "limit": str(NAME_LIMIT),
            },
            wanted,
        )
        sought = comparison_key(name)
        return tuple(
            str(entry["id"])
            for entry in _entries(answer, "artists")
            if entry.get("id")
            and comparison_key(str(entry.get("name") or "")) == sought
        )

    def albums_of(
        self, identifier: str, wanted: Wanted = always_wanted
    ) -> tuple[ReleaseGroup, ...]:
        """The albums and EPs this artist released, with their stated genres.

        A page at a time, the next asked for only after a full one, so an
        artist who fits on one page costs one request as always.
        """
        found: list[ReleaseGroup] = []
        for page in range(MOST_PAGES):
            asked = {
                "artist": identifier,
                "type": "album|ep",
                "inc": "genres",
                "fmt": "json",
                "limit": str(GROUP_LIMIT),
            }
            if page:
                asked["offset"] = str(page * GROUP_LIMIT)
            entries = _entries(
                self._fetch.json(RELEASE_GROUP_URL, asked, wanted), "release-groups"
            )
            found.extend(_groups(entries))
            if len(entries) < GROUP_LIMIT:
                break
        return tuple(found)

    def genres_of(
        self, identifier: str, wanted: Wanted = always_wanted
    ) -> tuple[str, ...]:
        """What this artist is said to play; empty where nothing is said."""
        answer = self._fetch.json(
            f"{ARTIST_URL}/{identifier}", {"inc": "genres", "fmt": "json"}, wanted
        )
        if not isinstance(answer, dict):
            return ()
        return _named(answer, "genres")


def _groups(entries: list[dict]) -> list[ReleaseGroup]:
    """The albums and EPs on one page, as the domain knows them."""
    found = []
    for entry in entries:
        title = str(entry.get("title") or "").strip()
        primary = str(entry.get("primary-type") or "").casefold()
        if not title or primary not in PRIMARY_WANTED:
            continue
        found.append(
            ReleaseGroup(
                title=title,
                kinds=_kinds_of(entry),
                genres=_named(entry, "genres"),
            )
        )
    return found
