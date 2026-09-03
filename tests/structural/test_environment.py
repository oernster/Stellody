"""The suite runs where the application runs, against what it declares.

Measured, at the cost of a working afternoon. PyAV was installed into the system
Python while the application was started with the venv's, so `import av` failed
for the listener and succeeded for every test. The whole gate reported green,
1544 tests and 100% coverage, while M4A could not be played at all. Nothing in
the suite could have caught it, because the suite was not running on the
machine that was broken.

Three assertions close it. The first says the checks run in the project's own
environment rather than whichever interpreter happened to be on the path. The
second says everything the project declares is actually installed there, so a
requirement added to the file and never installed fails here, naming itself,
rather than surfacing as a feature that quietly does nothing.

The third says the versions match. The runtime is pinned so that a build of one
commit is the same build whenever it is made; a pin nothing checks is a comment,
since an environment holding a different version reads exactly as green while
being the environment the pin exists to rule out.
"""

from __future__ import annotations

import pathlib
import sys
from importlib import metadata

from conftest import PACKAGE_ROOT

PROJECT_ROOT = PACKAGE_ROOT.parent
VENV_DIR = PROJECT_ROOT / "venv"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"

# Where a requirement's name stops and its version constraint begins.
CONSTRAINTS = "<>=!~;[ "
# What an exact pin is written as, against which a floor is ">=".
PIN = "=="


def _requirements() -> tuple[str, ...]:
    """Every requirement line in the file, comments and includes dropped."""
    lines = []
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith(("#", "-")):
            continue
        lines.append(text)
    return tuple(lines)


def _name_of(requirement: str) -> str:
    """The distribution a requirement names, without its constraint."""
    cut = min(
        (requirement.find(mark) for mark in CONSTRAINTS if mark in requirement),
        default=-1,
    )
    return requirement if cut < 0 else requirement[:cut]


def _declared() -> tuple[str, ...]:
    """Every distribution named in requirements.txt, without its constraints."""
    return tuple(_name_of(line) for line in _requirements())


def _pinned() -> tuple[tuple[str, str], ...]:
    """Each distribution pinned with `==`, as (name, exact version)."""
    return tuple(
        (_name_of(line), line.split(PIN, 1)[1].strip())
        for line in _requirements()
        if PIN in line
    )


def test_the_suite_runs_in_the_projects_own_environment() -> None:
    """Not whichever interpreter is first on the path.

    Skipped where there is no venv to run in, since there is then nothing to
    drift apart from. Where there is one, running the checks anywhere else is
    the fault this exists to catch: the checks pass and the application does
    not, while the two never meet.
    """
    if not VENV_DIR.is_dir():
        return
    running = pathlib.Path(sys.prefix).resolve()
    assert running == VENV_DIR.resolve(), (
        f"the checks are running in {running} while the project's environment "
        f"is {VENV_DIR}. Run them with {VENV_DIR / 'Scripts' / 'python.exe'}, "
        "or through gate.ps1, so the checks and the application agree."
    )


def test_everything_declared_is_installed_here() -> None:
    """A requirement nobody installed is a feature that silently does nothing.

    Asked of the metadata rather than by importing, so this stays cheap and so
    a package with heavy import-time work is not run to answer it: importing
    PyAV alone loads some sixty megabytes of shared libraries.
    """
    missing = []
    for name in _declared():
        try:
            metadata.distribution(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
    assert not missing, (
        "requirements.txt names packages that are not installed in "
        f"{sys.prefix}: {', '.join(missing)}. Install them with "
        "python -m pip install -r requirements.txt"
    )


def test_every_pin_is_the_version_installed() -> None:
    """A pin nothing checks is a comment.

    The runtime is pinned so a build of one commit is the same build whenever
    it is made. An environment holding a different version reads exactly as
    green otherwise, while being the environment the pin exists to rule out.
    """
    wrong = []
    for name, wanted in _pinned():
        try:
            held = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
        if held != wanted:
            wrong.append(f"{name} is {held} where requirements.txt pins {wanted}")
    assert not wrong, (
        "the environment does not match the pinned runtime: "
        + "; ".join(wrong)
        + ". Install it with python -m pip install -r requirements.txt"
    )
