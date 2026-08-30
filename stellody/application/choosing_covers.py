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

from typing import Protocol

from stellody.application.ports import ArtworkPort
from stellody.domain.cover_choice import CoverCandidate, ordered
from stellody.domain.identity import AlbumIdentity


class CoverSearchPort(Protocol):
    """Looks an album up somewhere outside and fetches a picture.

    The ONLY port that reaches the network. It lives here rather than among
    the rest because this service is the only thing that may hold one: a port
    kept beside its single caller cannot be reached for by accident from the
    other end of the application.
    """

    def search(self, artist: str, album: str) -> tuple[CoverCandidate, ...]:
        """The pictures on offer for this album; empty when there are none.

        Slow, then able to fail. A lookup that fails comes back empty rather
        than raising: that nothing was changed is what the caller needs to
        know; there is nothing useful for it to do with a reason.
        """
        ...

    def fetch(self, url: str) -> bytes | None:
        """The bytes of one picture; None when it cannot be had."""
        ...


class ChooseCover:
    """Offers an album some cover art and keeps whichever is chosen."""

    def __init__(self, search: CoverSearchPort, artwork: ArtworkPort) -> None:
        self._search = search
        self._artwork = artwork

    def offer(self, identity: AlbumIdentity) -> tuple[CoverCandidate, ...]:
        """What is on offer for this album, fronts first, largest first.

        Slow: it goes to the network. It belongs off the interface thread.

        Nothing guards against an album with no artist or no title, because an
        identity refuses to be built without both. A guard against a state the
        type forbids is a branch no test can reach honestly.
        """
        return ordered(self._search.search(identity.album_artist, identity.title))

    def accept(self, key: str, candidate: CoverCandidate) -> bytes | None:
        """Fetch the chosen picture and keep it for this album.

        The kept copy comes back so the caller can draw it at once rather than
        asking the store for what it has just been handed. A fetch that fails
        keeps nothing and answers None, leaving the album as it was.
        """
        data = self._search.fetch(candidate.image_url)
        if not data:
            return None
        return self._artwork.keep_chosen(key, data)

    def preview(self, candidate: CoverCandidate) -> bytes | None:
        """The small copy the chooser draws; None when it cannot be had.

        A thumbnail rather than the picture itself, because a release can
        carry a dozen images and a chooser that downloads all of them at full
        size to show a grid of squares is a chooser nobody waits for.
        """
        return self._search.fetch(candidate.thumbnail_url)
