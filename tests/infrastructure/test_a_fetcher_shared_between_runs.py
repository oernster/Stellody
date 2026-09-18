"""One fetcher asked from an abandoned run's thread and then from the next run's.

A discovery is built once, so every run asks through the same two fetchers. A
stopped run is abandoned rather than waited for, so the next run can be asking
before the old thread has ended. Each thread was given a manager of its own,
held in ONE place: whichever thread asked last owned it, whichever thread
ended last let go of it.

Measured on 2026-09-14 with the real runner against loopback services, four
tries of each; a fetcher per run as the control came through every time:

- The old run ending while the new run waited on a reply let go of the NEW
  run's manager. Three tries in four the process died with an access
  violation inside `_read`; the fourth lost that request to a reply already
  deleted.
- The new run asking while the old run's request was in flight replaced the
  OLD run's manager, deleting its reply under it. The old thread never ended,
  both tries.

Run in a fresh process, since the failure being guarded against takes the
process with it. The waiting there processes events as the running
application's loop does: what lets go of a manager when its thread ends is
delivered through that loop, so a wait that blocks it hides the fault. Measured
the same day, three tries in three with the loop turning and two clean tries in
two with it blocked.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

# Enough asks that the second run is still asking when the first run ends.
ASKS = 3
# Long enough that a reply is plainly in flight when the first run ends.
DELAY_S = 0.5
# How long either run may take to end once nothing should be holding it.
THREAD_LIMIT_MS = 10000
# How long the whole fresh process may take before it counts as hung.
PROCESS_LIMIT_S = 60

TWO_RUNS = """
import json
import os
import sys
import threading
import time

from PySide6.QtCore import QCoreApplication, QThread

from stellody.infrastructure.fetching import Fetcher
from tests.infrastructure.fetching_support import OpenGate, Service

MODE, ASKS = sys.argv[1], int(sys.argv[2])
DELAY_S, LIMIT_MS = float(sys.argv[3]), int(sys.argv[4])
SLICE_S = 0.01


def asked(service):
    end = time.monotonic() + LIMIT_MS / 1000
    while not service.asked and time.monotonic() < end:
        time.sleep(SLICE_S)


def ended(thread):
    end = time.monotonic() + LIMIT_MS / 1000
    while not thread.isFinished() and time.monotonic() < end:
        application.processEvents()
        time.sleep(SLICE_S)
    return thread.isFinished()


class First(QThread):
    def __init__(self, fetcher, address):
        super().__init__()
        self.fetcher, self.address = fetcher, address
        self.released = threading.Event()
        self.outcome = ""

    def run(self):
        try:
            wanted = lambda: not self.released.is_set()
            self.fetcher.json(self.address, {}, wanted=wanted)
            self.outcome = "answered"
            self.released.wait()
        except Exception as trouble:
            self.outcome = type(trouble).__name__


class Second(QThread):
    def __init__(self, fetcher, address):
        super().__init__()
        self.fetcher, self.address = fetcher, address
        self.results = []

    def run(self):
        for _ in range(ASKS):
            try:
                self.fetcher.json(self.address, {})
                self.results.append("answered")
            except Exception as trouble:
                self.results.append(f"{type(trouble).__name__}: {trouble}")


application = QCoreApplication([])
hangs = MODE == "in flight"
first_service = Service(hangs=True) if hangs else Service(body={"ok": True})
slow = Service(body={"ok": True}, delay_s=DELAY_S)
fetcher = Fetcher(gate=OpenGate(), note=lambda line: None)
first = First(fetcher, first_service.address)
second = Second(fetcher, slow.address)
first.start()
asked(first_service)
second.start()
asked(slow)
first.released.set()
report = {"first_ended": ended(first), "first": first.outcome}
report.update(second_ended=ended(second), second=second.results)
print(json.dumps(report))
sys.stdout.flush()
os._exit(0)
"""


@pytest.mark.parametrize("mode", ["in flight", "between requests"])
def test_two_runs_through_one_fetcher_each_keep_their_own_manager(
    tmp_path: pathlib.Path, mode: str
) -> None:
    """Both runs end; every request the second run makes is answered."""
    script = tmp_path / "two_runs.py"
    script.write_text(TWO_RUNS, encoding="utf-8")
    # The package and the tests are named on the path rather than assumed to
    # be found, since a script runs from its own directory.
    root = pathlib.Path(__file__).resolve().parents[2]
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH=str(root))
    finished = subprocess.run(
        [sys.executable, str(script), mode, str(ASKS), str(DELAY_S)]
        + [str(THREAD_LIMIT_MS)],
        capture_output=True,
        text=True,
        cwd=str(root),
        env=environment,
        timeout=PROCESS_LIMIT_S,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr
    report = json.loads(finished.stdout.strip().splitlines()[-1])
    assert report["first_ended"], f"the first run never ended: {report}"
    assert report["second_ended"], f"the second run never ended: {report}"
    assert report["second"] == ["answered"] * ASKS, report
