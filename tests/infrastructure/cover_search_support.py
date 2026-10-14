"""Canned MusicBrainz and Cover Art Archive answers, plus the fakes they go in.

The JSON below is not invented. It is the shape those two services actually
answered with on 2026-08-30, cut down to the fields this client reads. A test
written against a remembered API is a test of the memory.

No connection is opened by anything here. The opener is handed in, which is
also how the gate is: waiting a real second between requests would make the
suite a minute longer for nothing.
"""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO

from stellody.infrastructure.cover_search import ArchiveCovers

MBID = "69249908-12ef-4eae-be48-46acf1354837"
ART = f"https://coverartarchive.org/release/{MBID}"
SEARCH_HOST = "https://musicbrainz.org"
LISTING_HOST = "https://coverartarchive.org/release/"

SEARCH_ANSWER = {
    "count": 8,
    "releases": [
        {
            "id": MBID,
            "title": "Ether Song",
            "date": "2003-11-17",
            "country": "GB",
            "track-count": 15,
        }
    ],
}

LISTING_ANSWER = {
    "images": [
        {
            "approved": True,
            "back": False,
            "front": True,
            "id": "38850137623",
            "image": f"{ART}/38850137623.jpg",
            "thumbnails": {
                "250": f"{ART}/38850137623-250.jpg",
                "500": f"{ART}/38850137623-500.jpg",
                "1200": f"{ART}/38850137623-1200.jpg",
                "large": f"{ART}/38850137623-500.jpg",
                "small": f"{ART}/38850137623-250.jpg",
            },
            "types": ["Front"],
        },
        {
            "back": True,
            "front": False,
            "id": "38850137624",
            "image": f"{ART}/38850137624.jpg",
            "thumbnails": {"250": f"{ART}/38850137624-250.jpg"},
            "types": ["Back"],
        },
    ]
}


class NoWait:
    """A gate that lets everything through, so the suite does not wait."""

    def __init__(self) -> None:
        self.waits = 0

    def wait(self, wanted=lambda: True) -> bool:
        """Count the request and let it go, unless nobody wants it."""
        self.waits += 1
        return wanted()


class Answering:
    """An opener answering canned bytes, remembering what it was asked."""

    def __init__(self, answers: dict) -> None:
        self.answers = answers
        self.asked: list[str] = []
        self.headers: list[dict] = []

    def __call__(self, request, timeout=None):
        """Answer this request; raise the error it was told to raise."""
        self.asked.append(request.full_url)
        self.headers.append(dict(request.header_items()))
        for prefix, answer in self.answers.items():
            if request.full_url.startswith(prefix):
                if isinstance(answer, Exception):
                    raise answer
                return BytesIO(answer)
        raise urllib.error.HTTPError(request.full_url, 404, "NOT FOUND", {}, None)


def encoded(value: dict) -> bytes:
    """One canned JSON answer as bytes."""
    return json.dumps(value).encode("utf-8")


class Pauses:
    """The backoff, recorded rather than waited through."""

    def __init__(self) -> None:
        self.slept: list[float] = []

    def hold(self, seconds: float, wanted=lambda: True) -> bool:
        """Note the whole pause and return at once.

        The gap asked for rather than the slices the real waiter takes it in:
        what the terms ask for is the thing worth pinning.
        """
        self.slept.append(seconds)
        return wanted()


def client(answers: dict) -> tuple[ArchiveCovers, Answering, NoWait]:
    """A client over a canned opener and a gate that never waits."""
    opener = Answering(answers)
    gate = NoWait()
    return ArchiveCovers(gate=gate, opener=opener, waiter=Pauses()), opener, gate


BOTH = {
    SEARCH_HOST: encoded(SEARCH_ANSWER),
    LISTING_HOST: encoded(LISTING_ANSWER),
}


class Refusing:
    """An opener refusing a set number of times before it answers."""

    def __init__(self, refusals: int, answers: dict, code: int = 503) -> None:
        self.refusals = refusals
        self.answers = answers
        self.code = code
        self.asked = 0

    def __call__(self, request, timeout=None):
        """Refuse while there are refusals left, then answer normally."""
        self.asked += 1
        if self.refusals > 0:
            self.refusals -= 1
            raise urllib.error.HTTPError(
                request.full_url, self.code, "SERVICE UNAVAILABLE", {}, None
            )
        for prefix, answer in self.answers.items():
            if request.full_url.startswith(prefix):
                return BytesIO(answer)
        raise urllib.error.HTTPError(request.full_url, 404, "NOT FOUND", {}, None)


class Scripted:
    """An opener answering each address from a script, one entry per ask.

    The last entry repeats, so a script of one failure fails every time. An
    address in no script answers 404, as the archive does for a release with
    no art.
    """

    def __init__(self, script: dict) -> None:
        self.script = {prefix: list(outcomes) for prefix, outcomes in script.items()}
        self.asked: list[str] = []

    def __call__(self, request, timeout=None):
        """Answer the next entry for this address; raise it if it is an error."""
        self.asked.append(request.full_url)
        for prefix, outcomes in self.script.items():
            if request.full_url.startswith(prefix):
                outcome = outcomes.pop(0) if len(outcomes) > 1 else outcomes[0]
                if isinstance(outcome, Exception):
                    raise outcome
                return BytesIO(outcome)
        raise urllib.error.HTTPError(request.full_url, 404, "NOT FOUND", {}, None)


def scripted(script: dict) -> tuple[ArchiveCovers, Scripted, Pauses]:
    """A client over a scripted opener, recording the pauses it takes."""
    opener = Scripted(script)
    pauses = Pauses()
    return ArchiveCovers(gate=NoWait(), opener=opener, waiter=pauses), opener, pauses


def server_error(url: str) -> urllib.error.HTTPError:
    """What the archive's store answered for 9 of 11 misses on 2026-10-14."""
    return urllib.error.HTTPError(url, 500, "INTERNAL SERVER ERROR", {}, None)


def refused_client(refusals: int, code: int = 503):
    """A client whose search host refuses that many times first."""
    opener = Refusing(refusals, BOTH, code)
    pauses = Pauses()
    return ArchiveCovers(gate=NoWait(), opener=opener, waiter=pauses), opener, pauses
