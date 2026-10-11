"""The discovery dialog is built once, unseen, as the application opens.

Measured on 2026-10-11 in a real session: the first dialog of a session took
246 ms to build against 35 ms after, enough to starve the sound device on the
first press of Discover. What is held here is that building it ahead shows
nothing and leaves nothing behind.
"""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer
from tray_support import RememberingStore, build

from stellody.ui.discovery_dialog import DiscoveryDialog


def _dialogs(window) -> list[DiscoveryDialog]:
    return window.findChildren(DiscoveryDialog)


def test_building_ahead_shows_nothing_and_leaves_nothing(
    application: QApplication,
) -> None:
    made = build(RememberingStore(), RecordingPlayer())
    made.warm_discovery()
    assert not any(dialog.isVisible() for dialog in _dialogs(made))
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert _dialogs(made) == []
    assert made._discovery_dialog is None
    made.close()
