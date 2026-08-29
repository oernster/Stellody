"""Setup hands over to the application it started, then goes.

The window that appears is not necessarily owned by the process setup started.
A packaged application is commonly a bootstrap that unpacks itself and runs the
real program as a child, so the pid setup holds may own no window at all. That
is why the family of a process is worked out rather than the pid matched;
the walk is a pure function over who parented whom: the system call that
gathers the table cannot be stood up in a test, the reasoning over it can.
"""

from __future__ import annotations

import pathlib
import time

import pytest
from PySide6.QtWidgets import QApplication

from installer import actions, launching, running
from installer import app as setup
from installer.existing import Existing

INSTALLED_AT = pathlib.Path("C:/Programs/Stellody")
THIS_VERSION = "0.2.0"
BOOTSTRAP = 100
REAL_PROGRAM = 200
GRANDCHILD = 300
STRANGER = 900
DESKTOP = 4
# The longest a user should ever watch a spent setup program sit there.
MAX_LINGER_S = 5.0


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication for the whole session. Qt is never mocked."""
    existing = QApplication.instance()
    return existing or QApplication([])


class _FakeProcess:
    """A launched application, as far as setup needs to know."""

    pid = BOOTSTRAP


def _window(monkeypatch: pytest.MonkeyPatch) -> setup.SetupWindow:
    """A setup window over a machine with nothing installed on it."""
    here = Existing(
        version="",
        location=INSTALLED_AT,
        desktop=False,
        start_menu=False,
        sign_in=False,
    )
    monkeypatch.setattr(setup.existing, "look", lambda: here)
    monkeypatch.setattr(setup, "read_version", lambda: THIS_VERSION)
    monkeypatch.setattr(running, "is_running", lambda: False)
    return setup.SetupWindow(uninstalling=False)


def test_a_process_on_its_own_is_its_own_whole_family() -> None:
    assert launching.family(BOOTSTRAP, {BOOTSTRAP: DESKTOP}) == {BOOTSTRAP}


def test_the_program_a_bootstrap_unpacks_and_runs_counts_as_the_same_app() -> None:
    """The case this exists for: the window belongs to the child, not the pid."""
    parents = {BOOTSTRAP: DESKTOP, REAL_PROGRAM: BOOTSTRAP, STRANGER: DESKTOP}
    assert launching.family(BOOTSTRAP, parents) == {BOOTSTRAP, REAL_PROGRAM}


def test_the_family_reaches_all_the_way_down() -> None:
    parents = {BOOTSTRAP: DESKTOP, REAL_PROGRAM: BOOTSTRAP, GRANDCHILD: REAL_PROGRAM}
    assert launching.family(BOOTSTRAP, parents) == {
        BOOTSTRAP,
        REAL_PROGRAM,
        GRANDCHILD,
    }


def test_an_unrelated_process_is_never_taken_for_ours() -> None:
    """Fronting somebody else's window would be worse than fronting none."""
    parents = {BOOTSTRAP: DESKTOP, STRANGER: DESKTOP, GRANDCHILD: STRANGER}
    assert launching.family(BOOTSTRAP, parents) == {BOOTSTRAP}


def test_a_reused_pid_making_a_cycle_does_not_hang_the_walk() -> None:
    """A process table is read at one instant and pids are reused."""
    parents = {BOOTSTRAP: REAL_PROGRAM, REAL_PROGRAM: BOOTSTRAP}
    assert launching.family(BOOTSTRAP, parents) == {BOOTSTRAP, REAL_PROGRAM}


def test_an_empty_table_leaves_the_one_pid_that_was_started() -> None:
    """Which is the answer this gave before it could see a tree at all."""
    assert launching.family(BOOTSTRAP, {}) == {BOOTSTRAP}


def test_setup_goes_once_the_application_is_on_screen(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole point: a spent installer is not left sitting there."""
    window = _window(monkeypatch)
    window.show()
    monkeypatch.setattr(launching, "launch", lambda executable: _FakeProcess())
    monkeypatch.setattr(launching, "front", lambda pid: True)
    window._finish(INSTALLED_AT / actions.EXE_NAME, "Installed", "It is there.")
    assert window.isVisible(), "setup stays until the window it started is up"
    window._front_then_close()
    assert not window._front_timer.isActive()
    assert not window.isVisible(), "setup closed itself once the handover was done"


def test_setup_goes_at_the_deadline_even_if_the_window_never_comes(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(monkeypatch)
    window.show()
    monkeypatch.setattr(launching, "launch", lambda executable: _FakeProcess())
    monkeypatch.setattr(launching, "front", lambda pid: False)
    window._finish(INSTALLED_AT / actions.EXE_NAME, "Installed", "It is there.")
    window._front_then_close()
    assert window.isVisible(), "still waiting, the deadline has not passed"
    window._front_deadline = time.monotonic() - 1
    window._front_then_close()
    assert not window._front_timer.isActive()
    assert not window.isVisible()


def test_setup_goes_even_when_looking_for_the_window_fails(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A raising slot ends in silence; the timer would fire into it forever.

    So past the deadline nothing is called that could keep setup here.
    """

    def explode(pid: int) -> bool:
        raise OSError("the process tables would not be read")

    window = _window(monkeypatch)
    window.show()
    monkeypatch.setattr(launching, "launch", lambda executable: _FakeProcess())
    monkeypatch.setattr(launching, "front", explode)
    window._finish(INSTALLED_AT / actions.EXE_NAME, "Installed", "It is there.")
    window._front_deadline = time.monotonic() - 1
    window._front_then_close()
    assert not window._front_timer.isActive()
    assert not window.isVisible()


def test_the_wait_is_short_enough_not_to_read_as_setup_hanging_about() -> None:
    """It is a worst case a user could sit through, not a target."""
    assert launching.FOREGROUND_WAIT_S <= MAX_LINGER_S
