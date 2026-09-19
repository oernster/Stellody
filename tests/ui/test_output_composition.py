"""What the composition root hands the transport about the system's output.

Asserted over a real window built the way the application builds it, because
the pause for a moved output is three halves that each pass their own tests
while doing nothing at all unless the root joins them: the streams have to be
opened through the watcher, the watcher has to outlive the call that made it and
its signal has to reach the window.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest
from PySide6.QtCore import QEvent, QMetaMethod

from stellody.composition import build_window
from stellody.infrastructure.output_devices import OutputDevices
from stellody.infrastructure.store import SqliteLibraryStore


@pytest.fixture
def window(application):
    """The real window over a throwaway store, closed again afterwards."""
    folder = pathlib.Path(tempfile.mkdtemp())
    store = SqliteLibraryStore(str(folder / "t.sqlite3"))
    made = build_window(store)
    yield made
    made.close()
    made.deleteLater()
    application.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    store.close()


def _devices(window) -> OutputDevices:
    found = window.findChild(OutputDevices)
    assert found is not None, "the watcher is owned by the window"
    return found


def test_every_stream_is_opened_through_the_watcher(window) -> None:
    """Else a move is noticed and the next stream still opens on the old list."""
    assert window._transport._player._opener == _devices(window).open_output


def test_a_move_reaches_the_window(window) -> None:
    devices = _devices(window)
    signal = QMetaMethod.fromSignal(devices.changed)
    assert devices.isSignalConnected(signal)


@pytest.mark.parametrize(("left", "followed"), [(True, "moved"), (False, "switched")])
def test_whether_the_default_left_reaches_the_transport(
    window, left: bool, followed: str
) -> None:
    """Amendment 5: a departure pauses, an arrival carries on; both via Qt."""
    heard: list[str] = []
    transport = window._transport
    transport.output_moved = lambda: heard.append("moved") or False
    transport.output_switched = lambda: heard.append("switched") or False
    _devices(window).changed.emit(left)
    assert heard == [followed]
