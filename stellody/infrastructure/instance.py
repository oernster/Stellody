"""One Stellody at a time, over a channel to the copy already running.

Closing the window leaves the application in the notification area; a hidden
window has no button on the taskbar. So a second launch, from a pinned
shortcut, the Start menu, a dock or a desktop file, almost always means "show
me the one I already have" rather than "give me another".

Three system objects and no files, the same three on Windows, Linux and macOS.
A system semaphore is the mutex: it is held only across the moment ownership
is decided, so two copies starting together cannot both decide they are first.
A shared memory segment carries ownership itself, since it exists exactly as
long as somebody holds it. A local socket carries the activation, which is a
named pipe on Windows and a socket file the system owns elsewhere.

Ownership and activation are deliberately separate. Asking a listener whether
it is there answers "is one running" only once that listener is accepting,
which is a race at the exact moment it matters.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSharedMemory, QSystemSemaphore
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from stellody.shared.version import APP_NAME

# System wide names rather than paths, since the application may live in more
# than one place and there is still only one of it running.
GUARD_NAME = f"{APP_NAME}.instance.guard"
CLAIM_NAME = f"{APP_NAME}.instance.claim"
CHANNEL_NAME = f"{APP_NAME}.activation"

GUARD_HOLDERS = 1
CLAIM_BYTES = 1
SHOW_YOURSELF = b"show"
# Long enough to cross the channel on a busy machine, short enough that a copy
# which cannot be reached gives up rather than hanging on somebody's click.
REPLY_TIMEOUT_MS = 1000
# How long a caller that has connected is given to say what it came to say.
# Short, because the window waits on it: a caller that says nothing is far
# more likely to be something enumerating pipes than a Stellody launching.
SPEAK_TIMEOUT_MS = 250


class SingleInstance:
    """The claim to being the running copy, plus the way to reach it."""

    def __init__(
        self,
        guard: str = GUARD_NAME,
        claim: str = CLAIM_NAME,
        channel: str = CHANNEL_NAME,
    ) -> None:
        self._guard = QSystemSemaphore(guard, GUARD_HOLDERS)
        self._claim = QSharedMemory(claim)
        self._channel = channel
        self._server: QLocalServer | None = None
        # The asking socket is held rather than left to the scope that made
        # it. Measured: destroying it discards the word it had just written,
        # so the copy already running was asked by a caller that then took
        # the question back.
        self._caller: QLocalSocket | None = None

    def take(self) -> bool:
        """Whether this copy is the one that runs.

        The segment is attached and let go again first. A copy the system ends
        without unmapping leaves one behind on Unix, where the segment outlives
        its process; that attach is what clears it. Windows reclaims its own,
        so there the attach simply finds nothing.
        """
        self._guard.acquire()
        try:
            if self._claim.attach():
                self._claim.detach()
            return bool(self._claim.create(CLAIM_BYTES))
        finally:
            self._guard.release()

    def release(self) -> None:
        """Give the claim up. Safe whether or not it was ever taken."""
        if self._server is not None:
            self._server.close()
            self._server = None
        self._caller = None
        self._claim.detach()

    def listen(self, when_asked: Callable[[], None]) -> bool:
        """Answer later copies asking to be shown; False when nothing listens.

        A channel left behind by a copy the system ended is removed first: it
        names a listener that is not there and the name will not be handed out
        twice. Failing to listen costs the handoff rather than the
        application, so it is reported instead of raised.
        """
        QLocalServer.removeServer(self._channel)
        server = QLocalServer()
        if not server.listen(self._channel):
            return False
        server.newConnection.connect(lambda: self._answer(server, when_asked))
        self._server = server
        return True

    def _answer(self, server: QLocalServer, when_asked: Callable[[], None]) -> None:
        """Take one caller's word for it, once it has actually given its word.

        A connection is not the ask. Any process on the machine may open a
        named pipe; one that merely opened this one used to bring the window
        up out of the notification area with nobody having asked for it. The
        word was written by every caller and read by none, so the protocol
        decided nothing. The caller now has to say it.
        """
        connection = server.nextPendingConnection()
        if connection is None:
            return
        spoken = _spoken_by(connection)
        connection.disconnectFromServer()
        if spoken == SHOW_YOURSELF:
            when_asked()

    def ask(self) -> bool:
        """Ask the running copy to come forward; False when none answered."""
        caller = QLocalSocket()
        self._caller = caller
        caller.connectToServer(self._channel)
        if not caller.waitForConnected(REPLY_TIMEOUT_MS):
            return False
        caller.write(SHOW_YOURSELF)
        caller.flush()
        caller.waitForBytesWritten(REPLY_TIMEOUT_MS)
        caller.disconnectFromServer()
        return True


def _spoken_by(connection: QLocalSocket) -> bytes:
    """What a caller said; empty when it said nothing in the time allowed.

    The wait is skipped where the word has already arrived, which is the
    ordinary case: a launch writes and flushes before it lets go.
    """
    if not connection.bytesAvailable():
        connection.waitForReadyRead(SPEAK_TIMEOUT_MS)
    return bytes(connection.readAll().data())
