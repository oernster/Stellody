"""NFR-PRIV-003: the agent names Stellody, its version and a contact, nothing else.

MusicBrainz asks every client to say who it is. What it must not become is a
way of saying who the listener is, so the agent is held to how it is BUILT
rather than to what it happens to read today: an agent assembled from the
version module and one fixed address cannot come to carry a user name, a
machine name or a path without this failing.
"""

from __future__ import annotations

import ast

from conftest import PACKAGE_ROOT, parsed

COURTESY = PACKAGE_ROOT / "infrastructure" / "courtesy.py"
FETCHING = PACKAGE_ROOT / "infrastructure" / "fetching.py"
VERSION_MODULE = "stellody.shared.version"
COURTESY_MODULE = "stellody.infrastructure.courtesy"
# Everything the agent may be made of: the application's name, its version and
# the contact address the terms ask for. All three with nothing beside them.
FROM_THE_VERSION_MODULE = frozenset({"APP_NAME", "__version__"})
INGREDIENTS = FROM_THE_VERSION_MODULE | {"CONTACT"}
AGENT_HEADER = b"User-Agent"


def _assigned(tree: ast.Module, name: str) -> ast.expr:
    """The value a module-level name is given."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return node.value
    raise AssertionError(f"{name} is not assigned at the top of the module")


def _imported_from(tree: ast.Module, module: str) -> set[str]:
    """Every name a module imports from this one."""
    return {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == module
        for alias in node.names
    }


def _names_in(node: ast.AST) -> set[str]:
    """Every plain name an expression reads."""
    return {found.id for found in ast.walk(node) if isinstance(found, ast.Name)}


def test_the_agent_is_built_from_the_three_ingredients_alone() -> None:
    """No call and no other name, so nothing about the machine can be read in."""
    agent = _assigned(parsed(COURTESY), "USER_AGENT")
    assert isinstance(agent, ast.JoinedStr)
    assert _names_in(agent) == INGREDIENTS
    assert not [node for node in ast.walk(agent) if isinstance(node, ast.Call)]


def test_the_contact_is_a_fixed_string() -> None:
    """An address written down, rather than one looked up from anywhere."""
    contact = _assigned(parsed(COURTESY), "CONTACT")
    assert isinstance(contact, ast.Constant)
    assert isinstance(contact.value, str)


def test_the_name_and_version_come_from_the_version_module() -> None:
    """The one home both already have, so the agent cannot drift from them."""
    assert FROM_THE_VERSION_MODULE <= _imported_from(parsed(COURTESY), VERSION_MODULE)


def test_the_fetcher_sends_that_agent_and_no_other() -> None:
    """One agent header, set from the constant rather than spelled again."""
    tree = parsed(FETCHING)
    agents = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "setRawHeader"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == AGENT_HEADER
    ]
    assert len(agents) == 1
    assert _names_in(agents[0].args[1]) == {"USER_AGENT"}
    assert "USER_AGENT" in _imported_from(tree, COURTESY_MODULE)
