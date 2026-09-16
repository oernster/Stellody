"""How much sound is handed over at once; how much the device keeps queued.

One home for both, because the engine writes the blocks and the output modules
open the streams they go into. The two numbers only make sense together.

**The device keeps two blocks queued, not what the host would choose.** Left to
choose, a shared WASAPI stream on Oliver's Realtek output opened a 23 ms buffer
(1036 frames). Measured on 2026-09-16 through `dropouts.py`, with a Nuitka build
holding every core: 32 dropouts in 16 seconds of static, 30 of them silences of
4 to 46 ms inside a write, with 0 ms spent reading and 0 ms shaping. The feeder
was simply woken late, by tens of milliseconds; 23 ms could not cover it.

Asked for two blocks, the same device opened 8633 frames (195 ms). Writes still
took a steady 93 ms and stopping still took 0 ms; the buffer sat about 184 ms
full while writes kept up, so a wake that late is absorbed rather than heard.

The cost is that sound reaches the speakers later after it is decoded, which is
why `WasapiPlayback.lead_frames` counts the stream's own buffer: the position,
the visualiser and a video are all put back by that much.
"""

from __future__ import annotations

BLOCK_FRAMES = 4096
BUFFER_BLOCKS = 2


def buffer_seconds(sample_rate: int) -> float:
    """How long the device's queue is asked to be, at this rate."""
    return BUFFER_BLOCKS * BLOCK_FRAMES / sample_rate
