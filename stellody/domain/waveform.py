"""The shape of a track: how loud it is, all the way along.

A bar filling up says how far through a track playback is. A waveform says
that AND what is coming: where the quiet passage is, where the piece opens
out, whether the thing about to arrive is a drum or a breath. That is the
point of drawing it rather than a groove.

The shape covers a whole FILE rather than a track, because a cue-sheet album
is one file holding many tracks and measuring it once serves all of them. A
track then takes the part of it that belongs to that track, which is why
`between` exists.

A bucket holds how LOUD that stretch of the file is, as the root mean square
of its samples, on a scale where 1.0 is full scale. It held the loudest single
sample once; that was measured to be no shape at all. A bucket is a file
divided by two thousand, some 120 milliseconds, so the loudest sample in any
120 milliseconds carrying a drum or a sustained note sits within a few percent
of the whole track's peak. Measured over three unlike records, a peak envelope
drawn against its own loudest point put more than half of every track at 90
percent of full height and about 40 percent of it at 99. That is a clipping
detector rather than a waveform; it says the same thing about a gentle 1998
record as about a loud remaster.

Loudness answers what the drawing is for: where the quiet passage is and where
the piece opens out. The same three records measure to a median of 0.47 to 0.68
of their own loudest bucket, with a tenth of one percent of buckets at the top.
A transient still survives the drawing, because a column covering several
buckets takes the loudest of them rather than averaging again.
"""

from __future__ import annotations

from dataclasses import dataclass

# How many buckets a whole file is measured into. Wide enough that a window
# stretched across a large display still has more than one bucket per column,
# small enough that the measurement of a long file stays a few kilobytes.
BUCKETS = 2000

FULL_SCALE = 1.0
SILENCE = 0.0


@dataclass(frozen=True, slots=True)
class Envelope:
    """How loud each bucket of a source is, in order."""

    levels: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.levels:
            raise ValueError("an envelope needs at least one bucket")
        for level in self.levels:
            if level < SILENCE or level > FULL_SCALE:
                raise ValueError("a level sits between silence and full scale")

    @property
    def buckets(self) -> int:
        """How many buckets this envelope holds."""
        return len(self.levels)

    @property
    def loudest(self) -> float:
        """The loudest bucket in it; silence when the source is silent."""
        return max(self.levels)

    def between(self, first: int, last: int, of: int) -> Envelope:
        """The part of this envelope covering frames `first` to `last` of `of`.

        A cue-sheet track is a region of a file that has been measured whole,
        so this is how one track takes its own share of that measurement. The
        region is clamped to the envelope; a region that lands inside a
        single bucket still yields that bucket rather than nothing: a track
        too short to fill one has a shape, even if it is a coarse one.
        """
        if of <= 0:
            raise ValueError("a source covering no frames has no shape")
        start = self._bucket_at(first, of)
        end = self._bucket_at(last, of)
        if end <= start:
            end = start + 1
        return Envelope(levels=self.levels[start:end])

    def _bucket_at(self, frame: int, of: int) -> int:
        """Which bucket a frame falls in, clamped to this envelope."""
        placed = max(0, frame) * self.buckets // of
        return min(self.buckets, placed)

    def scaled_to(self, columns: int) -> tuple[float, ...]:
        """This envelope in exactly `columns` values, for drawing.

        Each column takes the loudest bucket it covers, so a loud moment
        survives being squeezed into a narrower window rather than being
        averaged a second time. Where there are more columns than buckets the shape is
        stretched, which is honest: it says the measurement is coarser than
        the drawing; it invents nothing between the points it has.
        """
        if columns <= 0:
            raise ValueError("a drawing needs at least one column")
        drawn = []
        for column in range(columns):
            first = column * self.buckets // columns
            last = max(first + 1, (column + 1) * self.buckets // columns)
            drawn.append(max(self.levels[first:last]))
        return tuple(drawn)


def envelope_from(levels: tuple[float, ...]) -> Envelope:
    """An envelope from measured levels, with anything over full scale clipped.

    A file whose samples exceed full scale is not unusual: an intersample peak
    or a lossy codec can both produce one. That is a fact about the audio and
    not an error, so it is flattened to the top of the scale rather than
    refused.
    """
    return Envelope(
        levels=tuple(min(FULL_SCALE, max(SILENCE, level)) for level in levels)
    )
