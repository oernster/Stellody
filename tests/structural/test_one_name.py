"""The product name has one home, so a rename reaches every surface at once.

Fifteen displayed strings once spelled it out: the close prompt, the About
dialog, the health report, the repair screen and the tag editor, plus the
directory the library sits in and the system wide names the single instance
guard claims. A rename would have reached the ones somebody remembered to
grep for and left the rest announcing a product that no longer existed.

Docstrings and comments are prose ABOUT the module rather than text anybody is
shown, so they are left alone; what is scanned is the string literals a reader
or the operating system could actually meet.
"""

from __future__ import annotations

import ast

from conftest import PACKAGE_ROOT, package_modules, parsed, relative

from stellody.shared.version import APP_NAME

# Where the name is defined. Everything else builds on it.
NAME_HOME = "shared/version.py"


def _docstring_nodes(tree: ast.Module) -> set[int]:
    """Every string node that is a docstring, by identity.

    A docstring is the first statement of a module, class or function, so it
    is found by looking there rather than by guessing from the quoting.
    """
    found: set[int] = set()
    holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, holders):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.add(id(first.value))
    return found


def test_the_product_name_is_written_in_one_place() -> None:
    """No string a reader or the system meets spells the name out again."""
    offences: list[str] = []
    for module in package_modules():
        if module.relative_to(PACKAGE_ROOT).as_posix() == NAME_HOME:
            continue
        tree = parsed(module)
        docstrings = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant):
                continue
            if not isinstance(node.value, str) or id(node) in docstrings:
                continue
            if APP_NAME in node.value:
                offences.append(f"{relative(module)}:{node.lineno}")
    assert not offences, (
        f"The name belongs in {NAME_HOME} and is built from APP_NAME elsewhere: "
        + "; ".join(offences)
    )
