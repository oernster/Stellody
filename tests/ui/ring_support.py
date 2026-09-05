"""What the two ring suites share: the real window and the sheet reader.

Held apart from either so both read the same window. A ring check that built
its own would be checking a window nobody uses.
"""

from __future__ import annotations

import pathlib
import re
import tempfile

from stellody.composition import build_window
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.ui.settings_keys import SETTING_ROOT

RING_RULE = re.compile(r"([^{}]*):(?:focus|hover)[^{}]*\{([^{}]*)\}")
COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
# Long enough for a walk of the ring to come back round to where it started.
RING_WALK = 40


def build_ring_window(application):
    """The real main window over a throwaway store, pointed at a folder.

    The folder is named rather than left empty because Rescan is offered only
    where there is somewhere to rescan, so a window that has never been pointed
    anywhere drops that control out of the ring entirely. The order it shows is
    what a settled installation shows, which is the one worth pinning. Nothing
    reads the folder: launch shows what the store already holds and never
    scans, so an empty temporary directory is enough to say one was chosen.
    """
    folder = pathlib.Path(tempfile.mkdtemp())
    store = SqliteLibraryStore(str(folder / "t.sqlite3"))
    store.set_setting(SETTING_ROOT, str(folder))
    made = build_window(store)
    made.show()
    application.processEvents()
    yield made
    made.close()
    store.close()


def ring_rules(sheet: str) -> list[tuple[str, str]]:
    """Every selector whose focus or hover block paints a visible border.

    Comments are stripped first: a comment explaining why a class gets NO rule
    names that class; scanning it would report the explanation as the fault.
    """
    found = []
    for selector, block in RING_RULE.findall(COMMENT.sub("", sheet)):
        if "border" in block or "outline" in block:
            found.append((selector.strip(), block))
    return found
