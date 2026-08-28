"""Finding a running Stellody, then ending it so setup can replace its files.

Extracting over a locked executable fails with a permission error, which is
what setup reported when the application was open, so this is asked BEFORE any
file is touched rather than discovered halfway through.

Termination is forced rather than a polite window close. Stellody minimises to
the notification area when its window is closed instead of exiting, so asking
its window to close leaves the process alive and the file locked. Only ending
the process frees it.

The image is named and the process TREE is never touched. A tree kill decides
what is descended from what by recorded parent process ids; on a machine
where the application has been started and killed repeatedly those ids churn,
so the setup program can end up recorded as a descendant and terminate itself:
the application closes, the setup window vanishes and there is no traceback,
because a terminate is not a crash.
"""

from __future__ import annotations

import subprocess
import time

APP_NAME = "Stellody"
EXE_NAME = f"{APP_NAME}.exe"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LIST_TIMEOUT_S = 5.0
CLOSE_TIMEOUT_S = 10.0
POLL_STEP_S = 0.2


def tasklist_arguments() -> list[str]:
    """The command that asks Windows whether the application is open."""
    return ["tasklist", "/fi", f"imagename eq {EXE_NAME}", "/nh"]


def taskkill_arguments() -> list[str]:
    """The command that ends it.

    `/f` stays, because the application intercepts a window close and would
    keep its files locked. `/t` must NEVER appear: see the module docstring.
    """
    return ["taskkill", "/f", "/im", EXE_NAME]


def _run(arguments: list[str], timeout: float) -> str:
    """Run one console command with no window of its own; its output, else ''."""
    try:
        result = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            creationflags=NO_WINDOW,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout


def names_a_process(output: str) -> bool:
    """True when tasklist's output actually names the executable.

    With no match tasklist prints an information line rather than nothing, so
    the executable's own name is what is looked for.
    """
    return EXE_NAME.lower() in output.lower()


def is_running() -> bool:
    """Whether Stellody is open. Best effort: an unanswerable question is 'no'."""
    return names_a_process(_run(tasklist_arguments(), LIST_TIMEOUT_S))


def close(now: float | None = None) -> bool:
    """End every instance and wait for the lock to release.

    Returns whether it is gone. The clock is injectable so a test can drive the
    timeout without waiting on one.
    """
    _run(taskkill_arguments(), LIST_TIMEOUT_S)
    started = time.monotonic() if now is None else now
    while is_running():
        if time.monotonic() - started > CLOSE_TIMEOUT_S:
            return False
        time.sleep(POLL_STEP_S)
    return True
