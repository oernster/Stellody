"""The launch focus holder stays a plain widget whatever dialogs are built.

Measured on 2026-10-12 on Windows: building the Discover dialog made the zero-size
holder native; Windows gave its window 160 by 160 over the start of the menu
bar, so every press on File, Edit or View went to it. Reproduced offscreen the
same day: the holder turns native as the dialog is built, unless the
application keeps native siblings plain (`native_windows.py`).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget
from recording_player import RecordingPlayer
from tray_support import RememberingStore, build


def test_building_a_dialog_leaves_the_holder_plain(application: QApplication) -> None:
    made = build(RememberingStore(), RecordingPlayer())
    made.show()
    holder = made.findChild(QWidget, "NeutralStart")
    made.warm_discovery()
    application.processEvents()
    assert not holder.testAttribute(Qt.WidgetAttribute.WA_NativeWindow)
    made.close()


def test_the_application_keeps_native_siblings_plain(application) -> None:
    assert application.testAttribute(
        Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings
    )
