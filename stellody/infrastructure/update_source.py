"""Reading Stellody's newest published release from GitHub.

The second module in Stellody that can open a connection. The whole of what it
does is read one small document about Stellody itself. It sends
nothing: no library, no listening, no identifier, not even a version. The
answer is compared on this machine, so the request says only that somebody,
somewhere, opened a music player.

**The endpoint is the guard.** `releases/latest` returns only a published
release: never a draft and never a prerelease. So a tag pushed while something
is half built is invisible here by the endpoint's own contract rather than by
this module remembering to filter it out. Nothing re-checks those flags
afterwards, because a check written twice is a check that can disagree.

**Every failure is the same failure.** No network, a refusal, a rate limit, a
body that is not the shape it should be: all of them answer None. The caller
has no use for the difference and a listener has less, so the distinction is
dropped here rather than carried upward to be ignored later.

**What goes out is stated, not left to the library.** The request carries a
fixed URL, an Accept header naming the API version plus a user agent that is
the product name alone. urllib would otherwise send `Python-urllib/<version>`,
which names the machine's Python; nothing here names the listener, the library
or the version Stellody is running.

**It goes nowhere else on anybody's say so.** A redirect is followed only to
the GitHub API over HTTPS; one to any other host or scheme is refused and read
as no release, the same as a source that could not be reached. Measured on
loopback before this was added: a 302 to another host was followed with the
headers re-sent and the answer believed.

**Nothing is trusted about the answer.** Every field is checked for its type
before it is used and a malformed asset is dropped rather than carried, since
this is a document from the internet being handed to a dialog that will offer
to open one of its addresses.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from stellody.application.values import ReleaseAsset, ReleaseInfo
from stellody.infrastructure.reach import (
    GITHUB_API_HOST,
    GITHUB_REACH,
    Reach,
    origin,
)
from stellody.shared.version import APP_NAME

RELEASES_URL = f"{origin(GITHUB_API_HOST)}/repos/oernster/stellody/releases/latest"
ACCEPT_HEADER = "application/vnd.github+json"
# Stated rather than left to urllib, which would otherwise send its own
# `Python-urllib/<version>`: that says which Python the machine runs, which
# is a fact about the listener's computer and no business of a version
# check. The product name is what GitHub asks callers to send and is all
# this needs to be. The running version is deliberately NOT in it: what
# Stellody has is decided here after the answer arrives, so sending it
# would tell the other end something it has no use for.
USER_AGENT = APP_NAME
# Long enough for a slow answer, short enough that nobody waits on it. The
# check runs off the interface thread, so this only bounds that thread's life.
TIMEOUT_SECONDS = 5.0
TAG_FIELD = "tag_name"
PAGE_FIELD = "html_url"
ASSETS_FIELD = "assets"
ASSET_NAME_FIELD = "name"
ASSET_URL_FIELD = "browser_download_url"

Opener = Callable[..., object]


def admitted(reach: Reach, url: str) -> bool:
    """Whether an address is one this reach may go to."""
    parts = urllib.parse.urlsplit(url)
    return reach.admits(parts.scheme, parts.hostname or "")


class PinnedRedirects(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to a host the client was given.

    urllib follows a redirect to anywhere by default, sending the same headers
    there and handing back whatever it said. Measured on loopback: the update
    check and the cover search both did. A redirect elsewhere is refused as an
    unreachable source, which is how each client already reports one.

    Here because the update check and the cover search both open through
    urllib and a judge written twice is two judges the day one is edited; the
    cover search borrows it rather than a fifth module being permitted to hold
    networking machinery.
    """

    def __init__(self, reach: Reach) -> None:
        super().__init__()
        self._reach = reach

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """The onward request; a refusal where it leaves the reach."""
        if not admitted(self._reach, newurl):
            fp.close()
            raise urllib.error.URLError(f"redirect refused: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def pinned_opener(reach: Reach) -> Opener:
    """An opener that follows redirects only within this reach."""
    return urllib.request.build_opener(PinnedRedirects(reach)).open


def _text(payload: dict, field: str) -> str:
    """One string field, empty when it is missing or is not a string."""
    value = payload.get(field)
    return value if isinstance(value, str) else ""


def _assets(payload: dict) -> tuple[ReleaseAsset, ...]:
    """Every downloadable file the release names, malformed entries dropped."""
    listed = payload.get(ASSETS_FIELD)
    if not isinstance(listed, list):
        return ()
    found: list[ReleaseAsset] = []
    for entry in listed:
        if not isinstance(entry, dict):
            continue
        name = _text(entry, ASSET_NAME_FIELD)
        url = _text(entry, ASSET_URL_FIELD)
        if name and url:
            found.append(ReleaseAsset(name=name, download_url=url))
    return tuple(found)


class GitHubReleases:
    """Stellody's own releases, read from the GitHub API and nothing else."""

    def __init__(
        self,
        opener: Opener | None = None,
        address: str = RELEASES_URL,
        reach: Reach = GITHUB_REACH,
    ) -> None:
        self._open = opener if opener is not None else pinned_opener(reach)
        self._address = address

    def latest_release(self) -> ReleaseInfo | None:
        """The newest published release; None when it could not be read."""
        request = urllib.request.Request(
            self._address,
            headers={"Accept": ACCEPT_HEADER, "User-Agent": USER_AGENT},
        )
        try:
            with self._open(request, timeout=TIMEOUT_SECONDS) as answer:
                payload = json.loads(answer.read().decode("utf-8"))
        except (OSError, ValueError, urllib.error.URLError):
            return None
        if not isinstance(payload, dict):
            return None
        version = _text(payload, TAG_FIELD)
        if not version:
            return None
        return ReleaseInfo(
            version=version,
            page_url=_text(payload, PAGE_FIELD),
            assets=_assets(payload),
        )
