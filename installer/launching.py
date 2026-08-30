"""Starting what setup has just written, then getting out of its way.

Setup's job is done once the application is running, so the same tick that
starts it also closes setup: leaving a spent installer on screen asks for a
second dismissal that says nothing.

The order matters. A window that arrives AFTER the program that launched it has
gone is denied the foreground by Windows and only flashes on the taskbar, so
setup stays alive until the new window is up, fronts it and closes then.

The window is not necessarily owned by the process setup started. A packaged
application is commonly a bootstrap that unpacks itself and runs the real
program as a child, so the pid setup holds owns no window at all and never
will. Every process descended from it is therefore treated as the same
application; matching the one pid meant waiting out the whole deadline before
closing, which is the spent installer this was written to avoid.
"""

from __future__ import annotations

import ctypes
import pathlib
import subprocess
from ctypes import wintypes

from stellody.shared.startup import HIDDEN_FLAG

# How long setup waits for the window before giving up and closing anyway. A
# missed foreground is a smaller fault than a setup program that will not go,
# so this is the worst case a user could see setup linger for, not a target.
FOREGROUND_WAIT_S = 5.0
FOREGROUND_POLL_MS = 200

# Started on its own: no console inherited, its own process group, out of any
# job object this program is in, so nothing that happens to setup reaches it.
# The values are Windows' own; subprocess only names the first two.
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
DETACHED = (
    getattr(subprocess, "DETACHED_PROCESS", 0)
    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    | CREATE_BREAKAWAY_FROM_JOB
)

TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE = -1
MAX_PATH = 260


class _ProcessEntry(ctypes.Structure):
    """One row of the system's process table, as Toolhelp reports it."""

    _fields_ = (
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * MAX_PATH),
    )


def launch(executable: pathlib.Path, quiet: bool = False) -> subprocess.Popen | None:
    """Start the application, on its own; None when it would not start at all.

    Detached and broken out of any job object setup belongs to, so what is
    started outlives the program that started it. Setup closes seconds later
    by design; a launch tied to its lifetime would be ended by that.
    A job that forbids breaking out refuses the flag rather than ignoring it,
    so the plain start is tried after it.

    A quiet launch waits in the notification area instead of opening a window.
    Setup used to start it the loud way whatever the user had asked for, so
    somebody who had chosen to have Stellody live in the tray was handed a
    window by every install, which is the same flag the sign-in entry passes
    for exactly the same reason.
    """
    command = [str(executable)]
    if quiet:
        command.append(HIDDEN_FLAG)
    for flags in (DETACHED, 0):
        try:
            return subprocess.Popen(
                command, cwd=str(executable.parent), creationflags=flags
            )
        except OSError:
            continue
    return None


def family(root: int, parents: dict[int, int]) -> set[int]:
    """A process and everything descended from it, given who parented whom.

    Kept apart from the system call that gathers the table so the walk itself
    can be exercised. A process table is a forest read at one instant; a
    pid can be reused, so a cycle is possible rather than unthinkable: each
    pid is visited once.
    """
    children: dict[int, list[int]] = {}
    for child, parent in parents.items():
        children.setdefault(parent, []).append(child)
    seen = {root}
    pending = [root]
    while pending:
        for child in children.get(pending.pop(), ()):
            if child not in seen:
                seen.add(child)
                pending.append(child)
    return seen


def _parent_map() -> dict[int, int]:
    """Every live process against the process that started it.

    An empty map on any failure, which leaves the caller matching the one pid
    it started: the same answer this gave before it could see a tree at all.
    """
    try:
        kernel32 = ctypes.windll.kernel32
    except (AttributeError, OSError):
        return {}
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE:
        return {}
    entry = _ProcessEntry()
    entry.dwSize = ctypes.sizeof(_ProcessEntry)
    parents: dict[int, int] = {}
    try:
        more = kernel32.Process32First(snapshot, ctypes.byref(entry))
        while more:
            parents[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
            more = kernel32.Process32Next(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return parents


def front(pid: int) -> bool:
    """Bring the launched application's first visible window forward.

    False when it has none yet. Called on a timer, so a false answer means
    "not yet" as often as it means "never": the caller decides when to stop
    asking.
    """
    try:
        user32 = ctypes.windll.user32
    except (AttributeError, OSError):
        return False
    ours = family(pid, _parent_map())
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _on_window(handle, _extra):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        if owner.value in ours and user32.IsWindowVisible(handle):
            found.append(handle)
            return False
        return True

    user32.EnumWindows(_on_window, 0)
    if not found:
        return False
    user32.SetForegroundWindow(found[0])
    return True
