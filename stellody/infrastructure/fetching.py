"""The one place a discovery run opens a connection.

Two catalogues are asked things during a run and neither client holds a socket:
they hand a base address and some parameters to this, then get back what was
said. That is deliberate. The offline structural test names every module able
to open a connection; a discovery that reaches two services would otherwise
have added two more names to a list whose whole value is being short.

**It also means the courtesies cannot be forgotten in one client and honoured
in the other.** The gate, the user agent and the timeout are applied here, once.

**What comes back is an answer or a typed refusal, never a stack trace from
urllib.** The service above knows what to do with each: a refusal is waited out
and asked again, an unreachable host ends the run, anything else is recorded
against that artist and the run goes on.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from stellody.application.discovering import (
    RateRefused,
    SourceFailed,
    SourceUnavailable,
)
from stellody.infrastructure.courtesy import (
    REFUSAL_CODES,
    TIMEOUT_S,
    USER_AGENT,
    Gate,
)


class Fetcher:
    """Asks one service for JSON, at the rate its terms allow.

    One fetcher stands in front of one service, because it carries that
    service's gate and a gap owed to one says nothing about another.
    """

    def __init__(self, gate: Gate | None = None, opener=None, timeout_s=TIMEOUT_S):
        self._gate = gate if gate is not None else Gate()
        self._opener = opener if opener is not None else urllib.request.urlopen
        self._timeout_s = timeout_s

    def json(self, address: str, parameters: dict[str, str]) -> object:
        """What the service said, decoded; a typed error where it said nothing.

        The parameters are encoded here rather than by the caller, so a client
        needs no networking package of its own and the structural test that
        counts those packages keeps meaning what it says.
        """
        self._gate.wait()
        url = f"{address}?{urllib.parse.urlencode(parameters)}"
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with self._opener(request, timeout=self._timeout_s) as answer:
                return json.loads(answer.read().decode("utf-8"))
        except urllib.error.HTTPError as refusal:
            if refusal.code in REFUSAL_CODES:
                raise RateRefused(f"the service asked to be asked again: {url}") from (
                    refusal
                )
            raise SourceFailed(f"the service answered {refusal.code}") from refusal
        except urllib.error.URLError as unreachable:
            raise SourceUnavailable(f"nothing answered at all: {unreachable}") from (
                unreachable
            )
        except (ValueError, OSError) as broken:
            raise SourceFailed(f"the answer could not be read: {broken}") from broken
