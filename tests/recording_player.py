"""The playback port every suite drives: one that records rather than plays.

Shared by the transport's own tests and by every window test that needs a
transport, because a real device would make a noise in a test run and a silent
one would prove nothing. It is hand written rather than a mock, so what is
asserted is the sequence of commands issued to a device that recorded them.

It sits at the top of the suite because pytest puts this directory on the
import path for every test beneath it, so each suite imports it by name.
"""

from __future__ import annotations

from stellody.domain.equalising import Equalisation
from stellody.domain.playback import (
    UNITY_VOLUME,
    OutputMode,
    OutputReport,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
)
from stellody.domain.spectrum import SILENT_BANDS
from stellody.domain.track import TrackSource


class RecordingPlayer:
    """A playback port that records rather than plays."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.loaded: list[TrackSource] = []
        self.requests: list[OutputRequest] = []
        self.state = PlaybackState.STOPPED
        self.finished = False
        self.volume = UNITY_VOLUME
        self.reported: PlaybackPosition | None = None
        self.lead = 0
        self.equalisation = Equalisation()
        # What the visualiser would read. Silent unless a test says
        # otherwise, which is what a device playing nothing reports.
        self.measured = SILENT_BANDS
        self.visualising = False
        # What the transport has lined up to follow, plus how many seams
        # this stand-in has been told it crossed. A test moves the count
        # itself, which is what the engine does on its feeder thread.
        self.lined_up: list[TrackSource | None] = []
        self.joins = True
        self.crossings = 0
        # Whether an exclusive request is granted, plus the reason given when
        # it is not. A real device refuses for reasons of its own; a
        # stand-in has to be told which answer it is giving.
        self.grants = True
        self.refusal = ""
        self._report: OutputReport | None = None

    @property
    def report(self) -> OutputReport | None:
        """What the last load answered; None before anything was loaded.

        A test that wants to see a refused mode on screen sets `grants` to
        False and reads this back, which is what a device holding the
        exclusive path does to a request for it.
        """
        return self._report

    def load(self, source: TrackSource, request: OutputRequest) -> OutputReport:
        """Record the load and report the stream this stand-in grants.

        Shared unless the test says the exclusive path is granted, which is
        the honest default: the mixer is the mode no device refuses.
        """
        self.calls.append("load")
        self.crossings = 0
        self.loaded.append(source)
        self.requests.append(request)
        self.finished = False
        self.state = PlaybackState.PAUSED
        granted = self.grants and request.mode is OutputMode.EXCLUSIVE
        self._report = OutputReport(
            request=request,
            mode=request.mode if granted else OutputMode.SHARED,
            sample_rate=request.sample_rate,
            bit_depth=request.bit_depth,
            fallback_reason="" if granted else self.refusal,
        )
        return self._report

    def queue_next(self, source: TrackSource | None) -> bool:
        """Record what was lined up to follow the loaded track."""
        self.lined_up.append(source)
        return self.joins and source is not None

    def cross(self) -> None:
        """Run into the lined-up source, as the feeder thread would."""
        self.crossings += 1

    def set_equalisation(self, equalisation) -> None:
        """Record the curve this stand-in was asked to apply."""
        self.equalisation = equalisation

    @property
    def levels(self) -> tuple[float, ...]:
        """Whatever this stand-in has been told the last block measured."""
        return self.measured

    def set_visualising(self, on: bool) -> None:
        """Record whether anything is watching, so nothing measures for nobody."""
        self.visualising = on

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

    def position(self) -> PlaybackPosition | None:
        """Whatever a test has put there; nothing by default."""
        return self.reported

    @property
    def lead_frames(self) -> int:
        """How far this stand-in claims the decode runs ahead."""
        return self.lead

    def set_volume(self, level: float) -> None:
        """Record the level asked for."""
        self.volume = level
