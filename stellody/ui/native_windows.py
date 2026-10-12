"""Keep one native window from turning its siblings native.

Every dialog makes its native window as it is built (`FirstStopDialog`); Qt's
default then makes that window's siblings native too. Measured on
2026-10-12 on Windows: building the Discover dialog, at launch or on a press,
gave the window's zero-size focus holder a native window of its own, which
Windows sized 160 by 160 over the start of the menu bar. Every press on File,
Edit or View then went to the holder, so the menus could not be opened.
Reproduced offscreen the same day: one Discover dialog built, the holder is
native; with this attribute set, it is not.

Must run before the application is built: Qt reads application attributes then.
"""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, Qt


def keep_siblings_plain() -> None:
    """Stop a native widget making its siblings native. Before the application."""
    QCoreApplication.setAttribute(
        Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings
    )
