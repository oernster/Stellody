"""The central safety invariant: Stellody never writes to a music library.

MediaMonkey 2024 damaged the reference library by writing tags back into the
files. Stellody keeps every piece of user state in its own store, so the only
modules permitted to write to disk are the ones that own that store; the
tag-writing API is unreachable from any module that can read tags at all.
"""

from __future__ import annotations

import ast

from conftest import package_modules, parsed, relative

# Modules owning Stellody's own state, which may therefore write to disk.
# A music library is never one of them.
WRITE_PERMITTED = frozenset(
    {
        "stellody/infrastructure/paths.py",
        "stellody/infrastructure/store.py",
        "stellody/infrastructure/art_cache.py",
        "stellody/infrastructure/settings.py",
        "stellody/infrastructure/startup_log.py",
        "stellody/infrastructure/switch_reset.py",
    }
)

# The tag libraries whose presence in a module makes tag writing reachable.
TAG_LIBRARIES = frozenset({"mutagen", "soundfile", "taglib"})

# The mutagen write surface. Unreachable from any module that reads tags.
TAG_WRITE_METHODS = frozenset({"save", "delete", "add_tags", "add_picture"})

# Calls that create, destroy or alter a file through os or shutil.
MODULE_WRITE_CALLS = frozenset(
    {
        ("os", "remove"),
        ("os", "unlink"),
        ("os", "rename"),
        ("os", "renames"),
        ("os", "replace"),
        ("os", "mkdir"),
        ("os", "makedirs"),
        ("os", "rmdir"),
        ("os", "removedirs"),
        ("os", "truncate"),
        ("os", "chmod"),
        ("os", "utime"),
        ("shutil", "copy"),
        ("shutil", "copy2"),
        ("shutil", "copyfile"),
        ("shutil", "copytree"),
        ("shutil", "move"),
        ("shutil", "rmtree"),
    }
)

# Methods that only a filesystem path object offers, all of which write.
PATH_WRITE_METHODS = frozenset(
    {
        "write_text",
        "write_bytes",
        "touch",
        "mkdir",
        "rmdir",
        "symlink_to",
        "hardlink_to",
    }
)

WRITE_MODE_CHARACTERS = "wax+"


def _imports_tag_library(tree: ast.Module) -> bool:
    """True when a module can reach a tag-reading library."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in TAG_LIBRARIES:
                    return True
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in TAG_LIBRARIES:
                return True
    return False


def _open_mode(call: ast.Call) -> str | None:
    """The mode string of an open() style call, when it is a literal."""
    positional = call.args[1] if len(call.args) >= 2 else None
    if isinstance(positional, ast.Constant) and isinstance(positional.value, str):
        return positional.value
    for keyword in call.keywords:
        if keyword.arg != "mode" or not isinstance(keyword.value, ast.Constant):
            continue
        if isinstance(keyword.value.value, str):
            return keyword.value.value
    return None


def _is_write_open(call: ast.Call) -> bool:
    """True when a call opens a path for writing."""
    name = None
    if isinstance(call.func, ast.Name):
        name = call.func.id
    elif isinstance(call.func, ast.Attribute):
        name = call.func.attr
    if name != "open":
        return False
    mode = _open_mode(call)
    if mode is None:
        return False
    return any(character in mode for character in WRITE_MODE_CHARACTERS)


def _module_call(call: ast.Call) -> tuple[str, str] | None:
    """The (module, function) pair of a call like os.remove(...)."""
    func = call.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return (func.value.id, func.attr)
    return None


def _attribute_name(call: ast.Call) -> str | None:
    """The attribute name of a method call, when the call is one."""
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def test_tag_writing_is_unreachable_from_every_tag_reading_module() -> None:
    """A module that can read tags may never call the API that writes them."""
    offences: list[str] = []
    for module in package_modules():
        tree = parsed(module)
        if not _imports_tag_library(tree):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            attribute = _attribute_name(node)
            if attribute in TAG_WRITE_METHODS:
                offences.append(f"{relative(module)}:{node.lineno} .{attribute}()")
    assert (
        not offences
    ), "Stellody must never write tags back into a music file. Found: " + "; ".join(
        offences
    )


def test_only_state_owning_modules_write_to_disk() -> None:
    """Filesystem writes are confined to the modules owning Stellody's store."""
    offences: list[str] = []
    for module in package_modules():
        name = relative(module)
        if name in WRITE_PERMITTED:
            continue
        for node in ast.walk(parsed(module)):
            if not isinstance(node, ast.Call):
                continue
            if _is_write_open(node):
                offences.append(f"{name}:{node.lineno} open(..., write mode)")
                continue
            pair = _module_call(node)
            if pair in MODULE_WRITE_CALLS:
                offences.append(f"{name}:{node.lineno} {pair[0]}.{pair[1]}()")
                continue
            attribute = _attribute_name(node)
            if attribute in PATH_WRITE_METHODS:
                offences.append(f"{name}:{node.lineno} .{attribute}()")
    assert not offences, (
        "Only modules owning Stellody's own state may write to disk. Found: "
        + "; ".join(offences)
    )
