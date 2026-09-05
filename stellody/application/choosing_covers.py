"""Offering an album some cover art, then keeping the one that was chosen.

**Nothing happens without being asked.** Stellody opens no connection of its
own; this is the one path that reaches outward and it runs only when a
listener asks it to. Somebody who never uses it runs an application that still
touches nothing; a structural test says so rather than a README.

**The listener chooses, because the application cannot.** Measured across the
reference library, not one file carries a MusicBrainz identifier, one carries a
DISCID and four carry an ISRC. A lookup therefore has nothing exact to match on
and falls back to searching by artist and title, which can find the wrong
release without knowing that it has. Showing what came back and letting
somebody pick turns a silent defect into an ordinary choice.

**A failure changes nothing.** A search that cannot reach anywhere comes back
empty and a fetch that fails keeps nothing, so the album is exactly as it was.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from stellody.application.ports import ArtworkPort
from stellody.domain.cover_choice import CoverCandidate, CoverOffer, ordered
from stellody.domain.identity import AlbumIdentity


def always_wanted() -> bool:
    """Nobody has asked for this to stop, which is the ordinary case.

    The default answer, so a caller with nothing to cancel says nothing about
    cancelling. Named rather than written as a lambda at four call sites: it
    is one fact about how this is asked for, so it is stated once.
    """
    return True


# Asked between the slow parts of a lookup, answering False the moment nobody
# is waiting for the result any more. It is a question rather than a flag
# because what it reads belongs to the caller: the worker knows it was
# cancelled and nothing below it should have to be told twice.
Wanted = Callable[[], bool]


class CoverSearchPort(Protocol):
    """Looks an album up somewhere outside and fetches a picture.

    The ONLY port that reaches the network. It lives here rather than among
    the rest because this service is the only thing that may hold one: a port
    kept beside its single caller cannot be reached for by accident from the
    other end of the application.
    """

    def search(
        self, artist: str, album: str, wanted: Wanted = always_wanted
    ) -> CoverOffer:
        """The pictures on offer for this album, plus whether it was answered.

        `wanted` is asked between the slow parts, so a search nobody is
        waiting for stops there rather than running to its own timeout.

        Slow, then able to fail. A lookup that fails comes back empty rather
        than raising, since nothing was changed either way. It does say which
        kind of empty it is: a service that refused to answer has made no claim
        about this album, so reporting it as an album with no art anywhere is a
        claim the search never made.
        """
        ...

    def fetch(self, url: str, wanted: Wanted = always_wanted) -> bytes | None:
        """The bytes of one picture; None when it cannot be had, None too as
        soon as nobody wants it."""
        ...


class ChooseCover:
    """Offers an album some cover art and keeps whichever is chosen."""

    def __init__(self, search: CoverSearchPort, artwork: ArtworkPort) -> None:
        self._search = search
        self._artwork = artwork

    def offer(
        self, identity: AlbumIdentity, wanted: Wanted = always_wanted
    ) -> CoverOffer:
        """What is on offer for this album, fronts first, largest first.

        Slow: it goes to the network. It belongs off the interface thread.

        Nothing guards against an album with no artist or no title, because an
        identity refuses to be built without both. A guard against a state the
        type forbids is a branch no test can reach honestly.
        """
        found = self._search.search(identity.album_artist, identity.title, wanted)
        return CoverOffer(ordered(found.candidates), refused=found.refused)

    def accept(
        self, key: str, candidate: CoverCandidate, wanted: Wanted = always_wanted
    ) -> bytes | None:
        """Fetch the chosen picture and keep it for this album.

        The kept copy comes back so the caller can draw it at once rather than
        asking the store for what it has just been handed. A fetch that fails
        keeps nothing and answers None, leaving the album as it was.
        """
        data = self._search.fetch(candidate.image_url, wanted)
        if not data:
            return None
        return self._artwork.keep_chosen(key, data)

    def preview(
        self, candidate: CoverCandidate, wanted: Wanted = always_wanted
    ) -> bytes | None:
        """The small copy the chooser draws; None when it cannot be had.

        A thumbnail rather than the picture itself, because a release can
        carry a dozen images and a chooser that downloads all of them at full
        size to show a grid of squares is a chooser nobody waits for.
        """
        return self._search.fetch(candidate.thumbnail_url, wanted)
