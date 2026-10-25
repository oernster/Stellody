"""How the process is left once everything durable is put away.

Moved out of the composition root, which had grown to the edge of the module
limit; it is the one concern there with no wiring in it.
"""

from __future__ import annotations

import os
import sys

from stellody.infrastructure import diary


def leave_at_once(code: int) -> None:
    """End the process where unwinding would end it worse.

    A cover lookup is given up within one read slice (`SLICE_S`), inside the quit
    wait: the archive asks whether anybody wants it between waits and in reads.
    What no amount of asking covers is a socket that never comes back at all.
    A thread still running when the application is torn down is one Qt ends the
    process over: measured on 2026-09-05, `QThread: Destroyed while thread
    is still running` from Qt6Core, an abort rather than an exit.

    So this is the last resort rather than the ordinary path. It should never
    be reached now; if it is, the alternative it replaces is a crash report.

    So the process is left before the tearing down begins. Everything that
    outlives a run has already been put away by the time this is reached: the
    store is closed and the single-instance claim released. What is skipped is
    the destruction of objects the operating system is about to reclaim
    anyway; what is bought is a quit that reports the code it meant rather than
    a crash the listener has to read as one.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def left_with(code: int, window) -> int:
    """Leave with this code, having decided how to leave with it.

    Everything durable is already put away by the time this is asked. What is
    left to decide is whether the ordinary unwinding is safe. It is not while
    a cover lookup is still inside a read: see `leave_at_once`.
    """
    if window.lookups_in_flight:
        diary.note("a cover lookup is still reading; leaving without unwinding")
        leave_at_once(code)
    return code
