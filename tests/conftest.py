"""One rule over the whole suite: a test may never start the application.

Measured on 2026-08-30 by watching the process table while the suite ran: a
test reached `installer.launching.launch` with its stand-in no longer matching
the signature, fell through to the real one and started the copy of Stellody
installed on the machine. It did that on every run, which is where a window
kept coming from while that very fault was being hunted. The copy being
started was the owner's own, on his own desktop.

A stand-in that stops matching is an ordinary mistake and will happen again.
What must not happen again is that the mistake reaches the machine, so
starting anything named like the application is refused outright, loudly
enough that the test which tried it is the one that fails.

Everything else a test legitimately runs, the formatter, the linters, the
process table, is left alone: the guard is aimed at the one program whose
appearance on somebody's screen is the harm.
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest

from stellody.infrastructure import diary

FORBIDDEN = "stellody.exe"


class RefusedToStartTheApplication(AssertionError):
    """Raised when a test tries to start the real application."""


def _names_the_application(command: object) -> bool:
    """Whether a command would start the application itself."""
    if isinstance(command, (str, bytes)):
        parts: tuple[object, ...] = (command,)
    elif isinstance(command, (list, tuple)):
        parts = tuple(command)
    else:
        return False
    return any(FORBIDDEN in str(part).lower() for part in parts)


@pytest.fixture(autouse=True)
def never_start_the_application(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refuse to start the application, whatever a test believes it patched."""
    real = subprocess.Popen

    def guarded(command, *arguments, **keywords):
        if _names_the_application(command):
            raise RefusedToStartTheApplication(
                "a test tried to start the real application: "
                f"{command}. Stand in for the launch instead."
            )
        return real(command, *arguments, **keywords)

    monkeypatch.setattr(subprocess, "Popen", guarded)


@pytest.fixture(autouse=True)
def keep_the_diary_out_of_the_real_one(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A test run must not write into the account of real runs.

    The suite drives the composition root, which writes down what a launch
    did. Left alone those lines land in the same file the owner reads when
    hunting a fault, so the evidence is mixed with runs nobody made.
    """
    monkeypatch.setattr(diary, "location", lambda: tmp_path / diary.LOG_NAME)
