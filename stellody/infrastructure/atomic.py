"""Replacing a file's contents without ever leaving half of one behind.

Written beside the target and moved over it, so a half-written file never
exists under the name anything reads and a failed write leaves the last good
copy intact.

Its own module because two files now need it: the discovery answer and the
shop list. One implementation rather than two, since a temporary suffix that
drifted between them would be two conventions to clean up after.
"""

from __future__ import annotations

import json
import os
import pathlib

# Written beside the file it replaces, so the move is on one filesystem and
# cannot half happen.
PENDING_SUFFIX = ".writing"
INDENT = 2


def written(where: pathlib.Path, content: object) -> None:
    """Put this where that is, atomically, else leave what is there alone."""
    pending = where.with_suffix(where.suffix + PENDING_SUFFIX)
    pending.write_text(
        json.dumps(content, indent=INDENT, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(pending, where)
