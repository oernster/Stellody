"""Getting a track's shape, from a measurement made once per file.

Measuring means decoding the whole file, which is far too slow to do while
somebody waits: a track has to start playing now, not once its picture is
ready. So this is deliberately two answers rather than one. `remembered` is
instant and may be nothing; `measured` is slow and always something. The
interface asks for the first, draws it if it is there and puts the second on
a thread.

The measurement is kept against the FILE. A cue-sheet album is one file
holding many tracks, so measuring it once serves all of them and the second
track of such an album has its shape before it is played.
"""

from __future__ import annotations

from stellody.application.ports import CancelledCheck, WaveformPort
from stellody.domain.track import TrackSource
from stellody.domain.waveform import Envelope


class TrackShapes:
    """A track's share of the shape of the file it lives in."""

    def __init__(self, waveforms: WaveformPort) -> None:
        self._waveforms = waveforms

    def remembered(self, source: TrackSource) -> Envelope | None:
        """This track's shape if the file has been measured; None otherwise.

        Never decodes, so it is safe to ask on the interface thread.
        """
        return self._share(source, self._waveforms.remembered(source.path))

    def measured(
        self, source: TrackSource, cancelled: CancelledCheck | None = None
    ) -> Envelope | None:
        """This track's shape, measuring the file if that has not been done.

        Slow: it decodes the file. It belongs off the interface thread. None
        when the file cannot be measured at all, which is not worth reporting
        to somebody who only wanted a picture; the track still plays.

        A measurement nobody is waiting for any more can be given up on. The
        highlight moving on is exactly that: measured, a whole album FLAC takes
        22 seconds to decode, so carrying on with one that has been passed over
        costs a core for no picture anybody will see.
        """
        return self._share(source, self._waveforms.measure(source.path, cancelled))

    def _share(self, source: TrackSource, whole: Envelope | None) -> Envelope | None:
        """The part of a file's shape belonging to one track in it."""
        if whole is None:
            return None
        frames = self._waveforms.frames_in(source.path)
        if frames is None or frames <= 0:
            return None
        if not source.is_slice:
            return whole
        last = source.end_frame if source.end_frame is not None else frames
        return whole.between(source.start_frame, last, frames)
