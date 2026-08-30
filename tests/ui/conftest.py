"""One QApplication for the suite; no window outliving the test that made it.

Closing a window is not destroying it. A window left for the garbage collector
is destroyed at whatever moment Python next collects it, which is typically
inside the NEXT test: measured as an access violation in setStyleSheet, which
repaints every widget the application knows about and walked into a half
destroyed one. Five runs in six.

So every top level widget is destroyed here, deterministically, between tests.
Qt is never mocked; this only makes its lifetimes match the tests'.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from stellody.domain.playback import (
    UNITY_VOLUME,
    OutputMode,
    OutputReport,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
)
from stellody.domain.track import TrackSource


class RecordingPlayer:
    """A playback port that records rather than plays.

    Shared by every window test that needs a transport, because a real device
    would make a noise in a test run and a silent one would prove nothing.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.loaded: list[TrackSource] = []
        self.state = PlaybackState.STOPPED
        self.finished = False
        self.volume = UNITY_VOLUME
        self.reported: PlaybackPosition | None = None
        self.lead = 0

    def load(self, source: TrackSource, request: OutputRequest) -> OutputReport:
        """Record the load and report a plain shared stream."""
        self.calls.append("load")
        self.loaded.append(source)
        self.finished = False
        self.state = PlaybackState.PAUSED
        return OutputReport(
            request=request,
            mode=OutputMode.SHARED,
            sample_rate=request.sample_rate,
            bit_depth=request.bit_depth,
        )

    def play(self) -> None:
        """Record the play."""
        self.calls.append("play")
        self.state = PlaybackState.PLAYING

    def pause(self) -> None:
        """Record the pause."""
        self.calls.append("pause")
        self.state = PlaybackState.PAUSED

    def stop(self) -> None:
        """Record the stop."""
        self.calls.append("stop")
        self.state = PlaybackState.STOPPED

    def seek(self, frame: int) -> None:
        """Record the seek."""
        self.calls.append(f"seek {frame}")

    def position(self):
        """Whatever a test has put there; nothing by default."""
        return self.reported

    @property
    def lead_frames(self) -> int:
        """How far this stand-in claims the decode runs ahead."""
        return self.lead

    def set_volume(self, level: float) -> None:
        """Record the level asked for."""
        self.volume = level


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication for the whole session."""
    existing = QApplication.instance()
    return existing or QApplication([])


@pytest.fixture(autouse=True)
def _no_window_outlives_its_test(application: QApplication):
    """Destroy anything left on screen once a test is done with it."""
    yield
    for widget in list(application.topLevelWidgets()):
        widget.close()
        widget.deleteLater()
    application.processEvents()
    application.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()
