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

**Nothing is trusted about the answer.** Every field is checked for its type
before it is used and a malformed asset is dropped rather than carried, since
this is a document from the internet being handed to a dialog that will offer
to open one of its addresses.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from stellody.application.values import ReleaseAsset, ReleaseInfo

RELEASES_URL = "https://api.github.com/repos/oernster/stellody/releases/latest"
ACCEPT_HEADER = "application/vnd.github+json"
# Long enough for a slow answer, short enough that nobody waits on it. The
# check runs off the interface thread, so this only bounds that thread's life.
TIMEOUT_SECONDS = 5.0
TAG_FIELD = "tag_name"
PAGE_FIELD = "html_url"
ASSETS_FIELD = "assets"
ASSET_NAME_FIELD = "name"
ASSET_URL_FIELD = "browser_download_url"

Opener = Callable[..., object]


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

    def __init__(self, opener: Opener | None = None) -> None:
        self._open = opener if opener is not None else urllib.request.urlopen

    def latest_release(self) -> ReleaseInfo | None:
        """The newest published release; None when it could not be read."""
        request = urllib.request.Request(
            RELEASES_URL, headers={"Accept": ACCEPT_HEADER}
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
