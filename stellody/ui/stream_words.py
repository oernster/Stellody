"""What the open stream is, said in a line a listener can read.

The report has been built since the exclusive path was written and nothing on
screen read it, which ARCHITECTURE.md recorded as the missing half of the
feature. This is that half: one line naming the mode, the rate, the depth and
whether anything altered the samples on the way out.

**It says what was OPENED, never what was asked for.** The switch on the strip
shows the choice; this shows the answer. A device another application is
holding refuses exclusive mode; a listener who is only told what they
chose has no way to find that out. The reason the device gave is carried
through, because "exclusive refused" without it sends nobody anywhere.

No widget is touched here, so what the line says can be checked without a
screen; that is the same reason the reports themselves are built as text apart
from the dialogs that show them.
"""

from __future__ import annotations

from stellody.domain.playback import OutputMode, OutputReport

KHZ_PER_HZ = 1000
# Said of the stream rather than of the file: a shared stream is the mixer's
# own depth, whatever the file holds.
BIT_PERFECT = "bit perfect"
EXCLUSIVE = "exclusive"
SHARED = "shared"
# Why exclusive mode was not what opened, when it was asked for and refused.
REFUSED = "exclusive refused: {reason}"


def rate_text(sample_rate: int) -> str:
    """A sample rate as a listener writes one: 44.1 kHz; 48 kHz flat.

    Trailing noughts are dropped rather than printed, so the common rates read
    as the numbers people use for them instead of as 48.0 and 96.0.
    """
    khz = sample_rate / KHZ_PER_HZ
    whole = int(khz)
    if khz == whole:
        return f"{whole} kHz"
    return f"{khz:g} kHz"


def stream_text(report: OutputReport | None) -> str:
    """The open stream in one line; nothing at all while none is open."""
    if report is None:
        return ""
    parts = [
        EXCLUSIVE if report.mode is OutputMode.EXCLUSIVE else SHARED,
        rate_text(report.sample_rate),
        f"{report.bit_depth} bit",
    ]
    if report.is_bit_perfect:
        parts.append(BIT_PERFECT)
    if report.fell_back and report.fallback_reason:
        parts.append(REFUSED.format(reason=report.fallback_reason))
    return ", ".join(parts)
