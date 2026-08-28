"""Module length limits.

The cap is 400 lines. A file inside the danger band just below it is reduced to
the comfortable target rather than shaved to 399, because shaving buys nothing:
the next edit breaks the cap again and the same file gets split repeatedly.
Build and packaging scripts are exempt; they are linear recipes.
"""

from __future__ import annotations

import pathlib

from conftest import REPO_ROOT, package_modules, relative

LINE_CAP = 400
DANGER_BAND_PERCENT = 5
COMFORTABLE_TARGET = 350

DANGER_BAND_FLOOR = LINE_CAP - (LINE_CAP * DANGER_BAND_PERCENT // 100)

BUILD_SCRIPTS = frozenset(
    {
        "buildexe.py",
        "buildinstaller.py",
        "builddmg.py",
        "dmg_icon.py",
        "build_utils.py",
        "generate_icons.py",
        "generate_scripts.py",
        "stamp_version.py",
    }
)


def _measured() -> list[pathlib.Path]:
    """Every source and test file the cap applies to."""
    tests = sorted((REPO_ROOT / "tests").rglob("*.py"))
    return [
        path for path in [*package_modules(), *tests] if path.name not in BUILD_SCRIPTS
    ]


def _line_count(path: pathlib.Path) -> int:
    """Total lines in a file, blank lines included."""
    return len(path.read_text(encoding="utf-8").splitlines())


def test_no_module_exceeds_the_line_cap() -> None:
    """No module may pass 400 lines."""
    over = [
        f"{relative(path)} ({_line_count(path)})"
        for path in _measured()
        if _line_count(path) > LINE_CAP
    ]
    assert not over, f"Modules over the {LINE_CAP} line cap: " + "; ".join(over)


def test_no_module_sits_in_the_danger_band() -> None:
    """A module between 381 and 399 lines is reduced to 350 or below."""
    inside = [
        f"{relative(path)} ({_line_count(path)})"
        for path in _measured()
        if DANGER_BAND_FLOOR < _line_count(path) <= LINE_CAP
    ]
    assert not inside, (
        f"Modules in the {DANGER_BAND_FLOOR + 1} to {LINE_CAP} danger band must "
        f"be reduced to {COMFORTABLE_TARGET} or below, not shaved: " + "; ".join(inside)
    )
