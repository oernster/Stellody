"""Reading the picture out of a video file, at the moment the sound has reached.

The sound is the clock and this follows it. Nothing here keeps time, schedules
anything or sleeps: it is asked for the picture due at a given moment and hands
back the last one that has arrived by then. That is what keeps the two streams
together without a second idea of when now is. It is why the audio path
needed no change at all to carry a video track.

Decoding runs FORWARD and only forward, because that is what playing a track
does. Frames arrive in order, each is kept until the next one is due, then the
reader walks on through them as the moment asked for advances. A moment BEHIND
the one in hand is a seek rather than a step, so the container is seeked and
the walk starts again from there; the same happens on the first read of a track
that starts part way in, which is what a cue slice does.

The picture is converted once, on the way out, into the rows of red, green and
blue every layer above can hold. PyAV is asked to do that conversion rather
than doing it here, since it is the library holding the colour arithmetic and
a second implementation of that would be a second thing to be wrong.
"""

from __future__ import annotations

from stellody.domain.picture import Picture
from stellody.domain.playback import PlaybackError
from stellody.domain.track import TrackSource

# The arrangement the domain states, named in PyAV's own vocabulary.
PICTURE_FORMAT = "rgb24"

MILLISECONDS_PER_SECOND = 1000

# How far behind the moment asked for a frame may be and still be the one to
# show. A frame is due from its own timestamp until the next arrives, so this
# is not a tolerance on lateness: it is the guard against walking the whole
# file forward when the moment jumps a long way, which is a seek wearing a
# step's clothes. A second is far longer than any frame interval and far
# shorter than a jump a listener would make.
STEP_LIMIT_MS = 1000


class PictureError(PlaybackError):
    """Raised when a file's picture cannot be opened or read at all."""


class VideoReader:
    """The picture stream of one file, walked forward as the sound advances."""

    def __init__(self, source: TrackSource) -> None:
        # Imported here rather than at module scope for the reason the packet
        # reader gives: it loads a shared FFmpeg build of some sixty megabytes,
        # which a library holding no video should never pay for.
        import av

        self._source = source
        try:
            self._container = av.open(source.path)
        except (OSError, ValueError, av.FFmpegError) as error:
            raise PictureError(f"cannot open {source.path}: {error}") from error
        streams = self._container.streams.video
        if not streams:
            self._container.close()
            raise PictureError(f"{source.path} holds no picture")
        self._stream = streams[0]
        # Frames are decoded in order out of one generator, which is restarted
        # whenever the moment asked for goes backwards.
        self._frames = self._container.decode(self._stream)
        # Both hold a PyAV video frame, which is not named in an annotation
        # here because this module may not import av until it is asked to.
        self._held = None
        self._held_ms = 0
        # A frame that has been decoded but is not due yet. It has to be held
        # somewhere: decoding is what reveals a frame's own moment, so the
        # reader cannot know it has gone too far until it has; throwing
        # that frame away would mean decoding it a second time to show it.
        self._pending = None
        self._pending_ms = 0
        self._ended = False
        self._offset_ms = self._start_ms()

    @property
    def size(self) -> tuple[int, int]:
        """The picture's width and height, as the file states them."""
        return (self._stream.codec_context.width, self._stream.codec_context.height)

    def _start_ms(self) -> int:
        """Where in the FILE this source begins, which a cue slice moves.

        A source counts its start in AUDIO frames, so the rate that converts
        them is the audio stream's and not the picture's. Taking the picture's
        was measured here as a slice starting twenty nine minutes into a three
        second file, which showed as the last frame and nothing else: 44100
        divided by 25 rather than by 44100.
        """
        if self._source.start_frame <= 0:
            return 0
        sound = self._container.streams.audio
        rate = sound[0].codec_context.rate if sound else 0
        if not rate:
            return 0
        return int(self._source.start_frame * MILLISECONDS_PER_SECOND / rate)

    def picture_at(self, elapsed_ms: int) -> Picture | None:
        """The frame showing at that moment within the track, None before one.

        `elapsed_ms` is measured from the start of the TRACK, so a cue slice
        counts from its own beginning; where in the file that falls is this
        reader's business and nobody else's.
        """
        wanted = max(0, elapsed_ms) + self._offset_ms
        if self._held is not None and self._is_a_jump(wanted):
            self._restart(wanted)
        self._walk_to(wanted)
        if self._held is None:
            return None
        return self._as_picture(self._held)

    def _is_a_jump(self, wanted_ms: int) -> bool:
        """True when the moment asked for is a seek rather than the next step.

        Two ways to be one. Going backwards is plainly a seek. Going a long way
        forwards is one wearing a step's clothes: walking there frame by frame
        would decode every picture in between and show none of them, which on a
        listener dragging the position bar means the picture stops until the
        file catches up.
        """
        behind = wanted_ms < self._held_ms
        far_ahead = wanted_ms - self._held_ms > STEP_LIMIT_MS
        return behind or far_ahead

    def _walk_to(self, wanted_ms: int) -> None:
        """Take frames until the one in hand is the one due at that moment.

        A frame shows from its own moment until the next one's, so the one to
        show is the LAST whose moment has passed. Reading one frame too far is
        how that is discovered; the frame read too far is the next to show, so
        it waits rather than being taken as the answer.
        """
        while True:
            if self._pending is not None:
                if self._pending_ms > wanted_ms:
                    return
                self._held, self._held_ms = self._pending, self._pending_ms
                self._pending = None
                continue
            if self._ended:
                return
            arrived = self._next_frame()
            if arrived is None:
                return
            when = self._moment_of(arrived)
            if self._held is not None and when > wanted_ms:
                self._pending, self._pending_ms = arrived, when
                return
            self._held, self._held_ms = arrived, when

    def _next_frame(self):
        """The next decoded frame, None once the stream has run out."""
        try:
            return next(self._frames)
        except StopIteration:
            self._ended = True
            return None

    def _moment_of(self, frame) -> int:
        """When a frame is due, in milliseconds from the start of the file."""
        if frame.pts is None or frame.time_base is None:
            return self._held_ms
        return int(frame.pts * frame.time_base * MILLISECONDS_PER_SECOND)

    def _restart(self, wanted_ms: int) -> None:
        """Seek the container and decode forward again from there."""
        target = max(0, wanted_ms)
        stamp = int(target / MILLISECONDS_PER_SECOND / self._stream.time_base)
        try:
            self._container.seek(stamp, stream=self._stream)
        except (OSError, ValueError):  # pragma: no cover
            # A container that will not seek is still worth showing forward
            # from wherever it is, rather than losing the picture entirely.
            pass
        self._frames = self._container.decode(self._stream)
        self._held = None
        self._held_ms = 0
        self._pending = None
        self._pending_ms = 0
        self._ended = False

    @staticmethod
    def _as_picture(frame) -> Picture:
        """One frame in the terms the layers above hold pictures in."""
        converted = frame.to_ndarray(format=PICTURE_FORMAT)
        height, width = converted.shape[0], converted.shape[1]
        return Picture(width=width, height=height, data=converted.tobytes())

    def close(self) -> None:
        """Give the file back."""
        self._held = None
        self._container.close()
