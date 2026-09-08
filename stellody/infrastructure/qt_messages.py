"""Qt's own complaints, written down instead of scrolling past.

Qt writes its warnings to the console. A packaged Stellody has no console, so
those lines are lost exactly where they would be most useful; run from source
they arrive with no timestamp, no thread and nothing around them, which is how
a message like `QIODevice::read (QSslSocket): device not open` can be seen
twice and still not be placed.

Reported on 2026-09-08: that message, after a discovery run, with no way to say
which of several candidates wrote it. Four theories were tried against it and
all four were disproved, which is the point at which an instrument is cheaper
than another guess.

So every message Qt writes goes to the diary, with the thread that was running
when it was written. The diary already carries what a launch did, so a warning
lands beside the run it belongs to rather than in a scrollback.

**The console still gets everything it got before.** The handler passes each
message on rather than swallowing it, since somebody running from source is
watching that console and a diagnostic that hides output is a step backwards.

**Nothing here may raise.** A handler that fails takes the message with it and
can be called from any thread, including one with no Python state to speak of.
That is the same rule the diary itself keeps.
"""

from __future__ import annotations

import sys
import threading

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

from stellody.infrastructure import diary

# What each kind of message is called in the diary. Qt's own names, since a
# reader matching a line against Qt's documentation should find the word it
# expects rather than a synonym chosen here.
KINDS = {
    QtMsgType.QtDebugMsg: "debug",
    QtMsgType.QtInfoMsg: "info",
    QtMsgType.QtWarningMsg: "warning",
    QtMsgType.QtCriticalMsg: "critical",
    QtMsgType.QtFatalMsg: "fatal",
}
UNKNOWN_KIND = "message"


def _where(context: object) -> str:
    """The file and line Qt named, where it named any.

    Qt fills these in for messages from code built with them and leaves them
    empty otherwise, which is the ordinary case for a warning from inside the
    network stack. An empty answer is left empty rather than padded out.
    """
    name = getattr(context, "file", None)
    line = getattr(context, "line", 0)
    if not name:
        return ""
    return f" at {name}:{line}"


def written(kind: QtMsgType, context: object, message: str) -> None:
    """Put one of Qt's messages in the diary, then let it through."""
    try:
        said = KINDS.get(kind, UNKNOWN_KIND)
        thread = threading.current_thread().name
        diary.note(f"Qt {said} on {thread}: {message}{_where(context)}")
    except Exception:  # noqa: BLE001, S110
        # A diary that breaks the application it is watching is worse than no
        # diary at all; this runs on every message Qt writes.
        pass


def _said_aloud(message: str) -> None:
    """Put a message where Qt's own handler would have put it.

    Measured on 2026-09-08: `qInstallMessageHandler` answers None, meaning Qt's
    built-in handler was the one in place; installing any handler replaces
    it. So a handler that only wrote to the diary would take the console
    output away from whoever is running from source, which is where these are
    read today. It is written out here rather than assumed to survive.
    """
    try:
        print(message, file=sys.stderr)
    except Exception:  # noqa: BLE001, S110
        pass


def listen() -> None:
    """Send Qt's messages to the diary as well as wherever they went.

    Called once, from the composition root, before anything Qt can complain
    about is built.
    """
    previous = qInstallMessageHandler(None)

    def both(kind: QtMsgType, context: object, message: str) -> None:
        """The diary, then whatever was handling these before."""
        written(kind, context, message)
        if previous is None:
            _said_aloud(message)
        else:
            previous(kind, context, message)

    qInstallMessageHandler(both)
