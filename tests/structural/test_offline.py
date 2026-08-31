"""The second safety invariant: Stellody opens no connection behind your back.

A local-first player that quietly talks to the internet is not local-first,
whatever its README says. Exactly two modules may reach the network and each is
named here with what it is for: cover art when a listener asks for a picture,
then the update check asking GitHub whether a newer Stellody has been
published.
Nothing on the scan path, the draw path or the playback path may hold the
machinery to open a socket.

Two rather than one is a change worth reading as such. The update check was
added deliberately, with the count in this file being what had to be edited to
allow it; a permitted module is granted its permission in front of somebody
rather than by a test quietly continuing to pass.

Stated as a structural test rather than as a promise, for the same reason the
read-only invariant is: a promise cannot fail a build. This one was proved to
bite by planting `import urllib.request` in a module outside the set below and
watching it fail.
"""

from __future__ import annotations

import ast

from conftest import package_modules, parsed, relative

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
    }
)

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


def _root_of(name: str) -> str:
    """The top package a dotted import belongs to."""
    return name.split(".")[0]


def _network_imports(tree: ast.AST) -> set[str]:
    """Every networking package a module imports, by its top-level name."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(
                _root_of(alias.name)
                for alias in node.names
                if _root_of(alias.name) in NETWORK_LIBRARIES
            )
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and _root_of(node.module) in NETWORK_LIBRARIES
        ):
            found.add(_root_of(node.module))
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
