"""NFR-PRIV-001 and NFR-PRIV-002: what a discovery run's requests carry.

Every question both catalogues are asked goes through a fetcher that records
it, then is read against a fixed allowed set: which fields each address may
carry, which of those may hold what the run was given and which may only ever
hold a constant the client states for itself. A field added later is a field
this set does not name, so it fails here rather than going out unnoticed.

The agent every request carries is NFR-PRIV-003's, held in
`tests/structural/test_user_agent.py`.
"""

from __future__ import annotations

import getpass
import pathlib
import platform

from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.infrastructure.catalogue import (
    ARTIST_URL,
    GROUP_LIMIT,
    NAME_LIMIT,
    RELEASE_GROUP_URL,
    MusicBrainz,
)
from stellody.infrastructure.similarity import ALGORITHM, SIMILAR_URL, ListenBrainz

NAME = "Kate Bush"
IDENTIFIER = "4b585938-f271-45e2-b19a-91c634b5e396"
# How many similar artists are asked for. Only has to be a number here.
MOST = 10

# The one field allowed to carry an artist's name, spelled the way the
# catalogue's search syntax wraps it; the fields allowed to carry an identifier.
NAME_FIELD = "query"
NAME_AS_ASKED = f'artist:"{NAME}"'
IDENTIFIER_FIELDS = frozenset({"artist", "artist_mbids"})
# Every other field, with every value it may hold. None of these depends on
# anything the run was given, so none can carry the library or the listener.
FIXED = {
    "fmt": frozenset({"json"}),
    "limit": frozenset({str(NAME_LIMIT), str(GROUP_LIMIT)}),
    "type": frozenset({"album|ep"}),
    "inc": frozenset({"genres"}),
    "algorithm": frozenset({ALGORITHM}),
    # Where the second page starts; asked only after a full first one.
    "offset": frozenset({str(GROUP_LIMIT)}),
}
# A first page full to the limit, so the second page is asked for too.
FULL_PAGE = {"release-groups": [{"title": "t", "primary-type": "Album"}] * GROUP_LIMIT}
# Which fields each address may carry. The identifier stands in the path of the
# one address that takes it there, which is still the identifier and no more.
ALLOWED = {
    ARTIST_URL: frozenset({"query", "fmt", "limit"}),
    RELEASE_GROUP_URL: frozenset({"artist", "type", "inc", "fmt", "limit", "offset"}),
    f"{ARTIST_URL}/{IDENTIFIER}": frozenset({"inc", "fmt"}),
    SIMILAR_URL: frozenset({"artist_mbids", "algorithm"}),
}


class Recording:
    """A fetcher that keeps every question and answers each with nothing."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, dict[str, str]]] = []

    def json(
        self,
        address: str,
        parameters: dict[str, str],
        wanted: Wanted = always_wanted,
    ) -> object:
        """Keep the address with its fields; one full page, then nothing."""
        first = not self.asked
        self.asked.append((address, dict(parameters)))
        return FULL_PAGE if address == RELEASE_GROUP_URL and first else {}


def asked() -> list[tuple[str, dict[str, str]]]:
    """Every question a run can put to either catalogue, once each."""
    fetch = Recording()
    catalogue = MusicBrainz(fetch)
    catalogue.albums_of(IDENTIFIER)
    catalogue.identify(NAME)
    catalogue.genres_of(IDENTIFIER)
    ListenBrainz(fetch).similar_to(IDENTIFIER, MOST)
    return fetch.asked


def about_this_machine() -> tuple[str, ...]:
    """What would identify the listener or the machine, were it sent."""
    home = pathlib.Path.home()
    said = (platform.node(), getpass.getuser(), str(home), home.as_posix())
    return tuple(word for word in said if word)


def test_every_address_asked_is_one_the_allowed_set_names() -> None:
    """A new question is a new entry above, made in front of somebody."""
    assert {address for address, _fields in asked()} == set(ALLOWED)


def test_every_field_sent_is_one_its_address_is_allowed() -> None:
    """NFR-PRIV-002's fixed set: a field nobody listed fails here."""
    for address, fields in asked():
        extra = set(fields) - ALLOWED[address]
        assert not extra, f"{address} sends fields nobody allowed: {sorted(extra)}"


def test_a_field_holds_the_name_the_identifier_or_a_constant() -> None:
    """NFR-PRIV-001: nothing goes out beyond names and identifiers."""
    for address, fields in asked():
        for field, value in fields.items():
            if field == NAME_FIELD:
                assert value == NAME_AS_ASKED, (address, field, value)
            elif field in IDENTIFIER_FIELDS:
                assert value == IDENTIFIER, (address, field, value)
            else:
                assert value in FIXED.get(field, frozenset()), (address, field, value)


def test_nothing_sent_names_the_listener_or_the_machine() -> None:
    """NFR-PRIV-002, read against this machine's own name, user and home."""
    for address, fields in asked():
        sent = " ".join((address, *fields.values())).casefold()
        for word in about_this_machine():
            assert word.casefold() not in sent, (address, word)
