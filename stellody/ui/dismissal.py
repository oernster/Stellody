"""Where the press that closed a popup landed, so a button can tell a
replayed click from a fresh one.

Windows replays the press that dismisses a popup to whatever sits under the
cursor. A press on the button that opened one therefore closes it and then
immediately reopens it, which reads as a control that will not go away.
Measured for the volume slider on 2026-09-19. Oliver then reported the list of
output devices behaving the same way; measured for that list on 2026-09-20.

One home for it rather than a copy in each popup: two popups meet the same
platform behaviour, so they answer it with the same knowledge. Windows is the
only platform that replays; on one that does not, the record is read by the
next press instead, which then puts the popup up on the press after it.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget


class Dismissal:
    """The press that last closed a popup, kept until it is asked about."""

    def __init__(self) -> None:
        # In screen coordinates, since the popup it closed is gone by then.
        self._where: QPoint | None = None

    def forget(self) -> None:
        """Nothing closed this popup, so no press is owed an answer."""
        self._where = None

    def note(self, popup: QWidget, event: QMouseEvent) -> None:
        """Keep where a press landed, when it landed outside the popup.

        A press inside is the listener using the control rather than leaving
        it, so it closes nothing and there is nothing to remember.
        """
        inside = popup.rect().contains(event.position().toPoint())
        self._where = None if inside else event.globalPosition().toPoint()

    def dismissed_by(self, button: QWidget) -> bool:
        """Whether the press that closed the popup landed on that button.

        Reading forgets, so one press is answered once and never twice.
        """
        where = self._where
        self._where = None
        if where is None:
            return False
        return button.rect().contains(button.mapFromGlobal(where))
