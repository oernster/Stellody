"""Starting what setup has just written, then getting out of its way.

Setup's job is done once the application is running, so the same tick that
starts it also closes setup: leaving a spent installer on screen asks for a
second dismissal that says nothing.

The order matters. A window that arrives AFTER the program that launched it has
gone is denied the foreground by Windows and only flashes on the taskbar, so
setup stays alive until the new window is up, fronts it and closes then.
"""

from __future__ import annotations

import ctypes
import pathlib
import subprocess
from ctypes import wintypes

# How long setup waits for the window before giving up and closing anyway. A
# missed foreground is a smaller fault than a setup program that will not go.
FOREGROUND_WAIT_S = 15.0
FOREGROUND_POLL_MS = 200


def launch(executable: pathlib.Path) -> subprocess.Popen | None:
    """Start the application; None when it could not be started at all."""
    try:
        return subprocess.Popen([str(executable)], cwd=str(executable.parent))
    except OSError:
        return None


def front(pid: int) -> bool:
    """Bring that process's first visible window forward; False if it has none.

    Called on a timer, so a false answer means "not yet" as often as it means
    "never": the caller decides when to stop asking.
    """
    try:
        user32 = ctypes.windll.user32
    except (AttributeError, OSError):
        return False
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _on_window(handle, _extra):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(handle):
            found.append(handle)
            return False
        return True

    user32.EnumWindows(_on_window, 0)
    if not found:
        return False
    user32.SetForegroundWindow(found[0])
    return True
