"""Every client that leaves the machine goes only where it was told it may.

Measured on loopback before this was written: the update check, the discovery
fetcher and the cover search all followed a 302 to another host, re-sending
their headers there and trusting whatever came back; the cover fetch opened a
`file:` address as readily as a picture. So each client is handed the hosts it
may reach and a redirect anywhere else is refused, reported the way an
unreachable service already is.

The services here are real ones on the loopback address. `localhost` and
`127.0.0.1` reach the same socket while being two hosts to a client judging
where it may go, which is what makes a cross-host redirect testable without
leaving the machine. A subdomain cannot be served that way (measured: this
machine does not resolve `*.localhost`), so the archive's image hosts are
proved through the cover client's own judge, which is what the redirect
handler asks.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from stellody.application.discovery_ports import SourceUnavailable
from stellody.infrastructure.cover_search import ArchiveCovers
from stellody.infrastructure.reach import (
    COVER_REACH,
    DISCOVERY_REACH,
    GITHUB_REACH,
    Reach,
)
from stellody.infrastructure.update_source import GitHubReleases, admitted
from tests.infrastructure.fetching_support import LOOPBACK, Service, fetching

# Loopback services speak plain HTTP, so a reach for them names that scheme;
# the real reaches name only HTTPS, which the judge tests below hold them to.
PLAIN_SCHEME = "http"
LOOPBACK_REACH = Reach(hosts=frozenset({LOOPBACK}), scheme=PLAIN_SCHEME)
# Another name for the same socket, so a different host to the judge.
OTHER_NAME = "localhost"
RELEASE = {"tag_name": "v9.9.9", "html_url": "", "assets": []}
PICTURE = {"a": "picture"}


class NoWait:
    """A gate that lets everything through, so the suite does not wait."""

    def wait(self, wanted=lambda: True) -> bool:
        """Let it through unless nobody wants it."""
        return wanted()


@pytest.fixture
def services():
    """Every service a test makes, closed however that test ends."""
    made: list[Service] = []

    def make(**configured) -> Service:
        service = Service(**configured)
        made.append(service)
        return service

    yield make
    for service in made:
        service.close()


class TestTheUpdateCheck:
    def test_a_redirect_to_another_host_is_no_release(self, services) -> None:
        elsewhere = services(body=RELEASE)
        first = services(redirect_to=elsewhere.address_as(OTHER_NAME))
        checking = GitHubReleases(address=first.address, reach=LOOPBACK_REACH)
        assert checking.latest_release() is None
        assert elsewhere.asked == []

    def test_a_redirect_on_the_same_host_is_still_followed(self, services) -> None:
        moved = services(body=RELEASE)
        first = services(redirect_to=moved.address)
        checking = GitHubReleases(address=first.address, reach=LOOPBACK_REACH)
        release = checking.latest_release()
        assert release is not None
        assert release.version == RELEASE["tag_name"]


class TestTheCoverSearch:
    def _covers(self) -> ArchiveCovers:
        return ArchiveCovers(gate=NoWait(), reach=LOOPBACK_REACH)

    def test_a_picture_redirected_to_another_host_is_none(self, services) -> None:
        elsewhere = services(body=PICTURE)
        first = services(redirect_to=elsewhere.address_as(OTHER_NAME))
        assert self._covers().fetch(first.address) is None
        assert elsewhere.asked == []

    def test_a_picture_redirected_on_the_same_host_arrives(self, services) -> None:
        moved = services(body=PICTURE)
        first = services(redirect_to=moved.address)
        assert self._covers().fetch(first.address) is not None

    def test_a_picture_named_on_another_host_is_never_asked_for(self, services) -> None:
        elsewhere = services(body=PICTURE)
        assert self._covers().fetch(elsewhere.address_as(OTHER_NAME)) is None
        assert elsewhere.asked == []

    @pytest.mark.parametrize(
        "named",
        [
            "file:///C:/Windows/win.ini",
            "file:///etc/passwd",
            "http://coverartarchive.org/release/x/1.jpg",
            "ftp://archive.org/x.jpg",
        ],
    )
    def test_a_picture_the_archive_names_off_https_is_never_opened(
        self, named: str
    ) -> None:
        assert ArchiveCovers(gate=NoWait()).fetch(named) is None


class TestTheDiscoveryFetcher:
    def test_a_redirect_to_another_host_is_an_unreachable_service(
        self, application: QApplication, services
    ) -> None:
        elsewhere = services(body={"artists": []})
        first = services(redirect_to=elsewhere.address_as(OTHER_NAME))
        with pytest.raises(SourceUnavailable):
            fetching(reach=LOOPBACK_REACH).json(first.address, {"fmt": "json"})
        assert elsewhere.asked == []

    def test_a_redirect_on_the_same_host_is_still_followed(
        self, application: QApplication, services
    ) -> None:
        moved = services(body={"artists": []})
        first = services(redirect_to=moved.address)
        answer = fetching(reach=LOOPBACK_REACH).json(first.address, {"fmt": "json"})
        assert answer == {"artists": []}


class TestTheHostsEachClientMayReach:
    @pytest.mark.parametrize(
        "url",
        [
            "https://api.github.com/repos/oernster/stellody/releases/latest",
            "https://api.github.com/repositories/1/releases/latest",
        ],
    )
    def test_the_update_check_reaches_the_github_api(self, url: str) -> None:
        assert admitted(GITHUB_REACH, url)

    @pytest.mark.parametrize(
        "url",
        [
            "http://api.github.com/repos/oernster/stellody/releases/latest",
            "https://github.com/oernster/stellody",
            "https://api.github.com.example.test/x",
            "https://example.test/x",
        ],
    )
    def test_the_update_check_reaches_nothing_else(self, url: str) -> None:
        assert not admitted(GITHUB_REACH, url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://musicbrainz.org/ws/2/release?query=x",
            "https://coverartarchive.org/release/abc/1.jpg",
            "https://archive.org/download/mbid-abc/mbid-abc-1.jpg",
            "https://ia800100.us.archive.org/1/items/mbid-abc/1.jpg",
        ],
    )
    def test_the_cover_search_reaches_the_archive_and_its_stores(
        self, url: str
    ) -> None:
        assert admitted(COVER_REACH, url)

    @pytest.mark.parametrize(
        "url",
        [
            "http://ia800100.us.archive.org/1/items/mbid-abc/1.jpg",
            "https://notarchive.org/1.jpg",
            "https://archive.org.example.test/1.jpg",
            "https://ia800100.us.coverartarchive.org/1.jpg",
            "https://example.test/1.jpg",
            "file:///etc/passwd",
        ],
    )
    def test_the_cover_search_reaches_nothing_else(self, url: str) -> None:
        assert not admitted(COVER_REACH, url)

    @pytest.mark.parametrize(
        ("scheme", "host", "expected"),
        [
            ("https", "musicbrainz.org", True),
            ("https", "labs.api.listenbrainz.org", True),
            ("https", "api.listenbrainz.org", False),
            ("http", "musicbrainz.org", False),
            ("https", "beta.musicbrainz.org", False),
            ("https", "example.test", False),
        ],
    )
    def test_discovery_reaches_its_two_catalogues_alone(
        self, scheme: str, host: str, expected: bool
    ) -> None:
        assert DISCOVERY_REACH.admits(scheme, host) is expected
