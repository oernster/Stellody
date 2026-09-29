"""What MusicBrainz knows about series of compilations.

The series half of `catalogue.py`, beside it rather than inside it so that
module keeps to the three questions it was written for. FR-D69, FR-D70.

**Measured against the live service on 2026-09-29.** A release group search
answers with the group's title, types and first release date; no series;
the series come from looking the group up with its series relations. A series
looked up with its release group relations lists every entry in order, each
with its title, its secondary types and its first release date; neither states
a genre, which the domain reads as undescribed and so keeps. "Global
Underground: Unique" belongs to no series; a search for its stem finds Unique,
Unique #2 and Unique #3.

**A release group is taken as this title where it sits in the same place of
the same series**, compared by stem and number rather than by the whole title,
since the library writes "/ Unmixed" and "- Ibiza" where the catalogue does not.

Nothing here opens a connection; `fetching.py` holds the socket.
"""

from __future__ import annotations

from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.domain.discovery import ReleaseGroup
from stellody.domain.series import Series, series_place, volume_title
from stellody.infrastructure.catalogue import (
    FIRST_RELEASE,
    GROUP_LIMIT,
    NAME_LIMIT,
    RELEASE_GROUP_URL,
    _entries,
    _escaped,
    _groups,
    _kinds_of,
)
from stellody.infrastructure.fetching import Fetcher

SERIES_URL = "https://musicbrainz.org/ws/2/series"
# What a relation to a series and to a release group are called there.
TO_SERIES = "series"
TO_GROUP = "release_group"
TARGET = "target-type"


class MusicBrainzSeries:
    """The catalogue, asked the three questions a series stage has for it."""

    def __init__(self, fetcher: Fetcher | None = None) -> None:
        self._fetch = fetcher if fetcher is not None else Fetcher()

    def _search(self, phrase: str, limit: int, wanted: Wanted) -> list[dict]:
        """The release groups a search for this phrase answers with."""
        answer = self._fetch.json(
            RELEASE_GROUP_URL,
            {
                "query": f'releasegroup:"{_escaped(phrase)}"',
                "fmt": "json",
                "limit": str(limit),
            },
            wanted,
        )
        return _entries(answer, "release-groups")

    def series_of(self, title: str, wanted: Wanted = always_wanted) -> tuple[str, ...]:
        """Every series a release group in this title's place belongs to."""
        place = series_place(title)
        found: dict[str, None] = {}
        for entry in self._search(volume_title(title), NAME_LIMIT, wanted):
            if not entry.get("id") or series_place(str(entry.get("title"))) != place:
                continue
            group = self._fetch.json(
                f"{RELEASE_GROUP_URL}/{entry['id']}",
                {"inc": "series-rels", "fmt": "json"},
                wanted,
            )
            for relation in _entries(group, "relations"):
                series = relation.get(TO_SERIES)
                if (
                    relation.get(TARGET) == TO_SERIES
                    and isinstance(series, dict)
                    and series.get("id")
                ):
                    found.setdefault(str(series["id"]), None)
        return tuple(found)

    def series(self, identifier: str, wanted: Wanted = always_wanted) -> Series:
        """One series by name, with every release group in it, in order."""
        answer = self._fetch.json(
            f"{SERIES_URL}/{identifier}",
            {"inc": "release-group-rels", "fmt": "json"},
            wanted,
        )
        name = str(answer.get("name") or "") if isinstance(answer, dict) else ""
        entries = []
        for relation in _entries(answer, "relations"):
            group = relation.get(TO_GROUP)
            if relation.get(TARGET) != TO_GROUP or not isinstance(group, dict):
                continue
            title = str(group.get("title") or "").strip()
            if title:
                entries.append(
                    ReleaseGroup(
                        title=title,
                        kinds=_kinds_of(group),
                        released=str(group.get(FIRST_RELEASE) or "").strip(),
                    )
                )
        return Series(name=name.strip() or identifier, entries=tuple(entries))

    def titled(
        self, stem: str, wanted: Wanted = always_wanted
    ) -> tuple[ReleaseGroup, ...]:
        """The albums and EPs a search for this stem answers with."""
        return tuple(_groups(self._search(stem, GROUP_LIMIT, wanted)))
