"""Shared helpers for the structural suite."""

from __future__ import annotations

import ast
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "stellody"


def package_modules() -> list[pathlib.Path]:
    """Every Python module inside the application package."""
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def parsed(path: pathlib.Path) -> ast.Module:
    """Parse one module into an AST."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def relative(path: pathlib.Path) -> str:
    """Repo-relative POSIX path, for readable assertion messages."""
    return path.relative_to(REPO_ROOT).as_posix()
