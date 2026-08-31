"""Asking whether a newer Stellody has been published; what to offer if so.

Stellody is local-first, so this is the one thing it ever asks the world about
itself. It is a question with three answers and they are kept apart on purpose:
there is a newer one, you have the newest one, nobody could be reached. The
third is not a failure to report on its own; it is only worth saying out loud
when a listener asked the question rather than when the clock did.

**A version that cannot be read is not newer.** Every comparison here is
between dotted runs of digits; anything that does not parse that way loses
rather than raises. A tag somebody typed wrongly must never be able to tell a
listener their working copy is out of date.

**What is offered is chosen here, not in the dialog.** Which file suits this
machine is a decision about the release, so it belongs beside the release. The
dialog is left with a URL to open, else nothing and the release page instead.
"""

from __future__ import annotations

from stellody.application.ports import ReleaseSource
from stellody.application.values import ReleaseAsset, UpdateStatus

WINDOWS = "windows"
MACOS = "macos"
LINUX = "linux"
# What a release names the file for each platform. Matched on the end of the
# name and case-insensitively, since a release is written by hand.
ASSET_SUFFIXES: dict[str, str] = {
    WINDOWS: ".exe",
    MACOS: ".dmg",
    LINUX: ".flatpak",
}
# What sys.platform calls the two it names outright. Everything else is a
# unix of some kind; the one Stellody ships for is Linux.
PLATFORM_NAMES: dict[str, str] = {"win32": WINDOWS, "darwin": MACOS}
VERSION_PREFIX = "v"


def _parts(version: str) -> tuple[int, ...]:
    """A version as numbers to compare; empty when it does not read as one."""
    cleaned = version.strip()
    if cleaned[:1].lower() == VERSION_PREFIX:
        cleaned = cleaned[1:]
    pieces = cleaned.split(".")
    numbers: list[int] = []
    for piece in pieces:
        if not piece.isdigit():
            return ()
        numbers.append(int(piece))
    return tuple(numbers)


def is_newer(latest: str, current: str) -> bool:
    """Whether the published version is ahead of the one running.

    Either side unreadable answers False. That way round deliberately: the
    cost of missing an update is that somebody updates a day later, while the
    cost of inventing one is telling somebody their copy is stale when it is
    not. Runs of different length compare as though the shorter were padded,
    so 1.2 and 1.2.0 are the same version rather than two.
    """
    ahead = _parts(latest)
    behind = _parts(current)
    if not ahead or not behind:
        return False
    width = max(len(ahead), len(behind))
    padded_ahead = ahead + (0,) * (width - len(ahead))
    padded_behind = behind + (0,) * (width - len(behind))
    return padded_ahead > padded_behind


def platform_key_for(platform_name: str) -> str:
    """Which file this machine wants, from what sys.platform calls it."""
    return PLATFORM_NAMES.get(platform_name, LINUX)


def select_asset_url(assets: tuple[ReleaseAsset, ...], platform_key: str) -> str:
    """The download for this platform; empty when the release offers none.

    Empty rather than the first thing on offer: handing a Windows installer to
    somebody on Linux is worse than sending them to the release page, where
    they can see everything the release actually carries.
    """
    suffix = ASSET_SUFFIXES.get(platform_key, "")
    if not suffix:
        return ""
    for asset in assets:
        if asset.name.lower().endswith(suffix):
            return asset.download_url
    return ""


class UpdateService:
    """One update check, with the platform and the running version fixed."""

    def __init__(
        self, source: ReleaseSource, current_version: str, platform_key: str
    ) -> None:
        self._source = source
        self._current = current_version
        self._platform_key = platform_key

    def check(self, skipped_version: str = "") -> UpdateStatus:
        """Ask, then say what it means for this machine.

        A skipped version is reported as read rather than as unreachable, so a
        listener who asks the question themselves is still told what the
        newest one is; it simply is not offered as an update. That is the
        difference between silencing a prompt and pretending nothing is there.
        """
        release = self._source.latest_release()
        if release is None:
            return UpdateStatus(current=self._current)
        available = is_newer(release.version, self._current) and (
            release.version != skipped_version
        )
        return UpdateStatus(
            current=self._current,
            latest=release.version,
            update_available=available,
            download_url=select_asset_url(release.assets, self._platform_key),
            page_url=release.page_url,
        )
