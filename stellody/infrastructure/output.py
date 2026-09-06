"""Which output module this machine plays through.

One question, answered in one place, so nothing else in the application has to
know there is more than one answer. Both modules behind it present the same
call and hand back the same three things, which is what lets the transport stay
ignorant of the platform it is running on.

The switch is on `sys.platform` rather than on what a device reports, because
what differs is the INTERFACE rather than the hardware: WASAPI exists on
Windows and nowhere else, so asking a Mac whether it has one is asking the
wrong question. Anything that is not Windows takes the substrate, which is the
safe direction for the rule to fail in: a platform nobody has thought about
plays through its mixer rather than not at all.
"""

from __future__ import annotations

import sys

from stellody.infrastructure import portaudio

WINDOWS = "win32"


def open_output(*args, **kwargs):
    """Open an output stream through whichever module this platform wants.

    Imported inside the call rather than at module scope, because the Windows
    module names a host API that only exists there. Importing it on a Mac
    costs nothing today and would be a trap the day it reaches for something
    Windows-only at import time.
    """
    if sys.platform == WINDOWS:
        from stellody.infrastructure import wasapi

        return wasapi.open_output(*args, **kwargs)
    return portaudio.open_output(*args, **kwargs)
