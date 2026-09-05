"""Layer boundaries and domain purity, enforced rather than documented.

UI -> Application -> Domain <- Infrastructure. Nothing imports upward; the
domain layer reaches neither the filesystem, the clock nor a framework.
"""

from __future__ import annotations

import ast

from conftest import PACKAGE_ROOT, package_modules, parsed, relative

FORBIDDEN_IMPORTS: dict[str, frozenset[str]] = {
    "domain": frozenset({"application", "infrastructure", "ui", "shared"}),
    "application": frozenset({"infrastructure", "ui"}),
    "infrastructure": frozenset({"ui"}),
    "ui": frozenset({"infrastructure"}),
}

FRAMEWORK_PACKAGES = frozenset(
    {"PySide6", "mutagen", "soundfile", "sounddevice", "numpy", "av"}
)

LAYERS_WITHOUT_FRAMEWORKS = frozenset({"domain", "application"})

# Standard library modules that would give the domain layer a side effect.
IMPURE_STDLIB = frozenset(
    {
        "os",
        "sys",
        "io",
        "pathlib",
        "shutil",
        "tempfile",
        "sqlite3",
        "logging",
        "threading",
        "multiprocessing",
        "subprocess",
        "socket",
        "time",
        "random",
        "urllib",
        "http",
    }
)

CLOCK_CALLS = frozenset({"now", "today", "utcnow", "monotonic", "time_ns"})

# The setup program is a CLIENT of the application: `installer/` reads
# stellody.shared, stellody.ui and stellody.infrastructure, while nothing under
# stellody/ may reach back. It is asserted rather than assumed because
# TECH_DEBT.md claimed for a while that a layering test enforced this while no
# test mentioned the installer at all, which is the shape of a guard nobody has
# ever seen fail.
SETUP_PACKAGE = "installer"


def _layer_of(module) -> str:
    """Which layer a module belongs to."""
    relative_parts = module.relative_to(PACKAGE_ROOT).parts
    return relative_parts[0] if len(relative_parts) > 1 else ""


def _imported_roots(tree: ast.Module) -> list[tuple[str, int]]:
    """Every top-level package name a module imports, with its line."""
    roots: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            roots.append((node.module, node.lineno))
    return roots


def test_layers_never_import_upward() -> None:
    """Each layer may only reach the layers beneath it."""
    offences: list[str] = []
    for module in package_modules():
        layer = _layer_of(module)
        forbidden = FORBIDDEN_IMPORTS.get(layer)
        if forbidden is None:
            continue
        for name, line in _imported_roots(parsed(module)):
            parts = name.split(".")
            if parts[0] != "stellody" or len(parts) < 2:
                continue
            if parts[1] in forbidden:
                offences.append(f"{relative(module)}:{line} imports {name}")
    assert not offences, "Layer boundary violated: " + "; ".join(offences)


def test_domain_and_application_are_framework_free() -> None:
    """No Qt, no tag library, no audio library below the infrastructure layer."""
    offences: list[str] = []
    for module in package_modules():
        if _layer_of(module) not in LAYERS_WITHOUT_FRAMEWORKS:
            continue
        for name, line in _imported_roots(parsed(module)):
            if name.split(".")[0] in FRAMEWORK_PACKAGES:
                offences.append(f"{relative(module)}:{line} imports {name}")
    assert not offences, "A framework leaked inward: " + "; ".join(offences)


def test_domain_has_no_side_effects() -> None:
    """The domain layer touches no filesystem, no network and no scheduler."""
    offences: list[str] = []
    for module in package_modules():
        if _layer_of(module) != "domain":
            continue
        for name, line in _imported_roots(parsed(module)):
            if name.split(".")[0] in IMPURE_STDLIB:
                offences.append(f"{relative(module)}:{line} imports {name}")
    assert not offences, "The domain layer must stay pure: " + "; ".join(offences)


def test_domain_never_reads_the_clock() -> None:
    """Time enters the domain as an argument, never by being looked up."""
    offences: list[str] = []
    for module in package_modules():
        if _layer_of(module) != "domain":
            continue
        for node in ast.walk(parsed(module)):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr in CLOCK_CALLS:
                offences.append(f"{relative(module)}:{node.lineno} .{node.func.attr}()")
    assert not offences, "The domain must not read the clock: " + "; ".join(offences)


def test_the_application_never_imports_the_setup_program() -> None:
    """The setup program reads the application; the application never reads it."""
    offences: list[str] = []
    for module in package_modules():
        for name, line in _imported_roots(parsed(module)):
            if name.split(".")[0] == SETUP_PACKAGE:
                offences.append(f"{relative(module)}:{line} imports {name}")
    assert (
        not offences
    ), "The application must not import the setup program: " + "; ".join(offences)
