"""Finding a running Stellody, then ending it without ending setup itself."""

from __future__ import annotations

import subprocess

import pytest

from installer import running


class Result:
    """A finished process, as subprocess.run reports one."""

    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout
        self.returncode = 0


def test_the_kill_never_touches_the_process_tree() -> None:
    """A tree kill can take the setup program with it, silently.

    Windows decides descent from recorded parent process ids; on a machine
    where the application has been started and killed repeatedly those ids
    churn, so setup can end up recorded as a descendant and terminate itself.
    There is no traceback, because a terminate is not a crash.
    """
    arguments = running.taskkill_arguments()
    assert "/t" not in arguments, "a tree kill can end the setup program itself"
    assert "/f" in arguments, "the app holds its files while it sits in the tray"
    assert running.EXE_NAME in arguments


def test_neither_command_opens_a_console_of_its_own(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict] = []

    def fake_run(command, **kwargs):
        captured.append(kwargs)
        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    running.is_running()
    running.close()
    assert captured, "nothing ran"
    assert running.NO_WINDOW != 0
    for kwargs in captured:
        assert kwargs["creationflags"] == running.NO_WINDOW


def test_an_empty_task_list_is_not_a_running_application() -> None:
    """tasklist prints an information line rather than nothing when it misses."""
    assert running.names_a_process("INFO: No tasks are running.") is False
    assert running.names_a_process("") is False


def test_the_executables_own_name_is_what_counts() -> None:
    assert running.names_a_process(f"{running.EXE_NAME}   1234 Console") is True


def test_a_question_windows_cannot_answer_reads_as_not_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Best effort: a broken tasklist must not block an install for ever."""

    def fake_run(command, **kwargs):
        raise OSError("tasklist is missing")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert running.is_running() is False


def test_closing_reports_success_once_it_is_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter([True, True, False])
    monkeypatch.setattr(running, "_run", lambda *args: "")
    monkeypatch.setattr(running, "is_running", lambda: next(answers))
    monkeypatch.setattr(running.time, "sleep", lambda _seconds: None)
    assert running.close() is True


def test_closing_gives_up_rather_than_waiting_for_ever(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = iter([0.0] + [running.CLOSE_TIMEOUT_S + 1.0] * 10)
    monkeypatch.setattr(running, "_run", lambda *args: "")
    monkeypatch.setattr(running, "is_running", lambda: True)
    monkeypatch.setattr(running.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(running.time, "sleep", lambda _seconds: None)
    assert running.close() is False
