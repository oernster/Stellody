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
# Which of the two library views was last chosen. It outlasts a session
# exactly as the sort order and the appearance do.
SETTING_COVERS = "show_covers"
# How large a sleeve is drawn in the grid, stored as the pixel size itself.
SETTING_COVER_SIZE = "cover_size"
# The size the window was left at, plus whether it was left maximised. Both,
# because a maximised window reports the screen as its size while the size to
# come back to is the other one.
SETTING_WINDOW_WIDTH = "window_width"
SETTING_WINDOW_HEIGHT = "window_height"
SETTING_WINDOW_MAXIMISED = "window_maximised"
# Written FALSE as a scan starts and TRUE when one finishes, so a scan that was
# interrupted is known for what it is the next time the application starts.
SETTING_SCAN_FINISHED = "scan_finished"
# Whole percent, which is what the slider shows and what the tooltip says.
SETTING_VOLUME = "volume_percent"
# The three switches on the trays. Each outlasts the track it was set during,
# so each is remembered between sessions rather than starting off every time.
SETTING_MUTED = "muted"
SETTING_SHUFFLE = "shuffle"
SETTING_REPEAT = "repeat"
# The equalizer, kept as two settings rather than one: the curve
# outlives being switched off, so somebody comparing on against off
# does not lose what they set up to compare.
SETTING_EQ_GAINS = "equaliser_gains_db"
SETTING_EQ_ENABLED = "equaliser_enabled"

# The release tag a listener asked not to be told about again. The exact tag
# string, since both sides of the comparison come from the same endpoint.
SETTING_SKIPPED_UPDATE = "skipped_update_version"

TRUE = "1"
FALSE = "0"

# How long a finished message stays before the status line goes quiet again.
STATUS_TIMEOUT_MS = 6000
# How long a message about a track that would not open sits on the status
# line. Long enough to read a sentence and short enough not to be read twice.
UNPLAYABLE_MESSAGE_MS = 8000
