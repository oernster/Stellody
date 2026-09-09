"""A real service on the loopback address, for testing the one module with a socket.

A real server rather than a stand-in for one. The fetcher is a thin arrangement
of Qt's network stack: what is worth asserting is what Qt makes of a status, a
body and a silence, so a fake reply would only be a test of the fake. Qt is
never mocked here for the same reason it is never mocked anywhere else.

Nothing leaves the machine. The server binds the loopback address on a port the
system picks, so two of these can run at once and neither can collide with
anything a developer happens to have listening.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOOPBACK = "127.0.0.1"
# The system picks the port, so nothing here can collide with anything else.
ANY_PORT = 0
# How long a deliberately silent request is held before the server gives up on
# it too. Long enough that a test watching a request be abandoned always wins
# the race, short enough that a suite cannot hang on one.
HANG_LIMIT_S = 10.0
# How long to wait for the serving thread to notice it has been shut down.
CLOSE_LIMIT_S = 5.0
OK = 200


class Service:
    """An HTTP service answering exactly as it was told to, once per ask.

    It records what it was asked for and who said they were asking, which is
    how the courtesies applied in one place are shown to have been applied.
    """

    def __init__(
        self,
        body: object = None,
        status: int = OK,
        text: str | None = None,
        delay_s: float = 0.0,
        hangs: bool = False,
        keeps_alive: bool = False,
    ) -> None:
        self.asked: list[str] = []
        self.agents: list[str] = []
        # How many connections are open right now. Only a service holding one
        # open has anything for a client to leave behind, so this is what a
        # test about closing them reads. Counted under a lock, since the
        # server answers each connection on a thread of its own.
        self.open_connections = 0
        # How many have been opened altogether, which is what a test about a
        # connection being reused reads: the count above returns to zero
        # whether the socket was reused or replaced.
        self.connections = 0
        self._counting = threading.Lock()
        self._released = threading.Event()
        service = self

        class Handler(BaseHTTPRequestHandler):
            """One ask, answered the way this service was configured."""

            # HTTP/1.0 closes every connection, which is the quiet default and
            # what almost every test here wants. A service asked to keep one
            # alive answers as a real one does, so a client that leaves an
            # idle socket behind can be seen doing it.
            protocol_version = "HTTP/1.1" if keeps_alive else "HTTP/1.0"

            def setup(self) -> None:
                """Count this connection in."""
                super().setup()
                with service._counting:
                    service.open_connections += 1
                    service.connections += 1

            def finish(self) -> None:
                """Count it out again, however it ended."""
                with service._counting:
                    service.open_connections -= 1
                super().finish()

            def do_GET(self) -> None:
                """Record the ask, then answer it or deliberately do not."""
                service.asked.append(self.path)
                service.agents.append(self.headers.get("User-Agent", ""))
                if hangs:
                    service._released.wait(HANG_LIMIT_S)
                    return
                if delay_s:
                    time.sleep(delay_s)
                said = text if text is not None else json.dumps(body)
                spoken = said.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(spoken)))
                self.end_headers()
                self.wfile.write(spoken)

            def log_message(self, format: str, *arguments: object) -> None:
                """Say nothing. A test run is not a web server log."""

            def log_error(self, format: str, *arguments: object) -> None:
                """Say nothing here either, since an abandoned ask is the point."""

        self._server = ThreadingHTTPServer((LOOPBACK, ANY_PORT), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def address(self) -> str:
        """Where to ask it something."""
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}/ask"

    def close(self) -> None:
        """Let go of everything, releasing a held request first."""
        self._released.set()
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(CLOSE_LIMIT_S)


def nowhere() -> str:
    """An address on this machine with nothing listening behind it.

    Port 9 is the discard service, which no ordinary machine runs, so a
    connection there is refused rather than answered or left hanging.
    """
    return f"http://{LOOPBACK}:9/ask"


class Noting:
    """Somewhere for a fetcher to write down what a request came to.

    Here rather than in one suite, since both the suite about the fetcher and
    the suite about the notes hand one in; a recorder written twice is two
    recorders the day one of them is changed.
    """

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, line: str) -> None:
        """Keep the line, in the order it was written."""
        self.lines.append(line)
