"""The guide's account of keeping a backup. BACKUP.md.

Its own module for the reason the discovery procedure is: it is one errand
told start to finish, which the guide's account of the window should not have
to be read around. The two commands are named by the labels the File menu
itself wears, never by a copy typed here.
"""

from __future__ import annotations

from stellody.shared.version import APP_NAME
from stellody.ui.backup_words import BACK_UP_LABEL, RESTORE_LABEL, spoken


def backups_html() -> str:
    """Backing up then restoring, as somebody would do it."""
    back_up = spoken(BACK_UP_LABEL)
    restore = spoken(RESTORE_LABEL)
    return (
        "<h3>Keeping a backup</h3>"
        f"<p><b>{back_up}</b> on the File menu writes one zip into a folder "
        "you choose: Downloads the first time, then wherever the last one "
        f"went. It holds everything {APP_NAME} knows about your library: "
        "ratings, play counts, corrections, stated tags, settings, taste "
        "profiles, the last discovery answer and the shop list. It does not "
        "hold the music, which is yours to copy. A backup never replaces one "
        "already in the folder; each is named for the minute it was made.</p>"
        f"<p><b>{restore}</b> checks the zip before asking you anything, "
        "then asks before it replaces your library. It saves a backup of the "
        f"library as it is first, beside your others, then starts {APP_NAME} "
        "again to put the restored one in place. Should that go wrong part "
        "way, the library you had is put back.</p>"
        "<p>A backup made by an older version always restores; whatever has "
        "changed since is brought up to date as it goes in. One made by a "
        "newer version is refused with the reason, since this version cannot "
        "know what the newer one changed. Restored on another computer whose "
        f"music sits elsewhere, {APP_NAME} says so and offers to choose the "
        "music folder.</p>"
    )
