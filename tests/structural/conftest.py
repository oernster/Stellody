"""Shared helpers for the structural suite."""

from __future__ import annotations

import ast
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "stellody"

# Directories in the working tree holding nothing anybody here wrote: other
# people's packages, tool state and what the build scripts write. Named once, so
# every guard that walks the whole tree skips the same things.
NOT_OURS = frozenset(
    {
        ".git",
        ".claude",
        "venv",
        "__pycache__",
        "node_modules",
        "build",
        "dist",
        "dist-installer",
        "dist-installer.build",
        "payload",
        "stage",
        ".flatpak-build",
        ".flatpak-builder",
        ".flatpak-repo",
        ".flatpak-vendor",
        ".flatpak-wheels",
        "packaging",
    }
)


def package_modules() -> list[pathlib.Path]:
    """Every Python module inside the application package."""
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def repository_files(root: pathlib.Path, pattern: str) -> list[pathlib.Path]:
    """Every file under `root` matching `pattern` that is the repository's own.

    A walk of the working tree rather than a question put to git, so a file
    nobody has staged yet is found as surely as one already committed.
    """
    return sorted(
        path
        for path in root.rglob(pattern)
        if path.is_file() and NOT_OURS.isdisjoint(path.relative_to(root).parts)
    )


def parsed(path: pathlib.Path) -> ast.Module:
    """Parse one module into an AST."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def relative(path: pathlib.Path) -> str:
    """Repo-relative POSIX path, for readable assertion messages."""
    return path.relative_to(REPO_ROOT).as_posix()
