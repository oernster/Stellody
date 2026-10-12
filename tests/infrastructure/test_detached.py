"""Starting the application again for a restore. BACKUP.md FR-B23.

Nothing here starts a real program: the start is stood in for, so these say
what WOULD be run, which is the part a test can settle. That a built copy
really comes back is checked by hand in a packaged build (A-02).
"""

from __future__ import annotations

import subprocess
import sys

from stellody.infrastructure import detached


class RecordingStart:
    """Stands in for Popen, recording each command and how it was asked."""

    def __init__(self, refuse: int | None = None) -> None:
        self.calls: list[tuple[list[str], dict]] = []
        self.refuse = refuse

    def __call__(self, command, **keywords):
        self.calls.append((command, keywords))
        if self.refuse is not None and keywords.get("creationflags") == self.refuse:
            raise OSError("refused")
        return object()


def test_a_run_from_source_is_started_through_the_interpreter() -> None:
    assert detached.command_for("C:/src/main.py", "C:/py/python.exe") == [
        "C:/py/python.exe",
        "C:/src/main.py",
    ]


def test_a_built_copy_is_started_as_itself() -> None:
    assert detached.command_for("C:/Programs/App/app.exe", "ignored") == [
        "C:/Programs/App/app.exe"
    ]


def test_on_windows_the_start_is_detached_first(monkeypatch) -> None:
    start = RecordingStart()
    monkeypatch.setattr(detached, "ON_WINDOWS", True)
    monkeypatch.setattr(subprocess, "Popen", start)
    assert detached.start(["app"], "here") is not None
    assert [keywords["creationflags"] for _, keywords in start.calls] == [
        detached.DETACHED
    ]


def test_a_refused_detach_falls_back_to_a_plain_start(monkeypatch) -> None:
    start = RecordingStart(refuse=detached.DETACHED)
    monkeypatch.setattr(detached, "ON_WINDOWS", True)
    monkeypatch.setattr(subprocess, "Popen", start)
    assert detached.start(["app"], "here") is not None
    assert [keywords["creationflags"] for _, keywords in start.calls] == [
        detached.DETACHED,
        0,
    ]


def test_elsewhere_a_new_session_does_the_detaching(monkeypatch) -> None:
    start = RecordingStart()
    monkeypatch.setattr(detached, "ON_WINDOWS", False)
    monkeypatch.setattr(subprocess, "Popen", start)
    detached.start(["app"], "here")
    assert start.calls == [(["app"], {"cwd": "here", "start_new_session": True})]


def test_a_start_that_fails_everywhere_is_reported(monkeypatch) -> None:
    def refuse(command, **keywords):
        raise OSError("no")

    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr(detached, "ON_WINDOWS", True)
    assert detached.start(["app"], "here") is None
    monkeypatch.setattr(detached, "ON_WINDOWS", False)
    assert detached.start(["app"], "here") is None


def test_starting_again_names_the_program_and_its_folder(monkeypatch, tmp_path) -> None:
    start = RecordingStart()
    monkeypatch.setattr(subprocess, "Popen", start)
    script = tmp_path / "main.py"
    assert detached.start_again(str(script))
    command, keywords = start.calls[0]
    assert command == [sys.executable, str(script.resolve())]
    assert keywords["cwd"] == str(tmp_path.resolve())
