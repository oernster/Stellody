"""Where each client that leaves the machine is allowed to go.

Three clients reach past this machine and each was written to ask one or two
named services. Nothing held them to it once a service answered: measured on
loopback, the update check, the discovery fetcher and the cover search all
followed a redirect to another host, sending their headers along and trusting
what came back. So each client is handed the hosts it may reach and a redirect
to anywhere else is refused.

**One home for every host.** The addresses the clients ask are built from the
names below, so a host cannot be asked in one place and left out of the set
that judges a redirect in another.

Nothing here opens a connection or parses an address. It holds names and says
whether a scheme and a host are among them; each client reads the address in
its own terms, since the modules that can hold networking machinery are
counted by the offline structural test.
"""

from __future__ import annotations

from dataclasses import dataclass

SECURE_SCHEME = "https"
GITHUB_API_HOST = "api.github.com"
MUSICBRAINZ_HOST = "musicbrainz.org"
LISTENBRAINZ_LABS_HOST = "labs.api.listenbrainz.org"
COVER_ART_HOST = "coverartarchive.org"
# The Internet Archive, which is where the Cover Art Archive keeps its files.
# A picture asked of the Cover Art Archive is redirected to archive.org, which
# hands it on to whichever of its storage hosts holds it; those are named like
# `ia800100.us.archive.org` and change from file to file. So the archive is
# admitted with its subdomains rather than host by host.
ARCHIVE_HOST = "archive.org"


def origin(host: str) -> str:
    """The secure address of a host, for a client to build its URLs from."""
    return f"{SECURE_SCHEME}://{host}"


@dataclass(frozen=True)
class Reach:
    """The hosts one client may reach and the one scheme it may use.

    `hosts` are admitted exactly. `families` are admitted with every
    subdomain, which is for a service that names its storage hosts as it goes.
    """

    hosts: frozenset[str]
    families: frozenset[str] = frozenset()
    scheme: str = SECURE_SCHEME

    def admits(self, scheme: str, host: str) -> bool:
        """Whether an address with this scheme and host is one to go to."""
        if scheme.lower() != self.scheme:
            return False
        name = host.lower()
        if name in self.hosts or name in self.families:
            return True
        return any(name.endswith(f".{family}") for family in self.families)


# Stellody's own releases and nothing else.
GITHUB_REACH = Reach(hosts=frozenset({GITHUB_API_HOST}))
# The two catalogues a discovery run asks.
DISCOVERY_REACH = Reach(hosts=frozenset({MUSICBRAINZ_HOST, LISTENBRAINZ_LABS_HOST}))
# The release search, the archive's listings and the stores its pictures
# are served from.
COVER_REACH = Reach(
    hosts=frozenset({MUSICBRAINZ_HOST, COVER_ART_HOST}),
    families=frozenset({ARCHIVE_HOST}),
)
