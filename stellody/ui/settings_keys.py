"""The names Stellody stores its own settings under, plus the two values.

One home for them, because the window and the library loading beside it both
read and write the same settings; a key spelled twice is a setting silently
written to one place and read from another.
"""

from __future__ import annotations

SETTING_THEME = "theme"
SETTING_ROOT = "library_root"
SETTING_CLOSE = "close_action"
SETTING_DESCENDING = "sort_descending"
# Written FALSE as a scan starts and TRUE when one finishes, so a scan that was
# interrupted is known for what it is the next time the application starts.
SETTING_SCAN_FINISHED = "scan_finished"

TRUE = "1"
FALSE = "0"

# How long a finished message stays before the status line goes quiet again.
STATUS_TIMEOUT_MS = 6000
