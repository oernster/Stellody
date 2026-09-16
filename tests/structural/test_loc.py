"""Module length limits.

The cap is 400 lines. A file inside the danger band just below it is reduced to
the comfortable target rather than shaved to 399, because shaving buys nothing:
the next edit breaks the cap again and the same file gets split repeatedly.
Build and packaging scripts are exempt; they are linear recipes.
"""

from __future__ import annotations

import pathlib

import pytest
from conftest import REPO_ROOT, relative, repository_files

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
        "stamp_sitemap.py",
        "stamp_version.py",
        "sync_site.py",
    }
)


def _measured() -> list[pathlib.Path]:
    """Every Python file in the repository the cap applies to.

    The whole tree is walked, repo root included, so `main.py` and whatever
    arrives beside it are held to the cap as surely as the package is; only
    `conftest.NOT_OURS` is skipped. The setup program's interface is held to it
    like any other code. The delivery scripts are not: they are linear recipes
    read top to bottom, where splitting a sequence of flags across modules
    costs more than it buys.
    """
    return [
        path
        for path in repository_files(REPO_ROOT, "*.py")
        if path.name not in BUILD_SCRIPTS
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
    """A module between 381 and 400 lines is reduced to 350 or below."""
    inside = [
        f"{relative(path)} ({_line_count(path)})"
        for path in _measured()
        if DANGER_BAND_FLOOR < _line_count(path) <= LINE_CAP
    ]
    assert not inside, (
        f"Modules in the {DANGER_BAND_FLOOR + 1} to {LINE_CAP} danger band must "
        f"be reduced to {COMFORTABLE_TARGET} or below, not shaved: " + "; ".join(inside)
    )


def test_every_exempt_script_is_one_the_walk_would_otherwise_measure() -> None:
    """An exemption naming nothing the walk reaches is an exemption doing nothing.

    The list once sat beside a walk that never looked at the repo root, which is
    where every script it names lives, so it exempted nothing for as long as
    nobody noticed. A stale name now fails here rather than lying quietly.
    """
    walked = {path.name for path in repository_files(REPO_ROOT, "*.py")}
    assert BUILD_SCRIPTS <= walked, sorted(BUILD_SCRIPTS - walked)


@pytest.mark.parametrize("name", ["planted.py", "buildexe.py"])
def test_a_planted_file_at_the_root_is_measured_unless_exempt(
    name: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The walk reaches the repo root and skips only what is not ours."""
    monkeypatch.setattr("test_loc.REPO_ROOT", tmp_path)
    planted = tmp_path / name
    over_the_cap = "\n" * (LINE_CAP + 1)
    planted.write_text(over_the_cap, encoding="utf-8")
    ignored = tmp_path / "venv" / "planted.py"
    ignored.parent.mkdir()
    ignored.write_text(over_the_cap, encoding="utf-8")
    measured = _measured()
    assert ignored not in measured, "the virtual environment is not ours"
    assert (planted in measured) is (name not in BUILD_SCRIPTS)
