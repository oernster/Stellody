"""NFR-REL-001: what discovery keeps is kept in Stellody's own data directory.

Four things are written: the discovery file, the candidate genre cache, the
catalogue memory and the running record each memory keeps. Stellody reads the
music folder and never writes into it, so every one of them has to land beside
the database, which `infrastructure/paths.py` is the one home for.

Held by how the two modules NAME their places rather than by where a test run
happens to find them: a module that asks `paths.py` for the directory and
names nothing else cannot come to write anywhere else without this failing.
"""

from __future__ import annotations

import ast

from conftest import PACKAGE_ROOT, parsed, relative

DISCOVERY_MODULES = (
    PACKAGE_ROOT / "infrastructure" / "discovery_file.py",
    PACKAGE_ROOT / "infrastructure" / "catalogue_memory.py",
)
PATH_SUFFIX = "_path"
PATHS_MODULE = "paths"
DATA_DIR = "data_dir"
# The modules a discovery module hands a place to, which is where it reads and
# writes: the running record and the atomic writer. Each is given its place.
HANDED_A_PLACE = frozenset({"journal"})
WRITER = "_written"
# Every way a module could name a directory of its own instead of asking
# `paths.py` for one: building a path, the home and working directories, the
# environment and the system's temporary directory.
ELSEWHERE_CALLS = frozenset(
    {
        "Path",
        "PurePath",
        "home",
        "cwd",
        "expanduser",
        "getcwd",
        "getenv",
        "gettempdir",
        "mkdtemp",
        "TemporaryDirectory",
    }
)
ELSEWHERE_ATTRIBUTES = frozenset({"environ"})


def _called(node: ast.Call) -> str:
    """The name a call is made through, however it is qualified."""
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return ""


def _path_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    """Every module-level function that names a place."""
    return [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.endswith(PATH_SUFFIX)
    ]


def _under_the_data_directory(value: ast.expr | None) -> bool:
    """Whether this is `paths.data_dir() / A_NAMED_CONSTANT`."""
    if not isinstance(value, ast.BinOp) or not isinstance(value.op, ast.Div):
        return False
    asked = value.left
    return (
        isinstance(asked, ast.Call)
        and isinstance(asked.func, ast.Attribute)
        and asked.func.attr == DATA_DIR
        and isinstance(asked.func.value, ast.Name)
        and asked.func.value.id == PATHS_MODULE
        and isinstance(value.right, ast.Name)
    )


def test_every_place_named_is_under_the_data_directory() -> None:
    """Each place is the data directory with a named file under it."""
    for module in DISCOVERY_MODULES:
        functions = _path_functions(parsed(module))
        assert functions, f"{relative(module)} names no place at all"
        for function in functions:
            returns = [
                node for node in ast.walk(function) if isinstance(node, ast.Return)
            ]
            assert len(returns) == 1, (relative(module), function.name)
            assert _under_the_data_directory(returns[0].value), (
                f"{relative(module)}::{function.name} names a place that is not "
                "paths.data_dir() / a named file"
            )


def test_no_discovery_module_names_a_directory_of_its_own() -> None:
    """No home, no working directory, no environment, no path built by hand."""
    for module in DISCOVERY_MODULES:
        tree = parsed(module)
        calls = {_called(node) for node in ast.walk(tree) if isinstance(node, ast.Call)}
        attributes = {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }
        assert not calls & ELSEWHERE_CALLS, (relative(module), calls & ELSEWHERE_CALLS)
        assert not attributes & ELSEWHERE_ATTRIBUTES, relative(module)


def _is_a_named_place(node: ast.expr | None) -> bool:
    """Whether this expression is a call to one of the `*_path` functions."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id.endswith(PATH_SUFFIX)
    )


def _places_held(function: ast.FunctionDef) -> set[str]:
    """The local names a function gives a named place to, as `write` does."""
    return {
        target.id
        for node in ast.walk(function)
        if isinstance(node, ast.Assign) and _is_a_named_place(node.value)
        for target in node.targets
        if isinstance(target, ast.Name)
    }


def _hands_over_a_place(node: ast.Call) -> bool:
    """Whether this call is a read or write that is given somewhere to do it."""
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id in HANDED_A_PLACE
    ) or (isinstance(func, ast.Name) and func.id == WRITER)


def test_every_read_and_write_is_given_one_of_those_places() -> None:
    """A place named correctly and then not used would hold nothing.

    Handed either the call itself or a local name the same function gave it:
    `write` holds the place so it can say where the file went.
    """
    for module in DISCOVERY_MODULES:
        for function in ast.walk(parsed(module)):
            if not isinstance(function, ast.FunctionDef):
                continue
            held = _places_held(function)
            for node in ast.walk(function):
                if not isinstance(node, ast.Call) or not _hands_over_a_place(node):
                    continue
                place = node.args[0] if node.args else None
                assert _is_a_named_place(place) or (
                    isinstance(place, ast.Name) and place.id in held
                ), f"{relative(module)} line {node.lineno} is handed a place of its own"
