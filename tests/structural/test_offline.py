"""The second safety invariant: Stellody opens no connection behind your back.

A local-first player that quietly talks to the internet is not local-first,
whatever its README says. Exactly four modules may hold the machinery to open a
connection and each is named here with what it is for: cover art when a
listener asks for a picture, the update check asking GitHub whether a newer
Stellody has been published, the one fetcher a discovery run asks two
catalogues through, then the channel a second launch speaks to the copy already
running over, which leaves the machine at all. Nothing on the scan path, the
draw path or the playback path may hold that machinery.

Each addition is a change worth reading as such. The update check was added
deliberately, with the count in this file being what had to be edited to allow
it; a permitted module is granted its permission in front of somebody rather
than by a test quietly continuing to pass.

Discovery reaches two services and added ONE name rather than two: neither
catalogue client holds a socket, since both hand their questions to the fetcher
and get answers back. That was the point of writing it that way.

**A package is named by its top level except where that says nothing.** Qt's
network module is `PySide6.QtNetwork`, whose top level is `PySide6`; listing
that would name every window in the application. So a dotted entry is matched
in full. The fetcher moved onto Qt on 2026-09-07 and would otherwise have gone
unwatched, which is how the fourth module came to be noticed at all: the
activation channel had been holding a local socket, unseen, since it was
written.

Stated as a structural test rather than as a promise, for the same reason the
read-only invariant is: a promise cannot fail a build. This one was proved to
bite by planting `import urllib.request` in a module outside the set below and
watching it fail.
"""

from __future__ import annotations

import ast

from conftest import REPO_ROOT, package_modules, parsed, relative

# The modules permitted to open a connection, each with what it is for. The
# composition root names them in order to build them; it holds the wiring and
# never a call. Adding to this set is the deliberate act, so it is short and
# every entry earns its line.
NETWORK_PERMITTED = frozenset(
    {
        # Looking an album up when a listener asks for its cover art.
        "stellody/infrastructure/cover_search.py",
        # Asking GitHub whether a newer Stellody has been published. It sends
        # nothing about the listener or their library; see the module itself.
        "stellody/infrastructure/update_source.py",
        # The one fetcher a discovery run asks its two catalogues through. It
        # sends artist names and identifiers from the genres a listener ticked,
        # plus the application's own user agent. Nothing about the machine.
        "stellody/infrastructure/fetching.py",
        # The channel a second launch tells the running copy to show itself
        # over. A named pipe on Windows, a socket file the system owns
        # elsewhere: it is addressed by name rather than by host and reaches
        # nothing off this machine. It is listed because it holds the same
        # machinery as the three above, not because it goes anywhere.
        "stellody/infrastructure/instance.py",
    }
)

# Networking packages named in FULL, for the case where a top-level name would
# be useless. Kept apart from the set above so neither kind of entry has to
# carry a rule about the other.
NETWORK_MODULES = frozenset({"PySide6.QtNetwork"})

# Anything that can reach a socket. Named rather than guessed at: each of these
# is a way a module could go outward without any of the others being present.
NETWORK_LIBRARIES = frozenset(
    {
        "urllib",
        "http",
        "socket",
        "ssl",
        "ftplib",
        "smtplib",
        "telnetlib",
        "asyncio",
        "requests",
        "httpx",
        "aiohttp",
        "websockets",
    }
)


def _reaching(name: str) -> str | None:
    """The networking package this import reaches; None where it reaches none.

    Two shapes of entry, matched two ways. A stdlib package is named by its top
    level, since `urllib.request` and `urllib.parse` both arrive under
    `urllib`. A Qt module cannot be, because its top level is imported by every
    window in the application, so it is matched in full instead.
    """
    if name in NETWORK_MODULES:
        return name
    root = name.split(".")[0]
    return root if root in NETWORK_LIBRARIES else None


def _network_imports(tree: ast.AST) -> set[str]:
    """Every networking package a module imports, however it was written.

    `from PySide6 import QtNetwork` names the module across the two halves of
    the statement, so the names are rejoined before being asked about; matching
    only what follows `from` would read that line as an ordinary Qt import.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                reached = _reaching(alias.name)
                if reached is not None:
                    found.add(reached)
        elif isinstance(node, ast.ImportFrom) and node.module:
            reached = _reaching(node.module)
            if reached is not None:
                found.add(reached)
                continue
            for alias in node.names:
                joined = _reaching(f"{node.module}.{alias.name}")
                if joined is not None:
                    found.add(joined)
    return found


def test_only_the_cover_search_can_reach_the_network() -> None:
    """Every other module is unable to open a connection, not merely unwilling."""
    offenders = {}
    for path in package_modules():
        where = relative(path)
        if where in NETWORK_PERMITTED:
            continue
        reached = _network_imports(parsed(path))
        if reached:
            offenders[where] = sorted(reached)
    assert not offenders, (
        "these modules can open a connection and must not: "
        f"{offenders}. A module that needs the network asks for it here, "
        "which is when there is something to weigh."
    )


def test_the_permitted_module_is_one_that_exists() -> None:
    """Permission granted in advance to code nobody has written is not a guard."""
    present = {relative(path) for path in package_modules()}
    assert NETWORK_PERMITTED <= present, (
        "these are permitted to reach the network but do not exist: "
        f"{sorted(NETWORK_PERMITTED - present)}"
    )


def test_the_search_is_reached_only_through_its_port() -> None:
    """Nothing imports the client directly except the composition root.

    The port is what everything else holds, so a module cannot come to depend
    on the archive being MusicBrainz; nor can a test come to depend on a
    connection: standing in front of a Protocol needs no network at all.
    """
    client = "stellody.infrastructure.cover_search"
    allowed = {"stellody/composition.py"}
    offenders = []
    for path in package_modules():
        where = relative(path)
        if where in allowed or where in NETWORK_PERMITTED:
            continue
        for node in ast.walk(parsed(path)):
            module = getattr(node, "module", None)
            names = [alias.name for alias in getattr(node, "names", [])]
            if module == client or client in names:
                offenders.append(where)
                break
    assert not offenders, f"these reach past the port to the client: {offenders}"


# The test tree, which the package scan above never reads. NFR-MAINT-002.
TEST_ROOT = REPO_ROOT / "tests"

# The test modules permitted to hold networking machinery, each with why none of
# them reaches past this machine. Every other test stands in front of a port
# with a hand-written fake, so it needs none of it.
TESTS_PERMITTED = frozenset(
    {
        # A real HTTP service bound to the loopback address on a port the system
        # picks, because what the fetcher makes of a status and a silence is
        # Qt's, which a fake reply would only imitate.
        "tests/infrastructure/fetching_support.py",
        # The fetcher's own suite, asking that loopback service through Qt.
        "tests/infrastructure/test_fetching.py",
        # The single-instance channel, a named pipe or a socket file the system
        # owns, which is addressed by name and goes nowhere off the machine.
        "tests/infrastructure/test_instance.py",
        # The error types the cover search's opener raises, raised by a fake
        # opener. Nothing is opened.
        "tests/infrastructure/test_cover_search.py",
        "tests/infrastructure/test_giving_up_a_lookup.py",
        # Reading the host out of each client's address constants, so About can
        # be checked to credit every service asked. Nothing is opened.
        "tests/ui/test_dialogs.py",
    }
)


def _test_tree_modules() -> list:
    """Every Python module in the test tree."""
    return sorted(TEST_ROOT.rglob("*.py"))


def test_no_test_holds_the_machinery_to_reach_the_network() -> None:
    """NFR-MAINT-002: a suite that asks a third party fails on their bad day.

    Read with the same reader as the package, so an import the package scan
    would catch is caught here too, spelled any of the three ways.
    """
    offenders = {}
    for path in _test_tree_modules():
        where = relative(path)
        if where in TESTS_PERMITTED:
            continue
        reached = _network_imports(parsed(path))
        if reached:
            offenders[where] = sorted(reached)
    assert not offenders, (
        f"these tests hold networking machinery: {offenders}. A test reaches a "
        "service through its port with a hand-written fake behind it."
    )


def test_every_permitted_test_module_exists_and_still_needs_it() -> None:
    """A permission nobody uses any more is a gap waiting for somebody to fill."""
    for where in sorted(TESTS_PERMITTED):
        path = REPO_ROOT / where
        assert path.exists(), f"{where} is permitted but does not exist"
        assert _network_imports(parsed(path)), f"{where} no longer needs permitting"
