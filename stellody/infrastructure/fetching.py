"""The one place a discovery run opens a connection.

Two catalogues are asked things during a run and neither client holds a socket:
they hand a base address and some parameters to this, then get back what was
said. That is deliberate. The offline structural test names every module able
to open a connection; a discovery that reaches two services would otherwise
have added two more names to a list whose whole value is being short.

**It also means the courtesies cannot be forgotten in one client and honoured
in the other.** The gate, the user agent and the timeout are applied here, once.

**What comes back is an answer or a typed refusal, never a stack trace.** The
service above knows what to do with each: a refusal is waited out and asked
again, an unreachable host ends the run, anything else is recorded against that
artist and the run goes on.

**A request here can be given up on, which is the whole reason it is written
this way.** It used to block a thread inside `urlopen`, where nothing could
reach it: a listener who pressed stop waited out the request; against a
service that had gone quiet that was the full twenty second timeout. Nothing
portable interrupts a thread waiting on a socket, so the answer is not to wait
on one. Qt's network stack is event driven and a reply in flight can be
abandoned outright.

Measured on 2026-09-07 against a server that accepts a connection and then says
nothing: `abort()` ends the reply in under a millisecond, where the blocking
client sat there until its timeout. Qt was already a dependency and its network
module already in use, so this costs nothing that was not being paid.

**Every request is written down, which is an instrument rather than logging.**
Reported on 2026-09-08: `QIODevice::read (QNetworkReplyHttpImpl): device not
open`, written on the run's own thread; in three runs out of three, within 25
milliseconds of the run ending. Two explanations were tested and both were
disproved, which is the point at which an instrument is cheaper than another
guess. Qt's own messages already reach the diary carrying the thread that
wrote them; what was missing is which request each one sat beside. So each
request notes its address, what it came to and how long it took; the next
sighting can then be read against the line above it.
"""

from __future__ import annotations

import json
import time
import urllib.parse
from collections.abc import Callable

from PySide6.QtCore import QEventLoop, QThread, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from stellody.application.choosing_covers import Wanted, always_wanted
from stellody.application.discovery_ports import (
    RateRefused,
    SourceFailed,
    SourceTooSlow,
    SourceUnavailable,
)
from stellody.infrastructure import diary
from stellody.infrastructure.courtesy import (
    REFUSAL_CODES,
    SLEEP_SLICE_S,
    TIMEOUT_S,
    USER_AGENT,
    Gate,
)

# How often a request in flight asks whether anybody still wants it. The same
# slice the waits between requests are taken in, for the same reason and so
# there is one number rather than two that drift.
GIVE_UP_SLICE_MS = int(SLEEP_SLICE_S * 1000)
MS_PER_SECOND = 1000
# The statuses that mean the service is asking to be asked again rather than
# answering. Read off the reply's own header, since Qt reports a refusal as a
# protocol error rather than as an answer.
STATUS_ATTRIBUTE = QNetworkRequest.Attribute.HttpStatusCodeAttribute
# How much of what a service said about a refusal is worth keeping. Enough for
# a sentence, since the interesting part is whether it names a rate limit or
# says it is simply unavailable; a body can otherwise be a whole page.
SAID_LIMIT = 160

# Handed one line about a request that has just ended. The diary is what fills
# this in; a test hands in a list instead.
Note = Callable[[str], None]


def _said(body: bytes) -> str:
    """What the service put in the body, in one line and cut short.

    A refusal usually carries its reason in the service's own words, which is
    the difference between being asked to slow down and being told the service
    is not there. Written down on 2026-09-08, when 21 refusals in one run left
    nothing to say which of the two it was.
    """
    try:
        answer = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        answer = None
    said = answer.get("error") if isinstance(answer, dict) else None
    spoken = str(said) if said else body.decode("utf-8", "replace")
    return " ".join(spoken.split())[:SAID_LIMIT]


class Fetcher:
    """Asks one service for JSON, at the rate its terms allow.

    One fetcher stands in front of one service, because it carries that
    service's gate and a gap owed to one says nothing about another.

    The access manager is built on the thread that first asks; rebuilt where
    a later run asks from a different one. Qt objects belong to the thread that
    made them, while a discovery runs on a thread of its own, so the manager
    has to live where the requests are made rather than where the fetcher was.
    """

    def __init__(
        self,
        gate: Gate | None = None,
        timeout_s: float = TIMEOUT_S,
        manager: QNetworkAccessManager | None = None,
        note: Note = diary.note,
    ) -> None:
        self._gate = gate if gate is not None else Gate()
        self._timeout_s = timeout_s
        self._manager = manager
        self._manager_thread = QThread.currentThread() if manager else None
        self._note = note

    def _asking(self) -> QNetworkAccessManager:
        """An access manager belonging to the thread doing the asking."""
        here = QThread.currentThread()
        if self._manager is None or self._manager_thread is not here:
            self._manager = QNetworkAccessManager()
            self._manager_thread = here
            # Let go of it when its thread ends. See `_let_go`.
            here.finished.connect(self._let_go)
        return self._manager

    def _let_go(self) -> None:
        """Close the connections when the thread that owns them ends.

        A run keeps its connections open between requests, which is what the
        gap the terms ask for makes worth doing. Nothing closed them when the
        run finished, so two idle sockets were left behind on a thread that
        had ended; Qt tore them down half a minute later with nobody home.

        Measured on 2026-09-08 from the diary, over two runs of different
        lengths: `QIODevice::read (QSslSocket): device not open`, twice, at
        29.914s and 29.877s after the last request, one for each host asked.
        A delay that steady against runs that differ by a second is a fixed
        idle timeout rather than anything about the run.

        **Connected to a bare method deliberately, which is the one place in
        this application that is right.** A signal connected to a callable
        runs in the SENDER's thread; here the sender is the thread that is
        ending and the sockets are its own, so its thread is exactly where
        they have to be closed. Anywhere else would be closing them across a
        boundary, which is the fault this avoids rather than commits.
        """
        manager = self._manager
        self._manager = None
        self._manager_thread = None
        if manager is not None:
            manager.clearConnectionCache()

    def json(
        self, address: str, parameters: dict[str, str], wanted: Wanted = always_wanted
    ) -> object:
        """What the service said, decoded; a typed error where it said nothing.

        The parameters are encoded here rather than by the caller, so a client
        needs no networking package of its own and the structural test that
        counts those packages keeps meaning what it says.

        `wanted` is asked throughout, during the gap owed to the service and
        again while the request is in flight. Answering False abandons the
        request there and then rather than at the end of it.
        """
        url = f"{address}?{urllib.parse.urlencode(parameters)}"
        if not self._gate.wait(wanted):
            raise SourceFailed(f"given up on before it was asked: {url}")
        started = time.monotonic()
        reply = self._sent(url)
        self._waited_on(reply, wanted)
        try:
            answer = self._read(reply, url, abandoned=not wanted())
        except (RateRefused, SourceFailed, SourceUnavailable) as ended:
            self._noted(url, started, f"{type(ended).__name__}: {ended}")
            raise
        self._noted(url, started, "answered")
        return answer

    def _noted(self, url: str, started: float, outcome: str) -> None:
        """Write down what one request came to and how long it took.

        The diary already carries Qt's own warnings with the thread that wrote
        them. This is the other half: a warning arriving between two of these
        lines can be read against the request it interrupted, which is what no
        amount of reasoning about the network stack could supply.
        """
        took = int((time.monotonic() - started) * MS_PER_SECOND)
        self._note(f"asked {url}: {outcome} in {took}ms")

    def _sent(self, url: str) -> QNetworkReply:
        """Put the question, without waiting for the answer."""
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"User-Agent", USER_AGENT.encode("utf-8"))
        return self._asking().get(request)

    def _waited_on(self, reply: QNetworkReply, wanted: Wanted) -> None:
        """Wait for the reply, giving it up where nobody wants it any more.

        A loop of its own rather than the thread's: this runs on a worker with
        no loop running, so one is started for exactly as long as the request
        takes. Both timers are asked on THIS thread, so nothing here touches a
        Qt object across a thread boundary.
        """
        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        giving_up = QTimer()
        giving_up.setInterval(GIVE_UP_SLICE_MS)
        giving_up.timeout.connect(lambda: None if wanted() else reply.abort())
        giving_up.start()
        QTimer.singleShot(int(self._timeout_s * MS_PER_SECOND), reply.abort)
        if not reply.isFinished():
            loop.exec()
        giving_up.stop()

    def _read(self, reply: QNetworkReply, url: str, abandoned: bool) -> object:
        """What the reply turned out to be: an answer, a refusal or a failure.

        The status is read off the reply rather than inferred from the error,
        since a service asking to be asked again arrives as a protocol error
        carrying a 429 or a 503, which is an ordinary answer to this run.

        A reply is abandoned for one of two reasons and Qt reports both the
        same way: somebody stopped wanting it; the wait ran out. Which it
        was is answered by asking whether it is still wanted, since only one
        of those two makes that False. They are different things to tell
        somebody, so they are different failures here.
        """
        try:
            status = reply.attribute(STATUS_ATTRIBUTE)
            trouble = reply.error()
            body = bytes(reply.readAll().data())
        finally:
            reply.deleteLater()
        if status in REFUSAL_CODES:
            raise RateRefused(f"{status}, saying: {_said(body)}")
        if trouble is QNetworkReply.NetworkError.OperationCanceledError:
            if abandoned:
                raise SourceFailed(f"given up on part way through: {url}")
            raise SourceTooSlow(f"no answer inside {self._timeout_s:.0f} seconds")
        if status is not None and trouble is not QNetworkReply.NetworkError.NoError:
            raise SourceFailed(f"the service answered {status}")
        if trouble is not QNetworkReply.NetworkError.NoError:
            raise SourceUnavailable(f"nothing answered at all: {trouble.name}")
        try:
            return json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as broken:
            raise SourceFailed(f"the answer could not be read: {broken}") from broken
