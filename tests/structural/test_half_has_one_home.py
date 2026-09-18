"""Halving has one home, so the next module that centres something imports it.

Six interface modules each wrote `HALF = 2` for themselves, found on
2026-09-18 when the tray rule needed it and a seventh copy was the easy way
in. Every copy agrees until one is edited, so they were folded into
`stellody/ui/theme.py` and this holds them there. Tests are scanned as well:
a test that defines its own copy is checking against a number the
application no longer states.
"""

from __future__ import annotations

import ast

from conftest import REPO_ROOT, package_modules, parsed, relative

NAME = "HALF"
HOME = "stellody/ui/theme.py"


def _defines(module: ast.Module) -> bool:
    """True where the module assigns the name at its top level."""
    for node in module.body:
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target] if isinstance(node, ast.AnnAssign) else []
        )
        if any(isinstance(t, ast.Name) and t.id == NAME for t in targets):
            return True
    return False


def test_half_is_defined_only_in_the_theme() -> None:
    """One definition, in the theme; every other module imports it."""
    scanned = [*package_modules(), *sorted((REPO_ROOT / "tests").rglob("*.py"))]
    homes = [relative(path) for path in scanned if _defines(parsed(path))]
    assert homes == [HOME], f"{NAME} defined in: {homes}"
