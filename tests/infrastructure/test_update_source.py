"""Reading the newest release from GitHub, without ever opening a connection.

Every test here stands in front of the opener, so the suite is as offline as
the rest of Stellody is. What is being guarded is not the network: it is that
a document from the internet cannot make this module raise; nor can it hand a
dialog an address the release never carried.
"""

from __future__ import annotations

import json
from typing import Self

import pytest

from stellody.infrastructure.update_source import (
    ACCEPT_HEADER,
    RELEASES_URL,
    TIMEOUT_SECONDS,
    GitHubReleases,
)

PAGE = "https://github.com/oernster/stellody/releases/tag/v0.6.0"


class Answer:
    """What urlopen hands back: a context manager over some bytes."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_unused) -> bool:
        return False

    def read(self) -> bytes:
        """The whole body, as the real answer gives it."""
        return self._body


class Opener:
    """An opener that answers with one prepared body, recording the ask."""

    def __init__(self, payload) -> None:
        self._body = payload if isinstance(payload, bytes) else json.dumps(payload)
        self.request = None
        self.timeout = None

    def __call__(self, request, timeout=None):
        self.request = request
        self.timeout = timeout
        body = self._body
        return Answer(body if isinstance(body, bytes) else body.encode("utf-8"))


class Refusing:
    """An opener that fails the way an unreachable host does."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def __call__(self, request, timeout=None):
        raise self._error


def _payload(**changes) -> dict:
    """A well formed release document, with any field overridden."""
    body = {
        "tag_name": "v0.6.0",
        "html_url": PAGE,
        "assets": [
            {
                "name": "StellodySetup.exe",
                "browser_download_url": "https://example.test/win",
            }
        ],
    }
    body.update(changes)
    return body


class TestAskingProperly:
    def test_it_asks_the_releases_endpoint_for_this_repository(self) -> None:
        """The URL bakes in the repository, so a wrong one checks another app."""
        opener = Opener(_payload())
        GitHubReleases(opener).latest_release()
        assert opener.request.full_url == RELEASES_URL
        assert "stellody" in RELEASES_URL

    def test_it_names_the_api_version_it_expects_and_waits_only_so_long(self) -> None:
        opener = Opener(_payload())
        GitHubReleases(opener).latest_release()
        assert opener.request.get_header("Accept") == ACCEPT_HEADER
        assert opener.timeout == TIMEOUT_SECONDS


class TestWhatComesBack:
    def test_a_release_is_read_with_its_page_and_its_files(self) -> None:
        release = GitHubReleases(Opener(_payload())).latest_release()
        assert release is not None
        assert release.version == "v0.6.0"
        assert release.page_url == PAGE
        assert release.assets[0].name == "StellodySetup.exe"
        assert release.assets[0].download_url == "https://example.test/win"

    def test_a_release_carrying_no_files_is_still_a_release(self) -> None:
        release = GitHubReleases(Opener(_payload(assets=[]))).latest_release()
        assert release is not None
        assert release.assets == ()

    def test_a_missing_page_leaves_the_page_empty_rather_than_absent(self) -> None:
        body = _payload()
        del body["html_url"]
        release = GitHubReleases(Opener(body)).latest_release()
        assert release is not None
        assert release.page_url == ""


class TestNothingUsableComesBack:
    @pytest.mark.parametrize("error", [OSError("unreachable"), ValueError("nonsense")])
    def test_a_refusal_is_no_release_rather_than_a_crash(self, error) -> None:
        assert GitHubReleases(Refusing(error)).latest_release() is None

    def test_a_body_that_is_not_json_is_no_release(self) -> None:
        assert (
            GitHubReleases(Opener(b"<html>rate limited</html>")).latest_release()
            is None
        )

    @pytest.mark.parametrize("body", [[], "a string", 7, None])
    def test_a_body_that_is_not_a_document_is_no_release(self, body) -> None:
        assert GitHubReleases(Opener(body)).latest_release() is None

    @pytest.mark.parametrize("tag", ["", None, 7, ["v1"]])
    def test_a_release_with_no_readable_tag_is_no_release(self, tag) -> None:
        """Without a version there is nothing to compare, so there is nothing."""
        assert GitHubReleases(Opener(_payload(tag_name=tag))).latest_release() is None

    @pytest.mark.parametrize("assets", [None, "none", 7, {}])
    def test_a_release_whose_files_are_not_a_list_carries_none(self, assets) -> None:
        release = GitHubReleases(Opener(_payload(assets=assets))).latest_release()
        assert release is not None
        assert release.assets == ()

    @pytest.mark.parametrize(
        "entry",
        [
            "not a mapping",
            {"name": "only.exe"},
            {"browser_download_url": "https://example.test/x"},
            {"name": "", "browser_download_url": "https://example.test/x"},
            {"name": "x.exe", "browser_download_url": ""},
            {"name": 7, "browser_download_url": "https://example.test/x"},
        ],
    )
    def test_a_malformed_file_is_dropped_rather_than_offered(self, entry) -> None:
        """A dialog offers to open one of these, so half an entry is no entry."""
        release = GitHubReleases(Opener(_payload(assets=[entry]))).latest_release()
        assert release is not None
        assert release.assets == ()

    def test_the_good_files_survive_the_bad_ones(self) -> None:
        good = {
            "name": "stellody.flatpak",
            "browser_download_url": "https://example.test/linux",
        }
        release = GitHubReleases(
            Opener(_payload(assets=["rubbish", good]))
        ).latest_release()
        assert release is not None
        assert len(release.assets) == 1
        assert release.assets[0].name == "stellody.flatpak"
