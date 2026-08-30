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


def test_a_quiet_launch_asks_for_the_notification_area(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Somebody who chose to have Stellody wait in the tray gets no window.

    Setup used to start it the loud way whatever had been asked for, so every
    install handed back a window: the same complaint the sign-in entry already
    passes this flag to avoid.
    """
    asked: list[list[str]] = []

    def start(command, **_):
        asked.append(list(command))
        return _FakeProcess()

    monkeypatch.setattr(launching.subprocess, "Popen", start)
    launching.launch(pathlib.Path("Stellody.exe"), quiet=True)
    assert asked[0][1:] == ["--hidden"], "a quiet launch says so on the command line"


def test_an_ordinary_launch_still_opens_a_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Somebody who did not ask for residency is handed their application."""
    asked: list[list[str]] = []

    def start(command, **_):
        asked.append(list(command))
        return _FakeProcess()

    monkeypatch.setattr(launching.subprocess, "Popen", start)
    launching.launch(pathlib.Path("Stellody.exe"))
    assert asked[0][1:] == [], "nothing was asked for, so nothing is passed"


def test_an_empty_table_leaves_the_one_pid_that_was_started() -> None:
    """Which is the answer this gave before it could see a tree at all."""
    assert launching.family(BOOTSTRAP, {}) == {BOOTSTRAP}


def test_setup_goes_once_the_application_is_on_screen(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole point: a spent installer is not left sitting there."""
    window = _window(monkeypatch)
    window._sign_in.setChecked(False)
    window.show()
    monkeypatch.setattr(
        launching, "launch", lambda executable, quiet=False: _FakeProcess()
    )
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
    window._sign_in.setChecked(False)
    window.show()
    monkeypatch.setattr(
        launching, "launch", lambda executable, quiet=False: _FakeProcess()
    )
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
    window._sign_in.setChecked(False)
    window.show()
    monkeypatch.setattr(
        launching, "launch", lambda executable, quiet=False: _FakeProcess()
    )
    monkeypatch.setattr(launching, "front", explode)
    window._finish(INSTALLED_AT / actions.EXE_NAME, "Installed", "It is there.")
    window._front_deadline = time.monotonic() - 1
    window._front_then_close()
    assert not window._front_timer.isActive()
    assert not window.isVisible()


def test_the_wait_is_short_enough_not_to_read_as_setup_hanging_about() -> None:
    """It is a worst case a user could sit through, not a target."""
    assert launching.FOREGROUND_WAIT_S <= MAX_LINGER_S


class RecordingStart:
    """A stand-in for Popen that records how it was asked to start things."""

    def __init__(self, refuse_flags: int | None = None) -> None:
        self.calls: list[int] = []
        self.refuse_flags = refuse_flags
        self.pid = 4242

    def __call__(self, arguments, cwd, creationflags):
        """Record the attempt, refusing the flags a locked down job would."""
        self.calls.append(creationflags)
        if self.refuse_flags is not None and creationflags == self.refuse_flags:
            raise OSError("access is denied")
        return self


def test_the_application_is_started_out_of_setups_reach(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setup closes seconds later, so what it starts must not be tied to it."""
    start = RecordingStart()
    monkeypatch.setattr(launching.subprocess, "Popen", start)
    started = launching.launch(pathlib.Path("C:/Programs/Stellody/Stellody.exe"))
    assert started is start
    assert start.calls == [launching.DETACHED]
    assert launching.DETACHED & launching.CREATE_BREAKAWAY_FROM_JOB


def test_a_job_that_refuses_to_be_left_still_gets_the_application_started(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The flag is refused rather than ignored, so the plain start follows it."""
    start = RecordingStart(refuse_flags=launching.DETACHED)
    monkeypatch.setattr(launching.subprocess, "Popen", start)
    started = launching.launch(pathlib.Path("C:/Programs/Stellody/Stellody.exe"))
    assert started is start
    assert start.calls == [launching.DETACHED, 0], "detached first, then plainly"


def test_an_application_that_will_not_start_at_all_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*_: object, **__: object) -> None:
        raise OSError("no such file")

    monkeypatch.setattr(launching.subprocess, "Popen", refuse)
    assert launching.launch(pathlib.Path("C:/nowhere/Stellody.exe")) is None


def test_a_quiet_install_closes_setup_without_waiting_for_a_window(
    application: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """There is no window coming, so waiting for one only holds setup there.

    The wait is bounded at five seconds, which is five seconds of a spent
    installer sitting on screen over a window that was never going to appear.
    """
    asked: list[bool] = []

    def start(executable, quiet=False):
        asked.append(quiet)
        return _FakeProcess()

    window = _window(monkeypatch)
    window._sign_in.setChecked(True)
    window.show()
    monkeypatch.setattr(launching, "launch", start)
    window._finish(INSTALLED_AT / actions.EXE_NAME, "Installed", "It is there.")
    assert asked == [True], "residency was asked for, so the launch is a quiet one"
    waiting = getattr(window, "_front_timer", None)
    assert waiting is None, "no timer, because nothing is being waited for"
