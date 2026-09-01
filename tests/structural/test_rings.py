"""A checkbox is never the plain one, so no checkbox can ship without a ring.

Qt draws a checkbox's square itself, so the ring on it has to be painted rather
than stated in the stylesheet; `stellody/ui/ringed_check.py` says why it cannot
be done from the sheet. That leaves one way for the defect to come back: some
later dialog builds a plain `QCheckBox` and gets a stop with nothing on it.

So the class is the rule. Anything the application constructs is the ringed one;
the only file allowed to name Qt's own is the module that subclasses it.
"""

from __future__ import annotations

import ast

from conftest import package_modules, parsed, relative

PLAIN = "QCheckBox"
RINGED = "RingedCheckBox"
# The one module allowed to name it: it is the subclass, so it must.
SUBCLASS_MODULE = "ringed_check.py"


def _constructed(tree: ast.AST) -> set[str]:
    """Every plain name called like a constructor in one module."""
    return {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def test_no_module_builds_a_checkbox_without_a_ring() -> None:
    """The ring lives in the class, so the class is what must be used."""
    offenders = [
        relative(path)
        for path in package_modules()
        if path.name != SUBCLASS_MODULE and PLAIN in _constructed(parsed(path))
    ]
    assert not offenders, f"a plain {PLAIN} is a stop with no ring: {offenders}"


def test_the_application_really_does_build_the_ringed_one() -> None:
    """Otherwise the check above passes by there being no checkboxes at all."""
    built = set()
    for path in package_modules():
        built |= _constructed(parsed(path))
    assert RINGED in built
