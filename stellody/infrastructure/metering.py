"""What the visualiser reads: the bands of the block that has just gone out.

Lifted out of `audio.py` on 2026-09-16, when watching the device for dropouts
needed room in a module already at the edge of the danger band. The seam is a
real one: this holds whether anybody is watching and what was last measured,
while the engine holds the device and the thread writing to it.

Off until something asks to see it, so a listener who never opens the
visualiser pays nothing at all for it. The analyser being None IS the switch:
there is no flag to disagree with it.
"""

from __future__ import annotations

import numpy as np

from stellody.domain.spectrum import SILENT_BANDS
from stellody.infrastructure.analysing import BlockAnalyser


class Meter:
    """The bands of what goes out, measured only while somebody is watching."""

    def __init__(self, block_frames: int) -> None:
        self._block_frames = block_frames
        self._analyser: BlockAnalyser | None = None
        self._visualising = False
        self._levels = SILENT_BANDS

    @property
    def levels(self) -> tuple[float, ...]:
        """The bands as they were last measured; silence when nothing is on."""
        return self._levels

    def open_for(self, sample_rate: int | None) -> None:
        """Get ready for a stream at this rate; None when nothing is open.

        One analyser per stream, since its bands depend on the sample rate.
        """
        if sample_rate is None or not self._visualising:
            self._analyser = None
            return
        self._analyser = BlockAnalyser(sample_rate, self._block_frames)

    def set_visualising(self, on: bool, sample_rate: int | None) -> None:
        """Start or stop measuring what goes out.

        Stopping forgets the last measurement as well as the analyser, so a
        display turned back on opens empty rather than showing the bands of
        whatever was playing when it was last switched off.
        """
        self._visualising = on
        self.open_for(sample_rate)
        if not on:
            self._levels = SILENT_BANDS

    def measure(self, shaped: np.ndarray) -> None:
        """Read the block that has just gone out, if anybody is watching.

        Called after the write, so this can never be what delays a device.
        What is measured is the block AFTER the equalizer and BEFORE the
        volume: the equalizer is what the bands are named for, while volume
        scales every band by the same amount and so says nothing about the
        music. A display that shrank when the volume came down would report
        the knob, not the record.

        The answer is swapped in as one whole tuple. The reader is the
        interface thread and a swap is a single rebinding, so what it reads is
        either the last measurement or this one, never half of each; a lock
        here would be the feeder waiting on a painter, which is exactly what
        this must never do.
        """
        analyser = self._analyser
        if analyser is None:
            return
        measured = analyser.measure(shaped)
        if measured is not None:
            self._levels = measured
