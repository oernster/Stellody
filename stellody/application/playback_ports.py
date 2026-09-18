"""The port that turns a track source into sound.

Split out of `ports.py` when that file reached the length a module is allowed
here, along the one seam in it that has a caller set of its own: the transport,
the following and the sound settings reach this port and no other one in that
file, while nothing reading a library reaches it at all. `discovery_ports.py`
was split out on the same ground.
"""

from __future__ import annotations

from typing import Protocol

from stellody.domain.equalising import Equalisation
from stellody.domain.outputs import OutputDevice
from stellody.domain.playback import (
    OutputReport,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
)
from stellody.domain.track import TrackSource


class OutputRefused(RuntimeError):
    """A device would not open a stream at all; the message is its reason.

    Apart from a refused MODE, which opens through the mixer and is carried in
    the report: this is a device that gave nothing, another application holding
    it say, so the transport falls back to the system default (FR-O08).
    """


class PlaybackPort(Protocol):
    """Turns a track source into sound. The only thing that touches a device.

    Every method is safe to call in any state, so the application never has to
    guard a transport command with a state check.
    """

    @property
    def state(self) -> PlaybackState:
        """Where the transport is right now."""
        ...

    @property
    def report(self) -> OutputReport | None:
        """What the open stream delivers; None while nothing is loaded.

        Declared on the port rather than read off an implementation, because
        the window shows it: a listener who asked for exclusive output and got
        the mixer instead is owed the reason; this is the only thing that
        knows one was given. See `ui/stream_words.py`.
        """
        ...

    @property
    def exclusive_rates(self) -> tuple[int, ...] | None:
        """Rates the open device takes exclusively; None where unknown.

        An empty tuple is a device that will take none, which is what
        lets the window stand the switch down rather than offer a mode
        that cannot happen. None means the platform cannot be asked
        without disturbing something, so nothing is claimed.
        """
        ...

    def use_device(self, device: OutputDevice | None) -> None:
        """Open every later stream on this device; None is the system default.

        The stream already open is left alone: a device belongs to a stream
        as a mode does, so moving the music means opening it again.
        """
        ...

    def load(self, source: TrackSource, request: OutputRequest) -> OutputReport:
        """Open `source` on a device and report what was actually opened.

        Stops whatever was playing first. Raises when the source cannot be
        decoded at all; raises `OutputRefused` when the device will not open.
        A device refusing the requested mode is a fallback recorded in the
        report, not an error.
        """
        ...

    def queue_next(self, source: TrackSource | None) -> bool:
        """Line up what follows, opened before the current track needs it.

        Answers whether it can actually follow without a seam. A source the
        open device cannot carry has to wait for a new one, which is a gap
        however it is arranged, so the answer is honest rather than hopeful.
        None clears whatever was lined up.
        """
        ...

    @property
    def crossings(self) -> int:
        """How many lined-up sources the device has run into by itself.

        A count rather than a signal, so a caller that was not looking at the
        moment it happened still learns about it. It belongs to the loaded
        session, so it starts again from nothing at every load.
        """
        ...

    def play(self) -> None:
        """Start or resume. Does nothing when no source is loaded."""
        ...

    def pause(self) -> None:
        """Hold position without releasing the device."""
        ...

    def stop(self) -> None:
        """End playback and release the device."""
        ...

    def seek(self, frame: int) -> None:
        """Move to a frame offset within the loaded source, clamped to it."""
        ...

    def position(self) -> PlaybackPosition | None:
        """How far the DECODE has reached; None when nothing is loaded.

        This runs ahead of what is coming out of the speakers, by whatever is
        sitting in the buffer. Use `Transport.position` for a figure fit to
        show somebody.
        """
        ...

    @property
    def lead_frames(self) -> int:
        """How far the decode runs ahead of what is audible, in frames.

        A property of the device the port opened rather than of the track, so
        the port is the only thing that can answer it.
        """
        ...

    @property
    def finished(self) -> bool:
        """Whether the loaded source has played all the way through.

        A track reaching its end is not a state the transport is in, it is an
        event nothing was told about: the device is still open and the position
        has simply stopped moving. Something has to ask.
        """
        ...

    def set_equalisation(self, equalisation: Equalisation) -> None:
        """Shape what is heard, else leave it exactly as the file holds it.

        A flat setting must cost nothing in the signal path rather than
        little, so an implementation applies no arithmetic at all there.
        """
        ...

    def set_volume(self, level: float) -> None:
        """Set output gain, where 0.0 is silence and 1.0 is unattenuated."""
        ...

    @property
    def levels(self) -> tuple[float, ...]:
        """How loud each of the equalizer's bands was in the last block out.

        One height per band, from 0.0 to 1.0. Read by whatever is drawing
        rather than pushed to it, so an implementation is never waiting on a
        painter and a reader that falls behind misses measurements instead of
        holding up the sound.
        """
        ...

    def set_visualising(self, on: bool) -> None:
        """Start or stop measuring what goes out.

        Off must cost nothing rather than little, the same bargain the
        equalizer makes: nobody watching means no measurement taken.
        """
        ...

    def close(self) -> None:
        """Release every resource. The port is unusable afterwards."""
        ...
