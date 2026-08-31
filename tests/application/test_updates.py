"""Asking whether a newer Stellody exists; what to offer for this machine.

The comparison is the part worth guarding hardest. Every way a version string
can be wrong has to lose rather than raise, because the cost of a false answer
is asymmetric: missing an update costs somebody a day, while inventing one
tells somebody their working copy is stale when it is not.
"""

from __future__ import annotations

import pytest

from stellody.application.updates import (
    LINUX,
    MACOS,
    WINDOWS,
    UpdateService,
    is_newer,
    platform_key_for,
    select_asset_url,
)
from stellody.application.values import ReleaseAsset, ReleaseInfo

CURRENT = "0.5.0"


class OneRelease:
    """A source that always answers with the release it was given."""

    def __init__(self, release: ReleaseInfo | None) -> None:
        self._release = release
        self.asked = 0

    def latest_release(self) -> ReleaseInfo | None:
        """The release this fake stands for; None when it stands for nothing."""
        self.asked += 1
        return self._release


def _release(version: str, assets: tuple[ReleaseAsset, ...] = ()) -> ReleaseInfo:
    """A published release at some version, with whatever files it carries."""
    return ReleaseInfo(
        version=version,
        page_url="https://github.com/oernster/stellody/releases/tag/x",
        assets=assets,
    )


class TestWhichVersionIsNewer:
    @pytest.mark.parametrize(
        "latest,current",
        [
            ("0.6.0", "0.5.0"),
            ("1.0.0", "0.9.9"),
            ("0.5.1", "0.5.0"),
            ("v0.6.0", "0.5.0"),
            ("V0.6.0", "0.5.0"),
            ("  0.6.0  ", "0.5.0"),
            ("0.5.0.1", "0.5.0"),
        ],
    )
    def test_a_higher_version_is_newer(self, latest, current) -> None:
        assert is_newer(latest, current)

    @pytest.mark.parametrize(
        "latest,current",
        [
            ("0.5.0", "0.5.0"),
            ("0.4.0", "0.5.0"),
            ("v0.5.0", "0.5.0"),
            ("0.5", "0.5.0"),
            ("0.5.0", "0.5"),
        ],
    )
    def test_the_same_or_older_is_not(self, latest, current) -> None:
        """A shorter run compares as though it were padded, so 0.5 is 0.5.0."""
        assert not is_newer(latest, current)

    @pytest.mark.parametrize(
        "latest,current",
        [
            ("", "0.5.0"),
            ("0.5.0", ""),
            ("nightly", "0.5.0"),
            ("0.6.0-rc1", "0.5.0"),
            ("0.6.0", "unreleased"),
            ("...", "0.5.0"),
            ("v", "0.5.0"),
        ],
    )
    def test_anything_unreadable_loses_rather_than_raises(
        self, latest, current
    ) -> None:
        """A tag somebody typed wrongly must never claim to be an update."""
        assert not is_newer(latest, current)


class TestWhichFileThisMachineWants:
    @pytest.mark.parametrize(
        "platform_name,expected",
        [
            ("win32", WINDOWS),
            ("darwin", MACOS),
            ("linux", LINUX),
            ("freebsd13", LINUX),
            ("", LINUX),
        ],
    )
    def test_the_platform_is_read_from_its_own_name(
        self, platform_name, expected
    ) -> None:
        """Everything that is not Windows or macOS is the one Linux build."""
        assert platform_key_for(platform_name) == expected

    def test_the_file_for_this_platform_is_the_one_chosen(self) -> None:
        assets = (
            ReleaseAsset("StellodySetup.exe", "https://example.test/win"),
            ReleaseAsset("Stellody.dmg", "https://example.test/mac"),
            ReleaseAsset("stellody.flatpak", "https://example.test/linux"),
        )
        assert select_asset_url(assets, WINDOWS) == "https://example.test/win"
        assert select_asset_url(assets, MACOS) == "https://example.test/mac"
        assert select_asset_url(assets, LINUX) == "https://example.test/linux"

    def test_the_suffix_is_matched_whatever_its_case(self) -> None:
        """A release is written by hand, so its file names are not reliable."""
        assets = (ReleaseAsset("StellodySetup.EXE", "https://example.test/win"),)
        assert select_asset_url(assets, WINDOWS) == "https://example.test/win"

    def test_a_release_with_nothing_for_this_machine_offers_nothing(self) -> None:
        """Nothing rather than the first file: a Windows installer is no use
        to somebody on Linux; the release page lists everything anyway."""
        assets = (ReleaseAsset("StellodySetup.exe", "https://example.test/win"),)
        assert select_asset_url(assets, LINUX) == ""

    def test_a_release_carrying_no_files_offers_nothing(self) -> None:
        assert select_asset_url((), WINDOWS) == ""

    def test_a_platform_nobody_builds_for_offers_nothing(self) -> None:
        assets = (ReleaseAsset("stellody.flatpak", "https://example.test/linux"),)
        assert select_asset_url(assets, "plan9") == ""


class TestTheCheckItself:
    def test_a_newer_release_is_offered_with_its_file_and_its_page(self) -> None:
        assets = (ReleaseAsset("StellodySetup.exe", "https://example.test/win"),)
        service = UpdateService(OneRelease(_release("0.6.0", assets)), CURRENT, WINDOWS)
        status = service.check()
        assert status.update_available
        assert status.latest == "0.6.0"
        assert status.current == CURRENT
        assert status.download_url == "https://example.test/win"
        assert status.page_url.endswith("/tag/x")

    def test_the_same_version_is_read_but_not_offered(self) -> None:
        service = UpdateService(OneRelease(_release(CURRENT)), CURRENT, WINDOWS)
        status = service.check()
        assert status.reached
        assert not status.update_available

    def test_a_source_that_answers_nothing_is_not_up_to_date(self) -> None:
        """Unreachable and up to date are different answers, said differently."""
        service = UpdateService(OneRelease(None), CURRENT, WINDOWS)
        status = service.check()
        assert not status.reached
        assert not status.update_available
        assert status.current == CURRENT

    def test_a_skipped_version_is_read_but_never_offered(self) -> None:
        """Skipping silences the prompt rather than the answer."""
        service = UpdateService(OneRelease(_release("0.6.0")), CURRENT, WINDOWS)
        status = service.check(skipped_version="0.6.0")
        assert status.reached
        assert status.latest == "0.6.0"
        assert not status.update_available

    def test_the_release_after_a_skipped_one_is_offered_normally(self) -> None:
        service = UpdateService(OneRelease(_release("0.7.0")), CURRENT, WINDOWS)
        assert service.check(skipped_version="0.6.0").update_available

    def test_the_source_is_asked_once_a_check(self) -> None:
        source = OneRelease(_release("0.6.0"))
        service = UpdateService(source, CURRENT, WINDOWS)
        service.check()
        service.check()
        assert source.asked == 2
