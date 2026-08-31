"""Formatting and linting run as assertions, not as a separate remembered step."""

from __future__ import annotations

import subprocess
import sys

from conftest import REPO_ROOT

TARGETS = (
    "stellody",
    "installer",
    "tests",
    "main.py",
    "buildexe.py",
    "buildinstaller.py",
    "generate_icons.py",
    "sync_site.py",
)


def _run(*command: str) -> subprocess.CompletedProcess[str]:
    """Run a checker from the repository root and capture its output."""
    return subprocess.run(
        [sys.executable, "-m", *command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_black_formatting_is_current() -> None:
    """Every module is already formatted the way black would format it."""
    result = _run("black", "--check", "--quiet", *TARGETS)
    assert result.returncode == 0, (
        "black would reformat these files:\n" + result.stdout + result.stderr
    )


def test_flake8_is_clean() -> None:
    """No flake8 findings anywhere in the package or the suite."""
    result = _run("flake8", *TARGETS)
    assert result.returncode == 0, "flake8 findings:\n" + result.stdout


def test_ruff_is_clean() -> None:
    """No ruff findings under the default rule set."""
    result = _run("ruff", "check", *TARGETS)
    assert result.returncode == 0, "ruff findings:\n" + result.stdout
