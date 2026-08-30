"""Looking an album up in MusicBrainz and its art up in the Cover Art Archive.

The one module in Stellody that opens a connection. It is reached only when a
listener asks for a cover, never on a scan and never on a draw.

**Two services, because they are two questions.** MusicBrainz knows which
releases an album has; the Cover Art Archive knows which pictures a release
has. A release with no art answers 404 there, which is an ordinary answer
rather than a failure: it means look at the next release.

**The terms are honoured rather than hoped for.** MusicBrainz asks for an
identifying user agent and no more than one request a second; it answers 503
when that is ignored. Measured on 2026-08-30: two searches sent back to back
were refused exactly that way. So every request goes through one gate that
waits its turn; the user agent names the application and a way to reach its
author.

**What the listing does and does not say.** Measured on the same day, an image
in the archive's listing carries `image`, `thumbnails` at 250, 500 and 1200,
`front`, `back` and `types`. It does NOT carry the pixel size of the original,
so the largest thumbnail offered is what a candidate can honestly claim.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from stellody.domain.cover_choice import THUMBNAIL_SIZES, CoverCandidate
from stellody.shared.version import APP_NAME, __version__

SEARCH_URL = "https://musicbrainz.org/ws/2/release"
ART_URL = "https://coverartarchive.org/release"
# What the terms mean by contact: a URL or an address whoever runs the service
# can reach the author of the application at, sent with every request so a
# misbehaving client can be told about rather than merely blocked. The
# project's own site, since the author's email is nobody else's business.
CONTACT = "https://stellody.com"
USER_AGENT = f"{APP_NAME}/{__version__} ( {CONTACT} )"
# One request a second is what the terms ask for. A tenth over it is not
# generosity; it is the margin that stops a clock rounding down into a refusal.
REQUEST_GAP_S = 1.1
TIMEOUT_S = 20
# Enough releases that a reissue with the art is reached, few enough that the
# wait stays a wait rather than a walk away. Each one is a second.
RELEASE_LIMIT = 8
IMAGE_TIMEOUT_S = 30


class _Gate:
    """Lets one request through at a time, no faster than the terms allow."""

    def __init__(self, gap_s: float = REQUEST_GAP_S) -> None:
        self._gap_s = gap_s
        self._last = 0.0

    def wait(self) -> None:
        """Hold until this request is allowed to go."""
        due = self._last + self._gap_s - time.monotonic()
        if due > 0:
            time.sleep(due)
        self._last = time.monotonic()


def _release_query(artist: str, album: str) -> str:
    """The search MusicBrainz is asked, with both terms quoted as phrases."""
    phrase = f'artist:"{_escaped(artist)}" AND release:"{_escaped(album)}"'
    return urllib.parse.urlencode(
        {"query": phrase, "fmt": "json", "limit": RELEASE_LIMIT}
    )


def _escaped(text: str) -> str:
    """A term safe to sit inside a quoted Lucene phrase."""
    return text.replace("\\", " ").replace('"', " ")


def _largest(thumbnails: dict) -> int:
    """The biggest size the archive will serve; zero when it names none."""
    for size in THUMBNAIL_SIZES:
        if thumbnails.get(str(size)):
            return size
    return 0


def _preview(thumbnails: dict) -> str:
    """The address of a picture small enough to draw in a grid."""
    for size in reversed(THUMBNAIL_SIZES):
        address = thumbnails.get(str(size))
        if address:
            return str(address)
    return ""


def _candidates_from(images: list, release: str) -> list[CoverCandidate]:
    """Every picture in one release's listing that can be shown and fetched."""
    made = []
    for image in images:
        thumbnails = image.get("thumbnails") or {}
        preview = _preview(thumbnails)
        full = image.get("image") or ""
        if not preview or not full:
            continue
        made.append(
            CoverCandidate(
                release=release,
                image_url=str(full),
                thumbnail_url=preview,
                largest_px=_largest(thumbnails),
                is_front=bool(image.get("front")),
            )
        )
    return made


def _release_label(release: dict) -> str:
    """What a release is called in the chooser: its title, year and country."""
    parts = [str(release.get("title") or "")]
    for field in ("date", "country"):
        value = release.get(field)
        if value:
            parts.append(str(value))
    return "  ".join(part for part in parts if part)


class ArchiveCovers:
    """Searches MusicBrainz, then reads the Cover Art Archive for pictures."""

    def __init__(self, gate: _Gate | None = None, opener=None) -> None:
        self._gate = gate if gate is not None else _Gate()
        self._opener = opener if opener is not None else urllib.request.urlopen

    def search(self, artist: str, album: str) -> tuple[CoverCandidate, ...]:
        """The pictures on offer for this album; empty when there are none."""
        found = self._json(f"{SEARCH_URL}?{_release_query(artist, album)}")
        if found is None:
            return ()
        gathered: list[CoverCandidate] = []
        for release in found.get("releases") or ():
            mbid = release.get("id")
            if not mbid:
                continue
            listing = self._json(f"{ART_URL}/{mbid}")
            if listing is None:
                continue
            gathered.extend(
                _candidates_from(listing.get("images") or [], _release_label(release))
            )
        return tuple(gathered)

    def fetch(self, url: str) -> bytes | None:
        """The bytes of one picture; None when it cannot be had.

        Not gated: the pictures come from the archive's own store rather than
        from the search, while a grid of a dozen thumbnails at a second each
        is a chooser that opens a dozen seconds late.
        """
        try:
            with self._opener(_asking(url), timeout=IMAGE_TIMEOUT_S) as answer:
                return bytes(answer.read())
        except (urllib.error.URLError, OSError, ValueError):
            return None

    def _json(self, url: str) -> dict | None:
        """One gated request, read as JSON; None when there is nothing to read.

        A 404 from the archive means this release carries no art, which is an
        answer rather than a failure. It looks the same from here as a service
        that is down: in both cases there is nothing to offer, so the next
        release is what to try.
        """
        self._gate.wait()
        try:
            with self._opener(_asking(url), timeout=TIMEOUT_S) as answer:
                return dict(json.loads(answer.read()))
        except (urllib.error.URLError, OSError, ValueError, TypeError):
            return None


def _asking(url: str) -> urllib.request.Request:
    """One request, naming the application and what it will accept."""
    return urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
