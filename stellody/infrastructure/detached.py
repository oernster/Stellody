"""Starting a program on its own, so it outlives whatever started it.

One home for two callers. The setup program starts the application it has just
written, then closes; the application starts itself again once a restore is
staged (BACKUP.md FR-B23), then leaves. Both need a process tied to nothing.

On Windows that means no console inherited, its own process group and out of
any job object the starter is in. A job that forbids breaking out refuses the
flag rather than ignoring it, so a plain start is tried after it. Elsewhere
Python refuses creation flags at all, so a new session does the same work.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

# The values are Windows' own; subprocess only names the first two.
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
DETACHED = (
    getattr(subprocess, "DETACHED_PROCESS", 0)
    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    | CREATE_BREAKAWAY_FROM_JOB
)
ON_WINDOWS = sys.platform == "win32"
# A run from source names the script; a built copy is the program itself.
SOURCE_SUFFIX = ".py"


def start(command: list[str], cwd: str) -> subprocess.Popen | None:
    """Start this command on its own; None when it would not start at all."""
    if not ON_WINDOWS:
        try:
            return subprocess.Popen(command, cwd=cwd, start_new_session=True)
        except OSError:
            return None
    for flags in (DETACHED, 0):
        try:
            return subprocess.Popen(command, cwd=cwd, creationflags=flags)
        except OSError:
            continue
    return None


def command_for(started_as: str, interpreter: str) -> list[str]:
    """What starts this application again, given what it was started as.

    From source the first argument is the script, which needs the interpreter
    in front of it; a built copy's first argument is the program itself. No
    other argument is carried over: a restart is asked for from an open
    window, so it must open one rather than repeat a quiet sign-in start.
    """
    if started_as.endswith(SOURCE_SUFFIX):
        return [interpreter, started_as]
    return [started_as]


def start_again(started_as: str) -> bool:
    """Start this application afresh; whether it could be started."""
    program = pathlib.Path(started_as).resolve()
    launched = start(command_for(str(program), sys.executable), str(program.parent))
    return launched is not None
